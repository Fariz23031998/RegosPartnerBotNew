"""
Authentication endpoints and helpers for Telegram Web App.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from database import get_db
from database.repositories import BotRepository
from regos.api import regos_async_api_request

logger = logging.getLogger(__name__)
router = APIRouter()


async def verify_telegram_user(
    telegram_user_id: int,
    bot_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify Telegram user and get their partner info from REGOS.
    
    SECURITY: bot_name is REQUIRED to ensure users of one bot cannot access data from other bots.
    Even if telegram_user_id is the same across bots, each bot must only access its own data.
    
    Args:
        telegram_user_id: Telegram user ID
        bot_name: REQUIRED bot name to find matching bot (no fallback allowed for security)
        
    Returns:
        dict: Partner info with regos_integration_token and bot_name if found
        
    Raises:
        HTTPException: If user is not authorized or bot_name is missing
    """
    # SECURITY: bot_name is REQUIRED - no fallback allowed
    if not bot_name or not bot_name.strip():
        logger.error("bot_name is REQUIRED for security - cannot fallback to first bot")
        raise HTTPException(
            status_code=400,
            detail="bot_name is required. Each bot must only access its own data."
        )
    
    # Find active bot with REGOS integration token from database
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        
        # Normalize bot_name
        bot_name = bot_name.strip()
        # URL decode bot_name in case it was encoded
        import urllib.parse
        bot_name = urllib.parse.unquote(bot_name)
        
        # Find specific bot by name - MUST match exactly
        logger.info(f"Looking for bot with bot_name: {bot_name}")
        matching_bot = await bot_repo.get_by_bot_name(bot_name)
        
        if not matching_bot:
            logger.warning(f"Bot not found with provided bot_name: {bot_name}")
            raise HTTPException(
                status_code=404,
                detail=f"Bot not found with name: {bot_name}"
            )
        
        if not matching_bot.is_active:
            logger.warning(f"Bot {matching_bot.bot_id} ({bot_name}) found but is inactive")
            raise HTTPException(
                status_code=404,
                detail="Bot is inactive"
            )
        
        if not matching_bot.regos_integration_token:
            logger.error(f"Bot {matching_bot.bot_id} ({matching_bot.bot_name}) found but has no regos_integration_token")
            raise HTTPException(
                status_code=404,
                detail="Bot found but has no REGOS integration token configured"
            )
        
        # Get regos_integration_token from database (bots table)
        # This is the token stored in the database for this specific bot
        # CRITICAL: This ensures each bot only uses its own regos_integration_token
        regos_token = matching_bot.regos_integration_token
        
        logger.info(f"Using bot_id={matching_bot.bot_id}, bot_name={matching_bot.bot_name}, regos_integration_token from database (first 10 chars: {regos_token[:10] if regos_token and len(regos_token) > 10 else regos_token}...)")
        
        return {
            "regos_integration_token": regos_token,  # From database bots.regos_integration_token
            "bot_id": matching_bot.bot_id,
            "bot_name": matching_bot.bot_name,
            "telegram_token": matching_bot.telegram_token
        }


async def verify_partner_telegram_id(
    regos_integration_token: str,
    partner_id: int,
    telegram_user_id: int
) -> bool:
    """
    Verify that partner's oked field matches Telegram user ID.
    
    Note: Fetches all partners and finds the one with matching ID, because
    fetching by ID might not return the oked field correctly.
    
    Args:
        regos_integration_token: REGOS integration token
        partner_id: Partner ID to check
        telegram_user_id: Telegram user ID to verify
        
    Returns:
        bool: True if oked matches, False otherwise
    """
    try:
        logger.info(f"Verifying partner {partner_id} with Telegram user ID {telegram_user_id}")
        
        # Fetch all partners to get the complete oked field data
        # (fetching by ID might not return oked field correctly)
        partners_response = await regos_async_api_request(
            endpoint="Partner/Get",
            request_data={},
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if not partners_response.get("ok"):
            logger.warning("Failed to fetch partners for verification")
            return False
        
        results = partners_response.get("result", [])
        partners = results if isinstance(results, list) else [results] if results else []
        
        # Find the partner with matching ID
        partner = None
        for p in partners:
            if isinstance(p, dict) and p.get("id") == partner_id:
                partner = p
                break
        
        if not partner:
            logger.warning(f"Partner {partner_id} not found in partners list")
            return False
        
        oked = partner.get("oked")
        logger.info(f"Partner {partner_id} oked field: {repr(oked)} (type: {type(oked).__name__})")
        
        if oked is None:
            logger.warning(f"Partner {partner_id} oked field is None")
            return False
        
        # Handle both string and numeric types
        if isinstance(oked, str):
            oked_cleaned = oked.strip()
            if oked_cleaned:
                try:
                    oked_int = int(oked_cleaned)
                    match = oked_int == telegram_user_id
                    logger.info(f"String comparison: oked='{oked_int}' (from '{oked_cleaned}') == telegram_user_id='{telegram_user_id}': {match}")
                    return match
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error converting oked string '{oked_cleaned}' to int: {e}")
                    return False
            logger.warning(f"Partner {partner_id} oked field is empty string")
            return False
        elif isinstance(oked, (int, float)):
            oked_int = int(oked)
            match = oked_int == telegram_user_id
            logger.info(f"Numeric comparison: oked={oked_int} == telegram_user_id={telegram_user_id}: {match}")
            return match
        
        logger.warning(f"Partner {partner_id} oked field has unexpected type: {type(oked)}")
        return False
    except Exception as e:
        logger.error(f"Error verifying partner Telegram ID: {e}", exc_info=True)
        return False


@router.get("/auth")
async def authenticate_telegram_user(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    bot_name: Optional[str] = Query(None, description="Bot name (REQUIRED for security)")
):
    """
    Authenticate Telegram user and return their partner info.
    Fetches all partners and checks if any partner's oked field matches the Telegram user ID.
    Returns partner_id if found.
    
    SECURITY: bot_name is REQUIRED. Each bot must only access its own data.
    Users of one bot cannot see data from other bots, even if telegram_user_id is the same.
    """
    try:
        # SECURITY: bot_name is REQUIRED - cannot search across all bots
        if not bot_name or not bot_name.strip():
            logger.error("bot_name is REQUIRED for security - cannot search across all bots")
            raise HTTPException(
                status_code=400,
                detail="bot_name is required. Each bot must only access its own data."
            )
        
        # Verify with the provided bot_name (no fallback)
        bot_info = await verify_telegram_user(telegram_user_id, bot_name)
        regos_token = bot_info["regos_integration_token"]
        
        # Fetch all partners
        try:
            logger.info(f"Fetching all partners to find match for Telegram user ID: {telegram_user_id}")
            partners_response = await regos_async_api_request(
                endpoint="Partner/Get",
                request_data={},
                token=regos_token,
                timeout_seconds=30
            )
            
            partner_id = None
            partner_name = None
            
            if partners_response.get("ok"):
                results = partners_response.get("result", [])
                # Handle both list and single object responses
                partners = results if isinstance(results, list) else [results] if results else []
                
                logger.info(f"Checking {len(partners)} partners for matching Telegram ID")
                
                # Check each partner's oked field
                for partner in partners:
                    if isinstance(partner, dict):
                        oked = partner.get("oked")
                        if oked is not None:
                            # Check if oked matches telegram_user_id
                            try:
                                if isinstance(oked, str):
                                    oked_cleaned = oked.strip()
                                    if oked_cleaned:
                                        if int(oked_cleaned) == telegram_user_id:
                                            partner_id = partner.get("id")
                                            partner_name = partner.get("name")
                                            logger.info(f"Found matching partner: ID={partner_id}, Name={partner_name}")
                                            break
                                elif isinstance(oked, (int, float)):
                                    if int(oked) == telegram_user_id:
                                        partner_id = partner.get("id")
                                        partner_name = partner.get("name")
                                        logger.info(f"Found matching partner: ID={partner_id}, Name={partner_name}")
                                        break
                            except (ValueError, TypeError) as e:
                                logger.debug(f"Error parsing oked field for partner {partner.get('id')}: {e}")
                                continue
            
            if partner_id:
                return {
                    "ok": True,
                    "bot_id": bot_info["bot_id"],
                    "bot_name": bot_info["bot_name"],
                    "telegram_user_id": telegram_user_id,
                    "partner_id": partner_id,
                    "partner_name": partner_name
                }
            else:
                logger.warning(f"No partner found with Telegram ID {telegram_user_id} in oked field")
                return {
                    "ok": False,
                    "message": "Partner not found with this Telegram ID. Please ensure your Telegram ID is registered in the partner.oked field."
                }
        except Exception as e:
            logger.error(f"Error fetching partners: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to fetch partners from REGOS")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error authenticating Telegram user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

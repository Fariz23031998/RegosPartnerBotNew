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
    bot_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify Telegram user and get their partner info from REGOS.
    
    Args:
        telegram_user_id: Telegram user ID
        bot_token: Optional bot token to find matching bot
        
    Returns:
        dict: Partner info with regos_integration_token and telegram_token if found
        
    Raises:
        HTTPException: If user is not authorized
    """
    # Find active bot with REGOS integration token
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        
        if bot_token:
            # Find specific bot by token
            bots = await bot_repo.get_all_active()
            matching_bot = None
            for bot in bots:
                if bot.telegram_token == bot_token:
                    matching_bot = bot
                    break
        else:
            # Get first active bot with REGOS integration token
            bots = await bot_repo.get_all_active()
            matching_bot = None
            for bot in bots:
                if bot.regos_integration_token:
                    matching_bot = bot
                    break
        
        if not matching_bot or not matching_bot.regos_integration_token:
            raise HTTPException(
                status_code=404,
                detail="No bot with REGOS integration found"
            )
        
        regos_token = matching_bot.regos_integration_token
        
        return {
            "regos_integration_token": regos_token,
            "bot_id": matching_bot.bot_id,
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
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """
    Authenticate Telegram user and return their partner info.
    Fetches all partners and checks if any partner's oked field matches the Telegram user ID.
    Returns partner_id if found.
    """
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
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

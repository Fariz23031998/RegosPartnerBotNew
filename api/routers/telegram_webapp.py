"""
Telegram Web App API routes for partners to view their documents.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel

from database import get_db
from database.repositories import BotRepository, BotSettingsRepository
from regos.api import regos_async_api_request
from regos.partner import get_partner_by_id
from regos.document_excel import generate_document_excel, generate_partner_balance_excel
from bot_manager import bot_manager
from core.utils import convert_to_unix_timestamp

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram-webapp", tags=["telegram-webapp"])


class TelegramAuth(BaseModel):
    """Telegram Web App authentication data"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float


class CreateOrderRequest(BaseModel):
    telegram_user_id: int
    partner_id: int
    address: str
    phone: Optional[str] = None
    is_takeaway: bool
    items: List[OrderItem]


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


@router.get("/documents/purchase")
async def get_purchase_documents(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get purchase documents for partner"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Build request data
        request_data = {
            "partner_ids": [partner_id],
            "performed": True
        }
        
        if start_date:
            # Add time to start of day for start_date
            start_date_with_time = f"{start_date} 00:00:00"
            request_data["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
        if end_date:
            # Add time to end of day for end_date
            end_date_with_time = f"{end_date} 23:59:59"
            request_data["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
        
        # Fetch purchase documents
        response = await regos_async_api_request(
            endpoint="DocPurchase/Get",
            request_data=request_data,
            token=regos_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            return {
                "ok": True,
                "documents": response.get("result", [])
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to fetch purchase documents")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching purchase documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/purchase-return")
async def get_purchase_return_documents(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get return purchase documents for partner"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Build request data
        request_data = {
            "partner_ids": [partner_id],
            "performed": True
        }
        
        if start_date:
            # Add time to start of day for start_date
            start_date_with_time = f"{start_date} 00:00:00"
            request_data["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
        if end_date:
            # Add time to end of day for end_date
            end_date_with_time = f"{end_date} 23:59:59"
            request_data["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
        
        # Fetch return purchase documents
        response = await regos_async_api_request(
            endpoint="DocReturnsToPartner/Get",
            request_data=request_data,
            token=regos_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            return {
                "ok": True,
                "documents": response.get("result", [])
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to fetch return purchase documents")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching return purchase documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/wholesale")
async def get_wholesale_documents(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get wholesale documents for partner"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Build request data
        request_data = {
            "partner_ids": [partner_id],
            "performed": True
        }
        
        if start_date:
            # Add time to start of day for start_date
            start_date_with_time = f"{start_date} 00:00:00"
            request_data["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
        if end_date:
            # Add time to end of day for end_date
            end_date_with_time = f"{end_date} 23:59:59"
            request_data["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
        
        # Fetch wholesale documents
        response = await regos_async_api_request(
            endpoint="DocWholeSale/Get",
            request_data=request_data,
            token=regos_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            return {
                "ok": True,
                "documents": response.get("result", [])
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to fetch wholesale documents")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching wholesale documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/wholesale-return")
async def get_wholesale_return_documents(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get wholesale return documents for partner"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Build request data
        request_data = {
            "partner_ids": [partner_id],
            "performed": True
        }
        
        if start_date:
            # Add time to start of day for start_date
            start_date_with_time = f"{start_date} 00:00:00"
            request_data["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
        if end_date:
            # Add time to end of day for end_date
            end_date_with_time = f"{end_date} 23:59:59"
            request_data["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
        
        # Fetch wholesale return documents
        response = await regos_async_api_request(
            endpoint="DocWholeSaleReturn/Get",
            request_data=request_data,
            token=regos_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            return {
                "ok": True,
                "documents": response.get("result", [])
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to fetch wholesale return documents")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching wholesale return documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/payment")
async def get_payment_documents(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get payment documents for partner"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Build request data
        timestamp_start = None
        timestamp_end = None
        if start_date:
            start_date_with_time = f"{start_date} 00:00:00"
            timestamp_start = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
        if end_date:
            end_date_with_time = f"{end_date} 23:59:59"
            timestamp_end = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
        
        base_request = {
            "partner_ids": [partner_id],
            "performed": True,
        }
        
        if timestamp_start:
            base_request["start_date"] = timestamp_start
        if timestamp_end:
            base_request["end_date"] = timestamp_end
        
        # Fetch both income and outcome payments
        import asyncio
        request_income = {**base_request, "payment_direction": "Income"}
        request_outcome = {**base_request, "payment_direction": "Outcome"}
        
        income_task = regos_async_api_request(
            token=regos_token,
            endpoint="DocPayment/Get",
            request_data=request_income
        )
        outcome_task = regos_async_api_request(
            token=regos_token,
            endpoint="DocPayment/Get",
            request_data=request_outcome
        )
        
        income_payments, outcome_payments = await asyncio.gather(income_task, outcome_task)
        
        result = {
            "income": [],
            "outcome": []
        }
        
        if income_payments and income_payments.get("ok") and income_payments.get("result"):
            result["income"] = income_payments["result"]
        if outcome_payments and outcome_payments.get("ok") and outcome_payments.get("result"):
            result["outcome"] = outcome_payments["result"]
        
        return {
            "ok": True,
            "documents": result
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payment documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/partner/info")
async def get_partner_info(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get partner information"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Get partner info
        partner = await get_partner_by_id(regos_token, partner_id)
        
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")
        
        return {
            "ok": True,
            "partner": partner
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching partner info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/firms")
async def get_firms(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get all firms"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Fetch firms
        response = await regos_async_api_request(
            endpoint="Firm/Get",
            request_data={},
            token=regos_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            return {
                "ok": True,
                "firms": response.get("result", [])
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to fetch firms")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching firms: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/currencies")
async def get_currencies(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get all currencies"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Fetch currencies
        response = await regos_async_api_request(
            endpoint="Currency/Get",
            request_data={},
            token=regos_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            return {
                "ok": True,
                "currencies": response.get("result", [])
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to fetch currencies")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching currencies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/partner-balance")
async def get_partner_balance(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    firm_ids: Optional[str] = Query(None, description="Comma-separated firm IDs"),
    currency_ids: Optional[str] = Query(None, description="Comma-separated currency IDs"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get partner balance"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Build request data
        request_data = {
            "partner_id": partner_id
        }
        
        # Add date filters
        if start_date:
            start_date_with_time = f"{start_date} 00:00:00"
            request_data["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
        if end_date:
            end_date_with_time = f"{end_date} 23:59:59"
            request_data["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
        
        # Parse firm and currency IDs
        firm_id_list = []
        if firm_ids:
            firm_id_list = [int(id.strip()) for id in firm_ids.split(',') if id.strip()]
        
        currency_id_list = []
        if currency_ids:
            currency_id_list = [int(id.strip()) for id in currency_ids.split(',') if id.strip()]
        
        # If no filters, return empty
        if not firm_id_list or not currency_id_list:
            return {
                "ok": True,
                "balance": []
            }
        
        # Fetch partner balance for each combination of firm and currency
        import asyncio
        balance_tasks = []
        
        for firm_id in firm_id_list:
            for currency_id in currency_id_list:
                balance_request = {
                    "partner_id": partner_id,
                    "firm_id": firm_id,
                    "currency_id": currency_id
                }
                
                if start_date:
                    start_date_with_time = f"{start_date} 00:00:00"
                    balance_request["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
                if end_date:
                    end_date_with_time = f"{end_date} 23:59:59"
                    balance_request["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
                
                balance_tasks.append(
                    regos_async_api_request(
                        endpoint="PartnerBalance/Get",
                        request_data=balance_request,
                        token=regos_token,
                        timeout_seconds=30
                    )
                )
        
        # Execute all requests in parallel
        responses = await asyncio.gather(*balance_tasks, return_exceptions=True)
        
        # Combine all results
        all_balance_entries = []
        for response in responses:
            if isinstance(response, Exception):
                logger.warning(f"Error fetching balance: {response}")
                continue
            if response.get("ok"):
                result = response.get("result", [])
                if isinstance(result, list):
                    all_balance_entries.extend(result)
                elif result:
                    all_balance_entries.append(result)
        
        # Sort by date (newest first)
        all_balance_entries.sort(key=lambda x: x.get("date", 0), reverse=True)
        
        return {
            "ok": True,
            "balance": all_balance_entries
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching partner balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/partner-balance/export")
async def export_partner_balance(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    firm_ids: Optional[str] = Query(None, description="Comma-separated firm IDs"),
    currency_ids: Optional[str] = Query(None, description="Comma-separated currency IDs"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Generate and send Excel file for partner balance to Telegram chat"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        telegram_bot_token = bot_info.get("telegram_token")
        
        if not telegram_bot_token:
            raise HTTPException(status_code=404, detail="Bot token not found")
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Parse firm and currency IDs
        firm_id_list = []
        if firm_ids:
            firm_id_list = [int(id.strip()) for id in firm_ids.split(',') if id.strip()]
        
        currency_id_list = []
        if currency_ids:
            currency_id_list = [int(id.strip()) for id in currency_ids.split(',') if id.strip()]
        
        # If no filters, return empty
        if not firm_id_list or not currency_id_list:
            raise HTTPException(status_code=400, detail="Please select at least one firm and one currency")
        
        # Fetch partner balance for each combination of firm and currency
        import asyncio
        balance_tasks = []
        
        for firm_id in firm_id_list:
            for currency_id in currency_id_list:
                balance_request = {
                    "partner_id": partner_id,
                    "firm_id": firm_id,
                    "currency_id": currency_id
                }
                
                if start_date:
                    start_date_with_time = f"{start_date} 00:00:00"
                    balance_request["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
                if end_date:
                    end_date_with_time = f"{end_date} 23:59:59"
                    balance_request["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
                
                balance_tasks.append(
                    regos_async_api_request(
                        endpoint="PartnerBalance/Get",
                        request_data=balance_request,
                        token=regos_token,
                        timeout_seconds=30
                    )
                )
        
        # Execute all requests in parallel
        responses = await asyncio.gather(*balance_tasks, return_exceptions=True)
        
        # Combine all results
        all_balance_entries = []
        for response in responses:
            if isinstance(response, Exception):
                logger.warning(f"Error fetching balance: {response}")
                continue
            if response.get("ok"):
                result = response.get("result", [])
                if isinstance(result, list):
                    all_balance_entries.extend(result)
                elif result:
                    all_balance_entries.append(result)
        
        if not all_balance_entries:
            raise HTTPException(status_code=404, detail="No balance data found for selected filters")
        
        # Generate Excel file
        excel_path = generate_partner_balance_excel(all_balance_entries)
        
        # Send to Telegram
        caption = f"📊 Баланс партнера (ID: {partner_id})"
        result = await bot_manager.send_document(
            telegram_bot_token,
            telegram_user_id,
            excel_path,
            caption
        )
        
        # Clean up file after sending
        try:
            import os
            os.remove(excel_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary Excel file: {e}")
        
        if result:
            return {"ok": True, "message": "Excel file sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send Excel file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting partner balance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/purchase/{document_id}")
async def get_purchase_document_details(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get purchase document details with operations"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch document
        doc_response = await regos_async_api_request(
            endpoint="DocPurchase/Get",
            request_data={"ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_response.get("result", [])
        document = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify document belongs to partner
        doc_partner = document.get("partner", {})
        if isinstance(doc_partner, dict) and doc_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Document does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="PurchaseOperation/Get",
            request_data={"document_ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        return {
            "ok": True,
            "document": document,
            "operations": operations
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching purchase document details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/purchase-return/{document_id}")
async def get_purchase_return_document_details(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get purchase return document details with operations"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch document
        doc_response = await regos_async_api_request(
            endpoint="DocReturnsToPartner/Get",
            request_data={"ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_response.get("result", [])
        document = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify document belongs to partner
        doc_partner = document.get("partner", {})
        if isinstance(doc_partner, dict) and doc_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Document does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="ReturnsToPartnerOperation/Get",
            request_data={"document_ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        return {
            "ok": True,
            "document": document,
            "operations": operations
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching purchase return document details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/wholesale/{document_id}")
async def get_wholesale_document_details(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get wholesale document details with operations"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch document
        doc_response = await regos_async_api_request(
            endpoint="DocWholeSale/Get",
            request_data={"ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_response.get("result", [])
        document = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify document belongs to partner
        doc_partner = document.get("partner", {})
        if isinstance(doc_partner, dict) and doc_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Document does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="WholeSaleOperation/Get",
            request_data={"document_ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        return {
            "ok": True,
            "document": document,
            "operations": operations
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching wholesale document details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/documents/wholesale-return/{document_id}")
async def get_wholesale_return_document_details(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get wholesale return document details with operations"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch document
        doc_response = await regos_async_api_request(
            endpoint="DocWholeSaleReturn/Get",
            request_data={"ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_response.get("result", [])
        document = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify document belongs to partner
        doc_partner = document.get("partner", {})
        if isinstance(doc_partner, dict) and doc_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Document does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="WholeSaleReturnOperation/Get",
            request_data={"document_ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        return {
            "ok": True,
            "document": document,
            "operations": operations
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching wholesale return document details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/purchase/{document_id}/export")
async def export_purchase_document(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Generate and send Excel file for purchase document to Telegram chat"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        telegram_bot_token = bot_info.get("telegram_token")
        
        if not telegram_bot_token:
            raise HTTPException(status_code=404, detail="Bot token not found")
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch document
        doc_response = await regos_async_api_request(
            endpoint="DocPurchase/Get",
            request_data={"ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_response.get("result", [])
        document = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify document belongs to partner
        doc_partner = document.get("partner", {})
        if isinstance(doc_partner, dict) and doc_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Document does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="PurchaseOperation/Get",
            request_data={"document_ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        # Generate Excel file
        excel_path = generate_document_excel(document, operations, "purchase")
        
        # Send to Telegram
        doc_code = document.get("code", document_id)
        caption = f"📄 Закупка №{doc_code}"
        result = await bot_manager.send_document(
            telegram_bot_token,
            telegram_user_id,
            excel_path,
            caption
        )
        
        # Clean up file after sending
        try:
            import os
            os.remove(excel_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary Excel file: {e}")
        
        if result:
            return {"ok": True, "message": "Excel file sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send Excel file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting purchase document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/purchase-return/{document_id}/export")
async def export_purchase_return_document(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Generate and send Excel file for purchase return document to Telegram chat"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        telegram_bot_token = bot_info.get("telegram_token")
        
        if not telegram_bot_token:
            raise HTTPException(status_code=404, detail="Bot token not found")
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch document
        doc_response = await regos_async_api_request(
            endpoint="DocReturnsToPartner/Get",
            request_data={"ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_response.get("result", [])
        document = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify document belongs to partner
        doc_partner = document.get("partner", {})
        if isinstance(doc_partner, dict) and doc_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Document does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="ReturnsToPartnerOperation/Get",
            request_data={"document_ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        # Generate Excel file
        excel_path = generate_document_excel(document, operations, "purchase-return")
        
        # Send to Telegram
        doc_code = document.get("code", document_id)
        caption = f"📄 Возврат закупки №{doc_code}"
        result = await bot_manager.send_document(
            telegram_bot_token,
            telegram_user_id,
            excel_path,
            caption
        )
        
        # Clean up file after sending
        try:
            import os
            os.remove(excel_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary Excel file: {e}")
        
        if result:
            return {"ok": True, "message": "Excel file sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send Excel file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting purchase return document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/wholesale/{document_id}/export")
async def export_wholesale_document(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Generate and send Excel file for wholesale document to Telegram chat"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        telegram_bot_token = bot_info.get("telegram_token")
        
        if not telegram_bot_token:
            raise HTTPException(status_code=404, detail="Bot token not found")
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch document
        doc_response = await regos_async_api_request(
            endpoint="DocWholeSale/Get",
            request_data={"ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_response.get("result", [])
        document = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify document belongs to partner
        doc_partner = document.get("partner", {})
        if isinstance(doc_partner, dict) and doc_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Document does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="WholeSaleOperation/Get",
            request_data={"document_ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        # Generate Excel file
        excel_path = generate_document_excel(document, operations, "wholesale")
        
        # Send to Telegram
        doc_code = document.get("code", document_id)
        caption = f"📄 Отгрузка №{doc_code}"
        result = await bot_manager.send_document(
            telegram_bot_token,
            telegram_user_id,
            excel_path,
            caption
        )
        
        # Clean up file after sending
        try:
            import os
            os.remove(excel_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary Excel file: {e}")
        
        if result:
            return {"ok": True, "message": "Excel file sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send Excel file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting wholesale document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/documents/wholesale-return/{document_id}/export")
async def export_wholesale_return_document(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Generate and send Excel file for wholesale return document to Telegram chat"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        telegram_bot_token = bot_info.get("telegram_token")
        
        if not telegram_bot_token:
            raise HTTPException(status_code=404, detail="Bot token not found")
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch document
        doc_response = await regos_async_api_request(
            endpoint="DocWholeSaleReturn/Get",
            request_data={"ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Document not found")
        
        result = doc_response.get("result", [])
        document = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Verify document belongs to partner
        doc_partner = document.get("partner", {})
        if isinstance(doc_partner, dict) and doc_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Document does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="WholeSaleReturnOperation/Get",
            request_data={"document_ids": [document_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        # Generate Excel file
        excel_path = generate_document_excel(document, operations, "wholesale-return")
        
        # Send to Telegram
        doc_code = document.get("code", document_id)
        caption = f"📄 Возврат отгрузки №{doc_code}"
        result = await bot_manager.send_document(
            telegram_bot_token,
            telegram_user_id,
            excel_path,
            caption
        )
        
        # Clean up file after sending
        try:
            import os
            os.remove(excel_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary Excel file: {e}")
        
        if result:
            return {"ok": True, "message": "Excel file sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send Excel file")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting wholesale return document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/bot-settings")
async def get_bot_settings_for_user(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get bot settings for the authenticated Telegram user"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        bot_id = bot_info["bot_id"]
        
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            bot_settings = await settings_repo.get_by_bot_id(bot_id)
            
            if not bot_settings:
                return {
                    "ok": True,
                    "bot_settings": None
                }
            
            return {
                "ok": True,
                "bot_settings": {
                    "id": bot_settings.id,
                    "bot_id": bot_settings.bot_id,
                    "online_store_stock_id": bot_settings.online_store_stock_id,
                    "online_store_price_type_id": bot_settings.online_store_price_type_id
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/products")
async def get_products(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    stock_id: Optional[int] = Query(None, description="Stock ID (overrides bot settings)"),
    price_type_id: Optional[int] = Query(None, description="Price type ID (overrides bot settings)"),
    group_ids: Optional[str] = Query(None, description="Comma-separated group IDs"),
    search: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(20, description="Limit"),
    offset: int = Query(0, description="Offset"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get products for online store"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        bot_id = bot_info["bot_id"]
        
        # Get bot settings
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            bot_settings = await settings_repo.get_by_bot_id(bot_id)
        
        # Use provided values or fall back to bot settings
        final_stock_id = stock_id
        final_price_type_id = price_type_id
        
        if not final_stock_id and bot_settings and bot_settings.online_store_stock_id:
            final_stock_id = bot_settings.online_store_stock_id
        
        if not final_price_type_id and bot_settings and bot_settings.online_store_price_type_id:
            final_price_type_id = bot_settings.online_store_price_type_id
        
        if not final_stock_id or not final_price_type_id:
            raise HTTPException(
                status_code=400,
                detail="Stock ID and Price Type ID must be configured in bot settings or provided as parameters"
            )
        
        # Build request data
        request_data: Dict[str, Any] = {
            "stock_id": final_stock_id,
            "price_type_id": final_price_type_id,
            "sort_orders": [
                {
                    "column": "Name",
                    "direction": "ASC"
                }
            ],
            "zero_quantity": False,  # Only show products with quantity > 0
            "zero_price": True,
            "image_size": "Large",
            "limit": limit,
            "offset": offset
        }
        
        # Add optional filters
        if group_ids:
            group_id_list = [int(id.strip()) for id in group_ids.split(',') if id.strip()]
            if group_id_list:
                request_data["group_ids"] = group_id_list
        
        if search:
            request_data["search"] = search
        
        # Fetch products
        response = await regos_async_api_request(
            endpoint="Item/GetExt",
            request_data=request_data,
            token=regos_token,
            timeout_seconds=30
        )
        
        if not response.get("ok"):
            raise HTTPException(status_code=404, detail="Failed to fetch products")
        
        result = response.get("result", [])
        if not isinstance(result, list):
            result = [result] if result else []
        
        # Filter products with quantity > 0
        filtered_products = []
        for item_data in result:
            quantity = item_data.get("quantity", {})
            common_quantity = quantity.get("common", 0) if isinstance(quantity, dict) else 0
            if common_quantity > 0:
                filtered_products.append(item_data)
        
        return {
            "ok": True,
            "products": filtered_products,
            "next_offset": response.get("next_offset", 0),
            "total": response.get("total", len(filtered_products))
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/product-groups")
async def get_product_groups(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get product groups for filtering"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        bot_id = bot_info["bot_id"]
        
        # Get bot settings
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            bot_settings = await settings_repo.get_by_bot_id(bot_id)
        
        # Use bot settings for stock_id and price_type_id
        stock_id = None
        price_type_id = None
        
        if bot_settings:
            stock_id = bot_settings.online_store_stock_id
            price_type_id = bot_settings.online_store_price_type_id
        
        if not stock_id or not price_type_id:
            # Return empty groups if settings are not configured
            return {
                "ok": True,
                "groups": []
            }
        
        # Fetch groups using Item/GetExt to get all groups from products
        request_data = {
            "stock_id": stock_id,
            "price_type_id": price_type_id,
            "limit": 1000,
            "offset": 0,
            "zero_quantity": False,
            "zero_price": True,
            "image_size": "Small"
        }
        
        response = await regos_async_api_request(
            endpoint="Item/GetExt",
            request_data=request_data,
            token=regos_token,
            timeout_seconds=30
        )
        
        if not response.get("ok"):
            raise HTTPException(status_code=404, detail="Failed to fetch product groups")
        
        result = response.get("result", [])
        if not isinstance(result, list):
            result = [result] if result else []
        
        # Extract unique groups
        groups_map = {}
        for item_data in result:
            item = item_data.get("item", {})
            group = item.get("group", {})
            if group and isinstance(group, dict):
                group_id = group.get("id")
                if group_id and group_id not in groups_map:
                    groups_map[group_id] = {
                        "id": group_id,
                        "name": group.get("name", ""),
                        "path": group.get("path", "")
                    }
        
        groups = list(groups_map.values())
        groups.sort(key=lambda x: x.get("name", ""))
        
        return {
            "ok": True,
            "groups": groups
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product groups: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


class OrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float


class CreateOrderRequest(BaseModel):
    telegram_user_id: int
    partner_id: int
    address: str
    phone: Optional[str] = None
    is_takeaway: bool
    items: List[OrderItem]


@router.get("/orders")
async def get_orders(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get orders for partner"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Build request data
        request_data = {
            "partner_ids": [partner_id],
            "status_ids": [1, 2, 3],
            "deleted_mark": False
        }
        
        if start_date:
            # Add time to start of day for start_date
            start_date_with_time = f"{start_date} 00:00:00"
            request_data["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
        if end_date:
            # Add time to end of day for end_date
            end_date_with_time = f"{end_date} 23:59:59"
            request_data["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
        
        # Fetch orders
        response = await regos_async_api_request(
            endpoint="DocOrderFromPartner/Get",
            request_data=request_data,
            token=regos_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            return {
                "ok": True,
                "orders": response.get("result", [])
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to fetch orders")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/orders/{order_id}")
async def get_order_details(
    order_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Get order details with operations"""
    try:
        bot_info = await verify_telegram_user(telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, partner_id, telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Fetch order document
        doc_response = await regos_async_api_request(
            endpoint="DocOrderFromPartner/Get",
            request_data={"ids": [order_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not doc_response.get("ok"):
            raise HTTPException(status_code=404, detail="Order not found")
        
        result = doc_response.get("result", [])
        order = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Verify order belongs to partner
        order_partner = order.get("partner", {})
        if isinstance(order_partner, dict) and order_partner.get("id") != partner_id:
            raise HTTPException(status_code=403, detail="Order does not belong to this partner")
        
        # Fetch operations
        ops_response = await regos_async_api_request(
            endpoint="OrderFromPartnerOperation/Get",
            request_data={"document_ids": [order_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        operations = []
        if ops_response.get("ok"):
            ops_result = ops_response.get("result", [])
            operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
        
        return {
            "ok": True,
            "order": order,
            "operations": operations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/orders/create")
async def create_order(
    request: CreateOrderRequest = Body(...),
    bot_token: Optional[str] = Query(None, description="Bot token (optional)")
):
    """Create an order from partner"""
    try:
        bot_info = await verify_telegram_user(request.telegram_user_id, bot_token)
        regos_token = bot_info["regos_integration_token"]
        bot_id = bot_info["bot_id"]
        
        # Verify partner's Telegram ID matches
        if not await verify_partner_telegram_id(regos_token, request.partner_id, request.telegram_user_id):
            raise HTTPException(
                status_code=403,
                detail="Telegram user ID does not match partner.oked field"
            )
        
        # Get bot settings
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            bot_settings = await settings_repo.get_by_bot_id(bot_id)
        
        if not bot_settings or not bot_settings.online_store_stock_id:
            raise HTTPException(
                status_code=400,
                detail="Stock ID must be configured in bot settings"
            )
        
        stock_id = bot_settings.online_store_stock_id
        
        # Get partner info to get currency_id
        partner_response = await regos_async_api_request(
            endpoint="Partner/Get",
            request_data={"ids": [request.partner_id]},
            token=regos_token,
            timeout_seconds=30
        )
        
        if not partner_response.get("ok"):
            raise HTTPException(status_code=404, detail="Partner not found")
        
        result = partner_response.get("result", [])
        partner = result[0] if isinstance(result, list) and len(result) > 0 else (result if isinstance(result, dict) else None)
        
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")
        
        # Get currency_id from bot settings (default to 1)
        currency_id = 1
        if bot_settings and bot_settings.online_store_currency_id:
            currency_id = bot_settings.online_store_currency_id
        
        # Get currency exchange rate
        currency_response = await regos_async_api_request(
            endpoint="Currency/Get",
            request_data={},
            token=regos_token,
            timeout_seconds=30
        )
        
        exchange_rate = 1.0
        if currency_response.get("ok"):
            currencies = currency_response.get("result", [])
            if isinstance(currencies, list) and len(currencies) > 0:
                # Find the currency by ID
                currency = next((c for c in currencies if c.get("id") == currency_id), None)
                if currency:
                    exchange_rate = currency.get("exchange_rate", 1.0)
        
        # Prepare order data
        from datetime import datetime
        current_timestamp = int(datetime.now().timestamp())
        
        # Build description with address/type and phone number if provided
        description_parts = []
        if request.is_takeaway:
            description_parts.append("С собой")
        elif request.address:
            description_parts.append(request.address)
        
        if request.phone:
            description_parts.append(f"Телефон: {request.phone}")
        
        description = ", ".join(description_parts) if description_parts else ""
        
        order_data = {
            "date": current_timestamp,
            "stock_id": stock_id,
            "partner_id": request.partner_id,
            "currency_id": currency_id,
            "status_id": 1,  # Default status
            "booked": True,
            "exchange_rate": exchange_rate,
            "description": description,
            "vat_calculation_type": "Include",
            "attached_user_id": 1
        }
        
        # Create the order
        order_response = await regos_async_api_request(
            endpoint="DocOrderFromPartner/Add",
            request_data=order_data,
            token=regos_token,
            timeout_seconds=30
        )
        
        if not order_response.get("ok"):
            error_msg = order_response.get("result", {}).get("description", "Failed to create order")
            raise HTTPException(status_code=400, detail=error_msg)
        
        order_id = order_response.get("result", {}).get("new_id")
        
        if not order_id:
            raise HTTPException(status_code=500, detail="Order created but no ID returned")
        
        # Add order operations using OrderFromPartnerOperation/Add
        # According to REGOS API docs: https://docs.regos.uz/uz/api/store/orderfrompartneroperation/add
        # - Must lock document before adding operations
        # - Must send operations as an array
        # - Must unlock document after adding operations
        # - Required fields: document_id, item_id, quantity, price, price2
        if request.items and len(request.items) > 0:
            try:
                # Lock the document before adding operations
                lock_response = await regos_async_api_request(
                    endpoint="DocOrderFromPartner/Lock",
                    request_data={"ids": [order_id]},
                    token=regos_token,
                    timeout_seconds=30
                )
                
                if not lock_response.get("ok"):
                    logger.warning(f"Failed to lock document {order_id}, but will try to add operations anyway")
                
                # Build array of operations
                operations_array = []
                for item in request.items:
                    # price2 is required - use the same as price (price without discount)
                    # In a real scenario, you might want to fetch the original price from item
                    operation_data = {
                        "document_id": order_id,
                        "item_id": item.product_id,
                        "quantity": item.quantity,
                        "price": item.price,  # Price with discount
                        "price2": item.price,  # Price without discount (required, using same as price for now)
                        "vat_value": 0  # Optional VAT value
                    }
                    operations_array.append(operation_data)
                
                # Add all operations in a single request (array)
                operation_response = await regos_async_api_request(
                    endpoint="OrderFromPartnerOperation/Add",
                    request_data=operations_array,
                    token=regos_token,
                    timeout_seconds=30
                )
                
                # Unlock the document after adding operations
                unlock_response = await regos_async_api_request(
                    endpoint="DocOrderFromPartner/Unlock",
                    request_data={"ids": [order_id]},
                    token=regos_token,
                    timeout_seconds=30
                )
                
                if not unlock_response.get("ok"):
                    logger.warning(f"Failed to unlock document {order_id}")
                
                if not operation_response.get("ok"):
                    error_msg = operation_response.get("result", {}).get("description", "Failed to create operations")
                    logger.error(f"Failed to create operations for order {order_id}: {error_msg}")
                    raise HTTPException(status_code=400, detail=f"Failed to create order operations: {error_msg}")
                
                # Get number of created operations
                raw_affected = operation_response.get("result", {}).get("raw_affected", 0)
                logger.info(f"Successfully created {raw_affected} operations for order {order_id}")
                
            except HTTPException:
                # Re-raise HTTP exceptions (like validation errors)
                raise
            except Exception as e:
                logger.error(f"Error creating operations for order {order_id}: {e}", exc_info=True)
                # Try to unlock document in case of error
                try:
                    await regos_async_api_request(
                        endpoint="DocOrderFromPartner/Unlock",
                        request_data={"ids": [order_id]},
                        token=regos_token,
                        timeout_seconds=30
                    )
                except:
                    pass
                raise HTTPException(status_code=500, detail=f"Failed to create order operations: {str(e)}")
        
        return {
            "ok": True,
            "order_id": order_id,
            "message": "Order created successfully"
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

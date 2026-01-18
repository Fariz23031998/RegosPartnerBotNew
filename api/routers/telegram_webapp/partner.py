"""
Partner-related endpoints for Telegram Web App.
Handles partner info, firms, and currencies.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from regos.api import regos_async_api_request
from regos.partner import get_partner_by_id
from .auth import verify_telegram_user, verify_partner_telegram_id

logger = logging.getLogger(__name__)
router = APIRouter()


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

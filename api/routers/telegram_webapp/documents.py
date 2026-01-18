"""
Document listing endpoints for Telegram Web App.
Handles purchase, wholesale, return, and payment document listings.
"""
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from regos.api import regos_async_api_request
from core.utils import convert_to_unix_timestamp
from .auth import verify_telegram_user, verify_partner_telegram_id

logger = logging.getLogger(__name__)
router = APIRouter()


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

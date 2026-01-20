"""
Partner balance endpoints for Telegram Web App.
Handles fetching and exporting partner balance data.
"""
import asyncio
import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from regos.api import regos_async_api_request
from regos.document_excel import generate_partner_balance_excel
from bot_manager import bot_manager
from core.utils import convert_to_unix_timestamp
from .auth import verify_telegram_user, verify_partner_telegram_id

logger = logging.getLogger(__name__)
router = APIRouter()


async def _fetch_balance_data(
    regos_token: str,
    partner_id: int,
    start_date: Optional[str],
    end_date: Optional[str],
    firm_id_list: list,
    currency_id_list: list
) -> list:
    """Helper function to fetch balance data for multiple firm/currency combinations"""
    if not firm_id_list or not currency_id_list:
        return []
    
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
    
    return all_balance_entries


@router.get("/partner-balance")
async def get_partner_balance(
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    firm_ids: Optional[str] = Query(None, description="Comma-separated firm IDs"),
    currency_ids: Optional[str] = Query(None, description="Comma-separated currency IDs"),
    bot_name: Optional[str] = Query(None, description="Bot name (REQUIRED for security)")
):
    """
    Get partner balance.
    
    SECURITY: bot_name is REQUIRED. Each bot must only access its own balance data.
    """
    try:
        # SECURITY: bot_name is REQUIRED
        if not bot_name or not bot_name.strip():
            logger.error("get_partner_balance: bot_name is REQUIRED for security")
            raise HTTPException(
                status_code=400,
                detail="bot_name is required. Each bot must only access its own data."
            )
        
        bot_info = await verify_telegram_user(telegram_user_id, bot_name)
        regos_token = bot_info["regos_integration_token"]
        
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
            return {
                "ok": True,
                "balance": []
            }
        
        # Fetch partner balance
        all_balance_entries = await _fetch_balance_data(
            regos_token=regos_token,
            partner_id=partner_id,
            start_date=start_date,
            end_date=end_date,
            firm_id_list=firm_id_list,
            currency_id_list=currency_id_list
        )
        
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
    bot_name: Optional[str] = Query(None, description="Bot name (REQUIRED for security)")
):
    """
    Generate and send Excel file for partner balance to Telegram chat.
    
    SECURITY: bot_name is REQUIRED. Each bot must only access its own balance data.
    """
    try:
        # SECURITY: bot_name is REQUIRED
        if not bot_name or not bot_name.strip():
            logger.error("export_partner_balance: bot_name is REQUIRED for security")
            raise HTTPException(
                status_code=400,
                detail="bot_name is required. Each bot must only access its own data."
            )
        
        bot_info = await verify_telegram_user(telegram_user_id, bot_name)
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
        
        # Fetch partner balance
        all_balance_entries = await _fetch_balance_data(
            regos_token=regos_token,
            partner_id=partner_id,
            start_date=start_date,
            end_date=end_date,
            firm_id_list=firm_id_list,
            currency_id_list=currency_id_list
        )
        
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

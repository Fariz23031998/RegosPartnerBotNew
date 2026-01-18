"""
Document detail endpoints for Telegram Web App.
Handles fetching document details with operations.
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from regos.api import regos_async_api_request
from .auth import verify_telegram_user, verify_partner_telegram_id

logger = logging.getLogger(__name__)
router = APIRouter()


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

"""
Document export endpoints for Telegram Web App.
Handles generating and sending Excel files for documents.
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from regos.api import regos_async_api_request
from regos.document_excel import generate_document_excel
from bot_manager import bot_manager
from .auth import verify_telegram_user, verify_partner_telegram_id
from services.translator_service import translator_service

logger = logging.getLogger(__name__)
router = APIRouter()

t = translator_service.get


async def _export_document_helper(
    document_id: int,
    telegram_user_id: int,
    partner_id: int,
    bot_name: Optional[str],
    doc_endpoint: str,
    ops_endpoint: str,
    doc_type: str,
    caption_template: str,
    lang_code: str = "en"
):
    """
    Helper function to export a document.
    
    SECURITY: bot_name is REQUIRED. Each bot must only access its own documents.
    """
    # SECURITY: bot_name is REQUIRED
    if not bot_name or not bot_name.strip():
        logger.error("_export_document_helper: bot_name is REQUIRED for security")
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
    
    # Fetch document
    doc_response = await regos_async_api_request(
        endpoint=doc_endpoint,
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
        endpoint=ops_endpoint,
        request_data={"document_ids": [document_id]},
        token=regos_token,
        timeout_seconds=30
    )
    
    operations = []
    if ops_response.get("ok"):
        ops_result = ops_response.get("result", [])
        operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
    
    # Generate Excel file
    excel_path = generate_document_excel(document, operations, doc_type, lang_code=lang_code)
    
    # Send to Telegram
    doc_code = document.get("code", document_id)
    caption = caption_template.format(code=doc_code)
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


@router.post("/documents/purchase/{document_id}/export")
async def export_purchase_document(
    document_id: int,
    telegram_user_id: int = Query(..., description="Telegram user ID"),
    partner_id: int = Query(..., description="Partner ID"),
    bot_name: Optional[str] = Query(None, description="Bot name (REQUIRED for security)"),
    lang_code: Optional[str] = Query(default="en", description="Language code (default is en, REQUIRED for sending notification using that language)")
):
    """
    Generate and send Excel file for purchase document to Telegram chat.
    
    SECURITY: bot_name is REQUIRED. Each bot must only access its own documents.
    """
    try:
        return await _export_document_helper(
            document_id=document_id,
            telegram_user_id=telegram_user_id,
            partner_id=partner_id,
            bot_name=bot_name,
            doc_endpoint="DocPurchase/Get",
            ops_endpoint="PurchaseOperation/Get",
            doc_type="purchase",
            caption_template=t("document_exports.purchase.caption", lang_code, default="📄 Закупка №{code}"),
            lang_code=lang_code
        )
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
    bot_name: Optional[str] = Query(None, description="Bot name (REQUIRED for security)"),
    lang_code: Optional[str] = Query(default="en", description="Language code (default is en, REQUIRED for sending notification using that language)")
):
    """
    Generate and send Excel file for purchase return document to Telegram chat.
    
    SECURITY: bot_name is REQUIRED. Each bot must only access its own documents.
    """
    try:
        return await _export_document_helper(
            document_id=document_id,
            telegram_user_id=telegram_user_id,
            partner_id=partner_id,
            bot_name=bot_name,
            doc_endpoint="DocReturnsToPartner/Get",
            ops_endpoint="ReturnsToPartnerOperation/Get",
            doc_type="purchase-return",
            caption_template=t("document_exports.purchase-return.caption", lang_code, default="📄 Возврат закупки №{code}"),
            lang_code=lang_code
        )
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
    bot_name: Optional[str] = Query(None, description="Bot name (REQUIRED for security)"),
    lang_code: Optional[str] = Query(default="en", description="Language code (default is en, REQUIRED for sending notification using that language)")
):
    """
    Generate and send Excel file for wholesale document to Telegram chat.
    
    SECURITY: bot_name is REQUIRED. Each bot must only access its own documents.
    """
    try:
        return await _export_document_helper(
            document_id=document_id,
            telegram_user_id=telegram_user_id,
            partner_id=partner_id,
            bot_name=bot_name,
            doc_endpoint="DocWholeSale/Get",
            ops_endpoint="WholeSaleOperation/Get",
            doc_type="wholesale",
            caption_template=t("document_exports.wholesale.caption", lang_code, default="📄 Отгрузка №{code}"),
            lang_code=lang_code
        )
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
    bot_name: Optional[str] = Query(None, description="Bot name (REQUIRED for security)"),
    lang_code: Optional[str] = Query(default="en", description="Language code (default is en, REQUIRED for sending notification using that language)")
):
    """
    Generate and send Excel file for wholesale return document to Telegram chat.
    
    SECURITY: bot_name is REQUIRED. Each bot must only access its own documents.
    """
    try:
        return await _export_document_helper(
            document_id=document_id,
            telegram_user_id=telegram_user_id,
            partner_id=partner_id,
            bot_name=bot_name,
            doc_endpoint="DocWholeSaleReturn/Get",
            ops_endpoint="WholeSaleReturnOperation/Get",
            doc_type="wholesale-return",
            caption_template=t("document_exports.wholesale-return.caption", lang_code, default="📄 Возврат отгрузки №{code}"),
            lang_code=lang_code
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting wholesale return document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

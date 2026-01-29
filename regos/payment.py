"""
REGOS Payment operations and formatting.
"""
import logging
from typing import Optional, Dict, Any

from core.number_format import format_number
from regos.api import regos_async_api_request
from config import APP_NAME
from services.translator_service import translator_service

logger = logging.getLogger(APP_NAME)

t = translator_service.get


async def get_payment_document(
    regos_integration_token: str,
    document_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get payment document by ID using DocPayment/Get endpoint.
    
    Args:
        regos_integration_token: REGOS integration token
        document_id: Document ID to fetch
        
    Returns:
        dict: Document data if found, None otherwise
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided")
        return None
    
    try:
        request_data = {
            "ids": [document_id]
        }
        
        logger.info(f"Fetching payment document {document_id}")
        response = await regos_async_api_request(
            endpoint="DocPayment/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            logger.debug(f"DocPayment/Get response for document {document_id}: {result}")
            
            if result:
                # Handle both list and single object responses
                if isinstance(result, list):
                    if len(result) > 0:
                        logger.info(f"Successfully fetched payment document {document_id} (from list)")
                        return result[0] if isinstance(result[0], dict) else None
                    else:
                        logger.warning(f"DocPayment/Get returned empty list for document {document_id}")
                elif isinstance(result, dict):
                    logger.info(f"Successfully fetched payment document {document_id}")
                    return result
                else:
                    logger.warning(f"DocPayment/Get returned unexpected type for document {document_id}: {type(result)}")
            else:
                logger.warning(f"DocPayment/Get returned no result for document {document_id}")
        else:
            error_msg = response.get("description", response.get("error", "Unknown error"))
            logger.error(f"DocPayment/Get failed for document {document_id}: {error_msg}")
        
        logger.warning(f"No payment document found with ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching payment document: {e}", exc_info=True)
        return None


def format_payment_notification(
    document: Dict[str, Any],
    warehouse_name: Optional[str] = None,
    is_cancelled: bool = False,
    lang_code: str = "en"
) -> str:
    """
    Format a payment document as a nicely formatted notification message for Telegram.
    
    Payment direction is determined from document.category.positive:
    - If True, it's Income (Поступление)
    - If False, it's Outcome (Списание)
    
    Args:
        document: Payment document data from DocPayment/Get endpoint
        warehouse_name: Optional warehouse/stock name for display
        is_cancelled: If True, add a "Cancelled" notice at the top
        
    Returns:
        str: Formatted payment notification message
    """
    # Extract document information
    doc_code = document.get("code", "N/A")
    doc_date = document.get("date", "")
    amount = document.get("amount", 0)
    payment_type = document.get("type", {})
    payment_type_name = payment_type.get("name", t("payment.unknown-type", lang_code, default="Неизвестный тип")) if isinstance(payment_type, dict) else t("payment.unknown-type", lang_code, default="Неизвестный тип")
    
    # Extract currency information
    currency = document.get("currency", {})
    currency_name = currency.get("name", "") if isinstance(currency, dict) else ""
    
    # Extract exchange rate
    exchange_rate = document.get("exchange_rate", 1.0)
    if isinstance(exchange_rate, str):
        try:
            exchange_rate = float(exchange_rate)
        except (ValueError, TypeError):
            exchange_rate = 1.0
    
    # Determine payment direction from category.positive
    category = document.get("category", {})
    category_positive = category.get("positive", False) if isinstance(category, dict) else False
    
    # Format date if available (assuming unix timestamp or ISO format)
    formatted_date = doc_date
    if isinstance(doc_date, (int, float)):
        from datetime import datetime
        try:
            formatted_date = datetime.fromtimestamp(doc_date).strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = str(doc_date)
    
    # Build notification message
    message_parts = []
    
    # Add cancelled notice at the top if applicable
    if is_cancelled:
        message_parts.extend([
            "❌ *" + t("payment.cancelled", lang_code, default="ОТМЕНЕНО") + "*",
            "",
        ])
    
    # Determine payment direction text from category.positive
    if category_positive:
        direction_text = t("payment.paid-out", lang_code, default="Выплачено")
        direction_emoji = "⬆️"
    else:
        direction_text = t("payment.received", lang_code, default="Получено")
        direction_emoji = "⬇️"
    
    message_parts.extend([
        f"{direction_emoji} *{direction_text}*",
        f"📄 *{t('payment.document-number', lang_code, default='Документ №')} {doc_code}*",
        f"📅 {t('payment.date', lang_code, default='Дата')}: {formatted_date}",
    ])
    
    if warehouse_name:
        message_parts.append(f"🏢 {t('payment.warehouse', lang_code, default='Склад')}: {warehouse_name}")
    
    message_parts.extend([
        "",
        f"💳 {t('payment.payment-type', lang_code, default='Тип платежа')}: {payment_type_name}",
    ])
    
    # Add currency and amount
    amount_line = f"💵 {t('payment.amount', lang_code, default='Сумма')}: {format_number(amount)}"
    if currency_name:
        amount_line += f" {currency_name}"
    message_parts.append(amount_line)
    
    # Add exchange rate only if it's not equal to 1
    if exchange_rate != 1.0:
        message_parts.append(f"📊 {t('payment.exchange-rate', lang_code, default='Курс обмена')}: {format_number(exchange_rate, 4)}")
    
    # Add additional payment details if available
    description = document.get("description")
    if description:
        message_parts.append(f"📝 {t('payment.note', lang_code, default='Примечание')}: {description}")
    
    return "\n".join(message_parts)

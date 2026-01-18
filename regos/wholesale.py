"""
REGOS WholeSale document operations.
"""
import logging
from typing import Optional, Dict, Any, List
from core.number_format import format_number
from regos.api import regos_async_api_request
from core.partner_terminology import get_partner_document_type_name
from config import APP_NAME

logger = logging.getLogger(APP_NAME)


async def get_wholesale_document(
    regos_integration_token: str,
    document_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get wholesale document by ID using DocWholeSale/Get endpoint.
    
    According to REGOS API documentation (https://docs.regos.uz/uz/api/store/docwholesale/get):
    - Uses DocWholeSale/Get endpoint
    - Requires document ID
    
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
            "ids": [document_id,]
        }
        
        logger.info(f"Fetching wholesale document {document_id}")
        response = await regos_async_api_request(
            endpoint="DocWholeSale/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            logger.debug(f"DocWholeSale/Get response for document {document_id}: {result}")
            
            if result:
                # Handle both list and single object responses
                if isinstance(result, list):
                    if len(result) > 0:
                        logger.info(f"Successfully fetched wholesale document {document_id} (from list)")
                        return result[0] if isinstance(result[0], dict) else None
                    else:
                        logger.warning(f"DocWholeSale/Get returned empty list for document {document_id}")
                elif isinstance(result, dict):
                    logger.info(f"Successfully fetched wholesale document {document_id}")
                    return result
                else:
                    logger.warning(f"DocWholeSale/Get returned unexpected type for document {document_id}: {type(result)}")
            else:
                logger.warning(f"DocWholeSale/Get returned no result for document {document_id}")
        else:
            error_msg = response.get("description", response.get("error", "Unknown error"))
            logger.error(f"DocWholeSale/Get failed for document {document_id}: {error_msg}")
        
        logger.warning(f"No wholesale document found with ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching wholesale document: {e}", exc_info=True)
        return None


async def get_wholesale_operations(
    regos_integration_token: str,
    document_id: int
) -> Optional[List[Dict[str, Any]]]:
    """
    Get wholesale document operations using WholeSaleOperation/Get endpoint.
    
    According to REGOS API documentation (https://docs.regos.uz/uz/api/store/wholesaleoperation):
    - Uses WholeSaleOperation/Get endpoint
    - Returns list of operations for a document
    
    Args:
        regos_integration_token: REGOS integration token
        document_id: Document ID to fetch operations for
        
    Returns:
        list: List of operations if found, None otherwise
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided")
        return None
    
    try:
        # REGOS API expects document_ids (plural) as a list
        request_data = {
            "document_ids": [document_id]
        }
        
        logger.info(f"Fetching wholesale operations for document {document_id}")
        response = await regos_async_api_request(
            endpoint="WholeSaleOperation/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            if result:
                # Handle both list and single object responses
                operations = result if isinstance(result, list) else [result]
                logger.info(f"Successfully fetched {len(operations)} operation(s) for document {document_id}")
                return operations
        
        logger.warning(f"No operations found for document ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching wholesale operations: {e}", exc_info=True)
        return None


def format_wholesale_receipt(
    document: Dict[str, Any],
    operations: List[Dict[str, Any]],
    warehouse_name: Optional[str] = None,
    is_cancelled: bool = False,
    is_return: bool = False,
    use_cost: bool = False
) -> str:
    """
    Format a document (wholesale, purchase, or their returns) as a nicely formatted receipt message for Telegram.
    
    Args:
        document: Document data from various Doc*/Get endpoints
        operations: List of operations from various Operation/Get endpoints
        warehouse_name: Optional warehouse/stock name for display
        is_cancelled: If True, add a "Cancelled" notice at the top
        is_return: If True, format as a return receipt instead of shipment/purchase receipt
        use_cost: If True, use "cost" field instead of "price" field (for purchase documents)
        
    Returns:
        str: Formatted receipt message
    """
    # Extract document information
    doc_code = document.get("code", "N/A")
    doc_date = document.get("date", "")
    # Try different possible field names for totals
    total_amount = document.get("total", document.get("total_amount", 0))
    total_with_discount = document.get("total_with_discount", document.get("total", total_amount))
    
    # Format date if available (assuming unix timestamp or ISO format)
    formatted_date = doc_date
    if isinstance(doc_date, (int, float)):
        from datetime import datetime
        try:
            formatted_date = datetime.fromtimestamp(doc_date).strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = str(doc_date)
    
    # Build receipt message
    message_parts = []
    
    # Add cancelled notice at the top if applicable
    if is_cancelled:
        message_parts.extend([
            "❌ *ОТМЕНЕНО*",
            "",
        ])
    
    # Determine receipt type text (system perspective, will be inverted by mapping function)
    if is_return:
        # For returns, determine if it's purchase return or wholesale return
        if use_cost:
            # System purchase return
            receipt_type = "Чек возврата закупки"
        else:
            # System wholesale return
            receipt_type = "Чек возврата отгрузки"
    elif use_cost:
        # System purchase
        receipt_type = "Чек закупки"
    else:
        # System wholesale
        receipt_type = "Чек отгрузки"
    
    # Apply partner terminology mapping to invert for partner view
    receipt_type = get_partner_document_type_name(receipt_type, "ru")
    
    message_parts.extend([
        f"🧾 *{receipt_type}*",
        f"📄 *Документ №{doc_code}*",
        f"📅 Дата: {formatted_date}",
    ])
    
    if warehouse_name:
        message_parts.append(f"🏢 Склад: {warehouse_name}")
    
    message_parts.extend([
        "",
        "📦 *Товары:*",
        ""
    ])
    
    # Add operations (items)
    total_items = 0
    total_to_pay = 0.0  # Calculate total as sum of quantity × cost/price
    
    for idx, operation in enumerate(operations, 1):
        item = operation.get("item", {})
        # Handle both dict and other types
        if isinstance(item, dict):
            item_name = item.get("name", "Неизвестный товар")
        else:
            item_name = str(item) if item else "Неизвестный товар"
        
        quantity = float(operation.get("quantity", 0))
        
        # Use cost for purchase documents, price for wholesale documents
        if use_cost:
            cost_or_price = float(operation.get("cost", 0))
        else:
            # For wholesale, use price (with discount if available)
            cost_or_price = float(operation.get("price", 0))  # Price with discount
        
        description = operation.get("description", "")
        
        total_items += quantity
        
        # Calculate item total: quantity × cost/price
        item_total = quantity * cost_or_price
        total_to_pay += item_total
        
        # Format item line with quantity × cost/price = total on single line
        item_line = f"{idx}. *{item_name}*"
        message_parts.append(item_line)
        message_parts.append(f"   {format_number(quantity)} × {format_number(cost_or_price)} = {format_number(item_total)}")
        
        if description:
            message_parts.append(f"   Примечание: {description}")
        
        message_parts.append("")
    
    # Add totals
    # Calculate "Итого к оплате" as sum of quantity × cost/price
    message_parts.extend([
        "─" * 20,
        f"📊 Всего товаров: {total_items}",
        f"💵 *Итого к оплате: {format_number(total_to_pay)}*"
    ])
    
    return "\n".join(message_parts)

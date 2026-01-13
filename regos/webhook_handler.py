"""
REGOS webhook handler for processing document events.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Request

from database import get_db
from database.repositories import BotRepository
from bot_manager import bot_manager
from regos.wholesale import get_wholesale_document, get_wholesale_operations, format_wholesale_receipt
from regos.stock import get_stock_by_id
from regos.payment import get_payment_document, format_payment_notification

logger = logging.getLogger(__name__)

# Track processed webhook event IDs to prevent duplicate processing
# Store event_id -> timestamp, cleanup old entries periodically
processed_webhook_events: Dict[str, datetime] = {}


async def get_wholesale_return_document(
    regos_integration_token: str,
    document_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get wholesale return document by ID using DocWholeSaleReturn/Get endpoint.
    
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
        from regos.api import regos_async_api_request
        
        request_data = {
            "ids": [document_id]
        }
        
        logger.info(f"Fetching wholesale return document {document_id}")
        response = await regos_async_api_request(
            endpoint="DocWholeSaleReturn/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            logger.debug(f"DocWholeSaleReturn/Get response for document {document_id}: {result}")
            
            if result:
                # Handle both list and single object responses
                if isinstance(result, list):
                    if len(result) > 0:
                        logger.info(f"Successfully fetched wholesale return document {document_id} (from list)")
                        return result[0] if isinstance(result[0], dict) else None
                    else:
                        logger.warning(f"DocWholeSaleReturn/Get returned empty list for document {document_id}")
                elif isinstance(result, dict):
                    logger.info(f"Successfully fetched wholesale return document {document_id}")
                    return result
                else:
                    logger.warning(f"DocWholeSaleReturn/Get returned unexpected type for document {document_id}: {type(result)}")
            else:
                logger.warning(f"DocWholeSaleReturn/Get returned no result for document {document_id}")
        else:
            error_msg = response.get("description", response.get("error", "Unknown error"))
            logger.error(f"DocWholeSaleReturn/Get failed for document {document_id}: {error_msg}")
        
        logger.warning(f"No wholesale return document found with ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching wholesale return document: {e}", exc_info=True)
        return None


async def get_wholesale_return_operations(
    regos_integration_token: str,
    document_id: int
) -> Optional[list]:
    """
    Get wholesale return document operations using WholeSaleReturnOperation/Get endpoint.
    
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
        from regos.api import regos_async_api_request
        
        # REGOS API expects document_ids (plural) as a list
        request_data = {
            "document_ids": [document_id]
        }
        
        logger.info(f"Fetching wholesale return operations for document {document_id}")
        response = await regos_async_api_request(
            endpoint="WholeSaleReturnOperation/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            if result:
                # Handle both list and single object responses
                operations = result if isinstance(result, list) else [result]
                logger.info(f"Successfully fetched {len(operations)} operation(s) for wholesale return document {document_id}")
                return operations
        
        logger.warning(f"No operations found for wholesale return document ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching wholesale return operations: {e}", exc_info=True)
        return None


async def get_purchase_document(
    regos_integration_token: str,
    document_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get purchase document by ID using DocPurchase/Get endpoint.
    
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
        from regos.api import regos_async_api_request
        
        request_data = {
            "ids": [document_id]
        }
        
        logger.info(f"Fetching purchase document {document_id}")
        response = await regos_async_api_request(
            endpoint="DocPurchase/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            logger.debug(f"DocPurchase/Get response for document {document_id}: {result}")
            
            if result:
                # Handle both list and single object responses
                if isinstance(result, list):
                    if len(result) > 0:
                        logger.info(f"Successfully fetched purchase document {document_id} (from list)")
                        return result[0] if isinstance(result[0], dict) else None
                    else:
                        logger.warning(f"DocPurchase/Get returned empty list for document {document_id}")
                elif isinstance(result, dict):
                    logger.info(f"Successfully fetched purchase document {document_id}")
                    return result
                else:
                    logger.warning(f"DocPurchase/Get returned unexpected type for document {document_id}: {type(result)}")
            else:
                logger.warning(f"DocPurchase/Get returned no result for document {document_id}")
        else:
            error_msg = response.get("description", response.get("error", "Unknown error"))
            logger.error(f"DocPurchase/Get failed for document {document_id}: {error_msg}")
        
        logger.warning(f"No purchase document found with ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching purchase document: {e}", exc_info=True)
        return None


async def get_purchase_operations(
    regos_integration_token: str,
    document_id: int
) -> Optional[list]:
    """
    Get purchase document operations using PurchaseOperation/Get endpoint.
    
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
        from regos.api import regos_async_api_request
        
        # REGOS API expects document_ids (plural) as a list
        request_data = {
            "document_ids": [document_id]
        }
        
        logger.info(f"Fetching purchase operations for document {document_id}")
        response = await regos_async_api_request(
            endpoint="PurchaseOperation/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            if result:
                # Handle both list and single object responses
                operations = result if isinstance(result, list) else [result]
                logger.info(f"Successfully fetched {len(operations)} operation(s) for purchase document {document_id}")
                return operations
        
        logger.warning(f"No operations found for purchase document ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching purchase operations: {e}", exc_info=True)
        return None


async def get_returns_to_partner_document(
    regos_integration_token: str,
    document_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get return purchase document by ID using DocReturnsToPartner/Get endpoint.
    
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
        from regos.api import regos_async_api_request
        
        request_data = {
            "ids": [document_id]
        }
        
        logger.info(f"Fetching return purchase document {document_id}")
        response = await regos_async_api_request(
            endpoint="DocReturnsToPartner/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            logger.debug(f"DocReturnsToPartner/Get response for document {document_id}: {result}")
            
            if result:
                # Handle both list and single object responses
                if isinstance(result, list):
                    if len(result) > 0:
                        logger.info(f"Successfully fetched return purchase document {document_id} (from list)")
                        return result[0] if isinstance(result[0], dict) else None
                    else:
                        logger.warning(f"DocReturnsToPartner/Get returned empty list for document {document_id}")
                elif isinstance(result, dict):
                    logger.info(f"Successfully fetched return purchase document {document_id}")
                    return result
                else:
                    logger.warning(f"DocReturnsToPartner/Get returned unexpected type for document {document_id}: {type(result)}")
            else:
                logger.warning(f"DocReturnsToPartner/Get returned no result for document {document_id}")
        else:
            error_msg = response.get("description", response.get("error", "Unknown error"))
            logger.error(f"DocReturnsToPartner/Get failed for document {document_id}: {error_msg}")
        
        logger.warning(f"No return purchase document found with ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching return purchase document: {e}", exc_info=True)
        return None


async def get_returns_to_partner_operations(
    regos_integration_token: str,
    document_id: int
) -> Optional[list]:
    """
    Get return purchase document operations using ReturnsToPartnerOperation/Get endpoint.
    
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
        from regos.api import regos_async_api_request
        
        # REGOS API expects document_ids (plural) as a list
        request_data = {
            "document_ids": [document_id]
        }
        
        logger.info(f"Fetching return purchase operations for document {document_id}")
        response = await regos_async_api_request(
            endpoint="ReturnsToPartnerOperation/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            if result:
                # Handle both list and single object responses
                operations = result if isinstance(result, list) else [result]
                logger.info(f"Successfully fetched {len(operations)} operation(s) for return purchase document {document_id}")
                return operations
        
        logger.warning(f"No operations found for return purchase document ID: {document_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching return purchase operations: {e}", exc_info=True)
        return None


async def process_document_event(
    document_id: int,
    regos_integration_token: str,
    telegram_token: str,
    get_document_func,
    get_operations_func,
    is_cancelled: bool = False,
    document_type: str = "wholesale"
) -> bool:
    """
    Shared function to process document events (wholesale, wholesale return, purchase, or return purchase).
    
    Args:
        document_id: Document ID to process
        regos_integration_token: REGOS integration token
        telegram_token: Telegram bot token
        get_document_func: Function to fetch document
        get_operations_func: Function to fetch operations
        is_cancelled: Whether the document is cancelled
        document_type: Type of document ("wholesale", "wholesale_return", "purchase", or "return_purchase")
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    logger.info(f"Processing {document_type} document event for document ID: {document_id}")
    
    # Fetch document and operations
    document = await get_document_func(regos_integration_token, document_id)
    
    logger.debug(f"Document fetch result for {document_id}: {document is not None}, type: {type(document)}")
    if not document:
        logger.warning(f"⚠️ {document_type.capitalize()} document {document_id} not found")
        return False
    
    logger.info(f"{document_type.capitalize()} document {document_id} retrieved successfully, has {len(document)} fields")
    operations = await get_operations_func(regos_integration_token, document_id)
    
    if not operations:
        logger.warning(f"⚠️ No operations found for {document_type} document {document_id}")
        return False
    
    # Get partner object from document (for oked field)
    partner = document.get("partner")
    
    if not partner or not isinstance(partner, dict):
        logger.warning(f"⚠️ {document_type.capitalize()} document {document_id} does not have partner object or partner is not a dictionary")
        return False
    
    # Extract partner ID and oked from partner object
    partner_id = partner.get("id")
    oked = partner.get("oked")
    
    # Get warehouse/stock information for display name
    # Try to extract stock_id from different possible locations in document
    stock_id = None
    stock_obj = document.get("stock")
    
    if isinstance(stock_obj, dict):
        stock_id = stock_obj.get("id")
    elif stock_id is None:
        stock_id = document.get("stock_id")
    
    warehouse_name = None
    
    if stock_id:
        stock = await get_stock_by_id(regos_integration_token, stock_id)
        if stock:
            warehouse_name = stock.get("name", "Склад")
            logger.info(f"Found warehouse: {warehouse_name} (ID: {stock_id})")
        else:
            logger.warning(f"⚠️ Stock {stock_id} not found, using default name")
            warehouse_name = "Склад"
    else:
        logger.warning(f"⚠️ Document {document_id} does not have stock_id or stock object, using default name")
        warehouse_name = "Склад"
    
    logger.info(f"Found partner object in document: Partner ID: {partner_id}, Warehouse: {warehouse_name}")
    
    # Check if oked field is not null and contains Telegram chat ID
    if oked is None:
        logger.info(f"ℹ️ Partner {partner_id} oked field is null (no Telegram chat ID)")
        return False
    
    # Handle both string and numeric types
    try:
        if isinstance(oked, str):
            oked_cleaned = oked.strip()
            if oked_cleaned:
                telegram_chat_id = int(oked_cleaned)
            else:
                logger.info(f"ℹ️ Partner {partner_id} oked field is empty string")
                return False
        elif isinstance(oked, (int, float)):
            telegram_chat_id = int(oked)
        else:
            logger.warning(f"⚠️ Partner {partner_id} oked field has unexpected type: {type(oked)}")
            return False
        
        # Format receipt message (with cancelled notice if applicable)
        is_return = document_type in ["wholesale_return", "return_purchase"]
        use_cost = document_type in ["purchase", "return_purchase"]
        receipt_message = format_wholesale_receipt(
            document,
            operations,
            warehouse_name,
            is_cancelled=is_cancelled,
            is_return=is_return,
            use_cost=use_cost
        )
        
        # Send message via Telegram bot
        result = await bot_manager.send_message(
            telegram_token,
            telegram_chat_id,
            receipt_message,
            parse_mode="Markdown"
        )
        
        if result:
            status_text = "cancelled receipt" if is_cancelled else "receipt"
            logger.info(
                f"✅ Successfully sent {status_text} to Telegram user {telegram_chat_id} "
                f"for {document_type} document {document_id} (warehouse: {warehouse_name})"
            )
            return True
        else:
            logger.warning(f"⚠️ Failed to send receipt to Telegram user {telegram_chat_id}")
            return False
            
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Partner {partner_id} oked field '{oked}' is not a valid Telegram chat ID: {e}")
        return False


async def process_payment_event(
    document_id: int,
    regos_integration_token: str,
    telegram_token: str,
    is_cancelled: bool = False
) -> bool:
    """
    Process payment document events (DocPaymentPerformed, DocPaymentPerformCanceled).
    
    Args:
        document_id: Payment document ID to process
        regos_integration_token: REGOS integration token
        telegram_token: Telegram bot token
        is_cancelled: Whether the payment is cancelled
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    logger.info(f"Processing payment event for document ID: {document_id} (cancelled: {is_cancelled})")
    
    # Fetch payment document (direction will be determined from category.positive)
    document = await get_payment_document(regos_integration_token, document_id)
    
    if not document:
        logger.warning(f"⚠️ Payment document {document_id} not found")
        return False
    
    logger.info(f"Payment document {document_id} retrieved successfully")
    
    # Get partner object from document (for oked field)
    partner = document.get("partner")
    
    if not partner or not isinstance(partner, dict):
        logger.warning(f"⚠️ Payment document {document_id} does not have partner object or partner is not a dictionary")
        return False
    
    # Extract partner ID and oked from partner object
    partner_id = partner.get("id")
    oked = partner.get("oked")
    
    # Get warehouse/stock information for display name
    stock_id = None
    stock_obj = document.get("stock")
    
    if isinstance(stock_obj, dict):
        stock_id = stock_obj.get("id")
    elif stock_id is None:
        stock_id = document.get("stock_id")
    
    warehouse_name = None
    
    if stock_id:
        stock = await get_stock_by_id(regos_integration_token, stock_id)
        if stock:
            warehouse_name = stock.get("name", "Склад")
            logger.info(f"Found warehouse: {warehouse_name} (ID: {stock_id})")
        else:
            logger.warning(f"⚠️ Stock {stock_id} not found, using default name")
            warehouse_name = "Склад"
    else:
        logger.warning(f"⚠️ Payment document {document_id} does not have stock_id or stock object, using default name")
        warehouse_name = "Склад"
    
    logger.info(f"Found partner object in payment document: Partner ID: {partner_id}, Warehouse: {warehouse_name}")
    
    # Check if oked field is not null and contains Telegram chat ID
    if oked is None:
        logger.info(f"ℹ️ Partner {partner_id} oked field is null (no Telegram chat ID)")
        return False
    
    # Handle both string and numeric types
    try:
        if isinstance(oked, str):
            oked_cleaned = oked.strip()
            if oked_cleaned:
                telegram_chat_id = int(oked_cleaned)
            else:
                logger.info(f"ℹ️ Partner {partner_id} oked field is empty string")
                return False
        elif isinstance(oked, (int, float)):
            telegram_chat_id = int(oked)
        else:
            logger.warning(f"⚠️ Partner {partner_id} oked field has unexpected type: {type(oked)}")
            return False
        
        # Format payment notification message
        payment_message = format_payment_notification(
            document,
            warehouse_name,
            is_cancelled=is_cancelled
        )
        
        # Send message via Telegram bot
        result = await bot_manager.send_message(
            telegram_token,
            telegram_chat_id,
            payment_message,
            parse_mode="Markdown"
        )
        
        if result:
            status_text = "cancelled payment notification" if is_cancelled else "payment notification"
            logger.info(
                f"✅ Successfully sent {status_text} to Telegram user {telegram_chat_id} "
                f"for payment document {document_id} (warehouse: {warehouse_name})"
            )
            return True
        else:
            logger.warning(f"⚠️ Failed to send payment notification to Telegram user {telegram_chat_id}")
            return False
            
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Partner {partner_id} oked field '{oked}' is not a valid Telegram chat ID: {e}")
        return False


async def handle_regos_webhook(request: Request) -> Dict[str, Any]:
    """
    Handle incoming webhooks from REGOS.
    
    According to REGOS webhook documentation (https://docs.regos.uz/ru/integration/webhooks#vvedenie):
    Webhook payload structure:
    {
      "action": "HandleWebhook",
      "event_id": "uuid",
      "occurred_at": "ISO8601 timestamp",
      "connected_integration_id": "string",
      "data": {
        "action": "EventName",
        "data": {...}
      }
    }
    """
    try:
        webhook_data = await request.json()
        logger.info(f"Received REGOS webhook: {webhook_data.get('action', 'unknown')}")
        
        # Check for duplicate webhook events using event_id
        event_id = webhook_data.get("event_id")
        if event_id:
            # Cleanup old entries (older than 1 hour)
            current_time = datetime.utcnow()
            expired_events = [
                eid for eid, timestamp in processed_webhook_events.items()
                if current_time - timestamp > timedelta(hours=1)
            ]
            for eid in expired_events:
                del processed_webhook_events[eid]
            
            # Check if this event was already processed
            if event_id in processed_webhook_events:
                logger.warning(
                    f"⚠️ Duplicate webhook event detected: {event_id}. "
                    f"Originally processed at {processed_webhook_events[event_id]}. Skipping processing."
                )
                return {"ok": True, "message": "Event already processed", "duplicate": True}
            
            # Mark this event as processed
            processed_webhook_events[event_id] = current_time
            logger.debug(f"Marked event {event_id} as processed at {current_time}")
        
        # Extract connected_integration_id from webhook
        connected_integration_id = webhook_data.get("connected_integration_id")
        if not connected_integration_id:
            logger.warning("REGOS webhook missing connected_integration_id")
            return {"ok": False, "error": "Missing connected_integration_id"}
        
        # Find bot with matching regos_integration_token
        db = await get_db()
        async with db.async_session_maker() as session:
            bot_repo = BotRepository(session)
            active_bots = await bot_repo.get_all_active()
            
            matching_bot = None
            for bot in active_bots:
                if bot.regos_integration_token and bot.regos_integration_token == connected_integration_id:
                    matching_bot = bot
                    break
            
            if matching_bot:
                # Log the webhook event
                event_action = webhook_data.get("data", {}).get("action", "unknown")
                occurred_at = webhook_data.get("occurred_at", "unknown")
                
                logger.info(
                    f"✅ REGOS Webhook matched bot: {matching_bot.bot_name or matching_bot.telegram_token[:10]} "
                    f"(bot_id: {matching_bot.bot_id})"
                )
                logger.info(
                    f"   Event: {event_action} | Event ID: {event_id} | Occurred at: {occurred_at}"
                )
                
                # Process DocWholeSalePerformed and DocWholeSalePerformCanceled events
                if event_action in ["DocWholeSalePerformed", "DocWholeSalePerformCanceled"]:
                    event_data = webhook_data.get("data", {}).get("data", {})
                    document_id = event_data.get("id")
                    is_cancelled = event_action == "DocWholeSalePerformCanceled"
                    
                    if document_id:
                        await process_document_event(
                            document_id=document_id,
                            regos_integration_token=matching_bot.regos_integration_token,
                            telegram_token=matching_bot.telegram_token,
                            get_document_func=get_wholesale_document,
                            get_operations_func=get_wholesale_operations,
                            is_cancelled=is_cancelled,
                            document_type="wholesale"
                        )
                    else:
                        logger.warning(f"⚠️ {event_action} event missing document ID")
                
                # Process DocWholeSaleReturnPerformed and DocWholeSaleReturnPerformCanceled events
                elif event_action in ["DocWholeSaleReturnPerformed", "DocWholeSaleReturnPerformCanceled"]:
                    event_data = webhook_data.get("data", {}).get("data", {})
                    document_id = event_data.get("id")
                    is_cancelled = event_action == "DocWholeSaleReturnPerformCanceled"
                    
                    if document_id:
                        await process_document_event(
                            document_id=document_id,
                            regos_integration_token=matching_bot.regos_integration_token,
                            telegram_token=matching_bot.telegram_token,
                            get_document_func=get_wholesale_return_document,
                            get_operations_func=get_wholesale_return_operations,
                            is_cancelled=is_cancelled,
                            document_type="wholesale_return"
                        )
                    else:
                        logger.warning(f"⚠️ {event_action} event missing document ID")
                
                # Process DocPurchasePerformed and DocPurchasePerformCanceled events
                elif event_action in ["DocPurchasePerformed", "DocPurchasePerformCanceled"]:
                    event_data = webhook_data.get("data", {}).get("data", {})
                    document_id = event_data.get("id")
                    is_cancelled = event_action == "DocPurchasePerformCanceled"
                    
                    if document_id:
                        await process_document_event(
                            document_id=document_id,
                            regos_integration_token=matching_bot.regos_integration_token,
                            telegram_token=matching_bot.telegram_token,
                            get_document_func=get_purchase_document,
                            get_operations_func=get_purchase_operations,
                            is_cancelled=is_cancelled,
                            document_type="purchase"
                        )
                    else:
                        logger.warning(f"⚠️ {event_action} event missing document ID")
                
                # Process DocReturnsToPartnerPerformed and DocReturnsToPartnerPerformCanceled events
                elif event_action in ["DocReturnsToPartnerPerformed", "DocReturnsToPartnerPerformCanceled"]:
                    event_data = webhook_data.get("data", {}).get("data", {})
                    document_id = event_data.get("id")
                    is_cancelled = event_action == "DocReturnsToPartnerPerformCanceled"
                    
                    if document_id:
                        await process_document_event(
                            document_id=document_id,
                            regos_integration_token=matching_bot.regos_integration_token,
                            telegram_token=matching_bot.telegram_token,
                            get_document_func=get_returns_to_partner_document,
                            get_operations_func=get_returns_to_partner_operations,
                            is_cancelled=is_cancelled,
                            document_type="return_purchase"
                        )
                    else:
                        logger.warning(f"⚠️ {event_action} event missing document ID")
                
                # Process DocPaymentPerformed and DocPaymentPerformCanceled events
                elif event_action in ["DocPaymentPerformed", "DocPaymentPerformCanceled"]:
                    event_data = webhook_data.get("data", {}).get("data", {})
                    document_id = event_data.get("id")
                    is_cancelled = event_action == "DocPaymentPerformCanceled"
                    
                    if document_id:
                        await process_payment_event(
                            document_id=document_id,
                            regos_integration_token=matching_bot.regos_integration_token,
                            telegram_token=matching_bot.telegram_token,
                            is_cancelled=is_cancelled
                        )
                    else:
                        logger.warning(f"⚠️ {event_action} event missing document ID")
                
                return {"ok": True, "message": "Webhook processed", "bot_id": matching_bot.bot_id}
            else:
                logger.warning(
                    f"REGOS webhook received but no matching bot found for integration_id: {connected_integration_id[:20]}..."
                )
                return {"ok": False, "error": "No matching bot found for this integration_id"}
    
    except Exception as e:
        logger.error(f"Error processing REGOS webhook: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}

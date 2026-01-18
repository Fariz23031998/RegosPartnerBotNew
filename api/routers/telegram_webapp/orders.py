"""
Order management endpoints for Telegram Web App.
Handles order listing, details, and creation.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Body

from database import get_db
from database.repositories import BotSettingsRepository
from regos.api import regos_async_api_request
from core.utils import convert_to_unix_timestamp
from .auth import verify_telegram_user, verify_partner_telegram_id
from .schemas import CreateOrderRequest

logger = logging.getLogger(__name__)
router = APIRouter()


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
            "deleted_mark": False,
            "sort_orders": [
                {
                "column": "Date",
                "direction": "DESC"
                }
            ]
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
        
        if not response.get("ok"):
            raise HTTPException(status_code=400, detail="Failed to fetch orders")
        
        orders = response.get("result", [])
        if not isinstance(orders, list):
            orders = [orders] if orders else []
        
        # Fetch operations for each order individually (API only accepts one document_id at a time)
        # OrderFromPartnerOperation/Get accepts document_ids array but only with a single element
        operations_by_order = {}
        order_ids = [order.get("id") for order in orders if order.get("id")]
        
        if order_ids:
            # Fetch operations for each order one by one
            for order_id in order_ids:
                try:
                    ops_response = await regos_async_api_request(
                        endpoint="OrderFromPartnerOperation/Get",
                        request_data={"document_ids": [order_id]},
                        token=regos_token,
                        timeout_seconds=30
                    )
                    
                    if ops_response.get("ok"):
                        ops_result = ops_response.get("result", [])
                        operations = ops_result if isinstance(ops_result, list) else [ops_result] if ops_result else []
                        
                        if operations:
                            operations_by_order[order_id] = operations
                except Exception as e:
                    logger.warning(f"Failed to fetch operations for order {order_id}: {e}")
                    continue
        
        # Attach operations to each order and filter to only include orders with operations
        orders_with_ops = []
        for order in orders:
            order_id = order.get("id")
            if not order_id:
                continue
            
            # Try to match order_id (might be int or could be string)
            matched_ops = None
            if order_id in operations_by_order:
                matched_ops = operations_by_order[order_id]
            else:
                # Try converting to int
                try:
                    order_id_int = int(order_id)
                    if order_id_int in operations_by_order:
                        matched_ops = operations_by_order[order_id_int]
                except (ValueError, TypeError):
                    pass
            
            # Only include orders that have operations
            if matched_ops:
                order["operations"] = matched_ops
                orders_with_ops.append(order)
        
        return {
            "ok": True,
            "orders": orders_with_ops
        }
            
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
        current_timestamp = int(datetime.now().timestamp())
        
        # Build description with address/type and phone number
        description_parts = []
        if request.is_takeaway:
            description_parts.append("С собой")
        elif request.address:
            description_parts.append(f"Адрес: {request.address}")
        
        # Always include phone number in description
        if request.phone:
            description_parts.append(f"Телефон: {request.phone}")
        else:
            description_parts.append("Телефон: не указан")
        
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

"""
Products and shop endpoints for Telegram Web App.
Handles bot settings, products, and product groups.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from database import get_db
from database.repositories import BotSettingsRepository
from regos.api import regos_async_api_request
from .auth import verify_telegram_user

logger = logging.getLogger(__name__)
router = APIRouter()


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
    zero_quantity: bool = Query(True, description="Include products with zero quantity"),
    filter_type: Optional[str] = Query(None, description="Filter type: in-stock, low-stock, cheap, expensive"),
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
        
        # Convert to int if they're strings (from query params)
        if final_stock_id:
            try:
                final_stock_id = int(final_stock_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid stock_id value: {final_stock_id}")
                final_stock_id = None
        
        if final_price_type_id:
            try:
                final_price_type_id = int(final_price_type_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid price_type_id value: {final_price_type_id}")
                final_price_type_id = None
        
        if not final_stock_id or not final_price_type_id:
            error_detail = "Stock ID and Price Type ID must be configured in bot settings or provided as parameters"
            if bot_settings:
                error_detail += f". Current settings: stock_id={bot_settings.online_store_stock_id}, price_type_id={bot_settings.online_store_price_type_id}"
            else:
                error_detail += ". Bot settings not found for this bot."
            logger.warning(f"Products endpoint error for bot_id={bot_id}, telegram_user_id={telegram_user_id}: {error_detail}")
            raise HTTPException(
                status_code=400,
                detail=error_detail
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
            "zero_quantity": zero_quantity,  # Use parameter value (default True)
            "zero_price": False,
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
        
        # Build filters array based on filter_type
        # According to Regos API docs: https://docs.regos.uz/ru/api/other/filter
        # Filters use: field (string), operator (Enum: Equal, Greater, Less, etc.), value (string)
        filters = []
        if filter_type:
            if filter_type == "in-stock":
                # В наличии: quantity.allowed > 0
                filters.append({
                    "field": "quantity.allowed",
                    "operator": "Greater",
                    "value": "0"
                })
            elif filter_type == "low-stock":
                # Мало: quantity.allowed > 0 AND quantity.allowed <= 10
                filters.append({
                    "field": "quantity.allowed",
                    "operator": "Greater",
                    "value": "0"
                })
                filters.append({
                    "field": "quantity.allowed",
                    "operator": "LessOrEqual",
                    "value": "10"
                })
            elif filter_type == "cheap":
                # Дешевые: price < 100000
                filters.append({
                    "field": "price",
                    "operator": "Less",
                    "value": "100000"
                })
            elif filter_type == "expensive":
                # Дорогие: price >= 100000
                filters.append({
                    "field": "price",
                    "operator": "GreaterOrEqual",
                    "value": "100000"
                })
        
        if filters:
            request_data["filters"] = filters
        
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
        
        # Return all products (filtering by stock will be done on frontend if needed)
        return {
            "ok": True,
            "products": result,
            "next_offset": response.get("next_offset", 0),
            "total": response.get("total", len(result))
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

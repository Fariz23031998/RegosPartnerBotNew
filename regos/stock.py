"""
REGOS Stock/Warehouse operations.
"""
import logging
from typing import Optional, Dict, Any
from regos.api import regos_async_api_request
from config import APP_NAME

logger = logging.getLogger(APP_NAME)


async def get_stock_by_id(
    regos_integration_token: str,
    stock_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get stock/warehouse by ID using Stock/Get endpoint.
    
    Args:
        regos_integration_token: REGOS integration token
        stock_id: Stock/Warehouse ID to fetch
        
    Returns:
        dict: Stock data if found, None otherwise
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided")
        return None
    
    try:
        request_data = {
            "id": stock_id
        }
        
        logger.info(f"Fetching stock/warehouse {stock_id}")
        response = await regos_async_api_request(
            endpoint="Stock/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            if result:
                # Handle both list and single object responses
                if isinstance(result, list):
                    if len(result) > 0:
                        stock = result[0]
                        if isinstance(stock, dict):
                            logger.info(f"Successfully fetched stock {stock_id}: {stock.get('name', 'Unknown')}")
                            return stock
                elif isinstance(result, dict):
                    logger.info(f"Successfully fetched stock {stock_id}: {result.get('name', 'Unknown')}")
                    return result
        
        logger.warning(f"No stock found with ID: {stock_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching stock by ID: {e}", exc_info=True)
        return None

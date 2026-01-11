"""
REGOS Field management operations.
"""
import logging
from typing import Optional
from regos.api import regos_async_api_request
from config import APP_NAME

logger = logging.getLogger(APP_NAME)


async def create_telegram_id_field(regos_integration_token: str) -> Optional[dict]:
    """
    Create a custom field in REGOS for storing Telegram chat ID.
    
    According to REGOS API documentation (https://docs.regos.uz/ru/api/references/field#fieldvalue-model-znacheni):
    - entity_type: Partner
    - key: field_telegram_id
    - name: ID чата в Telegram
    - data_type: string (Telegram chat IDs can be large numbers, string is safer)
    - required: False
    - is_custom: True (user-created field)
    
    Args:
        regos_integration_token: REGOS integration token
        
    Returns:
        dict: REGOS API response with created field data, or None if creation fails
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided, skipping field creation")
        return None
    
    try:
        field_data = {
            "key": "field_telegram_id",
            "name": "ID чата в Telegram",
            "entity_type": "Partner",
            "data_type": "string",
            "is_custom": True,
            "required": False
        }
        
        logger.info(f"Creating REGOS field 'field_telegram_id' for Partner entity")
        response = await regos_async_api_request(
            endpoint="Field/Add",
            request_data=field_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        logger.info(f"Successfully created REGOS field: {response}")
        return response
        
    except Exception as e:
        # Log error but don't fail bot creation if field already exists or creation fails
        logger.error(f"Failed to create REGOS field 'field_telegram_id': {e}")
        # Check if field already exists (common case - field might have been created before)
        if "already exists" in str(e).lower() or "уже существует" in str(e).lower():
            logger.info("Field 'field_telegram_id' may already exist in REGOS, continuing...")
        return None


async def check_field_exists(regos_integration_token: str, field_key: str) -> bool:
    """
    Check if a field with the given key already exists in REGOS.
    
    Args:
        regos_integration_token: REGOS integration token
        field_key: The key of the field to check
        
    Returns:
        bool: True if field exists, False otherwise
    """
    if not regos_integration_token:
        return False
    
    try:
        # Try to get fields filtered by entity_type Partner
        # REGOS API Field/Get may accept filters or empty dict
        try:
            response = await regos_async_api_request(
                endpoint="Field/Get",
                request_data={"entity_type": "Partner"},
                token=regos_integration_token,
                timeout_seconds=30
            )
        except:
            # If filtered request fails, try without filters
            response = await regos_async_api_request(
                endpoint="Field/Get",
                request_data={},
                token=regos_integration_token,
                timeout_seconds=30
            )
        
        if response.get("ok"):
            result = response.get("result")
            # Handle both list and single object responses
            if result:
                fields = result if isinstance(result, list) else [result]
                
                for field in fields:
                    if isinstance(field, dict):
                        # Check if this is a Partner field with matching key
                        if (field.get("key") == field_key and 
                            field.get("entity_type") == "Partner"):
                            logger.info(f"Field '{field_key}' already exists in REGOS for Partner entity")
                            return True
        
        return False
        
    except Exception as e:
        # If Field/Get fails, we'll try to create anyway
        # The creation endpoint will handle "already exists" errors gracefully
        logger.debug(f"Could not check if field exists (will attempt creation): {e}")
        return False


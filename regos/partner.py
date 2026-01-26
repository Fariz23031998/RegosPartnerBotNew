"""
REGOS Partner operations.
"""
import logging
from typing import Optional, List, Dict, Any
from regos.api import regos_async_api_request
from config import APP_NAME

logger = logging.getLogger(APP_NAME)


async def search_partner_by_phone(
    regos_integration_token: str,
    phone_number: str
) -> Optional[Dict[str, Any]]:
    """
    Search for a partner in REGOS by phone number.
    
    According to REGOS API documentation (https://docs.regos.uz/uz/api/store/docpurchase/get):
    - Uses Partner/Get endpoint with search parameter
    - Search parameter can search by phone number, name, INN, etc.
    
    Args:
        regos_integration_token: REGOS integration token
        phone_number: Phone number to search for (can be with or without + prefix)
        
    Returns:
        dict: Partner data if found, None otherwise
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided")
        return None
    
    try:
        # Normalize phone number for search
        # Remove common formatting characters
        normalized_phone = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        # Remove + prefix if present for search (REGOS might store without +)
        search_phone = normalized_phone.lstrip("+")
        
        # Partner/Get endpoint with search parameter
        # According to REGOS docs, search can match phones field
        request_data = {
            "deleted_mark": False
        }
        
        logger.info(f"Searching for partner with phone: {search_phone}")
        response = await regos_async_api_request(
            endpoint="Partner/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            # Handle both list and single object responses
            if result:
                partners = result if isinstance(result, list) else [result]
                
                # Find partner matching the phone number
                for partner in partners:
                    if isinstance(partner, dict):
                        partner_phones = partner.get("phones", "")
                        partner_phone_str = partner_phones if partner_phones else "#############"
                        logger.info(f"Phone: {partner_phones}")
                        
                        # Normalize partner's phone for comparison
                        partner_phone_normalized = partner_phone_str.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").lstrip("+")
                        
                        # Check if phone matches (exact match or contains)
                        if (search_phone in partner_phone_normalized or 
                            partner_phone_normalized in search_phone or
                            normalized_phone in partner_phone_str or
                            partner_phone_str in normalized_phone):
                            logger.info(f"Found partner: {partner.get('id')} - {partner.get('name')}")
                            return partner
                
        
        logger.info(f"No partner found with phone: {search_phone}")
        return None
        
    except Exception as e:
        logger.error(f"Error searching for partner by phone: {e}", exc_info=True)
        return None


async def get_partner_by_id(
    regos_integration_token: str,
    partner_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get partner by ID using Partner/Get endpoint.
    
    According to REGOS API documentation (https://docs.regos.uz/uz/api/references/partner/get):
    - Uses Partner/Get endpoint with id parameter
    
    Args:
        regos_integration_token: REGOS integration token
        partner_id: Partner ID to fetch
        
    Returns:
        dict: Partner data if found, None otherwise
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided")
        return None
    
    try:
        request_data = {
            "id": partner_id
        }
        
        logger.info(f"Fetching partner {partner_id}")
        response = await regos_async_api_request(
            endpoint="Partner/Get",
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
                        return result[0]
                elif isinstance(result, dict):
                    return result
        
        logger.warning(f"No partner found with ID: {partner_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error fetching partner by ID: {e}", exc_info=True)
        return None


async def update_partner_telegram_id(
    regos_integration_token: str,
    partner_id: int,
    telegram_chat_id: str,
    existing_partner_data: Dict[str, Any],
    lang_code: str = "en"
) -> bool:
    """
    Update partner's oked field with Telegram chat ID using Partner/Edit endpoint.
    
    According to REGOS API documentation (https://docs.regos.uz/uz/api/store/partner/edit):
    - Uses Partner/Edit endpoint
    - Updates the oked field with Telegram chat ID (as per user requirement)
    
    Note: According to REGOS API, when editing a Partner, we need to send all fields.
    The oked field will be updated with the Telegram chat ID.
    
    Args:
        regos_integration_token: REGOS integration token
        partner_id: Partner ID to update
        telegram_chat_id: Telegram chat ID to store (as string in oked field)
        existing_partner_data: Current partner data from Partner/Get (needed for edit)
        
    Returns:
        bool: True if update successful, False otherwise
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided")
        return False
    
    try:
        # Prepare edit data - REGOS Partner/Edit typically requires all fields
        edit_data = {
            "id": partner_id,
            "oked": str(telegram_chat_id),  # Store Telegram chat ID in oked field (as per requirement)
            "rs": lang_code
        }
   
        logger.info(f"Updating partner {partner_id} ({existing_partner_data.get('name')}) with Telegram chat ID: {telegram_chat_id}")
        response = await regos_async_api_request(
            endpoint="Partner/Edit",
            request_data=edit_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            logger.info(f"Successfully updated partner {partner_id} with Telegram chat ID in oked field")
            return True
        else:
            error_msg = response.get("description", response.get("error", "Unknown error"))
            logger.error(f"Failed to update partner {partner_id}: {error_msg}")
            return False
        
    except Exception as e:
        logger.error(f"Error updating partner with Telegram ID: {e}", exc_info=True)
        return False


async def search_partner_by_telegram_id(
    regos_integration_token: str,
    telegram_chat_id: str
) -> Optional[Dict[str, Any]]:
    """
    Search for a partner in REGOS by Telegram chat ID (stored in oked field).
    
    Args:
        regos_integration_token: REGOS integration token
        telegram_chat_id: Telegram chat ID to search for (as string)
        
    Returns:
        dict: Partner data if found, None otherwise
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided")
        return None
    
    try:
        # Partner/Get endpoint to get all partners
        request_data = {
            "deleted_mark": False
        }
        
        logger.info(f"Searching for partner with Telegram chat ID: {telegram_chat_id}")
        response = await regos_async_api_request(
            endpoint="Partner/Get",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result")
            # Handle both list and single object responses
            if result:
                partners = result if isinstance(result, list) else [result]
                
                # Find partner matching the Telegram chat ID in oked field
                for partner in partners:
                    if isinstance(partner, dict):
                        partner_oked = partner.get("oked", "")
                        # Compare as strings (oked field stores Telegram ID as string)
                        if partner_oked and str(partner_oked) == str(telegram_chat_id):
                            logger.info(f"Found partner: {partner.get('id')} - {partner.get('name')}")
                            return partner
        
        logger.info(f"No partner found with Telegram chat ID: {telegram_chat_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error searching for partner by Telegram ID: {e}", exc_info=True)
        return None


async def register_partner(
    regos_integration_token: str,
    group_id: int,
    name: str,
    full_name: str,
    phones: str,
    telegram_user_id: str,
    lang_code: str = "en"
) -> Optional[Dict[str, Any]]:
    """
    Register a new partner in REGOS using Partner/Add endpoint.
    
    Args:
        regos_integration_token: REGOS integration token
        group_id: Partner group ID (from bot settings partner_group_id)
        name: Partner name (short)
        full_name: Partner full name
        phones: Partner phone numbers (comma-separated)
        telegram_user_id: Telegram user ID to store in oked field
        
    Returns:
        dict: Registration result with new_id if successful, None otherwise
    """
    if not regos_integration_token:
        logger.warning("REGOS integration token not provided")
        return None
    
    try:
        request_data = {
            "group_id": group_id,
            "legal_status": "Legal",
            "name": name,
            "fullName": full_name,
            "phones": phones,
            "oked": telegram_user_id,  # Store Telegram user ID in oked field
            "rs": lang_code
        }
        
        logger.info(f"Registering new partner: {name} ({full_name})")
        response = await regos_async_api_request(
            endpoint="Partner/Add",
            request_data=request_data,
            token=regos_integration_token,
            timeout_seconds=30
        )
        
        if response.get("ok"):
            result = response.get("result", {})
            new_id = result.get("new_id")
            if new_id:
                logger.info(f"Successfully registered partner with ID: {new_id}")
                return {"ok": True, "new_id": new_id}
            else:
                logger.warning("Partner registration response missing new_id")
                return None
        else:
            error_msg = response.get("description", response.get("error", "Unknown error"))
            logger.error(f"Failed to register partner: {error_msg}")
            return None
        
    except Exception as e:
        logger.error(f"Error registering partner: {e}", exc_info=True)
        return None

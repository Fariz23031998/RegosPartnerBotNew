"""
Bot settings management API routes.
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from database import get_db
from database.repositories import BotSettingsRepository, BotRepository
from api.schemas import BotSettingsCreate, BotSettingsUpdate, BotSettingsResponse
from auth import verify_admin, verify_user, check_bot_ownership

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bot-settings", tags=["bot-settings"])


@router.post("", response_model=BotSettingsResponse)
async def create_bot_settings(
    settings: BotSettingsCreate,
    current_user: dict = Depends(verify_user)
):
    """Create new bot settings - users can only create settings for their own bots"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            bot_repo = BotRepository(session)
            settings_repo = BotSettingsRepository(session)
            
            # Verify bot exists
            bot = await bot_repo.get_by_id(settings.bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            
            # Check ownership
            if not await check_bot_ownership(settings.bot_id, current_user):
                raise HTTPException(
                    status_code=403,
                    detail="You can only manage settings for your own bots"
                )
            
            # Check if settings already exist for this bot
            existing = await settings_repo.get_by_bot_id(settings.bot_id)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail="Bot settings already exist for this bot. Use update endpoint instead."
                )
            
            # Create settings
            bot_settings = await settings_repo.create(
                bot_id=settings.bot_id,
                online_store_stock_id=settings.online_store_stock_id,
                online_store_price_type_id=settings.online_store_price_type_id,
                online_store_currency_id=settings.online_store_currency_id
            )
            
            return BotSettingsResponse(
                id=bot_settings.id,
                bot_id=bot_settings.bot_id,
                online_store_stock_id=bot_settings.online_store_stock_id,
                online_store_price_type_id=bot_settings.online_store_price_type_id,
                online_store_currency_id=bot_settings.online_store_currency_id,
                created_at=bot_settings.created_at.isoformat(),
                updated_at=bot_settings.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[BotSettingsResponse])
async def get_all_bot_settings(
    current_user: dict = Depends(verify_user)
):
    """Get all bot settings - users only see settings for their own bots"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            bot_repo = BotRepository(session)
            role = current_user.get("role", "admin")
            current_user_id = current_user.get("user_id")
            
            if role == "admin":
                all_settings = await settings_repo.get_all()
            else:
                if not current_user_id:
                    raise HTTPException(status_code=400, detail="User ID not found in token")
                # Get all bots for user, then get settings for those bots
                user_bots = await bot_repo.get_by_user(current_user_id)
                bot_ids = [bot.bot_id for bot in user_bots]
                all_settings = []
                for bot_id in bot_ids:
                    settings = await settings_repo.get_by_bot_id(bot_id)
                    if settings:
                        all_settings.append(settings)
            
            return [
                BotSettingsResponse(
                    id=settings.id,
                    bot_id=settings.bot_id,
                    online_store_stock_id=settings.online_store_stock_id,
                    online_store_price_type_id=settings.online_store_price_type_id,
                    online_store_currency_id=settings.online_store_currency_id,
                    created_at=settings.created_at.isoformat(),
                    updated_at=settings.updated_at.isoformat()
                )
                for settings in all_settings
            ]
    except Exception as e:
        logger.error(f"Error fetching bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{settings_id}", response_model=BotSettingsResponse)
async def get_bot_settings(
    settings_id: int,
    current_user: dict = Depends(verify_user)
):
    """Get bot settings by ID - users can only get settings for their own bots"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            bot_settings = await settings_repo.get_by_id(settings_id)
            
            if not bot_settings:
                raise HTTPException(status_code=404, detail="Bot settings not found")
            
            # Check ownership
            if not await check_bot_ownership(bot_settings.bot_id, current_user):
                raise HTTPException(
                    status_code=403,
                    detail="You can only access settings for your own bots"
                )
            
            return BotSettingsResponse(
                id=bot_settings.id,
                bot_id=bot_settings.bot_id,
                online_store_stock_id=bot_settings.online_store_stock_id,
                online_store_price_type_id=bot_settings.online_store_price_type_id,
                online_store_currency_id=bot_settings.online_store_currency_id,
                created_at=bot_settings.created_at.isoformat(),
                updated_at=bot_settings.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/bot/{bot_id}", response_model=BotSettingsResponse)
async def get_bot_settings_by_bot_id(
    bot_id: int,
    current_user: dict = Depends(verify_user)
):
    """Get bot settings by bot ID - users can only get settings for their own bots"""
    try:
        # Check ownership
        if not await check_bot_ownership(bot_id, current_user):
            raise HTTPException(
                status_code=403,
                detail="You can only access settings for your own bots"
            )
        
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            bot_settings = await settings_repo.get_by_bot_id(bot_id)
            
            if not bot_settings:
                raise HTTPException(status_code=404, detail="Bot settings not found")
            
            return BotSettingsResponse(
                id=bot_settings.id,
                bot_id=bot_settings.bot_id,
                online_store_stock_id=bot_settings.online_store_stock_id,
                online_store_price_type_id=bot_settings.online_store_price_type_id,
                online_store_currency_id=bot_settings.online_store_currency_id,
                created_at=bot_settings.created_at.isoformat(),
                updated_at=bot_settings.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{settings_id}", response_model=BotSettingsResponse)
async def update_bot_settings(
    settings_id: int,
    settings: BotSettingsUpdate,
    current_user: dict = Depends(verify_user)
):
    """Update bot settings - users can only update settings for their own bots"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            
            # Check if settings exist
            existing = await settings_repo.get_by_id(settings_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Bot settings not found")
            
            # Check ownership
            if not await check_bot_ownership(existing.bot_id, current_user):
                raise HTTPException(
                    status_code=403,
                    detail="You can only update settings for your own bots"
                )
            
            # Update settings
            updated = await settings_repo.update(
                settings_id=settings_id,
                online_store_stock_id=settings.online_store_stock_id,
                online_store_price_type_id=settings.online_store_price_type_id,
                online_store_currency_id=settings.online_store_currency_id
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Bot settings not found after update")
            
            return BotSettingsResponse(
                id=updated.id,
                bot_id=updated.bot_id,
                online_store_stock_id=updated.online_store_stock_id,
                online_store_price_type_id=updated.online_store_price_type_id,
                online_store_currency_id=updated.online_store_currency_id,
                created_at=updated.created_at.isoformat(),
                updated_at=updated.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/bot/{bot_id}", response_model=BotSettingsResponse)
async def update_bot_settings_by_bot_id(
    bot_id: int,
    settings: BotSettingsUpdate,
    current_user: dict = Depends(verify_user)
):
    """Update bot settings by bot ID - users can only update settings for their own bots"""
    try:
        # Check ownership
        if not await check_bot_ownership(bot_id, current_user):
            raise HTTPException(
                status_code=403,
                detail="You can only update settings for your own bots"
            )
        
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            
            # Check if settings exist
            existing = await settings_repo.get_by_bot_id(bot_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Bot settings not found")
            
            # Update settings
            updated = await settings_repo.update_by_bot_id(
                bot_id=bot_id,
                online_store_stock_id=settings.online_store_stock_id,
                online_store_price_type_id=settings.online_store_price_type_id,
                online_store_currency_id=settings.online_store_currency_id
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Bot settings not found after update")
            
            return BotSettingsResponse(
                id=updated.id,
                bot_id=updated.bot_id,
                online_store_stock_id=updated.online_store_stock_id,
                online_store_price_type_id=updated.online_store_price_type_id,
                online_store_currency_id=updated.online_store_currency_id,
                created_at=updated.created_at.isoformat(),
                updated_at=updated.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{settings_id}")
async def delete_bot_settings(
    settings_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Delete bot settings"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            
            # Check if settings exist
            existing = await settings_repo.get_by_id(settings_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Bot settings not found")
            
            # Delete settings
            deleted = await settings_repo.delete(settings_id)
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Bot settings not found")
            
            return {"ok": True, "message": "Bot settings deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/bot/{bot_id}")
async def delete_bot_settings_by_bot_id(
    bot_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Delete bot settings by bot ID"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            settings_repo = BotSettingsRepository(session)
            
            # Check if settings exist
            existing = await settings_repo.get_by_bot_id(bot_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Bot settings not found")
            
            # Delete settings
            deleted = await settings_repo.delete_by_bot_id(bot_id)
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Bot settings not found")
            
            return {"ok": True, "message": "Bot settings deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bot settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

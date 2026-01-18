"""
Bot management API routes.
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from database import get_db
from database.repositories import BotRepository, UserRepository
from api.schemas import BotCreate, BotUpdate, BotResponse
from auth import verify_admin, verify_user, check_bot_ownership
from bot_manager import bot_manager
from regos.fields import create_telegram_id_field, check_field_exists

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bots", tags=["bots"])


@router.post("", response_model=BotResponse)
async def create_bot(
    bot: BotCreate,
    current_user: dict = Depends(verify_user)
):
    """Create a new bot - users can only create bots for themselves"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            user_repo = UserRepository(session)
            bot_repo = BotRepository(session)
            
            role = current_user.get("role", "admin")
            current_user_id = current_user.get("user_id")
            
            # Users can only create bots for themselves
            if role == "user":
                if not current_user_id:
                    raise HTTPException(status_code=400, detail="User ID not found in token")
                if bot.user_id != current_user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="You can only create bots for yourself"
                    )
            
            # Verify user exists
            user = await user_repo.get_by_id(bot.user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Create bot in database
            bot_obj = await bot_repo.create(
                user_id=bot.user_id,
                telegram_token=bot.telegram_token,
                bot_name=bot.bot_name,
                regos_integration_token=bot.regos_integration_token
            )
            
            # Create REGOS field if integration token is provided
            # if bot.regos_integration_token:
            #     try:
            #         # Check if field already exists to avoid duplicate creation
            #         field_exists = await check_field_exists(
            #             bot.regos_integration_token, 
            #             "field_telegram_id"
            #         )
                    
            #         if not field_exists:
            #             await create_telegram_id_field(bot.regos_integration_token)
            #         else:
            #             logger.info("REGOS field 'field_telegram_id' already exists, skipping creation")
            #     except Exception as e:
            #         logger.warning(f"Failed to create REGOS field during bot creation: {e}")
                    # Don't fail bot creation if field creation fails
                    # Field might already exist or token might be invalid
            
            # Register bot in bot manager
            try:
                await bot_manager.register_bot(bot.telegram_token, bot.bot_name)
            except Exception as e:
                logger.error(f"Failed to register bot: {e}")
                # Bot is still saved in DB, but won't be active
            
            return bot_obj.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(
    bot_id: int,
    current_user: dict = Depends(verify_user)
):
    """Get bot by ID - users can only get their own bots"""
    db = await get_db()
    async with db.async_session_maker() as session:
        repo = BotRepository(session)
        bot = await repo.get_by_id(bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Check ownership
        if not await check_bot_ownership(bot_id, current_user):
            raise HTTPException(
                status_code=403,
                detail="You can only access your own bots"
            )
        
        return bot.to_dict()


@router.get("", response_model=List[BotResponse])
async def get_all_bots(
    current_user: dict = Depends(verify_user)
):
    """Get all bots - users only see their own bots"""
    db = await get_db()
    async with db.async_session_maker() as session:
        repo = BotRepository(session)
        role = current_user.get("role", "admin")
        current_user_id = current_user.get("user_id")
        
        if role == "admin":
            bots = await repo.get_all()
        else:
            if not current_user_id:
                raise HTTPException(status_code=400, detail="User ID not found in token")
            bots = await repo.get_by_user(current_user_id)
        
        return [bot.to_dict() for bot in bots]


@router.get("/users/{user_id}/bots", response_model=List[BotResponse])
async def get_user_bots(
    user_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Get all bots for a user"""
    db = await get_db()
    async with db.async_session_maker() as session:
        repo = BotRepository(session)
        bots = await repo.get_by_user(user_id)
        return [bot.to_dict() for bot in bots]


@router.patch("/{bot_id}", response_model=BotResponse)
async def update_bot(
    bot_id: int,
    bot_update: BotUpdate,
    current_user: dict = Depends(verify_user)
):
    """Update bot (name, regos token, telegram token, or status) - users can only update their own bots"""
    from datetime import datetime
    
    # Check ownership
    if not await check_bot_ownership(bot_id, current_user):
        raise HTTPException(
            status_code=403,
            detail="You can only update your own bots"
        )
    
    db = await get_db()
    
    # Prepare update parameters - only include fields that are explicitly set
    # Convert empty strings to None for optional fields
    update_params = {}
    if bot_update.telegram_token is not None:
        # Only update if provided and not empty (empty string means keep current)
        token_str = (bot_update.telegram_token or "").strip()
        if token_str:
            update_params["telegram_token"] = token_str
    if bot_update.bot_name is not None:
        # Convert empty string to None
        name_str = (bot_update.bot_name or "").strip()
        update_params["bot_name"] = name_str if name_str else None
    if bot_update.regos_integration_token is not None:
        # Convert empty string to None (allows clearing the token)
        regos_str = (bot_update.regos_integration_token or "").strip()
        update_params["regos_integration_token"] = regos_str if regos_str else None
    if bot_update.is_active is not None:
        # Check subscription if trying to activate
        if bot_update.is_active:
            async with db.async_session_maker() as session:
                repo = BotRepository(session)
                bot_obj = await repo.get_by_id(bot_id)
                if not bot_obj:
                    raise HTTPException(status_code=404, detail="Bot not found")
                
                # Check if subscription is active and not expired
                if not bot_obj.subscription_active:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot activate bot: subscription is not active. Please contact admin to activate subscription."
                    )
                
                if bot_obj.subscription_expires_at and bot_obj.subscription_expires_at <= datetime.utcnow():
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot activate bot: subscription has expired. Please contact admin to renew subscription."
                    )
        
        update_params["is_active"] = bot_update.is_active
    
    async with db.async_session_maker() as session:
        repo = BotRepository(session)
        bot_obj = await repo.get_by_id(bot_id)
        if not bot_obj:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        # Store original token and active status for bot manager
        original_token = bot_obj.telegram_token
        was_active = bot_obj.is_active
        
        # Determine if token is changing
        new_token = update_params.get("telegram_token", original_token)
        
        # Update bot
        updated_bot = await repo.update(bot_id, **update_params)
        
        if not updated_bot:
            raise HTTPException(status_code=500, detail="Failed to update bot")
    
    # Handle bot manager updates (outside session)
    # If token changed, unregister old and register new
    if "telegram_token" in update_params and update_params["telegram_token"] != original_token:
        await bot_manager.unregister_bot(original_token)
        try:
            await bot_manager.register_bot(new_token, updated_bot.bot_name or update_params.get("bot_name"))
        except Exception as e:
            logger.error(f"Failed to register bot with new token: {e}")
    # If status changed, register/unregister
    elif bot_update.is_active is not None:
        if bot_update.is_active and not was_active:
            # Activating bot
            try:
                await bot_manager.register_bot(new_token, updated_bot.bot_name)
            except Exception as e:
                logger.error(f"Failed to register bot: {e}")
        elif not bot_update.is_active and was_active:
            # Deactivating bot
            await bot_manager.unregister_bot(new_token)
    
    return updated_bot.to_dict()


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Delete a bot - admin only"""
    db = await get_db()
    async with db.async_session_maker() as session:
        repo = BotRepository(session)
        bot_obj = await repo.get_by_id(bot_id)
        if not bot_obj:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        telegram_token = bot_obj.telegram_token
        
        # Delete from database
        success = await repo.delete(bot_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete bot")
    
    # Unregister bot (outside session)
    await bot_manager.unregister_bot(telegram_token)
    
    return {"ok": True, "message": "Bot deleted successfully"}

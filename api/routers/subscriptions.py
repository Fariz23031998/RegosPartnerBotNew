"""
Subscription management API routes.
"""
import logging
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends

from database import get_db
from database.repositories import BotRepository, SubscriptionRepository
from api.schemas import (
    SubscriptionActivate,
    SubscriptionSetPrice,
    SubscriptionResponse,
    RevenueStats
)
from auth import verify_admin
from bot_manager import bot_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.post("/bots/{bot_id}/activate", response_model=dict)
async def activate_subscription(
    bot_id: int,
    subscription: SubscriptionActivate,
    current_user: dict = Depends(verify_admin)
):
    """Activate or extend subscription for a bot"""
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        subscription_repo = SubscriptionRepository(session)
        
        bot = await bot_repo.get_by_id(bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        if not bot.subscription_price or bot.subscription_price <= 0:
            raise HTTPException(
                status_code=400,
                detail="Subscription price not set. Please set a price first"
            )
        
        # Calculate subscription period
        now = datetime.utcnow()
        months = subscription.months
        
        # If bot already has an active subscription, extend from expiry date
        # Otherwise, start from now
        if bot.subscription_active and bot.subscription_expires_at and bot.subscription_expires_at > now:
            start_date = bot.subscription_expires_at
        else:
            start_date = now
        
        expires_at = start_date + timedelta(days=30 * months)
        amount = float(bot.subscription_price) * months
        
        # Create subscription record
        subscription_record = await subscription_repo.create(
            bot_id=bot_id,
            amount=amount,
            started_at=start_date,
            expires_at=expires_at
        )
        
        # Update bot subscription status
        await bot_repo.update(
            bot_id=bot_id,
            subscription_active=True,
            subscription_expires_at=expires_at
        )
        
        # If bot is active but wasn't registered, register it
        if bot.is_active:
            try:
                await bot_manager.register_bot(bot.telegram_token, bot.bot_name)
            except Exception as e:
                logger.warning(f"Failed to register bot after subscription activation: {e}")
        
        logger.info(f"Activated subscription for bot {bot_id}: {months} months, expires {expires_at}")
        
        return {
            "ok": True,
            "message": f"Subscription activated for {months} month(s)",
            "expires_at": expires_at.isoformat(),
            "amount": amount
        }


@router.post("/bots/{bot_id}/set-price", response_model=dict)
async def set_subscription_price(
    bot_id: int,
    price_data: SubscriptionSetPrice,
    current_user: dict = Depends(verify_admin)
):
    """Set subscription price for a bot"""
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        
        bot = await bot_repo.get_by_id(bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        await bot_repo.update(
            bot_id=bot_id,
            subscription_price=price_data.price
        )
        
        logger.info(f"Set subscription price for bot {bot_id}: {price_data.price}")
        
        return {
            "ok": True,
            "message": f"Subscription price set to {price_data.price}",
            "price": price_data.price
        }


@router.get("/bots/{bot_id}/history", response_model=List[SubscriptionResponse])
async def get_subscription_history(
    bot_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Get subscription history for a bot"""
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        subscription_repo = SubscriptionRepository(session)
        
        bot = await bot_repo.get_by_id(bot_id)
        if not bot:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        subscriptions = await subscription_repo.get_by_bot(bot_id)
        return [sub.to_dict() for sub in subscriptions]


@router.get("/revenue", response_model=RevenueStats)
async def get_revenue_stats(
    current_user: dict = Depends(verify_admin)
):
    """Get revenue statistics"""
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        subscription_repo = SubscriptionRepository(session)
        
        # Total revenue
        total_revenue = await subscription_repo.get_total_revenue()
        
        # Monthly revenue (last 30 days)
        monthly_start = datetime.utcnow() - timedelta(days=30)
        monthly_revenue = await subscription_repo.get_revenue_by_period(
            start_date=monthly_start
        )
        
        # Count active and expired subscriptions
        all_bots = await bot_repo.get_all()
        active_count = sum(1 for bot in all_bots if bot.subscription_active and 
                         bot.subscription_expires_at and bot.subscription_expires_at > datetime.utcnow())
        expired_count = sum(1 for bot in all_bots if bot.subscription_active and 
                          bot.subscription_expires_at and bot.subscription_expires_at <= datetime.utcnow())
        
        return {
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "active_subscriptions": active_count,
            "expired_subscriptions": expired_count
        }


@router.post("/check-expired")
async def check_expired_subscriptions(
    current_user: dict = Depends(verify_admin)
):
    """Manually check and deactivate expired subscriptions"""
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        
        expired_bots = await bot_repo.get_bots_with_expired_subscriptions()
        
        deactivated_count = 0
        for bot in expired_bots:
            await bot_repo.update(
                bot_id=bot.bot_id,
                subscription_active=False
            )
            
            # Unregister bot if it was active
            if bot.is_active:
                try:
                    await bot_manager.unregister_bot(bot.telegram_token)
                except Exception as e:
                    logger.warning(f"Failed to unregister expired bot {bot.bot_id}: {e}")
            
            deactivated_count += 1
            logger.info(f"Deactivated expired subscription for bot {bot.bot_id}")
        
        return {
            "ok": True,
            "message": f"Checked and deactivated {deactivated_count} expired subscription(s)",
            "deactivated_count": deactivated_count
        }

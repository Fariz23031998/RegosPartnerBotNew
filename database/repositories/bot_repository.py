"""
Bot repository for database operations.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Bot


class BotRepository:
    """Repository for Bot database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: int,
        telegram_token: str,
        bot_name: Optional[str] = None,
        regos_integration_token: Optional[str] = None
    ) -> Bot:
        """Create a new bot"""
        bot = Bot(
            user_id=user_id,
            telegram_token=telegram_token,
            regos_integration_token=regos_integration_token,
            bot_name=bot_name,
            is_active=True
        )
        self.session.add(bot)
        await self.session.commit()
        await self.session.refresh(bot)
        return bot
    
    async def get_by_id(self, bot_id: int) -> Optional[Bot]:
        """Get bot by ID"""
        result = await self.session.execute(
            select(Bot).where(Bot.bot_id == bot_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_telegram_token(self, telegram_token: str) -> Optional[Bot]:
        """Get bot by telegram token"""
        result = await self.session.execute(
            select(Bot).where(Bot.telegram_token == telegram_token)
        )
        return result.scalar_one_or_none()
    
    async def get_by_user(self, user_id: int) -> List[Bot]:
        """Get all bots for a user"""
        result = await self.session.execute(
            select(Bot).where(Bot.user_id == user_id)
        )
        return list(result.scalars().all())
    
    async def get_all_active(self) -> List[Bot]:
        """Get all active bots (both is_active and subscription_active must be True, and subscription not expired)"""
        from datetime import datetime
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Bot).where(
                Bot.is_active == True,
                Bot.subscription_active == True,
                (Bot.subscription_expires_at.is_(None)) | (Bot.subscription_expires_at > now)
            )
        )
        return list(result.scalars().all())
    
    async def get_bots_with_expired_subscriptions(self) -> List[Bot]:
        """Get all bots with expired subscriptions"""
        from datetime import datetime
        now = datetime.utcnow()
        result = await self.session.execute(
            select(Bot).where(
                Bot.subscription_active == True,
                Bot.subscription_expires_at < now
            )
        )
        return list(result.scalars().all())
    
    async def get_all(self) -> List[Bot]:
        """Get all bots"""
        result = await self.session.execute(select(Bot))
        return list(result.scalars().all())
    
    async def update(
        self,
        bot_id: int,
        telegram_token: Optional[str] = None,
        bot_name: Optional[str] = None,
        regos_integration_token: Optional[str] = None,
        is_active: Optional[bool] = None,
        subscription_active: Optional[bool] = None,
        subscription_expires_at: Optional[datetime] = None,
        subscription_price: Optional[float] = None
    ) -> Optional[Bot]:
        """Update bot"""
        update_values = {}
        if telegram_token is not None:
            update_values["telegram_token"] = telegram_token
        if bot_name is not None:
            update_values["bot_name"] = bot_name
        if regos_integration_token is not None:
            update_values["regos_integration_token"] = regos_integration_token
        if is_active is not None:
            update_values["is_active"] = is_active
        if subscription_active is not None:
            update_values["subscription_active"] = subscription_active
        if subscription_expires_at is not None:
            update_values["subscription_expires_at"] = subscription_expires_at
        if subscription_price is not None:
            update_values["subscription_price"] = subscription_price
        
        if update_values:
            await self.session.execute(
                update(Bot)
                .where(Bot.bot_id == bot_id)
                .values(**update_values)
            )
            await self.session.commit()
        
        # Fetch updated bot
        result = await self.session.execute(
            select(Bot).where(Bot.bot_id == bot_id)
        )
        return result.scalar_one_or_none()
    
    async def update_status(self, bot_id: int, is_active: bool) -> bool:
        """Update bot active status"""
        result = await self.session.execute(
            update(Bot)
            .where(Bot.bot_id == bot_id)
            .values(is_active=is_active)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def delete(self, bot_id: int) -> bool:
        """Delete a bot"""
        result = await self.session.execute(
            delete(Bot).where(Bot.bot_id == bot_id)
        )
        await self.session.commit()
        return result.rowcount > 0


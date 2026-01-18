"""
Subscription repository for database operations.
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription


class SubscriptionRepository:
    """Repository for Subscription database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        bot_id: int,
        amount: float,
        started_at: datetime,
        expires_at: datetime
    ) -> Subscription:
        """Create a new subscription record"""
        subscription = Subscription(
            bot_id=bot_id,
            amount=amount,
            started_at=started_at,
            expires_at=expires_at
        )
        self.session.add(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        return subscription
    
    async def get_by_id(self, subscription_id: int) -> Optional[Subscription]:
        """Get subscription by ID"""
        result = await self.session.execute(
            select(Subscription).where(Subscription.subscription_id == subscription_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_bot(self, bot_id: int) -> List[Subscription]:
        """Get all subscriptions for a bot"""
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.bot_id == bot_id)
            .order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_all(self) -> List[Subscription]:
        """Get all subscriptions"""
        result = await self.session.execute(
            select(Subscription).order_by(Subscription.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_total_revenue(self) -> float:
        """Get total revenue from all subscriptions"""
        result = await self.session.execute(
            select(func.sum(Subscription.amount))
        )
        total = result.scalar()
        return float(total) if total else 0.0
    
    async def get_revenue_by_period(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> float:
        """Get revenue for a specific period"""
        query = select(func.sum(Subscription.amount))
        
        if start_date:
            query = query.where(Subscription.created_at >= start_date)
        if end_date:
            query = query.where(Subscription.created_at <= end_date)
        
        result = await self.session.execute(query)
        total = result.scalar()
        return float(total) if total else 0.0

"""
Bot schedule repository for database operations.
"""
from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
import json

from database.models import BotSchedule


class BotScheduleRepository:
    """Repository for BotSchedule database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        bot_id: int,
        schedule_type: str,
        time: str,
        schedule_option: str,
        schedule_value: Optional[List[int]] = None,
        enabled: bool = True
    ) -> BotSchedule:
        """Create new bot schedule"""
        schedule_value_str = json.dumps(schedule_value) if schedule_value else None
        bot_schedule = BotSchedule(
            bot_id=bot_id,
            schedule_type=schedule_type,
            time=time,
            schedule_option=schedule_option,
            schedule_value=schedule_value_str,
            enabled=enabled
        )
        self.session.add(bot_schedule)
        await self.session.commit()
        await self.session.refresh(bot_schedule)
        return bot_schedule
    
    async def get_by_id(self, schedule_id: int) -> Optional[BotSchedule]:
        """Get bot schedule by ID"""
        result = await self.session.execute(
            select(BotSchedule).where(BotSchedule.id == schedule_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_bot_id(self, bot_id: int) -> List[BotSchedule]:
        """Get all bot schedules by bot ID"""
        result = await self.session.execute(
            select(BotSchedule).where(BotSchedule.bot_id == bot_id)
        )
        return list(result.scalars().all())
    
    async def get_all(self) -> List[BotSchedule]:
        """Get all bot schedules"""
        result = await self.session.execute(select(BotSchedule))
        return list(result.scalars().all())
    
    async def update(
        self,
        schedule_id: int,
        schedule_type: Optional[str] = None,
        time: Optional[str] = None,
        schedule_option: Optional[str] = None,
        schedule_value: Optional[List[int]] = None,
        enabled: Optional[bool] = None
    ) -> Optional[BotSchedule]:
        """Update bot schedule"""
        update_values = {}
        if schedule_type is not None:
            update_values["schedule_type"] = schedule_type
        if time is not None:
            update_values["time"] = time
        if schedule_option is not None:
            update_values["schedule_option"] = schedule_option
        if schedule_value is not None:
            update_values["schedule_value"] = json.dumps(schedule_value) if schedule_value else None
        if enabled is not None:
            update_values["enabled"] = enabled
        
        if update_values:
            await self.session.execute(
                update(BotSchedule)
                .where(BotSchedule.id == schedule_id)
                .values(**update_values)
            )
            await self.session.commit()
        
        # Fetch updated schedule
        result = await self.session.execute(
            select(BotSchedule).where(BotSchedule.id == schedule_id)
        )
        return result.scalar_one_or_none()
    
    async def delete(self, schedule_id: int) -> bool:
        """Delete bot schedule by ID"""
        result = await self.session.execute(
            delete(BotSchedule).where(BotSchedule.id == schedule_id)
        )
        await self.session.commit()
        return result.rowcount > 0

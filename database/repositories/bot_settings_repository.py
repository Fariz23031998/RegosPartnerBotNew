"""
Bot settings repository for database operations.
"""
from typing import Optional, List
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import BotSettings


class BotSettingsRepository:
    """Repository for BotSettings database operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        bot_id: int,
        online_store_stock_id: Optional[int] = None,
        online_store_price_type_id: Optional[int] = None,
        online_store_currency_id: int = 1,
        currency_name: Optional[str] = None
    ) -> BotSettings:
        """Create new bot settings"""
        bot_settings = BotSettings(
            bot_id=bot_id,
            online_store_stock_id=online_store_stock_id,
            online_store_price_type_id=online_store_price_type_id,
            online_store_currency_id=online_store_currency_id,
            currency_name=currency_name or "сум"
        )
        self.session.add(bot_settings)
        await self.session.commit()
        await self.session.refresh(bot_settings)
        return bot_settings
    
    async def get_by_id(self, settings_id: int) -> Optional[BotSettings]:
        """Get bot settings by ID"""
        result = await self.session.execute(
            select(BotSettings).where(BotSettings.id == settings_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_bot_id(self, bot_id: int) -> Optional[BotSettings]:
        """Get bot settings by bot ID"""
        result = await self.session.execute(
            select(BotSettings).where(BotSettings.bot_id == bot_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[BotSettings]:
        """Get all bot settings"""
        result = await self.session.execute(select(BotSettings))
        return list(result.scalars().all())
    
    async def update(
        self,
        settings_id: int,
        online_store_stock_id: Optional[int] = None,
        online_store_price_type_id: Optional[int] = None,
        online_store_currency_id: Optional[int] = None,
        currency_name: Optional[str] = None
    ) -> Optional[BotSettings]:
        """Update bot settings"""
        update_values = {}
        if online_store_stock_id is not None:
            update_values["online_store_stock_id"] = online_store_stock_id
        if online_store_price_type_id is not None:
            update_values["online_store_price_type_id"] = online_store_price_type_id
        if online_store_currency_id is not None:
            update_values["online_store_currency_id"] = online_store_currency_id
        if currency_name is not None:
            update_values["currency_name"] = currency_name
        
        if update_values:
            await self.session.execute(
                update(BotSettings)
                .where(BotSettings.id == settings_id)
                .values(**update_values)
            )
            await self.session.commit()
        
        # Fetch updated settings and refresh to ensure we get the latest data
        result = await self.session.execute(
            select(BotSettings).where(BotSettings.id == settings_id)
        )
        updated_settings = result.scalar_one_or_none()
        if updated_settings:
            await self.session.refresh(updated_settings)
        return updated_settings
    
    async def update_by_bot_id(
        self,
        bot_id: int,
        online_store_stock_id: Optional[int] = None,
        online_store_price_type_id: Optional[int] = None,
        online_store_currency_id: Optional[int] = None,
        currency_name: Optional[str] = None
    ) -> Optional[BotSettings]:
        """Update bot settings by bot ID"""
        update_values = {}
        if online_store_stock_id is not None:
            update_values["online_store_stock_id"] = online_store_stock_id
        if online_store_price_type_id is not None:
            update_values["online_store_price_type_id"] = online_store_price_type_id
        if online_store_currency_id is not None:
            update_values["online_store_currency_id"] = online_store_currency_id
        if currency_name is not None:
            update_values["currency_name"] = currency_name
        
        if update_values:
            await self.session.execute(
                update(BotSettings)
                .where(BotSettings.bot_id == bot_id)
                .values(**update_values)
            )
            await self.session.commit()
        
        # Fetch updated settings and refresh to ensure we get the latest data
        result = await self.session.execute(
            select(BotSettings).where(BotSettings.bot_id == bot_id)
        )
        updated_settings = result.scalar_one_or_none()
        if updated_settings:
            await self.session.refresh(updated_settings)
        return updated_settings
    
    async def delete(self, settings_id: int) -> bool:
        """Delete bot settings by ID"""
        result = await self.session.execute(
            delete(BotSettings).where(BotSettings.id == settings_id)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def delete_by_bot_id(self, bot_id: int) -> bool:
        """Delete bot settings by bot ID"""
        result = await self.session.execute(
            delete(BotSettings).where(BotSettings.bot_id == bot_id)
        )
        await self.session.commit()
        return result.rowcount > 0

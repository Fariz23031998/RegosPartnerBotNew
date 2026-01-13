"""
Bot schedules API routes.
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Query

from database import get_db
from database.repositories import BotRepository, BotScheduleRepository
from api.schemas import BotScheduleCreate, BotScheduleUpdate, BotScheduleResponse
from auth import verify_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bot-schedules", tags=["bot-schedules"])


@router.post("", response_model=BotScheduleResponse)
async def create_bot_schedule(
    schedule: BotScheduleCreate,
    current_user: dict = Depends(verify_admin)
):
    """Create new bot schedule"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            bot_repo = BotRepository(session)
            schedule_repo = BotScheduleRepository(session)
            
            # Verify bot exists
            bot = await bot_repo.get_by_id(schedule.bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            
            # Validate schedule_type
            if schedule.schedule_type not in ["send_partner_balance"]:
                raise HTTPException(status_code=400, detail="Invalid schedule_type")
            
            # Validate schedule_option
            if schedule.schedule_option not in ["daily", "weekdays", "monthly"]:
                raise HTTPException(status_code=400, detail="Invalid schedule_option. Must be 'daily', 'weekdays', or 'monthly'")
            
            # Validate schedule_value based on option
            if schedule.schedule_option == "weekdays" and schedule.schedule_value:
                if any(d < 0 or d > 6 for d in schedule.schedule_value):
                    raise HTTPException(status_code=400, detail="Weekdays must be between 0 (Monday) and 6 (Sunday)")
            elif schedule.schedule_option == "monthly" and schedule.schedule_value:
                if any(d < 1 or d > 31 for d in schedule.schedule_value):
                    raise HTTPException(status_code=400, detail="Monthly days must be between 1 and 31")
            elif schedule.schedule_option == "daily" and schedule.schedule_value:
                # Daily should not have schedule_value
                raise HTTPException(status_code=400, detail="Daily schedule option should not have schedule_value")
            
            # Validate time format (HH:MM)
            try:
                hours, minutes = schedule.time.split(":")
                int(hours)
                int(minutes)
                if len(hours) != 2 or len(minutes) != 2 or int(hours) > 23 or int(minutes) > 59:
                    raise ValueError
            except:
                raise HTTPException(status_code=400, detail="Time must be in HH:MM format")
            
            # Create schedule
            bot_schedule = await schedule_repo.create(
                bot_id=schedule.bot_id,
                schedule_type=schedule.schedule_type,
                time=schedule.time,
                schedule_option=schedule.schedule_option,
                schedule_value=schedule.schedule_value,
                enabled=schedule.enabled
            )
            
            return BotScheduleResponse(
                id=bot_schedule.id,
                bot_id=bot_schedule.bot_id,
                schedule_type=bot_schedule.schedule_type,
                time=bot_schedule.time,
                enabled=bot_schedule.enabled,
                schedule_option=bot_schedule.schedule_option,
                schedule_value=bot_schedule.to_dict().get("schedule_value"),
                created_at=bot_schedule.created_at.isoformat(),
                updated_at=bot_schedule.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bot schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=List[BotScheduleResponse])
async def get_all_bot_schedules(
    current_user: dict = Depends(verify_admin)
):
    """Get all bot schedules"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            schedule_repo = BotScheduleRepository(session)
            all_schedules = await schedule_repo.get_all()
            
            return [
                BotScheduleResponse(
                    id=schedule.id,
                    bot_id=schedule.bot_id,
                    schedule_type=schedule.schedule_type,
                    time=schedule.time,
                    enabled=schedule.enabled,
                    schedule_option=schedule.schedule_option,
                    schedule_value=schedule.to_dict().get("schedule_value"),
                    created_at=schedule.created_at.isoformat(),
                    updated_at=schedule.updated_at.isoformat()
                )
                for schedule in all_schedules
            ]
    except Exception as e:
        logger.error(f"Error fetching bot schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{schedule_id}", response_model=BotScheduleResponse)
async def get_bot_schedule(
    schedule_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Get bot schedule by ID"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            schedule_repo = BotScheduleRepository(session)
            bot_schedule = await schedule_repo.get_by_id(schedule_id)
            
            if not bot_schedule:
                raise HTTPException(status_code=404, detail="Bot schedule not found")
            
            return BotScheduleResponse(
                id=bot_schedule.id,
                bot_id=bot_schedule.bot_id,
                schedule_type=bot_schedule.schedule_type,
                time=bot_schedule.time,
                enabled=bot_schedule.enabled,
                schedule_option=bot_schedule.schedule_option,
                schedule_value=bot_schedule.to_dict().get("schedule_value"),
                created_at=bot_schedule.created_at.isoformat(),
                updated_at=bot_schedule.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bot schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/bot/{bot_id}", response_model=List[BotScheduleResponse])
async def get_bot_schedules_by_bot_id(
    bot_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Get all bot schedules for a specific bot"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            bot_repo = BotRepository(session)
            schedule_repo = BotScheduleRepository(session)
            
            # Verify bot exists
            bot = await bot_repo.get_by_id(bot_id)
            if not bot:
                raise HTTPException(status_code=404, detail="Bot not found")
            
            schedules = await schedule_repo.get_by_bot_id(bot_id)
            
            return [
                BotScheduleResponse(
                    id=schedule.id,
                    bot_id=schedule.bot_id,
                    schedule_type=schedule.schedule_type,
                    time=schedule.time,
                    enabled=schedule.enabled,
                    schedule_option=schedule.schedule_option,
                    schedule_value=schedule.to_dict().get("schedule_value"),
                    created_at=schedule.created_at.isoformat(),
                    updated_at=schedule.updated_at.isoformat()
                )
                for schedule in schedules
            ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bot schedules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{schedule_id}", response_model=BotScheduleResponse)
async def update_bot_schedule(
    schedule_id: int,
    schedule: BotScheduleUpdate,
    current_user: dict = Depends(verify_admin)
):
    """Update bot schedule"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            schedule_repo = BotScheduleRepository(session)
            
            # Check if schedule exists
            existing = await schedule_repo.get_by_id(schedule_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Bot schedule not found")
            
            # Validate schedule_type if provided
            if schedule.schedule_type is not None and schedule.schedule_type not in ["send_partner_balance"]:
                raise HTTPException(status_code=400, detail="Invalid schedule_type")
            
            # Validate schedule_option if provided
            if schedule.schedule_option is not None and schedule.schedule_option not in ["daily", "weekdays", "monthly"]:
                raise HTTPException(status_code=400, detail="Invalid schedule_option. Must be 'daily', 'weekdays', or 'monthly'")
            
            # Validate schedule_value based on option
            final_schedule_option = schedule.schedule_option or existing.schedule_option
            if schedule.schedule_value is not None:
                if final_schedule_option == "weekdays":
                    if any(d < 0 or d > 6 for d in schedule.schedule_value):
                        raise HTTPException(status_code=400, detail="Weekdays must be between 0 (Monday) and 6 (Sunday)")
                elif final_schedule_option == "monthly":
                    if any(d < 1 or d > 31 for d in schedule.schedule_value):
                        raise HTTPException(status_code=400, detail="Monthly days must be between 1 and 31")
                elif final_schedule_option == "daily":
                    raise HTTPException(status_code=400, detail="Daily schedule option should not have schedule_value")
            
            # Validate time format if provided
            if schedule.time is not None:
                try:
                    hours, minutes = schedule.time.split(":")
                    int(hours)
                    int(minutes)
                    if len(hours) != 2 or len(minutes) != 2 or int(hours) > 23 or int(minutes) > 59:
                        raise ValueError
                except:
                    raise HTTPException(status_code=400, detail="Time must be in HH:MM format")
            
            # Update schedule
            updated = await schedule_repo.update(
                schedule_id=schedule_id,
                schedule_type=schedule.schedule_type,
                time=schedule.time,
                schedule_option=schedule.schedule_option,
                schedule_value=schedule.schedule_value,
                enabled=schedule.enabled
            )
            
            if not updated:
                raise HTTPException(status_code=404, detail="Bot schedule not found after update")
            
            return BotScheduleResponse(
                id=updated.id,
                bot_id=updated.bot_id,
                schedule_type=updated.schedule_type,
                time=updated.time,
                enabled=updated.enabled,
                schedule_option=updated.schedule_option,
                schedule_value=updated.to_dict().get("schedule_value"),
                created_at=updated.created_at.isoformat(),
                updated_at=updated.updated_at.isoformat()
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bot schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{schedule_id}")
async def delete_bot_schedule(
    schedule_id: int,
    current_user: dict = Depends(verify_admin)
):
    """Delete bot schedule"""
    try:
        db = await get_db()
        async with db.async_session_maker() as session:
            schedule_repo = BotScheduleRepository(session)
            
            # Check if schedule exists
            existing = await schedule_repo.get_by_id(schedule_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Bot schedule not found")
            
            deleted = await schedule_repo.delete(schedule_id)
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Bot schedule not found")
            
            return {"ok": True, "message": "Bot schedule deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bot schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

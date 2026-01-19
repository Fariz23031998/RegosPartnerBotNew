"""
Scheduler for executing bot schedules (e.g., partner balance notifications).
Uses APScheduler for robust scheduling.
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from database import get_db
from database.repositories import BotRepository, BotScheduleRepository
from bot_manager import bot_manager
from regos.api import regos_async_api_request
from regos.document_excel import generate_partner_balance_excel
from core.utils import convert_to_unix_timestamp
from core.number_format import format_number

logger = logging.getLogger(__name__)


class ScheduleExecutor:
    """Executes scheduled bot tasks using APScheduler"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.job_ids: set = set()  # Track job IDs to avoid duplicates
    
    async def start(self):
        """Start the scheduler"""
        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler is already running")
            return
        
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        logger.info("APScheduler started")
        
        # Add periodic task to check expired subscriptions (runs every hour)
        self.scheduler.add_job(
            self._check_expired_subscriptions,
            trigger=CronTrigger(minute=0),  # Run at the top of every hour
            id="check_expired_subscriptions",
            replace_existing=True
        )
        logger.info("Added periodic task to check expired subscriptions")
        
        # Load all schedules from database
        await self._load_schedules()
    
    async def stop(self):
        """Stop the scheduler"""
        if self.scheduler:
            self.scheduler.shutdown(wait=True)
            self.job_ids.clear()
        logger.info("Scheduler stopped")
    
    async def _load_schedules(self):
        """Load all enabled schedules from database and add them to scheduler"""
        try:
            db = await get_db()
            async with db.async_session_maker() as session:
                schedule_repo = BotScheduleRepository(session)
                all_schedules = await schedule_repo.get_all()
                enabled_schedules = [s for s in all_schedules if s.enabled]
                
                logger.info(f"Loading {len(enabled_schedules)} enabled schedule(s)")
                
                for schedule in enabled_schedules:
                    try:
                        await self._add_schedule_job(schedule)
                    except Exception as e:
                        logger.error(f"Error adding schedule {schedule.id}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error loading schedules: {e}", exc_info=True)
    
    async def _add_schedule_job(self, schedule):
        """Add a schedule as a job to APScheduler"""
        job_id = f"schedule_{schedule.id}"
        
        # Remove existing job if it exists
        if job_id in self.job_ids:
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed existing job {job_id}")
            except Exception as e:
                logger.debug(f"Job {job_id} doesn't exist or couldn't be removed: {e}")
        
        # Create trigger based on schedule option
        trigger = self._create_trigger(schedule)
        if not trigger:
            logger.error(f"Could not create trigger for schedule {schedule.id} (type: {schedule.schedule_type}, option: {schedule.schedule_option}, time: {schedule.time}, value: {schedule.schedule_value})")
            return
        
        # Add job to scheduler
        try:
            self.scheduler.add_job(
                self._execute_schedule_job,
                trigger=trigger,
                id=job_id,
                args=[schedule.id],
                replace_existing=True
            )
            self.job_ids.add(job_id)
            logger.info(f"Successfully added schedule job {job_id} (schedule_id={schedule.id}, type={schedule.schedule_type}, option={schedule.schedule_option}, time={schedule.time}) with trigger: {trigger}")
        except Exception as e:
            logger.error(f"Failed to add schedule job {job_id}: {e}", exc_info=True)
    
    def _create_trigger(self, schedule):
        """Create APScheduler trigger from schedule configuration"""
        try:
            # Parse time
            schedule_hour, schedule_minute = map(int, schedule.time.split(":"))
            
            if schedule.schedule_option == "daily":
                # Daily: run every day at specified time
                logger.info(f"Creating daily trigger for schedule {schedule.id} at {schedule.time}")
                return CronTrigger(hour=schedule_hour, minute=schedule_minute)
            
            elif schedule.schedule_option == "weekdays":
                # Weekdays: run on specified days of week
                schedule_value = None
                if schedule.schedule_value:
                    try:
                        schedule_value = json.loads(schedule.schedule_value) if isinstance(schedule.schedule_value, str) else schedule.schedule_value
                    except Exception as e:
                        logger.warning(f"Error parsing weekdays JSON for schedule {schedule.id}: {e}, value: {schedule.schedule_value}")
                        return None
                
                if schedule_value and isinstance(schedule_value, list) and len(schedule_value) > 0:
                    # APScheduler uses 0=Monday, 6=Sunday (same as Python)
                    # Convert to day_of_week parameter (mon-sun)
                    day_names = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
                    days = [day_names[d] for d in schedule_value if 0 <= d <= 6]
                    if days:
                        logger.info(f"Creating weekdays trigger for schedule {schedule.id} at {schedule.time} on days: {days}")
                        return CronTrigger(hour=schedule_hour, minute=schedule_minute, day_of_week=','.join(days))
                    else:
                        logger.warning(f"No valid weekdays found for schedule {schedule.id}, schedule_value: {schedule_value}")
                else:
                    logger.warning(f"Invalid or empty schedule_value for weekdays schedule {schedule.id}: {schedule_value}")
                return None
            
            elif schedule.schedule_option == "monthly":
                # Monthly: run on specified days of month
                schedule_value = None
                if schedule.schedule_value:
                    try:
                        schedule_value = json.loads(schedule.schedule_value) if isinstance(schedule.schedule_value, str) else schedule.schedule_value
                    except Exception as e:
                        logger.warning(f"Error parsing monthly JSON for schedule {schedule.id}: {e}, value: {schedule.schedule_value}")
                        return None
                
                if schedule_value and isinstance(schedule_value, list) and len(schedule_value) > 0:
                    # Filter valid days (1-31)
                    days = [d for d in schedule_value if 1 <= d <= 31]
                    if days:
                        logger.info(f"Creating monthly trigger for schedule {schedule.id} at {schedule.time} on days: {days}")
                        return CronTrigger(hour=schedule_hour, minute=schedule_minute, day=','.join(map(str, days)))
                    else:
                        logger.warning(f"No valid monthly days found for schedule {schedule.id}, schedule_value: {schedule_value}")
                else:
                    logger.warning(f"Invalid or empty schedule_value for monthly schedule {schedule.id}: {schedule_value}")
                return None
            
            logger.warning(f"Unknown schedule_option '{schedule.schedule_option}' for schedule {schedule.id}")
            return None
        
        except Exception as e:
            logger.error(f"Error creating trigger for schedule {schedule.id}: {e}", exc_info=True)
            return None
    
    async def _execute_schedule_job(self, schedule_id: int):
        """Execute a schedule job (called by APScheduler)"""
        try:
            db = await get_db()
            async with db.async_session_maker() as session:
                schedule_repo = BotScheduleRepository(session)
                bot_repo = BotRepository(session)
                
                # Get schedule from database
                schedule = await schedule_repo.get_by_id(schedule_id)
                if not schedule:
                    logger.warning(f"Schedule {schedule_id} not found")
                    return
                
                if not schedule.enabled:
                    logger.info(f"Schedule {schedule_id} is disabled, skipping")
                    return
                
                logger.info(f"Executing schedule {schedule_id} (type: {schedule.schedule_type})")
                await self._execute_schedule(schedule, bot_repo)
        
        except Exception as e:
            logger.error(f"Error executing schedule job {schedule_id}: {e}", exc_info=True)
    
    async def _execute_schedule(self, schedule, bot_repo):
        """Execute a schedule"""
        if schedule.schedule_type == "send_partner_balance":
            await self._execute_partner_balance_schedule(schedule, bot_repo)
        else:
            logger.warning(f"Unknown schedule type: {schedule.schedule_type}")
    
    async def _execute_partner_balance_schedule(self, schedule, bot_repo):
        """Execute partner balance notification schedule"""
        try:
            # Get bot information
            bot = await bot_repo.get_by_id(schedule.bot_id)
            if not bot or not bot.is_active:
                logger.warning(f"Bot {schedule.bot_id} not found or inactive")
                return
            
            if not bot.regos_integration_token:
                logger.warning(f"Bot {schedule.bot_id} has no REGOS integration token")
                return
            
            regos_token = bot.regos_integration_token
            telegram_token = bot.telegram_token
            
            # Get all partners with Telegram IDs
            partners_with_telegram = await self._get_partners_with_telegram(regos_token)
            
            if not partners_with_telegram:
                logger.info(f"No partners with Telegram IDs found for bot {schedule.bot_id}")
                return
            
            logger.info(f"Found {len(partners_with_telegram)} partner(s) with Telegram IDs")
            
            # Get all firms and currencies
            firms, currencies = await self._get_firms_and_currencies(regos_token)
            
            if not firms or not currencies:
                logger.warning(f"No firms or currencies found for bot {schedule.bot_id}")
                return
            
            # Calculate date range (last 30 days by default)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            # Send balance to each partner
            for partner_id, telegram_chat_id in partners_with_telegram:
                try:
                    await self._send_partner_balance(
                        regos_token,
                        telegram_token,
                        partner_id,
                        telegram_chat_id,
                        firms,
                        currencies,
                        start_date_str,
                        end_date_str
                    )
                    # Small delay between sends to avoid rate limiting
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error sending balance to partner {partner_id}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error executing partner balance schedule {schedule.id}: {e}", exc_info=True)
    
    async def reload_schedules(self):
        """Reload all schedules from database (useful when schedules are updated)"""
        if not self.scheduler or not self.scheduler.running:
            logger.warning("Scheduler is not running, cannot reload schedules")
            return
        
        # Remove all existing schedule jobs
        for job_id in list(self.job_ids):
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
        self.job_ids.clear()
        
        # Reload schedules
        await self._load_schedules()
        logger.info("Schedules reloaded")
    
    async def _get_partners_with_telegram(self, regos_token: str) -> List[tuple]:
        """Get all partners that have Telegram IDs in their oked field"""
        try:
            response = await regos_async_api_request(
                endpoint="Partner/Get",
                request_data={"deleted_mark": False},
                token=regos_token,
                timeout_seconds=30
            )
            
            if not response.get("ok"):
                return []
            
            result = response.get("result", [])
            partners = result if isinstance(result, list) else [result]
            
            partners_with_telegram = []
            for partner in partners:
                if not isinstance(partner, dict):
                    continue
                
                partner_id = partner.get("id")
                oked = partner.get("oked")
                
                if partner_id and oked is not None:
                    try:
                        # Parse oked field (can be string or number)
                        if isinstance(oked, str):
                            oked_cleaned = oked.strip()
                            if oked_cleaned:
                                telegram_chat_id = int(oked_cleaned)
                                partners_with_telegram.append((partner_id, telegram_chat_id))
                        elif isinstance(oked, (int, float)):
                            telegram_chat_id = int(oked)
                            partners_with_telegram.append((partner_id, telegram_chat_id))
                    except (ValueError, TypeError):
                        continue
            
            return partners_with_telegram
        
        except Exception as e:
            logger.error(f"Error getting partners with Telegram IDs: {e}", exc_info=True)
            return []
    
    async def _get_firms_and_currencies(self, regos_token: str) -> tuple:
        """Get all firms and currencies"""
        try:
            firms_task = regos_async_api_request(
                endpoint="Firm/Get",
                request_data={},
                token=regos_token,
                timeout_seconds=30
            )
            currencies_task = regos_async_api_request(
                endpoint="Currency/Get",
                request_data={},
                token=regos_token,
                timeout_seconds=30
            )
            
            firms_response, currencies_response = await asyncio.gather(firms_task, currencies_task)
            
            firms = []
            if firms_response.get("ok"):
                firms_result = firms_response.get("result", [])
                firms = firms_result if isinstance(firms_result, list) else [firms_result]
                firms = [f for f in firms if f]  # Filter out None/empty
            
            currencies = []
            if currencies_response.get("ok"):
                currencies_result = currencies_response.get("result", [])
                currencies = currencies_result if isinstance(currencies_result, list) else [currencies_result]
                currencies = [c for c in currencies if c]  # Filter out None/empty
            
            return firms, currencies
        
        except Exception as e:
            logger.error(f"Error getting firms and currencies: {e}", exc_info=True)
            return [], []
    
    async def _send_partner_balance(
        self,
        regos_token: str,
        telegram_token: str,
        partner_id: int,
        telegram_chat_id: int,
        firms: List[Dict],
        currencies: List[Dict],
        start_date: str,
        end_date: str
    ):
        """Send partner balance Excel file to Telegram chat with text message if balance is negative"""
        try:
            # Get firm and currency IDs
            firm_ids = [f.get("id") for f in firms if f.get("id")]
            currency_ids = [c.get("id") for c in currencies if c.get("id")]
            
            if not firm_ids or not currency_ids:
                logger.warning(f"No firm or currency IDs for partner {partner_id}")
                return
            
            # Fetch partner balance for each combination
            balance_tasks = []
            
            for firm_id in firm_ids:
                for currency_id in currency_ids:
                    balance_request = {
                        "partner_id": partner_id,
                        "firm_id": firm_id,
                        "currency_id": currency_id
                    }
                    
                    start_date_with_time = f"{start_date} 00:00:00"
                    end_date_with_time = f"{end_date} 23:59:59"
                    balance_request["start_date"] = convert_to_unix_timestamp(start_date_with_time, "%Y-%m-%d %H:%M:%S")
                    balance_request["end_date"] = convert_to_unix_timestamp(end_date_with_time, "%Y-%m-%d %H:%M:%S")
                    
                    balance_tasks.append(
                        regos_async_api_request(
                            endpoint="PartnerBalance/Get",
                            request_data=balance_request,
                            token=regos_token,
                            timeout_seconds=30
                        )
                    )
            
            # Execute all requests in parallel
            responses = await asyncio.gather(*balance_tasks, return_exceptions=True)
            
            # Combine all results and group by firm/currency
            all_balance_entries = []
            balance_groups = {}  # (firm_id, currency_id) -> list of entries
            
            for response in responses:
                if isinstance(response, Exception):
                    logger.warning(f"Error fetching balance: {response}")
                    continue
                if response.get("ok"):
                    result = response.get("result", [])
                    entries = result if isinstance(result, list) else [result] if result else []
                    
                    for entry in entries:
                        all_balance_entries.append(entry)
                        
                        # Extract firm and currency from entry
                        firm = entry.get("firm", {})
                        currency = entry.get("currency", {})
                        firm_id = firm.get("id") if isinstance(firm, dict) else None
                        currency_id = currency.get("id") if isinstance(currency, dict) else None
                        
                        if firm_id and currency_id:
                            key = (firm_id, currency_id)
                            if key not in balance_groups:
                                balance_groups[key] = []
                            balance_groups[key].append(entry)
            
            if not all_balance_entries:
                logger.info(f"No balance data found for partner {partner_id}")
                return
            
            # Check if any balance is negative (last.start_amount + debit - credit < 0)
            has_negative_balance = False
            negative_balances = []  # List of (firm_name, currency_name, balance) tuples
            
            # Create lookup dictionaries for firm and currency names (from firms/currencies lists)
            firm_dict = {f.get("id"): f.get("name", f"Firm {f.get('id')}") for f in firms}
            currency_dict = {c.get("id"): c.get("name", f"Currency {c.get('id')}") for c in currencies}
            
            for (firm_id, currency_id), entries in balance_groups.items():
                if not entries:
                    continue
                
                # Sort entries by date to get the last one
                sorted_entries = sorted(entries, key=lambda x: x.get("date", 0))
                last_entry = sorted_entries[-1]
                
                start_amount = float(last_entry.get("start_amount", 0))
                debit = float(last_entry.get("debit", 0))
                credit = float(last_entry.get("credit", 0))
                final_balance = start_amount + debit - credit
                
                if final_balance > 0:
                    has_negative_balance = True
                    
                    # Try to get names from entry first, then from lookup dict
                    firm = last_entry.get("firm", {})
                    currency = last_entry.get("currency", {})
                    
                    firm_name = (
                        firm.get("name") if isinstance(firm, dict) and firm.get("name")
                        else firm_dict.get(firm_id, f"Firm {firm_id}")
                    )
                    currency_name = (
                        currency.get("name") if isinstance(currency, dict) and currency.get("name")
                        else currency_dict.get(currency_id, f"Currency {currency_id}")
                    )
                    
                    negative_balances.append((firm_name, currency_name, final_balance))
            
            # Only send if there's a negative balance
            if not has_negative_balance:
                logger.info(f"Partner {partner_id} has no negative balance, skipping notification")
                return
            
            # Generate text message with balance summary
            message_lines = [
                "⚠️ Уведомление о балансе",
                "",
                f"Партнер ID: {partner_id}",
                "",
                "Отрицательный баланс:",
                ""
            ]
            
            for firm_name, currency_name, balance in negative_balances:
                message_lines.append(f"🏢 {firm_name} ({currency_name}): -{format_number(balance)}")
            
            message_lines.extend([
                "",
                "Подробная информация в прикрепленном файле."
            ])
            
            text_message = "\n".join(message_lines)
            
            # Send text message first
            await bot_manager.send_message(
                telegram_token,
                telegram_chat_id,
                text_message
            )
            
            # Generate Excel file
            excel_path = generate_partner_balance_excel(all_balance_entries)
            
            # Send Excel file to Telegram
            caption = f"📊 Баланс партнера (ID: {partner_id})"
            result = await bot_manager.send_document(
                telegram_token,
                telegram_chat_id,
                excel_path,
                caption
            )
            
            # Clean up file after sending
            try:
                import os
                os.remove(excel_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary Excel file: {e}")
            
            if result:
                logger.info(f"Successfully sent balance to partner {partner_id} (Telegram ID: {telegram_chat_id})")
            else:
                logger.warning(f"Failed to send balance to partner {partner_id} (Telegram ID: {telegram_chat_id})")
        
        except Exception as e:
            logger.error(f"Error sending partner balance to {partner_id}: {e}", exc_info=True)
    
    async def _check_expired_subscriptions(self):
        """Check and deactivate expired subscriptions"""
        try:
            logger.info("Checking for expired subscriptions...")
            db = await get_db()
            async with db.async_session_maker() as session:
                bot_repo = BotRepository(session)
                
                expired_bots = await bot_repo.get_bots_with_expired_subscriptions()
                
                if not expired_bots:
                    logger.info("No expired subscriptions found")
                    return
                
                logger.info(f"Found {len(expired_bots)} bot(s) with expired subscriptions")
                
                deactivated_count = 0
                for bot in expired_bots:
                    # Update subscription status
                    await bot_repo.update(
                        bot_id=bot.bot_id,
                        subscription_active=False
                    )
                    
                    # Unregister bot if it was active
                    if bot.is_active:
                        try:
                            await bot_manager.unregister_bot(bot.telegram_token)
                            logger.info(f"Unregistered bot {bot.bot_id} due to expired subscription")
                        except Exception as e:
                            logger.warning(f"Failed to unregister expired bot {bot.bot_id}: {e}")
                    
                    deactivated_count += 1
                    logger.info(f"Deactivated expired subscription for bot {bot.bot_id} ({bot.bot_name or 'Unknown'})")
                
                logger.info(f"Successfully deactivated {deactivated_count} expired subscription(s)")
        
        except Exception as e:
            logger.error(f"Error checking expired subscriptions: {e}", exc_info=True)


# Global scheduler instance
schedule_executor = ScheduleExecutor()

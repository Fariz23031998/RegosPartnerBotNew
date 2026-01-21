"""
Async bot manager for handling multiple Telegram bots.
"""
import asyncio
import logging
from typing import Dict, Optional
import httpx
from datetime import datetime
from core.message_utils import split_message
from core.telegram_webhook import (
    get_bot_info,
    set_webhook,
    check_webhook_info,
    verify_webhook_accessible,
    delete_webhook,
    set_chat_menu_button
)

logger = logging.getLogger(__name__)


class BotManager:
    """Manages multiple Telegram bots asynchronously"""
    
    def __init__(self):
        self.bots: Dict[str, dict] = {}  # token -> bot_info
        self.webhook_url_base: Optional[str] = None
        # Temporary storage for registration data (chat_id -> registration_data)
        # Cleared after registration or timeout
        self.pending_registrations: Dict[int, dict] = {}
        # Temporary storage for registration data (chat_id -> registration_data)
        # Cleared after registration or timeout
        self.pending_registrations: Dict[int, dict] = {}
    
    def set_webhook_base_url(self, base_url: str):
        """Set the base URL for webhooks"""
        self.webhook_url_base = base_url.rstrip('/')
    
    async def register_bot(self, token: str, bot_name: Optional[str] = None, bot_id: Optional[int] = None) -> dict:
        """Register a new bot and set up its webhook"""
        if token in self.bots:
            logger.warning(f"Bot with token {token[:10]}... already registered, re-setting webhook...")
            # Re-setup webhook in case it wasn't configured before
            if self.webhook_url_base:
                webhook_path = f"/webhook/{token[:10]}"
                webhook_url = f"{self.webhook_url_base}{webhook_path}"
                if await set_webhook(token, webhook_url, bot_name or self.bots[token].get("bot_name")):
                    await check_webhook_info(token)
                # Re-set menu button with bot_name in URL
                # Use TELEGRAM_WEB_BASE_URL from config if available, otherwise fallback to webhook_url_base
                from config import TELEGRAM_WEB_BASE_URL
                web_base_url = TELEGRAM_WEB_BASE_URL or self.webhook_url_base
                
                if web_base_url:
                    base = web_base_url.rstrip('/')
                    final_bot_name = bot_name or self.bots[token].get("bot_name")
                    # URL encode bot_name for safe use in URL
                    import urllib.parse
                    encoded_bot_name = urllib.parse.quote(final_bot_name or "default", safe='')
                    web_app_url = f"{base}/mini-app/{encoded_bot_name}/"
                    await set_chat_menu_button(token, web_app_url, final_bot_name)
            return self.bots[token]
        
        # Get bot info from Telegram
        logger.info(f"Registering bot with token prefix: {token[:10]}...")
        bot_info = await get_bot_info(token)
        if not bot_info:
            raise ValueError(f"Invalid bot token: {token[:10]}... Could not get bot info from Telegram API")
        
        bot_data = {
            "token": token,
            "bot_name": bot_name or bot_info.get("username", "Unknown"),
            "bot_info": bot_info,
            "bot_id": bot_id,
            "registered_at": datetime.utcnow()
        }
        
        # Register bot first
        self.bots[token] = bot_data
        logger.info(f"Registered bot in memory: {bot_data['bot_name']} ({token[:10]}...)")
        
        # Set up webhook if base URL is configured
        if self.webhook_url_base:
            webhook_path = f"/webhook/{token[:10]}"
            webhook_url = f"{self.webhook_url_base}{webhook_path}"
            if await set_webhook(token, webhook_url, bot_data["bot_name"]):
                await check_webhook_info(token)
        else:
            logger.warning(f"Webhook base URL not set, bot {bot_data['bot_name']} registered but webhook not configured")
        
        # Set menu button to launch web app with bot_name in URL
        # Use TELEGRAM_WEB_BASE_URL from config if available, otherwise fallback to webhook_url_base
        from config import TELEGRAM_WEB_BASE_URL
        web_base_url = TELEGRAM_WEB_BASE_URL or self.webhook_url_base
        
        if web_base_url:
            # Construct web app URL with bot_name, ensuring it ends with /
            base = web_base_url.rstrip('/')
            import urllib.parse
            encoded_bot_name = urllib.parse.quote(bot_data["bot_name"] or "default", safe='')
            web_app_url = f"{base}/mini-app/{encoded_bot_name}/"
            await set_chat_menu_button(token, web_app_url, bot_data["bot_name"])
        else:
            logger.warning(f"Web base URL not set, menu button for {bot_data['bot_name']} not configured")
        
        return bot_data
    
    async def unregister_bot(self, token: str) -> bool:
        """Unregister a bot and delete its webhook"""
        if token not in self.bots:
            return False
        
        # Delete webhook
        await delete_webhook(token)
        
        del self.bots[token]
        logger.info(f"Unregistered bot: {token[:10]}...")
        return True
    
    async def process_update(
        self, 
        token: str, 
        update: dict, 
        regos_integration_token: Optional[str] = None
    ) -> Optional[dict]:
        """
        Process an incoming update for a specific bot.
        
        Args:
            token: Telegram bot token
            update: Telegram update object
            regos_integration_token: Optional REGOS integration token for partner operations
        """
        if token not in self.bots:
            logger.warning(f"Received update for unregistered bot: {token[:10]}...")
            logger.warning(f"Registered bots: {list(self.bots.keys())[:3]}...")  # Log first few for debugging
            return None
        
        bot_data = self.bots[token]
        bot_name = bot_data["bot_name"]
        
        logger.info(f"Processing update for bot {bot_name} (token: {token[:10]}...)")
        logger.debug(f"Update structure: message={'message' in update}, callback_query={'callback_query' in update}")
        
        # Handle callback query updates (button clicks)
        if "callback_query" in update:
            callback_query = update["callback_query"]
            callback_data = callback_query.get("data", "")
            chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
            from_user = callback_query.get("from", {})
            user_id = from_user.get("id")
            
            logger.info(f"Received callback query: data='{callback_data}', chat_id={chat_id}, user_id={user_id}")
            
            # Handle registration confirmation callbacks
            if callback_data.startswith("register_yes_") or callback_data.startswith("register_no_"):
                callback_query_id = callback_query.get("id")
                result = await self.handle_registration_callback(
                    token,
                    callback_data,
                    chat_id,
                    user_id,
                    regos_integration_token,
                    bot_id=bot_data.get("bot_id"),
                    callback_query_id=callback_query_id
                )
                # Answer callback query after handling
                await self.answer_callback_query(token, callback_query_id, "")
                return result
            
            # Answer callback query to remove loading state
            await self.answer_callback_query(token, callback_query.get("id"))
            return None
        
        # Handle message updates
        if "message" in update:
            message = update["message"]
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "").strip()
            
            logger.info(f"Received message from chat {chat_id}: text='{text[:50] if text else 'N/A'}', has_contact={'contact' in message}, message_type={message.get('message_id')}")
            
            if not chat_id:
                logger.error(f"Message has no chat_id: {message}")
                return None
            
            # Handle contact sharing first (if user shares contact)
            if "contact" in message:
                contact = message.get("contact")
                contact_user_id = contact.get("user_id")
                phone_number = contact.get("phone_number")
                message_from_id = message.get("from", {}).get("id")
                
                logger.info(f"Contact shared: phone={phone_number}, contact_user_id={contact_user_id}, message_from_id={message_from_id}")
                
                # Verify that the contact belongs to the user who sent it
                # contact_user_id might be None for contacts that don't have Telegram account
                # In that case, we still process the contact if it was sent by the user
                if contact_user_id is None or contact_user_id == message_from_id:
                    bot_id = bot_data.get("bot_id")
                    # Get user info from message
                    from_user = message.get("from", {})
                    user_first_name = from_user.get("first_name", "Партнер")
                    user_last_name = from_user.get("last_name", "")
                    return await self.handle_contact_shared(
                        token, 
                        chat_id, 
                        phone_number, 
                        regos_integration_token,
                        bot_id,
                        user_first_name,
                        user_last_name
                    )
                else:
                    return await self.send_message(
                        token, 
                        chat_id, 
                        "❌ Пожалуйста, поделитесь своим контактом, а не контактом другого пользователя.\n\n"
                        "Нажмите кнопку '📱 Поделиться контактом' для отправки вашего собственного контакта."
                    )
            
            # Handle /start command
            if text == "/start" or text.startswith("/start"):
                logger.info(f"Handling /start command for chat {chat_id}")
                try:
                    bot_id = bot_data.get("bot_id")
                    result = await self.handle_start_command(token, chat_id, regos_integration_token, bot_id)
                    if result:
                        logger.info(f"Successfully handled /start command for chat {chat_id}")
                    else:
                        logger.warning(f"handle_start_command returned None for chat {chat_id}")
                    return result
                except Exception as e:
                    logger.error(f"Error handling /start command for chat {chat_id}: {e}", exc_info=True)
                    # Send error message to user
                    await self.send_message(
                        token,
                        chat_id,
                        "❌ Произошла ошибка при обработке команды /start. Пожалуйста, попробуйте позже или обратитесь к администратору."
                    )
                    return None
            
            # If user sends any other text, remind them to share contact
            if text:
                logger.info(f"Received text message (not /start): '{text[:50]}'")
                # Remind user to use /start or share contact
                return await self.send_message(
                    token,
                    chat_id,
                    "👋 Для начала работы, пожалуйста, отправьте команду /start и поделитесь своим контактом."
                )
        else:
            logger.debug(f"Update does not contain a message, update keys: {update.keys()}")
        
        return None
    
    async def send_message(
        self, 
        token: str, 
        chat_id: int, 
        text: str, 
        parse_mode: Optional[str] = None,
        reply_markup: Optional[dict] = None
    ) -> Optional[dict]:
        """
        Send a message via Telegram API.
        If message exceeds 4096 characters, splits it into chunks and sends them sequentially.
        
        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID
            text: Message text (will be split if > 4096 chars)
            parse_mode: Optional parse mode (Markdown, HTML, etc.)
            reply_markup: Optional reply markup (keyboard, etc.)
        
        Returns:
            Result of the last message sent, or None if all failed
        """
        # Split message if it exceeds Telegram's limit
        chunks = split_message(text, max_length=4096)
        
        if len(chunks) > 1:
            logger.info(f"Message exceeds 4096 characters, splitting into {len(chunks)} chunks")
        
        last_result = None
        
        async with httpx.AsyncClient() as client:
            for idx, chunk in enumerate(chunks):
                try:
                    payload = {
                        "chat_id": chat_id,
                        "text": chunk
                    }
                    if parse_mode:
                        payload["parse_mode"] = parse_mode
                    # Only include reply_markup in the first chunk
                    if reply_markup and idx == 0:
                        payload["reply_markup"] = reply_markup
                    
                    response = await client.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json=payload,
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("ok"):
                            last_result = data.get("result")
                            # Small delay between chunks to avoid rate limiting
                            if idx < len(chunks) - 1:
                                await asyncio.sleep(0.1)
                        else:
                            logger.warning(f"Failed to send message chunk {idx + 1}/{len(chunks)}: {data.get('description', 'Unknown error')}")
                    else:
                        logger.warning(f"HTTP error sending message chunk {idx + 1}/{len(chunks)}: {response.status_code}")
                except Exception as e:
                    logger.error(f"Error sending message chunk {idx + 1}/{len(chunks)}: {e}")
                    # Continue sending remaining chunks even if one fails
        
        return last_result
    
    async def send_document(
        self,
        token: str,
        chat_id: int,
        document_path: str,
        caption: Optional[str] = None
    ) -> Optional[dict]:
        """Send a document/file via Telegram API"""
        import os
        if not os.path.exists(document_path):
            logger.error(f"File not found: {document_path}")
            return None
        
        async with httpx.AsyncClient() as client:
            try:
                with open(document_path, 'rb') as file:
                    files = {
                        'document': (os.path.basename(document_path), file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    }
                    data = {
                        'chat_id': chat_id
                    }
                    if caption:
                        data['caption'] = caption
                    
                    response = await client.post(
                        f"https://api.telegram.org/bot{token}/sendDocument",
                        data=data,
                        files=files,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("ok"):
                            logger.info(f"Successfully sent document to chat {chat_id}")
                            return result.get("result")
                        else:
                            logger.error(f"Failed to send document: {result.get('description')}")
                    else:
                        logger.error(f"HTTP error sending document: {response.status_code}")
                    return None
            except Exception as e:
                logger.error(f"Error sending document: {e}", exc_info=True)
                return None
    
    async def answer_callback_query(
        self,
        token: str,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> bool:
        """Answer a callback query to remove loading state"""
        try:
            url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
            data = {
                "callback_query_id": callback_query_id
            }
            if text:
                data["text"] = text
            if show_alert:
                data["show_alert"] = True
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=data)
                result = response.json()
                if result.get("ok"):
                    return True
                else:
                    logger.error(f"Failed to answer callback query: {result}")
                    return False
        except Exception as e:
            logger.error(f"Error answering callback query: {e}", exc_info=True)
            return False
    
    async def handle_registration_callback(
        self,
        token: str,
        callback_data: str,
        chat_id: int,
        user_id: int,
        regos_integration_token: Optional[str],
        bot_id: Optional[int] = None,
        callback_query_id: Optional[str] = None
    ) -> Optional[dict]:
        """Handle registration confirmation callback"""
        logger.info(f"Handling registration callback: {callback_data}, chat_id={chat_id}, user_id={user_id}")
        
        if callback_data.startswith("register_no_"):
            # User declined registration - clear pending registration data
            if chat_id in self.pending_registrations:
                del self.pending_registrations[chat_id]
            if callback_query_id:
                await self.answer_callback_query(token, callback_query_id, "Отменено")
            return await self.send_message(
                token,
                chat_id,
                "Хорошо, если передумаете, отправьте команду /start снова."
            )
        
        if not callback_data.startswith("register_yes_"):
            if callback_query_id:
                await self.answer_callback_query(token, callback_query_id, "")
            return None
        
        # User confirmed registration - get registration data from temporary storage
        if not regos_integration_token:
            if callback_query_id:
                await self.answer_callback_query(token, callback_query_id, "Ошибка: интеграция не настроена")
            return await self.send_message(
                token,
                chat_id,
                "Ошибка: Интеграция с REGOS не настроена. Обратитесь к администратору."
            )
        
        # Get registration data from temporary storage
        registration_data = self.pending_registrations.get(chat_id)
        if not registration_data:
            logger.error(f"No pending registration data found for chat_id={chat_id}")
            if callback_query_id:
                await self.answer_callback_query(token, callback_query_id, "Ошибка: данные не найдены")
            return await self.send_message(
                token,
                chat_id,
                "❌ Произошла ошибка. Пожалуйста, отправьте команду /start снова и поделитесь контактом."
            )
        
        phone_number = registration_data.get("phone")
        user_first_name = registration_data.get("first_name", "Партнер")
        user_last_name = registration_data.get("last_name", "")
        stored_bot_id = registration_data.get("bot_id")
        
        # Use stored bot_id if available, otherwise use passed bot_id
        if stored_bot_id:
            bot_id = stored_bot_id
        
        # Clear pending registration data
        del self.pending_registrations[chat_id]
        
        # Get bot settings for partner_group_id
        partner_group_id = 1
        if bot_id:
            try:
                from database import get_db
                from database.repositories import BotSettingsRepository
                db = await get_db()
                async with db.async_session_maker() as session:
                    settings_repo = BotSettingsRepository(session)
                    bot_settings = await settings_repo.get_by_bot_id(bot_id)
                    if bot_settings:
                        partner_group_id = bot_settings.partner_group_id
            except Exception as e:
                logger.error(f"Error fetching bot settings: {e}", exc_info=True)
        
        if callback_query_id:
            await self.answer_callback_query(token, callback_query_id, "Регистрация...")
        
        # Register partner directly (we already have contact info from when they shared it)
        from regos.partner import register_partner
        
        await self.send_message(token, chat_id, "📝 Регистрация нового партнера...")
        
        # Use provided user names
        full_name = f"{user_first_name} {user_last_name}".strip() if user_last_name else user_first_name
        
        # Register partner
        registration_result = await register_partner(
            regos_integration_token,
            partner_group_id,
            user_first_name,
            full_name,
            phone_number,
            str(chat_id)
        )
        
        if registration_result and registration_result.get("ok"):
            new_partner_id = registration_result.get("new_id")
            return await self.send_message(
                token,
                chat_id,
                f"✅ Регистрация успешна!\n\n"
                f"Вы зарегистрированы как новый партнер.\n"
                f"ID партнера: {new_partner_id}\n"
                f"Теперь вы будете получать уведомления через этого бота."
            )
        else:
            return await self.send_message(
                token,
                chat_id,
                "❌ Произошла ошибка при регистрации.\n\n"
                "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
            )
    
    async def handle_start_command(
        self, 
        token: str, 
        chat_id: int, 
        regos_integration_token: Optional[str],
        bot_id: Optional[int] = None
    ) -> Optional[dict]:
        """Handle /start command - request contact to check if user exists by phone number"""
        logger.info(f"handle_start_command called: chat_id={chat_id}, has_regos_token={regos_integration_token is not None}, bot_id={bot_id}")
        
        if not regos_integration_token:
            logger.warning(f"No REGOS integration token provided for bot")
            return await self.send_message(
                token,
                chat_id,
                "Ошибка: Интеграция с REGOS не настроена. Обратитесь к администратору."
            )
        
        # Get bot settings to check can_register
        can_register = False
        if bot_id:
            try:
                from database import get_db
                from database.repositories import BotSettingsRepository
                db = await get_db()
                async with db.async_session_maker() as session:
                    settings_repo = BotSettingsRepository(session)
                    bot_settings = await settings_repo.get_by_bot_id(bot_id)
                    if bot_settings:
                        can_register = bot_settings.can_register
                        logger.info(f"Bot settings: can_register={can_register}")
            except Exception as e:
                logger.error(f"Error fetching bot settings: {e}", exc_info=True)
        
        # Always request contact first - we'll check by phone number in handle_contact_shared
        # After checking, if not found and can_register is true, we'll show registration confirmation
        welcome_text = (
            "Добро пожаловать! 👋\n\n"
            "Для продолжения работы, пожалуйста, поделитесь своим контактом, "
            "чтобы мы могли найти ваш аккаунт в системе."
        )
        
        # Create keyboard with contact request button
        keyboard = {
            "keyboard": [[
                {
                    "text": "📱 Поделиться контактом",
                    "request_contact": True
                }
            ]],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        
        logger.info(f"Sending welcome message with contact request to chat {chat_id}")
        result = await self.send_message(
            token, 
            chat_id, 
            welcome_text,
            reply_markup=keyboard
        )
        
        if result:
            logger.info(f"Successfully sent welcome message to chat {chat_id}")
        else:
            logger.error(f"Failed to send welcome message to chat {chat_id}")
        
        return result
    
    async def handle_contact_shared(
        self,
        token: str,
        chat_id: int,
        phone_number: str,
        regos_integration_token: Optional[str],
        bot_id: Optional[int] = None,
        user_first_name: str = "Партнер",
        user_last_name: str = ""
    ) -> Optional[dict]:
        """Handle contact sharing - search partner and update REGOS, or register if not found"""
        if not regos_integration_token:
            return await self.send_message(
                token,
                chat_id,
                "Ошибка: Интеграция с REGOS не настроена. Обратитесь к администратору."
            )
        
        try:
            # Import REGOS partner functions
            from regos.partner import search_partner_by_phone, update_partner_telegram_id, register_partner
            
            # Get bot settings to check can_register and partner_group_id
            can_register = False
            partner_group_id = 1
            if bot_id:
                try:
                    from database import get_db
                    from database.repositories import BotSettingsRepository
                    db = await get_db()
                    async with db.async_session_maker() as session:
                        settings_repo = BotSettingsRepository(session)
                        bot_settings = await settings_repo.get_by_bot_id(bot_id)
                        if bot_settings:
                            can_register = bot_settings.can_register
                            partner_group_id = bot_settings.partner_group_id
                            logger.info(f"Bot settings loaded: can_register={can_register}, partner_group_id={partner_group_id}")
                        else:
                            logger.warning(f"No bot settings found for bot_id={bot_id}")
                except Exception as e:
                    logger.error(f"Error fetching bot settings: {e}", exc_info=True)
            else:
                logger.warning(f"bot_id is None, cannot fetch bot settings. Defaulting can_register=False")
            
            # Show processing message
            await self.send_message(token, chat_id, "🔍 Поиск вашего аккаунта в системе по номеру телефона...")
            
            # Search for partner by phone number (this is how we determine if user exists)
            partner = await search_partner_by_phone(regos_integration_token, phone_number)
            
            logger.info(f"Partner search result: found={partner is not None}, can_register={can_register}, bot_id={bot_id}")
            
            if not partner:
                # Partner not found by phone number - check if we can register
                logger.info(f"Partner not found by phone {phone_number}. Checking can_register={can_register}")
                if can_register:
                    # Store registration data temporarily (will be used when user clicks "Да")
                    registration_data = {
                        "phone": phone_number,
                        "first_name": user_first_name,
                        "last_name": user_last_name,
                        "chat_id": chat_id,
                        "bot_id": bot_id
                    }
                    self.pending_registrations[chat_id] = registration_data
                    logger.info(f"Stored registration data for chat_id={chat_id}, phone={phone_number}")
                    
                    welcome_text = (
                        "Вы не зарегистрированы. Хотите зарегистрироваться сейчас?"
                    )
                    
                    # Create inline keyboard with Да and Нет buttons
                    # Use simple callback_data (chat_id only) since we store data in memory
                    keyboard = {
                        "inline_keyboard": [[
                            {
                                "text": "Да",
                                "callback_data": f"register_yes_{chat_id}"
                            },
                            {
                                "text": "Нет",
                                "callback_data": f"register_no_{chat_id}"
                            }
                        ]]
                    }
                    
                    return await self.send_message(
                        token,
                        chat_id,
                        welcome_text,
                        reply_markup=keyboard
                    )
                else:
                    # Partner not found by phone number and registration not allowed
                    return await self.send_message(
                        token,
                        chat_id,
                        "❌ Извините, ваш аккаунт не найден в системе по номеру телефона.\n\n"
                        "Пожалуйста, убедитесь, что вы зарегистрированы как партнер в REGOS, "
                        "или обратитесь к администратору для регистрации."
                    )
            
            # Partner found by phone number - user exists in system
            partner_id = partner.get("id")
            partner_name = partner.get("name", "Партнер")
            partner_oked = partner.get("oked", "")
            
            # Check if this Telegram ID is already linked to this partner
            if partner_oked and str(partner_oked) == str(chat_id):
                # Already linked - user is already registered
                logger.info(f"Partner {partner_id} ({partner_name}) already linked to Telegram chat ID: {chat_id}")
                return await self.send_message(
                    token,
                    chat_id,
                    f"✅ Вы уже зарегистрированы, {partner_name}!\n\n"
                    f"Ваш Telegram аккаунт уже привязан к вашему профилю в системе.\n"
                    f"ID партнера: {partner_id}\n\n"
                    f"Вы будете получать уведомления через этого бота."
                )
            
            # Partner found by phone number but not linked to this Telegram ID - update it
            logger.info(f"Found partner {partner_id} ({partner_name}) by phone number {phone_number}, updating with Telegram chat ID: {chat_id}")
            
            # Update partner's oked field with Telegram chat ID
            success = await update_partner_telegram_id(
                regos_integration_token,
                partner_id,
                str(chat_id),
                partner
            )
            
            if success:
                return await self.send_message(
                    token,
                    chat_id,
                    f"✅ Отлично, {partner_name}!\n\n"
                    f"Ваш Telegram аккаунт успешно привязан к вашему профилю в системе.\n"
                    f"ID партнера: {partner_id}\n"
                    f"Теперь вы будете получать уведомления через этого бота."
                )
            else:
                return await self.send_message(
                    token,
                    chat_id,
                    "⚠️ Ваш аккаунт найден по номеру телефона, но произошла ошибка при привязке Telegram.\n\n"
                    "Пожалуйста, попробуйте еще раз или обратитесь к администратору."
                )
                
        except Exception as e:
            logger.error(f"Error handling contact share: {e}", exc_info=True)
            return await self.send_message(
                token,
                chat_id,
                "❌ Произошла ошибка при обработке вашего запроса.\n\n"
                "Пожалуйста, попробуйте еще раз позже или обратитесь к администратору."
            )
    
    async def get_bot_token_from_update(self, update: dict) -> Optional[str]:
        """Extract bot token from update (if stored in webhook path)"""
        # This is a helper method - in practice, you'd match the webhook path
        # to the token. For now, we'll need to pass token explicitly
        pass
    
    def get_registered_bots(self) -> Dict[str, dict]:
        """Get all registered bots"""
        return self.bots.copy()
    
    async def reload_all_bots(self, tokens: list):
        """Reload all bots from a list of tokens"""
        for token in tokens:
            try:
                await self.register_bot(token)
            except Exception as e:
                logger.error(f"Failed to register bot {token[:10]}...: {e}")


# Global bot manager instance
bot_manager = BotManager()


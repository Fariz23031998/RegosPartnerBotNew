"""
Async bot manager for handling multiple Telegram bots.
"""
import asyncio
import logging
from typing import Dict, Optional
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)


class BotManager:
    """Manages multiple Telegram bots asynchronously"""
    
    def __init__(self):
        self.bots: Dict[str, dict] = {}  # token -> bot_info
        self.webhook_url_base: Optional[str] = None
    
    def set_webhook_base_url(self, base_url: str):
        """Set the base URL for webhooks"""
        self.webhook_url_base = base_url.rstrip('/')
    
    async def register_bot(self, token: str, bot_name: Optional[str] = None) -> dict:
        """Register a new bot and set up its webhook"""
        if token in self.bots:
            logger.warning(f"Bot with token {token[:10]}... already registered, re-setting webhook...")
            # Re-setup webhook in case it wasn't configured before
            if self.webhook_url_base:
                await self._set_webhook(token, bot_name or self.bots[token].get("bot_name"))
            return self.bots[token]
        
        # Get bot info from Telegram
        logger.info(f"Registering bot with token prefix: {token[:10]}...")
        bot_info = await self._get_bot_info(token)
        if not bot_info:
            raise ValueError(f"Invalid bot token: {token[:10]}... Could not get bot info from Telegram API")
        
        bot_data = {
            "token": token,
            "bot_name": bot_name or bot_info.get("username", "Unknown"),
            "bot_info": bot_info,
            "registered_at": datetime.utcnow()
        }
        
        # Register bot first
        self.bots[token] = bot_data
        logger.info(f"Registered bot in memory: {bot_data['bot_name']} ({token[:10]}...)")
        
        # Set up webhook if base URL is configured
        if self.webhook_url_base:
            await self._set_webhook(token, bot_data["bot_name"])
        else:
            logger.warning(f"Webhook base URL not set, bot {bot_data['bot_name']} registered but webhook not configured")
        
        return bot_data
    
    async def unregister_bot(self, token: str) -> bool:
        """Unregister a bot and delete its webhook"""
        if token not in self.bots:
            return False
        
        # Delete webhook
        await self._delete_webhook(token)
        
        del self.bots[token]
        logger.info(f"Unregistered bot: {token[:10]}...")
        return True
    
    async def _get_bot_info(self, token: str) -> Optional[dict]:
        """Get bot information from Telegram API"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getMe",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        return data.get("result")
                return None
            except Exception as e:
                logger.error(f"Error getting bot info: {e}")
                return None
    
    async def _set_webhook(self, token: str, bot_name: Optional[str] = None):
        """Set webhook for a bot"""
        if not self.webhook_url_base:
            logger.warning("Webhook base URL not set, skipping webhook setup")
            return
        
        # Create a unique webhook path for this bot
        # Using first 10 chars of token as identifier
        webhook_path = f"/webhook/{token[:10]}"
        webhook_url = f"{self.webhook_url_base}{webhook_path}"
        
        async with httpx.AsyncClient() as client:
            try:
                # Set webhook with allowed_updates to ensure we receive all message types
                response = await client.post(
                    f"https://api.telegram.org/bot{token}/setWebhook",
                    json={
                        "url": webhook_url,
                        "allowed_updates": ["message", "callback_query"],
                        "drop_pending_updates": False
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        logger.info(f"Webhook set for {bot_name or token[:10]}: {webhook_url}")
                        # Verify webhook info after setting
                        await self._check_webhook_info(token)
                    else:
                        logger.error(f"Failed to set webhook: {data.get('description')}")
                else:
                    logger.error(f"HTTP error setting webhook: {response.status_code}")
            except Exception as e:
                logger.error(f"Error setting webhook: {e}")
    
    async def _check_webhook_info(self, token: str):
        """Check webhook info from Telegram and validate accessibility"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getWebhookInfo",
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        webhook_info = data.get("result", {})
                        webhook_url = webhook_info.get("url", "")
                        pending_count = webhook_info.get("pending_update_count", 0)
                        last_error = webhook_info.get("last_error_message")
                        last_error_date = webhook_info.get("last_error_date")
                        
                        logger.info(f"Webhook info: URL={webhook_url}, Pending updates={pending_count}")
                        
                        # Check for webhook errors
                        if last_error:
                            logger.error(f"⚠️ WEBHOOK ERROR: {last_error} (Date: {last_error_date})")
                            logger.error("This means Telegram cannot reach your webhook URL!")
                            logger.error("Possible causes:")
                            logger.error("  1. Tunnel service (localtunnel/ngrok) is not running or not accessible")
                            logger.error("  2. Firewall blocking connections to tunnel service")
                            logger.error("  3. Webhook URL is not publicly accessible")
                            logger.error(f"  4. SSL certificate issues with {webhook_url}")
                        elif webhook_url and pending_count > 0:
                            logger.warning(f"⚠️ {pending_count} pending updates - webhook may not be processing correctly")
                        
                        # Verify webhook URL is accessible (if it's set)
                        if webhook_url:
                            await self._verify_webhook_accessible(webhook_url)
            except Exception as e:
                logger.error(f"Error checking webhook info: {e}")
    
    async def _verify_webhook_accessible(self, webhook_url: str):
        """Verify that the webhook URL is accessible from the internet"""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                # Extract base URL and try to reach the health endpoint to verify the tunnel is working
                # webhook_url format: https://domain.com/webhook/token_prefix
                # We want: https://domain.com/health
                from urllib.parse import urlparse, urlunparse
                parsed = urlparse(webhook_url)
                # Build health URL from the base domain
                health_url = f"{parsed.scheme}://{parsed.netloc}/health"
                
                response = await client.get(health_url, timeout=5.0)
                if response.status_code == 200:
                    logger.info(f"✅ Webhook URL is accessible: {webhook_url}")
                else:
                    logger.warning(f"⚠️ Webhook URL health check returned status {response.status_code} (this may not affect webhook functionality)")
            except httpx.ConnectError:
                logger.error(f"❌ CRITICAL: Cannot connect to {webhook_url}")
                logger.error("   Your tunnel service (localtunnel/ngrok) is not working!")
                logger.error("   Telegram cannot send updates to your bot.")
            except Exception as e:
                logger.warning(f"Could not verify webhook accessibility: {e} (this may not affect webhook functionality)")
    
    async def _delete_webhook(self, token: str):
        """Delete webhook for a bot"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"https://api.telegram.org/bot{token}/deleteWebhook",
                    timeout=10.0
                )
                if response.status_code == 200:
                    logger.info(f"Webhook deleted for {token[:10]}...")
            except Exception as e:
                logger.error(f"Error deleting webhook: {e}")
    
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
        
        # Handle message updates
        if "message" in update:
            message = update["message"]
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "").strip()
            
            logger.info(f"Received message from chat {chat_id}: text='{text[:50] if text else 'N/A'}', has_contact={'contact' in message}")
            
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
                    return await self.handle_contact_shared(
                        token, 
                        chat_id, 
                        phone_number, 
                        regos_integration_token
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
                return await self.handle_start_command(token, chat_id, regos_integration_token)
            
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
        """Send a message via Telegram API"""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "chat_id": chat_id,
                    "text": text
                }
                if parse_mode:
                    payload["parse_mode"] = parse_mode
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                
                response = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json=payload,
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        return data.get("result")
                return None
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return None
    
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
    
    async def handle_start_command(
        self, 
        token: str, 
        chat_id: int, 
        regos_integration_token: Optional[str]
    ) -> Optional[dict]:
        """Handle /start command - request contact from user"""
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
        
        return await self.send_message(
            token, 
            chat_id, 
            welcome_text,
            reply_markup=keyboard
        )
    
    async def handle_contact_shared(
        self,
        token: str,
        chat_id: int,
        phone_number: str,
        regos_integration_token: Optional[str]
    ) -> Optional[dict]:
        """Handle contact sharing - search partner and update REGOS"""
        if not regos_integration_token:
            return await self.send_message(
                token,
                chat_id,
                "Ошибка: Интеграция с REGOS не настроена. Обратитесь к администратору."
            )
        
        try:
            # Import REGOS partner functions
            from regos.partner import search_partner_by_phone, update_partner_telegram_id
            
            # Show processing message
            await self.send_message(token, chat_id, "🔍 Поиск вашего аккаунта в системе...")
            
            # Search for partner by phone number
            partner = await search_partner_by_phone(regos_integration_token, phone_number)
            
            if not partner:
                # Partner not found
                return await self.send_message(
                    token,
                    chat_id,
                    "❌ Извините, ваш аккаунт не найден в системе.\n\n"
                    "Пожалуйста, убедитесь, что вы зарегистрированы как партнер в REGOS, "
                    "или обратитесь к администратору для регистрации."
                )
            
            # Partner found - update with Telegram chat ID
            partner_id = partner.get("id")
            partner_name = partner.get("name", "Партнер")
            
            logger.info(f"Found partner {partner_id} ({partner_name}), updating with Telegram chat ID: {chat_id}")
            
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
                    "⚠️ Ваш аккаунт найден, но произошла ошибка при привязке Telegram.\n\n"
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


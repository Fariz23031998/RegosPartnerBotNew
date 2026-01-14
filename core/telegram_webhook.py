"""
Telegram webhook management utilities.
"""
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


async def get_bot_info(token: str) -> Optional[dict]:
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


async def set_webhook(token: str, webhook_url: str, bot_name: Optional[str] = None):
    """Set webhook for a bot"""
    async with httpx.AsyncClient() as client:
        try:
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
                    return True
                else:
                    logger.error(f"Failed to set webhook: {data.get('description')}")
            else:
                logger.error(f"HTTP error setting webhook: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False


async def check_webhook_info(token: str):
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
                    
                    if webhook_url:
                        await verify_webhook_accessible(webhook_url)
        except Exception as e:
            logger.error(f"Error checking webhook info: {e}")


async def verify_webhook_accessible(webhook_url: str):
    """Verify that the webhook URL is accessible from the internet"""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(webhook_url)
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


async def delete_webhook(token: str):
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

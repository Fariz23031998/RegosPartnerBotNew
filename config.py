"""
Example configuration file.
Copy this to config.py and update with your values.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Webhook base URL - set this to your public domain
# For development with ngrok: "https://your-ngrok-url.ngrok.io"
# For production: "https://your-domain.com"
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "https://your-domain.com")

# Telegram Web App base URL - set this to your public domain for the web app
# For development with ngrok: "https://your-ngrok-url.ngrok.io"
# For production: "https://your-domain.com"
TELEGRAM_WEB_BASE_URL = os.getenv("TELEGRAM_WEB_BASE_URL", WEBHOOK_BASE_URL)

# Database path
DATABASE_PATH = os.getenv("DATABASE_PATH", "telegram_bots.db")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

APP_NAME = os.getenv("APP_NAME", "RegosPartnerBot")

"""
FastAPI application for Telegram bot webhook engine.
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import get_db, init_db, close_db
from database.repositories import BotRepository
from bot_manager import bot_manager
from api.routers import auth, users, bots, bot_settings, bot_schedules, telegram_webapp
from auth import verify_admin
from config import WEBHOOK_BASE_URL
from regos.webhook_handler import handle_regos_webhook

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting application...")
    await init_db()
    
    # Set webhook base URL FIRST (before loading bots)
    bot_manager.set_webhook_base_url(WEBHOOK_BASE_URL)
    logger.info(f"Webhook base URL set to: {WEBHOOK_BASE_URL}")
    
    # Load active bots from database and register them
    db = await get_db()
    async with db.async_session_maker() as session:
        bot_repo = BotRepository(session)
        active_bots = await bot_repo.get_all_active()
        logger.info(f"Loading {len(active_bots)} active bot(s) from database...")
        for bot in active_bots:
            try:
                await bot_manager.register_bot(bot.telegram_token, bot.bot_name)
                logger.info(f"Successfully loaded and registered bot: {bot.bot_name or bot.telegram_token[:10]}")
            except Exception as e:
                logger.error(f"Failed to load bot {bot.telegram_token[:10]}...: {e}", exc_info=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Telegram Bot Webhook Engine",
    description="Multi-bot webhook engine using FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Admin panel (Vite default port)
        "http://localhost:3000",  # Alternative admin panel port
        "http://localhost:5175",   # Telegram web app port
        "https://941e514f5679.ngrok-free.app",   # Telegram web app port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(bots.router)
app.include_router(bot_settings.router)
app.include_router(bot_schedules.router)
app.include_router(telegram_webapp.router)


# Webhook endpoint - dynamic path for each bot (public, no auth needed)
@app.post("/webhook/{token_prefix}")
async def webhook_handler(token_prefix: str, request: Request):
    """Handle incoming webhook updates from Telegram"""
    try:
        update_data = await request.json()
        logger.info(f"Received webhook update for token prefix: {token_prefix}")
        logger.debug(f"Update data: {update_data}")
        
        # Find the bot by prefix (first 10 characters)
        db = await get_db()
        async with db.async_session_maker() as session:
            bot_repo = BotRepository(session)
            active_bots = await bot_repo.get_all_active()
            bot_obj = None
            for bot in active_bots:
                if bot.telegram_token[:10] == token_prefix:
                    bot_obj = bot
                    break
            
            if not bot_obj:
                logger.warning(f"Bot not found for token prefix: {token_prefix}")
                raise HTTPException(status_code=404, detail="Bot not found")
            
            if not bot_obj.is_active:
                logger.warning(f"Bot {bot_obj.bot_id} is inactive")
                raise HTTPException(status_code=404, detail="Bot is inactive")
            
            logger.info(f"Processing update for bot: {bot_obj.bot_name or bot_obj.telegram_token[:10]}")
            
            # Process the update with bot object (includes regos_integration_token)
            result = await bot_manager.process_update(
                bot_obj.telegram_token, 
                update_data,
                regos_integration_token=bot_obj.regos_integration_token
            )
            
            logger.info(f"Successfully processed update for bot {bot_obj.bot_id}")
            return {"ok": True, "result": result}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/registered-bots")
async def get_registered_bots(current_user: dict = Depends(verify_admin)):
    """Get all currently registered bots (for admin panel)"""
    bots_info = bot_manager.get_registered_bots()
    # Remove sensitive token information
    return {
        bot_token[:10]: {
            "bot_name": bot_data["bot_name"],
            "bot_info": bot_data["bot_info"],
            "registered_at": bot_data["registered_at"].isoformat()
        }
        for bot_token, bot_data in bots_info.items()
    }


@app.post("/regos/webhook")
async def regos_webhook_handler(request: Request):
    """Handle incoming webhooks from REGOS - delegates to webhook_handler module"""
    return await handle_regos_webhook(request)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "bots_registered": len(bot_manager.bots)}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

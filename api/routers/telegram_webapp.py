"""
Telegram Web App API routes for partners.
This module re-exports the router from the telegram_webapp subdirectory.
"""
import importlib.util
from pathlib import Path

# Import the router from the subdirectory's __init__.py
_subdir_init = Path(__file__).parent / "telegram_webapp" / "__init__.py"
spec = importlib.util.spec_from_file_location("telegram_webapp_subdir", _subdir_init)
telegram_webapp_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(telegram_webapp_module)

# Re-export the router
router = telegram_webapp_module.router

__all__ = ["router"]

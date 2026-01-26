from fastapi import APIRouter, Depends
import os
import sys

from services.translator_service import translator_service
from auth import verify_admin

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


router = APIRouter(prefix="/api/lang", tags=["language"])

@router.get("/{lang_code}")
async def get_language(lang_code: str):
    if lang_code.lower() not in ("en", "ru", "uz"):
        lang_code = "en"

    return translator_service.get_language_translations(lang_code)

@router.get("/{lang_code}/version")
async def get_version(lang_code: str):
    if lang_code.lower() not in ("en", "ru", "uz"):
        lang_code = "en"

    return translator_service.get_language_version(lang_code)

@router.post("/reload")
async def reload_translator_service(current_user: dict = Depends(verify_admin)):
    translator_service.clear_cache()
    return {"message": "Translator service reloaded"}
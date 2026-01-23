from fastapi import APIRouter
import os
import sys

from services.translator_service import Translator

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


router = APIRouter(prefix="/api/lang", tags=["language"])

translator = Translator()

@router.get("/{lang_code}")
async def get_language(lang_code: str):
    if lang_code.lower() not in ("en", "ru", "uz"):
        lang_code = "en"

    return translator.get_language_translations(lang_code)

@router.get("/{lang_code}/version")
async def get_version(lang_code: str):
    if lang_code.lower() not in ("en", "ru", "uz"):
        lang_code = "en"

    return translator.get_language_version(lang_code)
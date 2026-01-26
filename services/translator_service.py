from pathlib import Path
import json
from typing import Dict, Optional

class Translator:
    _cache: Dict[str, dict] = {}  # Class-level cache
    _locales_dir = Path(__file__).parent.parent / "languages"

    def __init__(self, default_lang: str = "en"):
        self.default_lang = default_lang
        self._load_language(default_lang)

    def _load_language(self, lang: str):
        """Load language file into memory if not already cached."""
        if lang in self._cache:
            return
        file_path = self._locales_dir / f"{lang}.json"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self._cache[lang] = json.load(f)
        except FileNotFoundError:
            # If language file doesn't exist, store empty dict
            self._cache[lang] = {}

    def get(
            self,
            key: str,
            lang: str = None,
            default: str = None,
            **kwargs
        ) -> str:
        lang = lang or self.default_lang
        self._load_language(lang)

        value = self._cache[lang]["translations"].get(key)

        if value is None and lang != self.default_lang:
            self._load_language(self.default_lang)
            value = self._cache[self.default_lang].get(key)

        if value is None:
            value = default if default is not None else key

        try:
            return value.format(**kwargs)
        except KeyError:
            # Missing variable → return untranslated string safely
            return value

    def get_language_translations(self, lang: str) -> Dict[str, str]:
        self._load_language(lang)
        return self._cache[lang]

    def get_language_version(self, lang: str) -> dict:
        self._load_language(lang)
        lang_data = self._cache[lang]
        return {
            "version": lang_data.get("version", "0"),
            "last_updated": lang_data.get("last_updated", "")
        }

    def clear_cache(self):
        """Clear all cached languages (useful in development)."""
        self._cache.clear()

translator_service = Translator()
# Singleton instance
if __name__ == "__main__":
    partner_name = "Master"
    partner_id = "1234567890"
    text = f"✅ Отлично, {partner_name}!\n\n"
    text += f"Ваш Telegram аккаунт успешно привязан к вашему профилю в системе.\n"
    text += f"ID партнера: {partner_id}\n"
    text += f"Теперь вы будете получать уведомления через этого бота."
    test = translator_service.get("bot_manager.contact-shared.success", "ru", default=text, partner_name=partner_name, partner_id=partner_id)
    print(test)
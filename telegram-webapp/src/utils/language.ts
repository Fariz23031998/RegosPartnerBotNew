import { indexedDBService } from "./indexedDB";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "https://3b71d0de96e1.ngrok-free.app";

export type SupportedLanguage = "uz" | "ru" | "en";

export interface LanguageVersion {
  version: string;
  last_updated: string;
}

export interface TranslationDictionary {
  [key: string]: string;
}

class LanguageService {
  private currentLanguage: SupportedLanguage = "en";
  private translations: TranslationDictionary = {};
  private supportedLanguages: SupportedLanguage[] = ["uz", "ru", "en"];

  private normalizeLanguageCode(code: unknown): SupportedLanguage | null {
    if (typeof code !== "string") return null;

    const trimmed = code.trim();
    if (!trimmed) return null;

    const langCode = trimmed.split(/[-_]/)[0].toLowerCase();
    if (this.supportedLanguages.includes(langCode as SupportedLanguage)) {
      return langCode as SupportedLanguage;
    }

    return null;
  }

  private extractLanguageFromInitData(initData: unknown): SupportedLanguage | null {
    if (typeof initData !== "string") return null;
    if (!initData.trim()) return null;

    try {
      const params = new URLSearchParams(initData);
      const userStr = params.get("user");
      if (!userStr) return null;

      const user = JSON.parse(userStr);
      return this.normalizeLanguageCode(user?.language_code);
    } catch {
      return null;
    }
  }

  private tryGetTelegramLanguage(): SupportedLanguage | null {
    const tg = (window as any).Telegram?.WebApp;

    const fromUnsafe = this.normalizeLanguageCode(tg?.initDataUnsafe?.user?.language_code);
    if (fromUnsafe) return fromUnsafe;

    const fromInitData = this.extractLanguageFromInitData(tg?.initData);
    if (fromInitData) return fromInitData;

    return null;
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Always detect language from Telegram Mini App
   */
  detectTelegramLanguage(): SupportedLanguage {
    return this.tryGetTelegramLanguage() ?? "en";
  }

  /**
   * Telegram clients (especially mobile) can expose WebApp data slightly later
   * than the first render. This waits briefly for Telegram-provided language.
   */
  async detectTelegramLanguageWithRetry(
    timeoutMs: number = 800,
    pollIntervalMs: number = 50
  ): Promise<SupportedLanguage> {
    const start = Date.now();

    while (Date.now() - start < timeoutMs) {
      const lang = this.tryGetTelegramLanguage();
      if (lang) return lang;

      // If Telegram WebApp is not present at all, don't delay startup.
      if (!(window as any).Telegram?.WebApp) {
        return "en";
      }

      await this.sleep(pollIntervalMs);
    }

    return "en";
  }

  /**
   * Initialize language system
   * Language is ALWAYS taken from Telegram
   */
  async initialize(): Promise<SupportedLanguage> {
    const telegramLang = await this.detectTelegramLanguageWithRetry();
    this.currentLanguage = telegramLang;

    await this.loadLanguage(telegramLang);

    return telegramLang;
  }

  /**
   * Load translations (cache-aware)
   * No language persistence here
   */
  async loadLanguage(langCode: SupportedLanguage): Promise<void> {
    try {
      const needsUpdate = await this.checkLanguageVersion(langCode);

      if (needsUpdate) {
        await this.fetchLanguageFromBackend(langCode);
        this.currentLanguage = langCode;
      }

      const cachedTranslations = await indexedDBService.getLanguage(langCode);

      if (cachedTranslations) {
        this.translations = cachedTranslations;
      } else {
        await this.fetchLanguageFromBackend(langCode);
      }
    } catch (error) {
      console.error("Error loading language:", error);
      this.translations = this.getFallbackTranslations();
    }
  }

  /**
   * Check backend language version
   */
  async checkLanguageVersion(langCode: SupportedLanguage): Promise<boolean> {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/lang/${langCode}/version`,
        {
          headers: {
            "ngrok-skip-browser-warning": "true",
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) return false;

      const data: LanguageVersion = await response.json();
      const cachedVersion = await indexedDBService.getLanguageVersion(langCode);

      return !cachedVersion || cachedVersion !== data.version;
    } catch (error) {
      console.error("Error checking language version:", error);
      return false;
    }
  }

  /**
   * Fetch translations from backend
   */
  async fetchLanguageFromBackend(langCode: SupportedLanguage): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/lang/${langCode}`, {
      headers: {
        "ngrok-skip-browser-warning": "true",
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error("Failed to fetch language data");
    }

    const data = await response.json();

    await indexedDBService.saveLanguage(
      langCode,
      data.version,
      data.translations
    );

    this.translations = data.translations;
  }

  /**
   * Translate key
   */
  t(key: string, fallback?: string): string {
    return this.translations[key] || fallback || key;
  }

  /**
   * Current language (Telegram-driven)
   */
  getCurrentLanguage(): SupportedLanguage {
    return this.currentLanguage;
  }

  getSupportedLanguages(): SupportedLanguage[] {
    return this.supportedLanguages;
  }

  /**
   * Language change is ignored (Telegram controls it)
   * Optional: throw or log warning
   */
  async changeLanguage(_: SupportedLanguage): Promise<void> {
    console.warn(
      "Language change ignored. Language is controlled by Telegram settings."
    );
  }

  /**
   * Fallback translations
   */
  private getFallbackTranslations(): TranslationDictionary {
    return {
      "common.loading": "Loading...",
      "common.save": "Save",
      "common.cancel": "Cancel",
      "common.delete": "Delete",
      "common.edit": "Edit",
      "common.close": "Close",
      "common.confirm": "Confirm",
      "common.search": "Search",
      "common.add": "Add",
      "common.create": "Create",
      "common.error": "Error",
      "common.success": "Success",
    };
  }

  /**
   * Clear cached translations only
   */
  async clearCache(): Promise<void> {
    await indexedDBService.clearLanguageData();
  }
}

export const languageService = new LanguageService();

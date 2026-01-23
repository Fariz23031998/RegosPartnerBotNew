import { indexedDBService } from "./indexedDB";
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

  /**
   * Detect browser language and return supported language code
   */
  detectBrowserLanguage(): SupportedLanguage {
    const browserLang = navigator.language || (navigator as any).userLanguage;
    const langCode = browserLang.split("-")[0].toLowerCase();

    if (this.supportedLanguages.includes(langCode as SupportedLanguage)) {
      return langCode as SupportedLanguage;
    }

    return "en"; // Default to English
  }

  /**
   * Initialize language system on app load
   */
  async initialize(): Promise<SupportedLanguage> {
    // Detect browser language
    const detectedLang = this.detectBrowserLanguage();
    
    // Get stored language preference or use detected
    const storedLang = await indexedDBService.getSetting("current_language");
    const langToUse: SupportedLanguage = storedLang || detectedLang;

    // Load language
    await this.loadLanguage(langToUse);

    return langToUse;
  }

  /**
   * Load language from IndexedDB or backend
   */
  async loadLanguage(langCode: SupportedLanguage): Promise<void> {
    try {
      // Check if language needs update
      const needsUpdate = await this.checkLanguageVersion(langCode);

      if (needsUpdate) {
        // Fetch from backend
        await this.fetchLanguageFromBackend(langCode);
      }

      // Load from IndexedDB
      const cachedTranslations = await indexedDBService.getLanguage(langCode);
      
      if (cachedTranslations) {
        this.translations = cachedTranslations;
        this.currentLanguage = langCode;
        await indexedDBService.saveSetting("current_language", langCode);
      } else {
        await this.fetchLanguageFromBackend(langCode);
      }
    } catch (error) {
      console.error("Error loading language:", error);
      this.translations = this.getFallbackTranslations();
      this.currentLanguage = "en";
    }
  }

  /**
   * Check if language version needs update
   */
  async checkLanguageVersion(langCode: SupportedLanguage): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/lang/${langCode}/version`, {
        headers: {},
      });

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
   * Fetch language data from backend
   */
  async fetchLanguageFromBackend(langCode: SupportedLanguage): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/lang/${langCode}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json"
        }
      });

      if (!response.ok) throw new Error("Failed to fetch language data");

      const data = await response.json();
      
      // Save to IndexedDB
      await indexedDBService.saveLanguage(langCode, data.version, data.translations);
      
      // Update current translations
      this.translations = data.translations;
      this.currentLanguage = langCode;
      await indexedDBService.saveSetting("current_language", langCode);
    } catch (error) {
      console.error("Error fetching language from backend:", error);
      throw error;
    }
  }

  /**
   * Get translation for a key
   */
  t(key: string, fallback?: string): string {
    return this.translations[key] || fallback || key;
  }

  /**
   * Get current language
   */
  getCurrentLanguage(): SupportedLanguage {
    return this.currentLanguage;
  }

  /**
   * Get supported languages
   */
  getSupportedLanguages(): SupportedLanguage[] {
    return this.supportedLanguages;
  }

  /**
   * Change language
   */
  async changeLanguage(langCode: SupportedLanguage): Promise<void> {
    await this.loadLanguage(langCode);
  }

  /**
   * Fallback translations (English)
   */
  private getFallbackTranslations(): TranslationDictionary {
    return {
      // Common
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
      
      // Header
      "header.main": "Main",
      "header.logout": "Logout",
      "header.profile": "Profile",
      "header.changePassword": "Change Password",
      "header.currentPlan": "Current Plan",
      "header.plans": "Plans",
      "header.payments": "Payments",
      "header.about": "About",
      "header.addToken": "Add Regos Integration Token",
      
      // Add more as needed...
    };
  }

  /**
   * Clear all language cache
   */
  async clearCache(): Promise<void> {
    await indexedDBService.clearLanguageData();
  }
}

export const languageService = new LanguageService();
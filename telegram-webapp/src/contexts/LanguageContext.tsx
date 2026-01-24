import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { languageService, SupportedLanguage, TranslationDictionary } from "../utils/language";

interface LanguageContextType {
  currentLanguage: SupportedLanguage;
  changeLanguage: (lang: SupportedLanguage) => Promise<void>;
  t: (key: string, fallback?: string, params?: Record<string, string | number>) => string;
  isLoading: boolean;
  supportedLanguages: SupportedLanguage[];
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

interface LanguageProviderProps {
  children: ReactNode;
}

export const LanguageProvider: React.FC<LanguageProviderProps> = ({ children }) => {
  const [currentLanguage, setCurrentLanguage] = useState<SupportedLanguage>(() =>
    languageService.detectTelegramLanguage()
  );
  const [isLoading, setIsLoading] = useState(true);
  const [, setTranslations] = useState<TranslationDictionary>({});

  useEffect(() => {
    const initializeLanguage = async () => {
      setIsLoading(true);
      try {
        const detectedLang = await languageService.initialize();
        setCurrentLanguage(detectedLang);
      } catch (error) {
        console.error("Failed to initialize language:", error);
      } finally {
        setIsLoading(false);
      }
    };

    initializeLanguage();
  }, []);

  const changeLanguage = async (lang: SupportedLanguage) => {
    setIsLoading(true);
    try {
      await languageService.changeLanguage(lang);
      setCurrentLanguage(lang);
      setTranslations({}); // Force re-render
    } catch (error) {
      console.error("Failed to change language:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const t = (key: string, fallback?: string, params?: Record<string, string | number>): string => {
    let translation = languageService.t(key, fallback);
    
    // Handle interpolation if params provided
    if (params) {
      Object.keys(params).forEach(param => {
        const value = params[param].toString();
        // Support both {param} and {{param}} syntax
        translation = translation.replace(new RegExp(`\\{\\{?${param}\\}?\\}`, 'g'), value);
      });
    }
    
    return translation;
  };

  const value: LanguageContextType = {
    currentLanguage,
    changeLanguage,
    t,
    isLoading,
    supportedLanguages: languageService.getSupportedLanguages(),
  };

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
};
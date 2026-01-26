import { Globe } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { useLanguage } from "../contexts/LanguageContext";
import { SupportedLanguage } from "../utils/language";
import "./LanguageSelector.css";

const languageNames: Record<SupportedLanguage, string> = {
  uz: "O'zbekcha",
  ru: "Русский",
  en: "English"
};

const languageFlags: Record<SupportedLanguage, string> = {
  uz: "UZ",
  ru: "RU",
  en: "EN"
};

export const LanguageSelector = () => {
  const { currentLanguage, changeLanguage, supportedLanguages } = useLanguage();
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleLanguageClick = (lang: SupportedLanguage) => {
    changeLanguage(lang);
    setIsOpen(false);
  };

  return (
    <div className="language-selector" ref={dropdownRef}>
      <button
        className="language-button"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        {currentLanguage.toUpperCase()}
        <Globe className="h-5 w-5" />
      </button>

      <div className={`dropdown-content ${isOpen ? "open" : ""}`}>
        {supportedLanguages.map((lang) => (
          <button
            key={lang}
            onClick={() => handleLanguageClick(lang)}
            className={`dropdown-item ${currentLanguage === lang ? "active" : ""}`}
          >
            <span className="flag-text">{languageFlags[lang]}</span>
            {languageNames[lang]}
          </button>
        ))}
      </div>
    </div>
  );
};
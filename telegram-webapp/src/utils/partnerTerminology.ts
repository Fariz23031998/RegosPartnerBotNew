/**
 * Partner-facing terminology translation utilities.
 * 
 * In the app's logic, selling products corresponds to buying from the partner's perspective,
 * so debit/credit terminology should be inverted in partner-facing messages.
 */

/**
 * Get inverted debit/credit labels for partner-facing messages.
 * 
 * In the system:
 * - Debit = money coming in (from partner's perspective: they receive)
 * - Credit = money going out (from partner's perspective: they pay)
 * 
 * For partners, we invert:
 * - Debit (system) -> Credit (partner view: they receive money)
 * - Credit (system) -> Debit (partner view: they pay money)
 */
export function getInvertedDebitCreditLabels(lang: string = "ru"): { debitLabel: string; creditLabel: string } {
  const translations: Record<string, { debitLabel: string; creditLabel: string }> = {
    ru: { debitLabel: "Кредит", creditLabel: "Дебет" },  // Inverted
    en: { debitLabel: "Credit", creditLabel: "Debit" },  // Inverted
    uz: { debitLabel: "Kredit", creditLabel: "Debet" }   // Inverted
  };
  
  return translations[lang] || translations.ru;
}

/**
 * Get the label for 'debit' from partner's perspective (inverted)
 */
export function getPartnerDebitLabel(lang: string = "ru"): string {
  return getInvertedDebitCreditLabels(lang).debitLabel;
}

/**
 * Get the label for 'credit' from partner's perspective (inverted)
 */
export function getPartnerCreditLabel(lang: string = "ru"): string {
  return getInvertedDebitCreditLabels(lang).creditLabel;
}

/**
 * Convert document type name from system perspective to partner perspective.
 * 
 * From partner's perspective:
 * - System "Закупка" (Purchase) -> Partner sees "Отгрузка" (Shipment)
 * - System "Отгрузка" (Shipment) -> Partner sees "Закупка" (Purchase)
 * - System "Возврат закупки" -> Partner sees "Возврат отгрузки"
 * - System "Возврат отгрузки" -> Partner sees "Возврат закупки"
 * - System "Чек закупки" -> Partner sees "Чек отгрузки"
 * - System "Чек отгрузки" -> Partner sees "Чек закупки"
 */
export function getPartnerDocumentTypeName(systemName: string, lang: string = "ru"): string {
  if (!systemName) {
    return systemName;
  }
  
  const systemNameLower = systemName.toLowerCase().trim();
  
  // Russian mappings
  if (lang === "ru") {
    const mappings: Record<string, string> = {
      "закупка": "Отгрузка",
      "отгрузка": "Закупка",
      "возврат закупки": "Возврат отгрузки",
      "возврат отгрузки": "Возврат закупки",
      "чек закупки": "Чек отгрузки",
      "чек отгрузки": "Чек закупки",
      "чеки закупки": "Чеки отгрузки",
      "чеки отгрузки": "Чеки закупки",
      "чек возврата закупки": "Чек возврата отгрузки",
      "чек возврата отгрузки": "Чек возврата закупки",
    };
    
    // Try exact match first
    if (mappings[systemNameLower]) {
      return mappings[systemNameLower];
    }
    
    // Try partial matches
    if (systemNameLower.includes("закупка") && !systemNameLower.includes("возврат") && !systemNameLower.includes("чек")) {
      return systemName.replace(/Закупка/gi, "Отгрузка").replace(/закупка/gi, "отгрузка");
    } else if (systemNameLower.includes("отгрузка") && !systemNameLower.includes("возврат") && !systemNameLower.includes("чек")) {
      return systemName.replace(/Отгрузка/gi, "Закупка").replace(/отгрузка/gi, "закупка");
    } else if (systemNameLower.includes("возврат закупки")) {
      return systemName.replace(/Возврат закупки/gi, "Возврат отгрузки").replace(/возврат закупки/gi, "возврат отгрузки");
    } else if (systemNameLower.includes("возврат отгрузки")) {
      return systemName.replace(/Возврат отгрузки/gi, "Возврат закупки").replace(/возврат отгрузки/gi, "возврат закупки");
    } else if (systemNameLower.includes("чек возврата закупки")) {
      return systemName.replace(/Чек возврата закупки/gi, "Чек возврата отгрузки").replace(/чек возврата закупки/gi, "чек возврата отгрузки");
    } else if (systemNameLower.includes("чек возврата отгрузки")) {
      return systemName.replace(/Чек возврата отгрузки/gi, "Чек возврата закупки").replace(/чек возврата отгрузки/gi, "чек возврата закупки");
    } else if (systemNameLower.includes("чек закупки") || systemNameLower.includes("чеки закупки")) {
      return systemName.replace(/Чек закупки/gi, "Чек отгрузки").replace(/чек закупки/gi, "чек отгрузки").replace(/Чеки закупки/gi, "Чеки отгрузки");
    } else if (systemNameLower.includes("чек отгрузки") || systemNameLower.includes("чеки отгрузки")) {
      return systemName.replace(/Чек отгрузки/gi, "Чек закупки").replace(/чек отгрузки/gi, "чек закупки").replace(/Чеки отгрузки/gi, "Чеки закупки");
    }
  }
  
  // English mappings
  if (lang === "en") {
    const mappings: Record<string, string> = {
      "purchase": "Shipment",
      "shipment": "Purchase",
      "wholesale": "Purchase",
      "purchase return": "Shipment Return",
      "shipment return": "Purchase Return",
      "wholesale return": "Purchase Return",
    };
    
    if (mappings[systemNameLower]) {
      return mappings[systemNameLower];
    }
    
    if (systemNameLower.includes("purchase") && !systemNameLower.includes("return")) {
      return systemName.replace(/Purchase/gi, "Shipment").replace(/purchase/gi, "shipment");
    } else if (systemNameLower.includes("shipment") || systemNameLower.includes("wholesale")) {
      if (systemNameLower.includes("wholesale")) {
        return systemName.replace(/Wholesale/gi, "Purchase").replace(/wholesale/gi, "purchase");
      }
      return systemName.replace(/Shipment/gi, "Purchase").replace(/shipment/gi, "purchase");
    }
  }
  
  // If no mapping found, return original
  return systemName;
}

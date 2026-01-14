"""
Partner-facing terminology translation utilities.

In the app's logic, selling products corresponds to buying from the partner's perspective,
so debit/credit terminology should be inverted in partner-facing messages.
"""


def get_inverted_debit_credit_labels(lang: str = "ru") -> tuple[str, str]:
    """
    Get inverted debit/credit labels for partner-facing messages.
    
    In the system:
    - Debit = money coming in (from partner's perspective: they receive)
    - Credit = money going out (from partner's perspective: they pay)
    
    For partners, we invert:
    - Debit (system) -> Credit (partner view: they receive money)
    - Credit (system) -> Debit (partner view: they pay money)
    
    Args:
        lang: Language code ('ru', 'en', 'uz')
    
    Returns:
        Tuple of (debit_label, credit_label) for partner view
    """
    translations = {
        "ru": ("Кредит", "Дебет"),  # Inverted: system debit -> partner credit, system credit -> partner debit
        "en": ("Credit", "Debit"),  # Inverted
        "uz": ("Kredit", "Debet")   # Inverted
    }
    
    return translations.get(lang, translations["ru"])


def get_partner_debit_label(lang: str = "ru") -> str:
    """Get the label for 'debit' from partner's perspective (inverted)"""
    return get_inverted_debit_credit_labels(lang)[0]


def get_partner_credit_label(lang: str = "ru") -> str:
    """Get the label for 'credit' from partner's perspective (inverted)"""
    return get_inverted_debit_credit_labels(lang)[1]


def swap_debit_credit_values(debit: float, credit: float) -> tuple[float, float]:
    """
    Swap debit and credit values for partner view.
    
    Args:
        debit: System debit value
        credit: System credit value
    
    Returns:
        Tuple of (partner_debit, partner_credit) - swapped values
    """
    return credit, debit


def get_partner_document_type_name(system_name: str, lang: str = "ru") -> str:
    """
    Convert document type name from system perspective to partner perspective.
    
    From partner's perspective:
    - System "Закупка" (Purchase) -> Partner sees "Отгрузка" (Shipment)
    - System "Отгрузка" (Shipment) -> Partner sees "Закупка" (Purchase)
    - System "Возврат закупки" -> Partner sees "Возврат отгрузки"
    - System "Возврат отгрузки" -> Partner sees "Возврат закупки"
    - System "Чек закупки" -> Partner sees "Чек отгрузки"
    - System "Чек отгрузки" -> Partner sees "Чек закупки"
    
    Args:
        system_name: Document type name from system perspective
        lang: Language code ('ru', 'en', 'uz')
    
    Returns:
        Document type name from partner's perspective
    """
    if not system_name:
        return system_name
    
    system_name_lower = system_name.lower().strip()
    
    # Russian mappings
    if lang == "ru":
        mappings = {
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
        }
        
        # Try exact match first
        if system_name_lower in mappings:
            return mappings[system_name_lower]
        
        # Try partial matches
        if "закупка" in system_name_lower and "возврат" not in system_name_lower and "чек" not in system_name_lower:
            return system_name.replace("Закупка", "Отгрузка").replace("закупка", "отгрузка").replace("ЗАКУПКА", "ОТГРУЗКА")
        elif "отгрузка" in system_name_lower and "возврат" not in system_name_lower and "чек" not in system_name_lower:
            return system_name.replace("Отгрузка", "Закупка").replace("отгрузка", "закупка").replace("ОТГРУЗКА", "ЗАКУПКА")
        elif "возврат закупки" in system_name_lower:
            return system_name.replace("Возврат закупки", "Возврат отгрузки").replace("возврат закупки", "возврат отгрузки")
        elif "возврат отгрузки" in system_name_lower:
            return system_name.replace("Возврат отгрузки", "Возврат закупки").replace("возврат отгрузки", "возврат закупки")
        elif "чек возврата закупки" in system_name_lower:
            return system_name.replace("Чек возврата закупки", "Чек возврата отгрузки").replace("чек возврата закупки", "чек возврата отгрузки")
        elif "чек возврата отгрузки" in system_name_lower:
            return system_name.replace("Чек возврата отгрузки", "Чек возврата закупки").replace("чек возврата отгрузки", "чек возврата закупки")
        elif "чек закупки" in system_name_lower or "чеки закупки" in system_name_lower:
            return system_name.replace("Чек закупки", "Чек отгрузки").replace("чек закупки", "чек отгрузки").replace("Чеки закупки", "Чеки отгрузки")
        elif "чек отгрузки" in system_name_lower or "чеки отгрузки" in system_name_lower:
            return system_name.replace("Чек отгрузки", "Чек закупки").replace("чек отгрузки", "чек закупки").replace("Чеки отгрузки", "Чеки закупки")
    
    # English mappings
    elif lang == "en":
        mappings = {
            "purchase": "Shipment",
            "shipment": "Purchase",
            "wholesale": "Purchase",
            "purchase return": "Shipment Return",
            "shipment return": "Purchase Return",
            "wholesale return": "Purchase Return",
        }
        
        if system_name_lower in mappings:
            return mappings[system_name_lower]
        
        # Partial matches for English
        if "purchase" in system_name_lower and "return" not in system_name_lower:
            return system_name.replace("Purchase", "Shipment").replace("purchase", "shipment")
        elif "shipment" in system_name_lower or "wholesale" in system_name_lower:
            if "wholesale" in system_name_lower:
                return system_name.replace("Wholesale", "Purchase").replace("wholesale", "purchase")
            return system_name.replace("Shipment", "Purchase").replace("shipment", "purchase")
    
    # Uzbek mappings (similar pattern)
    elif lang == "uz":
        mappings = {
            "xarid": "yuklama",
            "yuklama": "xarid",
            "xarid qaytishi": "yuklama qaytishi",
            "yuklama qaytishi": "xarid qaytishi",
        }
        
        if system_name_lower in mappings:
            return mappings[system_name_lower]
    
    # If no mapping found, return original
    return system_name

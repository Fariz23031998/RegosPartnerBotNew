"""
Number formatting utilities for consistent display across the application.

Examples:
    60000.00 → "60 000"
    60000.05 → "60 000.05"
    60000.234557 → "60 000.23"
"""


def format_number(value, max_decimals=2):
    """
    Format a number with thousand separators and smart decimal handling.
    
    Args:
        value: The number to format (int, float, str, or None)
        max_decimals: Maximum decimal places (default: 2)
    
    Returns:
        Formatted number string with space-separated thousands
    """
    if value is None or value == '':
        return '0'
    
    try:
        num = float(value)
    except (ValueError, TypeError):
        return '0'
    
    if num != num:  # Check for NaN
        return '0'
    
    # Round to max_decimals
    rounded = round(num, max_decimals)
    
    # Split into integer and decimal parts
    parts = str(rounded).split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ''
    
    # Add thousand separators (spaces) to integer part
    # Reverse, add spaces every 3 digits, reverse back
    integer_reversed = integer_part[::-1]
    formatted_integer = ' '.join(
        integer_reversed[i:i+3] for i in range(0, len(integer_reversed), 3)
    )[::-1]
    
    # Handle decimal part
    if decimal_part:
        # Remove trailing zeros
        trimmed_decimal = decimal_part.rstrip('0')
        if trimmed_decimal:
            return f"{formatted_integer}.{trimmed_decimal}"
    
    # No decimal part or all zeros
    return formatted_integer


def format_currency(value, currency='', max_decimals=2):
    """
    Format a number with currency symbol.
    
    Args:
        value: The number to format
        currency: Currency symbol (default: '')
        max_decimals: Maximum decimal places (default: 2)
    
    Returns:
        Formatted number string with currency
    """
    formatted = format_number(value, max_decimals)
    return f"{formatted} {currency}".strip() if currency else formatted

/**
 * Format a number with thousand separators and smart decimal handling
 * 
 * Examples:
 * 60000.00 → "60 000"
 * 60000.05 → "60 000.05"
 * 60000.234557 → "60 000.23"
 * 
 * @param value - The number to format
 * @param maxDecimals - Maximum decimal places (default: 2)
 * @returns Formatted number string
 */
export function formatNumber(value: number | string | null | undefined, maxDecimals: number = 2): string {
  if (value === null || value === undefined || value === '') {
    return '0'
  }

  const num = typeof value === 'string' ? parseFloat(value) : value

  if (isNaN(num)) {
    return '0'
  }

  // Round to maxDecimals
  const rounded = Math.round(num * Math.pow(10, maxDecimals)) / Math.pow(10, maxDecimals)

  // Split into integer and decimal parts
  const parts = rounded.toString().split('.')
  const integerPart = parts[0]
  const decimalPart = parts[1]

  // Add thousand separators (spaces) to integer part
  const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')

  // Handle decimal part
  if (decimalPart) {
    // Remove trailing zeros
    const trimmedDecimal = decimalPart.replace(/0+$/, '')
    if (trimmedDecimal) {
      return `${formattedInteger}.${trimmedDecimal}`
    }
  }

  // No decimal part or all zeros
  return formattedInteger
}

/**
 * Format a number with currency symbol
 * 
 * @param value - The number to format
 * @param currency - Currency symbol (default: '')
 * @param maxDecimals - Maximum decimal places (default: 2)
 * @returns Formatted number string with currency
 */
export function formatCurrency(value: number | string | null | undefined, currency: string = '', maxDecimals: number = 2): string {
  const formatted = formatNumber(value, maxDecimals)
  return currency ? `${formatted} ${currency}` : formatted
}

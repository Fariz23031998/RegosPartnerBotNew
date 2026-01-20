/**
 * Cart validation utilities for stock management
 */

export interface StockInfo {
  common: number
  allowed?: number
}

export interface CartValidationResult {
  isValid: boolean
  error?: string
  maxQuantity?: number
}

/**
 * Check if a product can be added to cart based on stock availability
 */
export function canAddToCart(
  stockInfo: StockInfo | undefined,
  currentCartQuantity: number = 0
): CartValidationResult {
  if (!stockInfo) {
    return {
      isValid: false,
      error: 'Информация о наличии товара недоступна'
    }
  }

  // Check if product is out of stock
  if (stockInfo.common <= 0) {
    return {
      isValid: false,
      error: 'Товар отсутствует в наличии'
    }
  }

  // Use allowed quantity if available and positive, otherwise use common quantity
  // Only use allowed if it's defined and greater than 0
  const maxAvailable = stockInfo.allowed !== undefined && stockInfo.allowed > 0
    ? stockInfo.allowed
    : stockInfo.common

  if (maxAvailable <= 0) {
    return {
      isValid: false,
      error: 'Товар отсутствует в наличии'
    }
  }

  // Check if adding one more would exceed available stock
  const newQuantity = currentCartQuantity + 1
  if (newQuantity > maxAvailable) {
    return {
      isValid: false,
      error: `Доступно только ${maxAvailable} шт.`,
      maxQuantity: maxAvailable
    }
  }

  return {
    isValid: true,
    maxQuantity: maxAvailable
  }
}

/**
 * Check if a quantity update is valid based on stock availability
 */
export function canUpdateQuantity(
  newQuantity: number,
  stockInfo: StockInfo | undefined
): CartValidationResult {
  if (newQuantity <= 0) {
    return {
      isValid: true // Removing from cart is always valid
    }
  }

  if (!stockInfo) {
    return {
      isValid: false,
      error: 'Информация о наличии товара недоступна'
    }
  }

  // Check if product is out of stock
  if (stockInfo.common <= 0) {
    return {
      isValid: false,
      error: 'Товар отсутствует в наличии'
    }
  }

  // Use allowed quantity if available and positive, otherwise use common quantity
  // Only use allowed if it's defined and greater than 0
  const maxAvailable = stockInfo.allowed !== undefined && stockInfo.allowed > 0
    ? stockInfo.allowed
    : stockInfo.common

  if (maxAvailable <= 0) {
    return {
      isValid: false,
      error: 'Товар отсутствует в наличии'
    }
  }

  // Check if new quantity exceeds available stock
  if (newQuantity > maxAvailable) {
    return {
      isValid: false,
      error: `Доступно только ${maxAvailable} шт.`,
      maxQuantity: maxAvailable
    }
  }

  return {
    isValid: true,
    maxQuantity: maxAvailable
  }
}

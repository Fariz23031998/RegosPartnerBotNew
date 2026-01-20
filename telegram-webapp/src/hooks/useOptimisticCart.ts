/**
 * Optimized cart hook with immediate UI updates
 */
import { useCallback } from 'react'
import { useCart, CartItem } from '../contexts/CartContext'
import { canAddToCart, canUpdateQuantity, StockInfo, CartValidationResult } from '../utils/cartValidation'

export interface OptimisticCartResult {
  cart: CartItem[]
  addToCart: (item: Omit<CartItem, 'quantity'>, stockInfo?: StockInfo) => CartValidationResult
  updateQuantity: (productId: number, quantity: number, stockInfo?: StockInfo) => CartValidationResult
  removeFromCart: (productId: number) => void
  clearCart: () => void
  getCartTotal: () => number
  getCartItemCount: () => number
  getItemQuantity: (productId: number) => number
}

/**
 * Optimized cart hook with immediate UI updates
 * Validation is fast and synchronous, cart updates happen instantly
 */
export function useOptimisticCart(): OptimisticCartResult {
  const cart = useCart()

  const addToCart = useCallback((
    item: Omit<CartItem, 'quantity'>,
    stockInfo?: StockInfo
  ): CartValidationResult => {
    // Fast validation check
    if (stockInfo !== undefined) {
      const currentQuantity = cart.getItemQuantity(item.productId)
      const validation = canAddToCart(stockInfo, currentQuantity)
      if (!validation.isValid) {
        return validation
      }
    }

    // Update cart immediately - React will batch this automatically
    cart.addToCart(item)
    return { isValid: true }
  }, [cart])

  const updateQuantity = useCallback((
    productId: number,
    quantity: number,
    stockInfo?: StockInfo
  ): CartValidationResult => {
    // Fast validation check
    if (stockInfo !== undefined) {
      const validation = canUpdateQuantity(quantity, stockInfo)
      if (!validation.isValid) {
        return validation
      }
    }

    // Update cart immediately - React will batch this automatically
    cart.updateQuantity(productId, quantity)
    return { isValid: true }
  }, [cart])

  return {
    cart: cart.cart,
    addToCart,
    updateQuantity,
    removeFromCart: cart.removeFromCart,
    clearCart: cart.clearCart,
    getCartTotal: cart.getCartTotal,
    getCartItemCount: cart.getCartItemCount,
    getItemQuantity: cart.getItemQuantity,
  }
}

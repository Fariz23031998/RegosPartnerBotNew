/**
 * Hook that wraps cart functions with stock validation
 */
import { useCallback } from 'react'
import { useCart, CartItem } from '../contexts/CartContext'
import { canAddToCart, canUpdateQuantity, StockInfo, CartValidationResult } from '../utils/cartValidation'

export interface CartWithValidation {
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
 * Hook that provides cart functions with stock validation
 * If stockInfo is provided, validates before adding/updating
 */
export function useCartWithValidation(): CartWithValidation {
  const cart = useCart()

  const addToCart = useCallback((
    item: Omit<CartItem, 'quantity'>,
    stockInfo?: StockInfo
  ): CartValidationResult => {
    const currentQuantity = cart.getItemQuantity(item.productId)
    
    // If stock info is provided, validate
    if (stockInfo !== undefined) {
      const validation = canAddToCart(stockInfo, currentQuantity)
      if (!validation.isValid) {
        return validation
      }
    }

    // If validation passed or no stock info, add to cart
    cart.addToCart(item)
    return { isValid: true }
  }, [cart])

  const updateQuantity = useCallback((
    productId: number,
    quantity: number,
    stockInfo?: StockInfo
  ): CartValidationResult => {
    // If stock info is provided, validate
    if (stockInfo !== undefined) {
      const validation = canUpdateQuantity(quantity, stockInfo)
      if (!validation.isValid) {
        return validation
      }
    }

    // If validation passed or no stock info, update quantity
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

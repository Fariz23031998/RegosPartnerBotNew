import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface CartItem {
  productId: number
  name: string
  price: number
  image_url?: string
  code: number
  group: string
  quantity: number
  quantityAllowed?: number
}

interface CartContextType {
  cart: CartItem[]
  addToCart: (item: Omit<CartItem, 'quantity'>) => void
  updateQuantity: (productId: number, quantity: number) => void
  removeFromCart: (productId: number) => void
  clearCart: () => void
  getCartTotal: () => number
  getCartItemCount: () => number
  getItemQuantity: (productId: number) => number
}

const CartContext = createContext<CartContextType | undefined>(undefined)

// Helper function to get cart storage key with bot_name prefix
function getCartStorageKey(botName: string | null): string {
  if (!botName) {
    return 'telegram_shop_cart' // Fallback for backward compatibility
  }
  return `${botName}_telegram_shop_cart`
}

// Helper function to load cart from localStorage
function loadCartFromStorage(botName: string | null): CartItem[] {
  try {
    const storageKey = getCartStorageKey(botName)
    const savedCart = localStorage.getItem(storageKey)
    if (savedCart) {
      const parsed = JSON.parse(savedCart)
      if (Array.isArray(parsed)) {
        return parsed
      }
    }
  } catch (e) {
    console.error('Error loading cart from localStorage:', e)
  }
  return []
}

export function CartProvider({ children, botName }: { children: ReactNode; botName?: string | null }) {
  // Initialize cart from localStorage immediately
  const [cart, setCart] = useState<CartItem[]>(() => loadCartFromStorage(botName || null))
  const [isInitialized, setIsInitialized] = useState(false)

  // Mark as initialized after first render
  useEffect(() => {
    setIsInitialized(true)
  }, [])

  // Reload cart when botName changes
  useEffect(() => {
    if (botName && isInitialized) {
      const loadedCart = loadCartFromStorage(botName)
      setCart(loadedCart)
    }
  }, [botName, isInitialized])

  // Save cart to localStorage whenever it changes (but not on initial load)
  useEffect(() => {
    if (isInitialized && botName) {
      const storageKey = getCartStorageKey(botName)
      localStorage.setItem(storageKey, JSON.stringify(cart))
    }
  }, [cart, isInitialized, botName])

  const addToCart = (item: Omit<CartItem, 'quantity'>) => {
    setCart(prev => {
      const existing = prev.find(i => i.productId === item.productId)
      if (existing) {
        return prev.map(i =>
          i.productId === item.productId
            ? { ...i, quantity: i.quantity + 1 }
            : i
        )
      }
      return [...prev, { ...item, quantity: 1 }]
    })
  }

  const updateQuantity = (productId: number, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(productId)
      return
    }
    setCart(prev =>
      prev.map(item =>
        item.productId === productId ? { ...item, quantity } : item
      )
    )
  }

  const removeFromCart = (productId: number) => {
    setCart(prev => prev.filter(item => item.productId !== productId))
  }

  const clearCart = () => {
    setCart([])
  }

  const getCartTotal = () => {
    return cart.reduce((total, item) => total + item.price * item.quantity, 0)
  }

  const getCartItemCount = () => {
    return cart.reduce((count, item) => count + item.quantity, 0)
  }

  const getItemQuantity = (productId: number) => {
    const item = cart.find(i => i.productId === productId)
    return item ? item.quantity : 0
  }

  return (
    <CartContext.Provider
      value={{
        cart,
        addToCart,
        updateQuantity,
        removeFromCart,
        clearCart,
        getCartTotal,
        getCartItemCount,
        getItemQuantity,
      }}
    >
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const context = useContext(CartContext)
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider')
  }
  return context
}

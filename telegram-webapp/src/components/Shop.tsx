import { useState, useEffect, useCallback } from 'react'
import { FaShoppingCart, FaArrowLeft, FaImages } from 'react-icons/fa'
import { FaBasketShopping } from "react-icons/fa6"
import { FaReceipt } from "react-icons/fa";
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import Cart from './Cart'
import Checkout from './Checkout'
import OrderDetail from './OrderDetail'
import Toast from './Toast'
import { useCart } from '../contexts/CartContext'
import { useOptimisticCart } from '../hooks/useOptimisticCart'
import { useProducts } from '../hooks/useProducts'
import { useOrders } from '../hooks/useOrders'
import { formatNumber } from '../utils/formatNumber'
import { formatDate, calculateOrderTotal, getOrderStatus } from '../utils/orderUtils'
import './Shop.css'
import { useLanguage } from '../contexts/LanguageContext'

interface ShopProps {
  telegramUserId: number
  partnerId: number
  botName: string | null
  currencyName: string
  onBack: () => void
}

type ShopTab = 'products' | 'orders'

function Shop({ telegramUserId, partnerId, botName, currencyName, onBack }: ShopProps) {
  const [activeTab, setActiveTab] = useState<ShopTab>('products')
  const [showGroupFilter, setShowGroupFilter] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  const [showCart, setShowCart] = useState(false)
  const [showCheckout, setShowCheckout] = useState(false)
  const { getCartItemCount } = useCart()
  const cart = useOptimisticCart()
  const [cartError, setCartError] = useState<string | null>(null)
  const { t } = useLanguage()
  // Memoize stock info creation to avoid recreating objects
  const createStockInfo = useCallback((product: { quantity: { common: number; allowed?: number } }) => ({
    common: product.quantity.common,
    allowed: product.quantity.allowed
  }), [])

  // Optimized handlers that batch state updates
  const handleAddToCart = useCallback((product: any) => {
    const stockInfo = createStockInfo(product)
    const result = cart.addToCart({
      productId: product.item.id,
      name: product.item.name,
      price: product.price,
      image_url: product.image_url || product.item.image_url,
      code: product.item.code,
      group: product.item.group.name,
      quantityAllowed: product.quantity.allowed,
    }, stockInfo)
    
    // Batch error state update
    if (!result.isValid && result.error) {
      setCartError(result.error)
    } else {
      setCartError(null)
    }
  }, [cart, createStockInfo])

  const handleUpdateQuantity = useCallback((productId: number, newQuantity: number, stockInfo: { common: number; allowed?: number }) => {
    const result = cart.updateQuantity(productId, newQuantity, stockInfo)
    if (!result.isValid && result.error) {
      setCartError(result.error)
      if (result.maxQuantity !== undefined) {
        cart.updateQuantity(productId, result.maxQuantity, stockInfo)
      }
    } else {
      setCartError(null)
    }
  }, [cart])

  const { getItemQuantity } = cart

  // Quick filter state
  type QuickFilter = 'all' | 'in-stock' | 'low-stock' | 'cheap' | 'expensive'
  
  // Helper function to get filter storage key with bot_name prefix
  const getFilterStorageKey = useCallback((botName: string | null): string => {
    if (!botName) {
      return 'shop-quick-filter' // Fallback for backward compatibility
    }
    return `${botName}_shop-quick-filter`
  }, [])

  const [quickFilter, setQuickFilter] = useState<QuickFilter>(() => {
    const storageKey = getFilterStorageKey(botName)
    const saved = localStorage.getItem(storageKey)
    return (saved as QuickFilter) || 'all'
  })

  // Reload quick filter when botName changes
  useEffect(() => {
    if (botName) {
      const storageKey = getFilterStorageKey(botName)
      const saved = localStorage.getItem(storageKey)
      if (saved) {
        setQuickFilter(saved as QuickFilter)
      }
    }
  }, [botName, getFilterStorageKey])

  // Orders state
  const [selectedOrder, setSelectedOrder] = useState<{ id: number } | null>(null)
  const { orders, isLoadingOrders, ordersError } = useOrders(telegramUserId, partnerId, botName)

  // Use products hook
  const {
    products,
    groups,
    selectedGroups,
    setSelectedGroups,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    searchQuery,
    setSearchQuery,
    observerTarget,
    applyQuickFilter
  } = useProducts(telegramUserId, botName, quickFilter)

  // Save quick filter to localStorage
  useEffect(() => {
    if (botName) {
      const storageKey = getFilterStorageKey(botName)
      localStorage.setItem(storageKey, quickFilter)
    }
  }, [quickFilter, botName, getFilterStorageKey])

  const selectGroup = (groupId: number) => {
    setSelectedGroups([groupId])
    setShowGroupFilter(false)
  }

  const clearGroupFilter = () => {
    setSelectedGroups([])
    setShowGroupFilter(false)
  }

  const getSelectedGroupName = () => {
    if (selectedGroups.length === 0) {
      return t("shop.all-products", "Все товары")
    }
    const selectedGroup = groups.find(g => g.id === selectedGroups[0])
    return selectedGroup ? selectedGroup.name : t("shop.all-products", "Все товары")
  }

  const formatPrice = (price: number) => {
    return formatNumber(price)
  }

  // Highlight search matches in text
  const highlightText = (text: string, query: string) => {
    if (!query || !query.trim()) {
      return text
    }

    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const regex = new RegExp(`(${escapedQuery})`, 'gi')
    const parts = text.split(regex)

    return parts.map((part, index) => {
      // Check if this part matches the query (case-insensitive)
      if (part.toLowerCase() === query.toLowerCase()) {
        return <mark key={index} className="search-highlight">{part}</mark>
      }
      return part
    })
  }




  if (isLoading) {
    return <Loading />
  }

  if (error) {
    return <ErrorMessage message={error} />
  }

  if (showCheckout) {
    return (
      <>
        {cartError && (
          <Toast
            message={cartError}
            type="warning"
            duration={3000}
            onClose={() => setCartError(null)}
          />
        )}
        <Checkout
          telegramUserId={telegramUserId}
          partnerId={partnerId}
          botName={botName}
          currencyName={currencyName}
          onBack={() => setShowCheckout(false)}
          onComplete={() => {
            setShowCheckout(false)
            setShowCart(false)
          }}
        />
      </>
    )
  }

  if (selectedOrder) {
    return (
      <>
        {cartError && (
          <Toast
            message={cartError}
            type="warning"
            duration={3000}
            onClose={() => setCartError(null)}
          />
        )}
        <OrderDetail
          orderId={selectedOrder.id}
          telegramUserId={telegramUserId}
          partnerId={partnerId}
          botName={botName}
          currencyName={currencyName}
          onBack={() => setSelectedOrder(null)}
        />
      </>
    )
  }

  return (
    <div className="shop">
      {cartError && (
        <Toast
          message={cartError}
          type="warning"
          duration={3000}
          onClose={() => setCartError(null)}
        />
      )}
      <div className="shop-header">
        <button className="back-button-icon" onClick={onBack} aria-label="Назад">
          <FaArrowLeft />
        </button>
        <div className="shop-tabs">
          <button
            className={`shop-tab ${activeTab === 'products' ? 'active' : ''}`}
            onClick={() => setActiveTab('products')}
          >
            <FaBasketShopping size={30} />
          </button>
          <button
            className={`shop-tab ${activeTab === 'orders' ? 'active' : ''}`}
            onClick={() => setActiveTab('orders')}
          >
            <FaReceipt size={30} />
          </button>
        </div>
        {activeTab === 'products' && (
          <>
            {!showSearch && (
              <button
                className="search-icon-button"
                onClick={() => setShowSearch(true)}
                aria-label={t("shop.search", "Поиск")}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="m21 21-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            )}
            <button
              className="cart-icon-button"
              onClick={() => setShowCart(true)}
              title={t("shop.cart", "Корзина")}
            >
              <FaShoppingCart />
              {getCartItemCount() > 0 && (
                <span className="cart-badge">{getCartItemCount()}</span>
              )}
            </button>
          </>
        )}
      </div>

      {activeTab === 'products' && showSearch && (
        <div className="shop-filters sticky-filters">
          <div className="search-container">
            <div className={`search-box ${showSearch ? 'expanded' : ''}`}>
              <input
                type="text"
                placeholder={t("shop.search-placeholder", "Поиск товаров...")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input"
                autoFocus
              />
              <button
                className="search-close-button"
                onClick={() => {
                  setShowSearch(false)
                  setSearchQuery('')
                }}
                aria-label={t("shop.close-search", "Закрыть поиск")}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          </div>

          <div className="quick-filters">
            <button
              className={`quick-filter-chip ${quickFilter === 'all' ? 'active' : ''}`}
              onClick={() => setQuickFilter('all')}
            >
              {t("shop.all", "Все")}
            </button>
            <button
              className={`quick-filter-chip ${quickFilter === 'in-stock' ? 'active' : ''}`}
              onClick={() => setQuickFilter('in-stock')}
            >
              {t("shop.in-stock", "В наличии")}
            </button>
            <button
              className={`quick-filter-chip ${quickFilter === 'low-stock' ? 'active' : ''}`}
              onClick={() => setQuickFilter('low-stock')}
            >
              {t("shop.low-stock", "Мало")} 
            </button>
            <button
              className={`quick-filter-chip ${quickFilter === 'cheap' ? 'active' : ''}`}
              onClick={() => setQuickFilter('cheap')}
            >
              {t("shop.cheap", "Дешевые")}
            </button>
            <button
              className={`quick-filter-chip ${quickFilter === 'expensive' ? 'active' : ''}`}
              onClick={() => setQuickFilter('expensive')}
            >
              {t("shop.expensive", "Дорогие")}
            </button>
          </div>

          {groups.length > 0 && (
            <div className="group-filter-container">
              <button
                className="group-filter-button"
                onClick={() => setShowGroupFilter(!showGroupFilter)}
              >
                {getSelectedGroupName()}
                <span className="group-filter-arrow">{showGroupFilter ? '▲' : '▼'}</span>
              </button>

              {showGroupFilter && (
                <div className="group-filter-dropdown">
                  <button
                    className={`group-filter-item ${selectedGroups.length === 0 ? 'active' : ''}`}
                    onClick={clearGroupFilter}
                  >
                    {t("shop.all-products", "Все товары")}
                  </button>
                  {groups.map(group => (
                    <button
                      key={group.id}
                      className={`group-filter-item ${selectedGroups.includes(group.id) ? 'active' : ''}`}
                      onClick={() => selectGroup(group.id)}
                    >
                      {group.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'products' && (
        <>
          {(() => {
            const filteredProducts = applyQuickFilter(products)
            return filteredProducts.length === 0 ? (
              <div className="empty-products">
                {products.length === 0 ? t("shop.products-not-found", "Товары не найдены") : t("shop.products-not-found-by-filter", "Товары не найдены по выбранному фильтру")}
              </div>
            ) : (
              <>
                <div className={`products-grid ${showSearch ? 'search-active' : ''}`}>
                  {filteredProducts.map((product) => {
                    const itemQuantity = getItemQuantity(product.item.id)
                    const hasImage = product.image_url || product.item.image_url

                    return (
                      <div key={product.item.id} className="product-card">
                        <div className="product-image">
                          {hasImage ? (
                            <img src={product.image_url || product.item.image_url} alt={product.item.name} />
                          ) : (
                            <div className="product-image-placeholder">
                              <FaImages />
                            </div>
                          )}
                        </div>
                        <div className="product-info">
                          <div className="product-name">{highlightText(product.item.name, searchQuery)}</div>
                          <div className="product-details">
                            <div className="product-price">{formatPrice(product.price)} {currencyName}</div>
                            <div className="product-quantity">{t("shop.in-stock", "В наличии")}: {product.quantity.allowed} {product.item.unit?.name}</div>
                            <div className="product-code">{t("shop.code", "Код")}: {product.item.code}</div>
                            <div className="product-group">{product.item.group.name}</div>
                          </div>
                          {itemQuantity === 0 ? (
                            <button
                              className={`product-add-to-cart ${product.quantity.allowed !== undefined && product.quantity.allowed <= 0 ? 'disabled' : ''}`}
                              onClick={() => handleAddToCart(product)}
                            >
                              <FaShoppingCart />
                            </button>
                          ) : (
                            <div className="product-quantity-controls">
                              <button
                                className="quantity-btn"
                                onClick={() => {
                                  const stockInfo = createStockInfo(product)
                                  handleUpdateQuantity(product.item.id, itemQuantity - 1, stockInfo)
                                }}
                              >
                                −
                              </button>
                              <input
                                type="number"
                                min="1"
                                max={product.quantity.allowed !== undefined ? product.quantity.allowed : product.quantity.common}
                                value={itemQuantity}
                                onChange={(e) => {
                                  const qty = parseInt(e.target.value) || 1
                                  const stockInfo = createStockInfo(product)
                                  handleUpdateQuantity(product.item.id, qty, stockInfo)
                                }}
                                className="quantity-input"
                              />
                              <button
                                className={`quantity-btn ${itemQuantity >= (product.quantity.allowed !== undefined ? product.quantity.allowed : product.quantity.common) ? 'disabled' : ''}`}
                                onClick={() => {
                                  const stockInfo = createStockInfo(product)
                                  handleUpdateQuantity(product.item.id, itemQuantity + 1, stockInfo)
                                }}
                              >
                                +
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>

                {isLoadingMore && (
                  <div className="loading-more">
                    <Loading />
                  </div>
                )}

                {hasMore && !isLoadingMore && (
                  <div ref={observerTarget} className="observer-target" />
                )}
              </>
            )
          })()}
        </>
      )}

      {activeTab === 'orders' && (
        <>
          {isLoadingOrders ? (
            <Loading />
          ) : ordersError ? (
            <ErrorMessage message={ordersError} />
          ) : (() => {
            // Filter out empty orders (no operations)
            const nonEmptyOrders = orders.filter(order => {
              const operations = order.operations || []
              return operations.length > 0
            })
            
            return nonEmptyOrders.length === 0 ? (
              <div className="empty-products">
                {t("shop.orders-not-found", "Заказы не найдены")}
              </div>
            ) : (
              <div className="orders-list">
                {nonEmptyOrders.map((order) => (
                  <div
                    key={order.id}
                    className="order-card"
                    onClick={() => setSelectedOrder({ id: order.id })}
                  >
                    <div className="order-header">
                      <div className="order-code">{t("shop.order-code", "Заказ №")}{order.code || order.id}</div>
                      <div className={`order-status ${order.performed ? 'performed' : 'pending'}`}>
                        {getOrderStatus(order)}
                      </div>
                    </div>
                    <div className="order-date">
                      {t("shop.date", "Дата")}: {formatDate(order.date)}
                    </div>
                    {order.description && (
                      <div className="order-description">
                        {order.description}
                      </div>
                    )}
                    <div className="order-total">
                      {t("shop.total", "Итого")}: {formatPrice(calculateOrderTotal(order))} {order.currency?.name || currencyName}
                    </div>
                  </div>
                ))}
              </div>
            )
          })()}
        </>
      )}

      {activeTab === 'products' && showCart && (
        <Cart
          currencyName={currencyName}
          onCheckout={() => {
            setShowCart(false)
            setShowCheckout(true)
          }}
          onClose={() => setShowCart(false)}
        />
      )}
    </div>
  )
}

export default Shop

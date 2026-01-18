import { useState, useEffect, useCallback, useRef } from 'react'
import { FaShoppingCart, FaArrowLeft, FaImages } from 'react-icons/fa'
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import Cart from './Cart'
import Checkout from './Checkout'
import OrderDetail from './OrderDetail'
import { useCart } from '../contexts/CartContext'
import { apiFetch } from '../utils/api'
import { formatNumber } from '../utils/formatNumber'
import './Shop.css'

interface Product {
  item: {
    id: number
    name: string
    code: number
    image_url?: string
    unit?: {
      name: string
    }
    group: {
      id: number
      name: string
      path?: string
    }
  }
  quantity: {
    common: number
    allowed?: number
  }
  price: number
  image_url?: string
}

interface Group {
  id: number
  name: string
  path?: string
}

interface ShopProps {
  telegramUserId: number
  partnerId: number
  onBack: () => void
}

type ShopTab = 'products' | 'orders'

function Shop({ telegramUserId, partnerId, onBack }: ShopProps) {
  const [activeTab, setActiveTab] = useState<ShopTab>('products')
  const [products, setProducts] = useState<Product[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [selectedGroups, setSelectedGroups] = useState<number[]>([])
  const [showGroupFilter, setShowGroupFilter] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [showCart, setShowCart] = useState(false)
  const [showCheckout, setShowCheckout] = useState(false)
  const observerTarget = useRef<HTMLDivElement>(null)
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { addToCart, updateQuantity, getItemQuantity, getCartItemCount } = useCart()

  // Quick filter state
  type QuickFilter = 'all' | 'in-stock' | 'low-stock' | 'cheap' | 'expensive'
  const [quickFilter, setQuickFilter] = useState<QuickFilter>(() => {
    const saved = localStorage.getItem('shop-quick-filter')
    return (saved as QuickFilter) || 'all'
  })

  // Orders state
  const [orders, setOrders] = useState<any[]>([])
  const [isLoadingOrders, setIsLoadingOrders] = useState(false)
  const [ordersError, setOrdersError] = useState<string | null>(null)
  const [selectedOrder, setSelectedOrder] = useState<{ id: number } | null>(null)

  useEffect(() => {
    if (activeTab === 'products') {
      fetchGroups()
      fetchProducts(true)
    } else if (activeTab === 'orders') {
      fetchOrders()
    }
  }, [telegramUserId, activeTab])

  // Debounce search query
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    searchTimeoutRef.current = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery)
    }, 1000)

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchQuery])

  // Save quick filter to localStorage
  useEffect(() => {
    localStorage.setItem('shop-quick-filter', quickFilter)
  }, [quickFilter])

  useEffect(() => {
    // Reset and fetch when filters change
    setOffset(0)
    setProducts([])
    fetchProducts(true)
  }, [selectedGroups, debouncedSearchQuery, quickFilter])

  const fetchGroups = async () => {
    try {
      const response = await apiFetch(`/telegram-webapp/product-groups?telegram_user_id=${telegramUserId}`)
      const data = await response.json()
      if (data.ok) {
        setGroups(data.groups || [])
      }
    } catch (err) {
      console.error('Error fetching groups:', err)
    }
  }

  const fetchProducts = async (reset: boolean = false) => {
    try {
      if (reset) {
        setIsLoading(true)
        setError(null)
      } else {
        setIsLoadingMore(true)
      }

      const currentOffset = reset ? 0 : offset
      const groupIds = selectedGroups.length > 0 ? selectedGroups.join(',') : undefined

      const url = new URL('/telegram-webapp/products', window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('limit', '20')
      url.searchParams.set('offset', currentOffset.toString())
      if (groupIds) {
        url.searchParams.set('group_ids', groupIds)
      }
      if (debouncedSearchQuery) {
        url.searchParams.set('search', debouncedSearchQuery)
      }
      // Set zero_quantity to false for "in-stock" and "low-stock" filters
      if (quickFilter === 'in-stock' || quickFilter === 'low-stock') {
        url.searchParams.set('zero_quantity', 'false')
      }
      // Pass filter_type to backend for server-side filtering
      if (quickFilter !== 'all') {
        url.searchParams.set('filter_type', quickFilter)
      }

      const response = await apiFetch(url.pathname + url.search)
      const data = await response.json()

      if (data.ok) {
        const newProducts = data.products || []
        if (reset) {
          setProducts(newProducts)
        } else {
          setProducts(prev => [...prev, ...newProducts])
        }
        setOffset(currentOffset + newProducts.length)
        // Continue loading if there's a next_offset and we got products
        // Note: Filtering happens client-side, so we might need to load more to fill the view
        setHasMore(data.next_offset > 0 && newProducts.length > 0)
      } else {
        setError(data.message || 'Failed to fetch products')
      }
    } catch (err) {
      setError('Error loading products')
    } finally {
      setIsLoading(false)
      setIsLoadingMore(false)
    }
  }

  const handleLoadMore = useCallback(() => {
    if (!isLoadingMore && hasMore) {
      fetchProducts(false)
    }
  }, [isLoadingMore, hasMore, offset, selectedGroups, debouncedSearchQuery])

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore) {
          handleLoadMore()
        }
      },
      { threshold: 0.1 }
    )

    const currentTarget = observerTarget.current
    if (currentTarget) {
      observer.observe(currentTarget)
    }

    return () => {
      if (currentTarget) {
        observer.unobserve(currentTarget)
      }
    }
  }, [handleLoadMore, hasMore, isLoadingMore])

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
      return 'Все товары'
    }
    const selectedGroup = groups.find(g => g.id === selectedGroups[0])
    return selectedGroup ? selectedGroup.name : 'Все товары'
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

  // Apply quick filters to products (now mostly handled server-side, but keep for any edge cases)
  const applyQuickFilter = (productList: Product[]) => {
    // Server-side filtering is now used, so just return the list as-is
    // This function is kept for backward compatibility and any client-side edge case filtering
    return productList
  }

  const fetchOrders = async () => {
    try {
      setIsLoadingOrders(true)
      setOrdersError(null)

      const url = new URL('/telegram-webapp/orders', window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())

      const response = await apiFetch(url.pathname + url.search)
      const data = await response.json()

      if (data.ok) {
        setOrders(data.orders || [])
      } else {
        setOrdersError(data.message || 'Не удалось загрузить заказы')
      }
    } catch (err) {
      console.error('Error fetching orders:', err)
      setOrdersError('Ошибка при загрузке заказов')
    } finally {
      setIsLoadingOrders(false)
    }
  }

  const formatDate = (timestamp: number | string) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp * 1000)
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  }

  // Calculate total from operations if order.total is not available
  const calculateOrderTotal = (order: any) => {
    if (order.total) {
      return order.total
    }
    // Calculate from operations if available
    if (order.operations && order.operations.length > 0) {
      return order.operations.reduce((sum: number, op: any) => {
        const amount = op.amount || (op.quantity || 0) * (op.price || 0)
        return sum + amount
      }, 0)
    }
    return 0
  }

  const getOrderStatus = (order: any) => {
    if (order.performed) {
      return 'Выполнен'
    }
    if (order.booked) {
      return 'Забронирован'
    }
    return 'Новый'
  }

  if (isLoading) {
    return <Loading />
  }

  if (error) {
    return <ErrorMessage message={error} />
  }

  if (showCheckout) {
    return (
      <Checkout
        telegramUserId={telegramUserId}
        partnerId={partnerId}
        onBack={() => setShowCheckout(false)}
        onComplete={() => {
          setShowCheckout(false)
          setShowCart(false)
        }}
      />
    )
  }

  if (selectedOrder) {
    return (
      <OrderDetail
        orderId={selectedOrder.id}
        telegramUserId={telegramUserId}
        partnerId={partnerId}
        onBack={() => setSelectedOrder(null)}
      />
    )
  }

  return (
    <div className="shop">
      <div className="shop-header">
        <button className="back-button-icon" onClick={onBack} aria-label="Назад">
          <FaArrowLeft />
        </button>
        <div className="shop-tabs">
          <button
            className={`shop-tab ${activeTab === 'products' ? 'active' : ''}`}
            onClick={() => setActiveTab('products')}
          >
            Товары
          </button>
          <button
            className={`shop-tab ${activeTab === 'orders' ? 'active' : ''}`}
            onClick={() => setActiveTab('orders')}
          >
            Заказы
          </button>
        </div>
        {activeTab === 'products' && (
          <>
            {!showSearch && (
              <button
                className="search-icon-button"
                onClick={() => setShowSearch(true)}
                aria-label="Поиск"
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
              title="Корзина"
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
                placeholder="Поиск товаров..."
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
                aria-label="Закрыть поиск"
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
              Все
            </button>
            <button
              className={`quick-filter-chip ${quickFilter === 'in-stock' ? 'active' : ''}`}
              onClick={() => setQuickFilter('in-stock')}
            >
              В наличии
            </button>
            <button
              className={`quick-filter-chip ${quickFilter === 'low-stock' ? 'active' : ''}`}
              onClick={() => setQuickFilter('low-stock')}
            >
              Мало
            </button>
            <button
              className={`quick-filter-chip ${quickFilter === 'cheap' ? 'active' : ''}`}
              onClick={() => setQuickFilter('cheap')}
            >
              Дешевые
            </button>
            <button
              className={`quick-filter-chip ${quickFilter === 'expensive' ? 'active' : ''}`}
              onClick={() => setQuickFilter('expensive')}
            >
              Дорогие
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
                    Все товары
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
                {products.length === 0 ? 'Товары не найдены' : 'Товары не найдены по выбранному фильтру'}
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
                          <div className="product-name">{highlightText(product.item.name, debouncedSearchQuery)}</div>
                          <div className="product-details">
                            <div className="product-price">{formatPrice(product.price)} сум</div>
                            <div className="product-quantity">В наличии: {product.quantity.common} {product.item.unit?.name}</div>
                            <div className="product-code">Код: {product.item.code}</div>
                            <div className="product-group">{product.item.group.name}</div>
                          </div>
                          {itemQuantity === 0 ? (
                            <button
                              className="product-add-to-cart"
                              onClick={() => addToCart({
                                productId: product.item.id,
                                name: product.item.name,
                                price: product.price,
                                image_url: product.image_url || product.item.image_url,
                                code: product.item.code,
                                group: product.item.group.name,
                                quantityAllowed: product.quantity.allowed,
                              })}
                            >
                              <FaShoppingCart />
                            </button>
                          ) : (
                            <div className="product-quantity-controls">
                              <button
                                className="quantity-btn"
                                onClick={() => updateQuantity(product.item.id, itemQuantity - 1)}
                              >
                                −
                              </button>
                              <input
                                type="number"
                                min="1"
                                value={itemQuantity}
                                onChange={(e) => {
                                  const qty = parseInt(e.target.value) || 1
                                  updateQuantity(product.item.id, qty)
                                }}
                                className="quantity-input"
                              />
                              <button
                                className="quantity-btn"
                                onClick={() => updateQuantity(product.item.id, itemQuantity + 1)}
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
                Заказы не найдены
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
                      <div className="order-code">Заказ №{order.code || order.id}</div>
                      <div className={`order-status ${order.performed ? 'performed' : 'pending'}`}>
                        {getOrderStatus(order)}
                      </div>
                    </div>
                    <div className="order-date">
                      Дата: {formatDate(order.date)}
                    </div>
                    {order.description && (
                      <div className="order-description">
                        {order.description}
                      </div>
                    )}
                    <div className="order-total">
                      Итого: {formatPrice(calculateOrderTotal(order))} {order.currency?.name || 'сум'}
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

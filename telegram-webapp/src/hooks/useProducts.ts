/**
 * Hook for fetching and managing products
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../utils/api'

export interface Product {
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

export interface Group {
  id: number
  name: string
  path?: string
}

type QuickFilter = 'all' | 'in-stock' | 'low-stock' | 'cheap' | 'expensive'

export function useProducts(
  telegramUserId: number,
  botName: string | null,
  quickFilter: QuickFilter
) {
  const [products, setProducts] = useState<Product[]>([])
  const [groups, setGroups] = useState<Group[]>([])
  const [selectedGroups, setSelectedGroups] = useState<number[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('')
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const observerTarget = useRef<HTMLDivElement>(null)

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

  // Fetch groups when botName becomes available
  useEffect(() => {
    if (!botName) return
    
    const fetchGroupsData = async () => {
      try {
        const url = new URL('/telegram-webapp/product-groups', window.location.origin)
        url.searchParams.set('telegram_user_id', telegramUserId.toString())
        url.searchParams.set('bot_name', botName)
        const response = await apiFetch(url.pathname + url.search)
        const data = await response.json()
        if (data.ok) {
          setGroups(data.groups || [])
        }
      } catch (err) {
        console.error('Error fetching groups:', err)
      }
    }

    fetchGroupsData()
  }, [telegramUserId, botName])

  // Fetch products when botName or filters change
  useEffect(() => {
    if (!botName) return
    
    const groupIds = selectedGroups.length > 0 ? selectedGroups.join(',') : undefined
    
    const fetchProductsData = async () => {
      try {
        setIsLoading(true)
        setError(null)
        setOffset(0)
        setProducts([])
        
        const url = new URL('/telegram-webapp/products', window.location.origin)
        url.searchParams.set('telegram_user_id', telegramUserId.toString())
        url.searchParams.set('limit', '20')
        url.searchParams.set('offset', '0')
        url.searchParams.set('bot_name', botName)
        if (groupIds) {
          url.searchParams.set('group_ids', groupIds)
        }
        if (debouncedSearchQuery) {
          url.searchParams.set('search', debouncedSearchQuery)
        }
        if (quickFilter === 'in-stock' || quickFilter === 'low-stock') {
          url.searchParams.set('zero_quantity', 'false')
        }
        if (quickFilter !== 'all') {
          url.searchParams.set('filter_type', quickFilter)
        }

        const response = await apiFetch(url.pathname + url.search)
        const data = await response.json()

        if (data.ok) {
          const newProducts = data.products || []
          setProducts(newProducts)
          setOffset(newProducts.length)
          setHasMore(data.next_offset > 0 && newProducts.length > 0)
        } else {
          setError(data.message || 'Failed to fetch products')
        }
      } catch (err) {
        setError('Error loading products')
      } finally {
        setIsLoading(false)
      }
    }

    fetchProductsData()
  }, [telegramUserId, botName, selectedGroups, debouncedSearchQuery, quickFilter])

  const fetchProducts = useCallback(async (reset: boolean = false) => {
    try {
      if (reset) {
        setIsLoading(true)
        setError(null)
      } else {
        setIsLoadingMore(true)
      }

      const currentOffset = reset ? 0 : offset
      const groupIds = selectedGroups.length > 0 ? selectedGroups.join(',') : undefined

      if (!botName) {
        console.error('bot_name is required but not available')
        setError('Bot name is required. Please refresh the page.')
        return
      }
      
      const url = new URL('/telegram-webapp/products', window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('limit', '20')
      url.searchParams.set('offset', currentOffset.toString())
      url.searchParams.set('bot_name', botName)
      if (groupIds) {
        url.searchParams.set('group_ids', groupIds)
      }
      if (debouncedSearchQuery) {
        url.searchParams.set('search', debouncedSearchQuery)
      }
      if (quickFilter === 'in-stock' || quickFilter === 'low-stock') {
        url.searchParams.set('zero_quantity', 'false')
      }
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
  }, [telegramUserId, botName, offset, selectedGroups, debouncedSearchQuery, quickFilter])

  const handleLoadMore = useCallback(() => {
    if (!isLoadingMore && hasMore) {
      fetchProducts(false)
    }
  }, [isLoadingMore, hasMore, fetchProducts])

  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0].isIntersecting && hasMore && !isLoadingMore) {
          handleLoadMore()
        }
      },
      { threshold: 0.1 }
    )

    if (observerTarget.current) {
      observer.observe(observerTarget.current)
    }

    return () => {
      if (observerTarget.current) {
        observer.unobserve(observerTarget.current)
      }
    }
  }, [hasMore, isLoadingMore, handleLoadMore])

  const applyQuickFilter = useCallback((productsToFilter: Product[]): Product[] => {
    if (quickFilter === 'all') {
      return productsToFilter
    }

    return productsToFilter.filter(product => {
      switch (quickFilter) {
        case 'in-stock':
          return product.quantity.common > 0
        case 'low-stock':
          return product.quantity.common > 0 && product.quantity.common <= 10
        case 'cheap':
          return product.price <= 100000
        case 'expensive':
          return product.price > 100000
        default:
          return true
      }
    })
  }, [quickFilter])

  return {
    products,
    groups,
    selectedGroups,
    setSelectedGroups,
    isLoading,
    isLoadingMore,
    error,
    setError,
    hasMore,
    searchQuery,
    setSearchQuery,
    observerTarget,
    applyQuickFilter,
    fetchProducts
  }
}

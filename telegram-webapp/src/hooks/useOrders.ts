/**
 * Hook for fetching and managing orders
 */
import { useState, useEffect } from 'react'
import { apiFetch } from '../utils/api'

export function useOrders(
  telegramUserId: number,
  partnerId: number,
  botName: string | null
) {
  const [orders, setOrders] = useState<any[]>([])
  const [isLoadingOrders, setIsLoadingOrders] = useState(false)
  const [ordersError, setOrdersError] = useState<string | null>(null)

  const fetchOrders = async () => {
    try {
      setIsLoadingOrders(true)
      setOrdersError(null)

      if (!botName) {
        console.error('bot_name is required but not available')
        setOrdersError('Bot name is required. Please refresh the page.')
        return
      }
      
      const url = new URL('/telegram-webapp/orders', window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())
      url.searchParams.set('bot_name', botName)

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

  useEffect(() => {
    if (botName) {
      fetchOrders()
    }
  }, [telegramUserId, partnerId, botName])

  return {
    orders,
    isLoadingOrders,
    ordersError,
    fetchOrders
  }
}

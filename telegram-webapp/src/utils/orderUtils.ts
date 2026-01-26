/**
 * Utility functions for order formatting and calculations
 */
import { useLanguage } from '../contexts/LanguageContext'

const { t } = useLanguage()

export function formatDate(timestamp: number | string): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp * 1000)
  return date.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

export function calculateOrderTotal(order: any): number {
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

export function getOrderStatus(order: any): string {
  if (order.performed) {
    return t('order-detail.info.status.performed', 'Выполнен')
  }
  if (order.booked) {
    return t('order-detail.info.status.booked', 'Забронирован')
  }
  return t('order-detail.info.status.new', 'Новый')
}

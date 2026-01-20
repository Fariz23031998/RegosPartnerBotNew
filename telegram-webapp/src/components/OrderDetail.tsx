import { useState, useEffect } from 'react'
import { FaArrowLeft } from 'react-icons/fa'
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import { apiFetch } from '../utils/api'
import { formatNumber } from '../utils/formatNumber'
import './OrderDetail.css'

interface OrderDetailProps {
  orderId: number
  telegramUserId: number
  partnerId: number
  botName: string | null
  currencyName: string
  onBack: () => void
}

function OrderDetail({ orderId, telegramUserId, partnerId, botName, currencyName, onBack }: OrderDetailProps) {
  const [order, setOrder] = useState<any>(null)
  const [operations, setOperations] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchOrderDetails()
  }, [orderId])

  const fetchOrderDetails = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // SECURITY: bot_name is REQUIRED
      if (!botName) {
        setError('Bot name is required. Please refresh the page.')
        return
      }
      
      const url = new URL(`/telegram-webapp/orders/${orderId}`, window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())
      url.searchParams.set('bot_name', botName) // REQUIRED

      const response = await apiFetch(url.pathname + url.search)
      const data = await response.json()

      if (data.ok) {
        setOrder(data.order)
        setOperations(data.operations || [])
      } else {
        setError(data.message || 'Не удалось загрузить детали заказа')
      }
    } catch (err) {
      console.error('Error fetching order details:', err)
      setError('Ошибка при загрузке деталей заказа')
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (timestamp: number | string) => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp * 1000)
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatPrice = (price: number) => {
    return formatNumber(price)
  }

  // Calculate total from operations if order.total is not available
  const calculateTotal = () => {
    if (order?.total) {
      return order.total
    }
    // Calculate from operations
    return operations.reduce((sum, op) => {
      const amount = op.amount || (op.quantity || 0) * (op.price || 0)
      return sum + amount
    }, 0)
  }

  if (isLoading) {
    return <Loading />
  }

  if (error) {
    return <ErrorMessage message={error} />
  }

  if (!order) {
    return <ErrorMessage message="Заказ не найден" />
  }

  return (
    <div className="order-detail">
      <div className="order-detail-header">
        <button className="back-button-icon" onClick={onBack} aria-label="Назад">
          <FaArrowLeft />
        </button>
        <h2>Заказ №{order.code || order.id}</h2>
      </div>

      <div className="order-detail-info">
        <div className="info-row">
          <span className="info-label">Дата:</span>
          <span className="info-value">{formatDate(order.date)}</span>
        </div>
        <div className="info-row">
          <span className="info-label">Статус:</span>
          <span className={`info-value status ${order.performed ? 'performed' : 'pending'}`}>
            {order.performed ? 'Выполнен' : order.booked ? 'Забронирован' : 'Новый'}
          </span>
        </div>
        {order.description && (
          <div className="info-row">
            <span className="info-label">Описание:</span>
            <span className="info-value">{order.description}</span>
          </div>
        )}
        {order.stock && (
          <div className="info-row">
            <span className="info-label">Склад:</span>
            <span className="info-value">{order.stock.name}</span>
          </div>
        )}
        {order.currency && (
          <div className="info-row">
            <span className="info-label">Валюта:</span>
            <span className="info-value">
              {order.currency.name}
              {order.exchange_rate && order.exchange_rate !== 1 && (
                <span> (Курс: {order.exchange_rate})</span>
              )}
            </span>
          </div>
        )}
      </div>

      <div className="order-operations">
        <h3>Товары в заказе</h3>
        {operations.length > 0 ? (
          <>
            <div className="operations-list">
              {operations.map((op, index) => {
                const amount = op.amount || (op.quantity || 0) * (op.price || 0)
                return (
                  <div key={op.id || index} className="operation-card">
                    <div className="operation-item-header">
                      <div className="operation-item-name">
                        {op.item?.name || op.item?.fullname || `Товар #${op.item_id || op.id || index + 1}`}
                      </div>
                      {op.item?.code && (
                        <div className="operation-item-code">Код: {op.item.code}</div>
                      )}
                    </div>
                    <div className="operation-details">
                      <div className="operation-detail-row">
                        <span className="operation-detail-label">Количество:</span>
                        <span className="operation-detail-value">{op.quantity || 0}</span>
                      </div>
                      <div className="operation-detail-row">
                        <span className="operation-detail-label">Цена:</span>
                        <span className="operation-detail-value">{formatPrice(op.price || 0)}</span>
                      </div>
                      <div className="operation-detail-row operation-total-row">
                        <span className="operation-detail-label">Сумма:</span>
                        <span className="operation-detail-value operation-amount">{formatPrice(amount)}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
            <div className="order-total">
              <span className="total-label">Итого к оплате:</span>
              <span className="total-value">
                {formatPrice(calculateTotal())} {order.currency?.name || currencyName}
              </span>
            </div>
          </>
        ) : (
          <div className="no-operations">
            В заказе пока нет товаров
          </div>
        )}
      </div>
    </div>
  )
}

export default OrderDetail
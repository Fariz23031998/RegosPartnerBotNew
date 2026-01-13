import { useState, useEffect } from 'react'
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import './OrderDetail.css'

interface OrderDetailProps {
  orderId: number
  telegramUserId: number
  partnerId: number
  onBack: () => void
}

function OrderDetail({ orderId, telegramUserId, partnerId, onBack }: OrderDetailProps) {
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

      const url = new URL(`/api/telegram-webapp/orders/${orderId}`, window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())

      const response = await fetch(url.toString())
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
    return new Intl.NumberFormat('ru-RU').format(price)
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
        <button className="back-button" onClick={onBack}>
          ←
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
            <div className="operations-table">
              <div className="operations-header">
                <div>Товар</div>
                <div>Кол-во</div>
                <div>Цена</div>
                <div>Сумма</div>
              </div>
              {operations.map((op, index) => (
                <div key={op.id || index} className="operation-row">
                  <div className="operation-item-name">
                    {op.item?.name || op.item?.fullname || `Товар #${op.item_id || op.id || index + 1}`}
                    {op.item?.code && (
                      <span className="operation-item-code"> (Код: {op.item.code})</span>
                    )}
                  </div>
                  <div className="operation-quantity">
                    {op.quantity || 0}
                  </div>
                  <div className="operation-price">
                    {formatPrice(op.price || 0)}
                  </div>
                  <div className="operation-amount">
                    {formatPrice(op.amount || (op.quantity || 0) * (op.price || 0))}
                  </div>
                </div>
              ))}
            </div>
            {order.total && (
              <div className="order-total">
                <span className="total-label">Итого к оплате:</span>
                <span className="total-value">
                  {formatPrice(order.total)} {order.currency?.name || 'сум'}
                </span>
              </div>
            )}
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
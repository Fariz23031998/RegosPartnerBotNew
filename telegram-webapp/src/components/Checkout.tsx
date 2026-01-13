import { useState } from 'react'
import { useCart } from '../contexts/CartContext'
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import './Checkout.css'

interface CheckoutProps {
  telegramUserId: number
  partnerId: number
  onBack: () => void
  onComplete: () => void
}

function Checkout({ telegramUserId, partnerId, onBack, onComplete }: CheckoutProps) {
  const { cart, getCartTotal, clearCart } = useCart()
  const [address, setAddress] = useState('')
  const [phone, setPhone] = useState('')
  const [isTakeaway, setIsTakeaway] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ru-RU').format(price)
  }

  const handleComplete = async () => {
    if (cart.length === 0) return

    // Validate required fields
    if (!isTakeaway && !address.trim()) {
      setError('Пожалуйста, введите адрес доставки')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch('/api/telegram-webapp/orders/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
          body: JSON.stringify({
          telegram_user_id: telegramUserId,
          partner_id: partnerId,
          address: isTakeaway ? '' : address.trim(),
          phone: phone.trim() || undefined,
          is_takeaway: isTakeaway,
          items: cart.map(item => ({
            product_id: item.productId,
            quantity: item.quantity,
            price: item.price,
          })),
        }),
      })

      const data = await response.json()

      if (data.ok) {
        clearCart()
        const tg = window.Telegram?.WebApp
        if (tg) {
          tg.showAlert('Заказ успешно создан!')
        } else {
          alert('Заказ успешно создан!')
        }
        onComplete()
      } else {
        setError(data.message || 'Ошибка при создании заказа')
      }
    } catch (err) {
      setError('Ошибка при отправке заказа. Попробуйте еще раз.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="checkout">
      <div className="checkout-header">
        <button className="back-button" onClick={onBack} title="Назад">
          ←
        </button>
        <h2>Оформление заказа</h2>
      </div>

      <div className="checkout-content">
        <div className="checkout-items">
          <h3>Товары в заказе:</h3>
          {cart.map((item) => (
            <div key={item.productId} className="checkout-item">
              <div className="checkout-item-name">{item.name}</div>
              <div className="checkout-item-details">
                <span>{item.quantity} × {formatPrice(item.price)} сум</span>
                <span className="checkout-item-total">
                  {formatPrice(item.price * item.quantity)} сум
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="checkout-form">
          <div className="form-group">
            <label htmlFor="phone">Телефон</label>
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+998901234567"
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isTakeaway}
                onChange={(e) => setIsTakeaway(e.target.checked)}
                className="checkbox-input"
              />
              <span>С собой</span>
            </label>
          </div>

          {!isTakeaway && (
            <div className="form-group">
              <label htmlFor="address">Адрес доставки *</label>
              <textarea
                id="address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Введите адрес доставки"
                className="form-textarea"
                rows={3}
                required={!isTakeaway}
              />
            </div>
          )}
        </div>

        {error && (
          <div className="checkout-error">
            {error}
          </div>
        )}

        <div className="checkout-total">
          <div className="checkout-total-row">
            <span>Итого:</span>
            <span className="checkout-total-amount">
              {formatPrice(getCartTotal())} сум
            </span>
          </div>
        </div>

        <div className="checkout-actions">
          <button 
            className="checkout-btn" 
            onClick={handleComplete}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Отправка...' : 'Подтвердить заказ'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default Checkout

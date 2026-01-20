import { useState } from 'react'
import { FaArrowLeft } from 'react-icons/fa'
import { useCart } from '../contexts/CartContext'
import { apiFetch } from '../utils/api'
import { formatNumber } from '../utils/formatNumber'
import './Checkout.css'

interface CheckoutProps {
  telegramUserId: number
  partnerId: number
  botName: string | null
  currencyName: string
  onBack: () => void
  onComplete: () => void
}

function Checkout({ telegramUserId, partnerId, botName, currencyName, onBack, onComplete }: CheckoutProps) {
  const { cart, getCartTotal, clearCart } = useCart()
  const [address, setAddress] = useState('')
  const [phone, setPhone] = useState('')
  const [isTakeaway, setIsTakeaway] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const formatPrice = (price: number) => {
    return formatNumber(price)
  }

  const handleComplete = async () => {
    if (cart.length === 0) return

    // Validate required fields
    if (!isTakeaway && !address.trim()) {
      setError('Пожалуйста, введите адрес доставки')
      return
    }

    // Validate that all products have quantity.allowed > 0
    const invalidItems = cart.filter(item => {
      if (item.quantityAllowed !== undefined) {
        return item.quantityAllowed <= 0
      }
      return false
    })

    if (invalidItems.length > 0) {
      const itemNames = invalidItems.map(item => item.name).join(', ')
      setError(`Невозможно оформить заказ: товары "${itemNames}" отсутствуют в наличии`)
      return
    }

    setIsSubmitting(true)
    setError(null)

    // SECURITY: bot_name is REQUIRED
    if (!botName) {
      setError('Bot name is required. Please refresh the page.')
      return
    }
    
    try {
      const url = new URL('/telegram-webapp/orders/create', window.location.origin)
      url.searchParams.set('bot_name', botName) // REQUIRED
      
      const response = await apiFetch(url.pathname + url.search, {
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
        <button className="back-button-icon" onClick={onBack} aria-label="Назад">
          <FaArrowLeft />
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
                <span>{item.quantity} × {formatPrice(item.price)} {currencyName}</span>
                <span className="checkout-item-total">
                  {formatPrice(item.price * item.quantity)} {currencyName}
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
              {formatPrice(getCartTotal())} {currencyName}
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

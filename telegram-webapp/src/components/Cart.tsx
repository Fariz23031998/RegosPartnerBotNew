import { useCart } from '../contexts/CartContext'
import { formatNumber } from '../utils/formatNumber'
import { FaImages } from 'react-icons/fa'
import './Cart.css'

interface CartProps {
  onCheckout: () => void
  onClose: () => void
}

function Cart({ onCheckout, onClose }: CartProps) {
  const {
    cart,
    updateQuantity,
    removeFromCart,
    getCartTotal,
    clearCart,
  } = useCart()

  const formatPrice = (price: number) => {
    return formatNumber(price)
  }

  const handleCheckout = () => {
    if (cart.length === 0) return
    onCheckout()
  }

  if (cart.length === 0) {
    return (
      <div className="cart-overlay" onClick={onClose}>
        <div className="cart-panel" onClick={(e) => e.stopPropagation()}>
          <div className="cart-header">
            <h2>Корзина</h2>
            <button className="cart-close" onClick={onClose}>×</button>
          </div>
          <div className="cart-empty">
            <p>Корзина пуста</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="cart-overlay" onClick={onClose}>
      <div className="cart-panel" onClick={(e) => e.stopPropagation()}>
        <div className="cart-header">
          <h2>Корзина</h2>
          <button className="cart-close" onClick={onClose}>×</button>
        </div>

        <div className="cart-items">
          {cart.map((item) => (
            <div key={item.productId} className="cart-item">
              {item.image_url ? (
                <img
                  src={item.image_url}
                  alt={item.name}
                  className="cart-item-image"
                />
              ) : (
                <div className="cart-item-image-placeholder">
                  <FaImages />
                </div>
              )}
              <div className="cart-item-info">
                <div className="cart-item-name">{item.name}</div>
                <div className="cart-item-price">{formatPrice(item.price)} сум</div>
                <div className="cart-item-controls">
                  <button
                    className="cart-quantity-btn"
                    onClick={() => updateQuantity(item.productId, item.quantity - 1)}
                  >
                    −
                  </button>
                  <input
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={(e) => {
                      const qty = parseInt(e.target.value) || 1
                      updateQuantity(item.productId, qty)
                    }}
                    className="cart-quantity-input"
                  />
                  <button
                    className="cart-quantity-btn"
                    onClick={() => updateQuantity(item.productId, item.quantity + 1)}
                  >
                    +
                  </button>
                  <button
                    className="cart-remove-btn"
                    onClick={() => removeFromCart(item.productId)}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="cart-footer">
          <div className="cart-total">
            <span>Итого:</span>
            <span className="cart-total-amount">{formatPrice(getCartTotal())} сум</span>
          </div>
          <div className="cart-actions">
            <button className="cart-clear-btn" onClick={clearCart}>
              Очистить
            </button>
            <button className="cart-checkout-btn" onClick={handleCheckout}>
              Оформить заказ
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Cart

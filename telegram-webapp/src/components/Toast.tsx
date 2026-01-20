import { useEffect } from 'react'
import './Toast.css'

interface ToastProps {
  message: string
  type?: 'error' | 'warning' | 'success'
  duration?: number
  onClose: () => void
}

function Toast({ message, type = 'warning', duration = 3000, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose()
    }, duration)

    return () => {
      clearTimeout(timer)
    }
  }, [duration, onClose])

  return (
    <div className={`toast toast-${type}`}>
      <div className="toast-content">
        <span className="toast-icon">
          {type === 'error' && '❌'}
          {type === 'warning' && '⚠️'}
          {type === 'success' && '✅'}
        </span>
        <span className="toast-message">{message}</span>
      </div>
      <button className="toast-close" onClick={onClose} aria-label="Close">
        ×
      </button>
    </div>
  )
}

export default Toast

import { useEffect, useState } from 'react'
import DocumentList from './components/DocumentList'
import HomeScreen from './components/HomeScreen'
import Shop from './components/Shop'
import Loading from './components/Loading'
import ErrorMessage from './components/ErrorMessage'
import { CartProvider } from './contexts/CartContext'
import { apiFetch } from './utils/api'
import './App.css'

// Declare Telegram WebApp types
declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        ready: () => void
        expand: () => void
        initData: string
        initDataUnsafe: {
          user?: {
            id: number
            first_name?: string
            last_name?: string
            username?: string
          }
        }
        showAlert: (message: string) => void
      }
    }
  }
}

type Page = 'home' | 'reports' | 'shop'

function AppContent() {
  const [isAuthorized, setIsAuthorized] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [partnerId, setPartnerId] = useState<number | null>(null)
  const [telegramUserId, setTelegramUserId] = useState<number | null>(null)
  const [currentPage, setCurrentPage] = useState<Page>('home')

  useEffect(() => {
    // Check if running in Telegram Web App
    const tg = window.Telegram?.WebApp
    
    if (tg) {
      // Initialize Telegram Web App
      tg.ready()
      tg.expand()
      
      // Get Telegram user ID from init data
      const user = tg.initDataUnsafe?.user
      
      if (user?.id) {
        const userId = user.id
        setTelegramUserId(userId)
        // Authenticate user
        authenticateUser(userId)
        return
      }
      
      // Fallback: Try to parse initData string
      try {
        const initData = tg.initData || ''
        if (initData) {
          const params = new URLSearchParams(initData)
          const userStr = params.get('user')
          
          if (userStr) {
            const user = JSON.parse(userStr)
            const userId = user.id
            setTelegramUserId(userId)
            authenticateUser(userId)
            return
          }
        }
      } catch (err) {
        console.error('Error parsing initData:', err)
      }
    }
    
    // If no Telegram data found, show error
    setError('This app must be opened from Telegram. Please open it through your Telegram bot.')
    setIsLoading(false)
  }, [])

  const authenticateUser = async (userId: number) => {
    try {
      const response = await apiFetch(`/telegram-webapp/auth?telegram_user_id=${userId}`)
      const data = await response.json()

      if (data.ok) {
        setIsAuthorized(true)
        if (data.partner_id) {
          setPartnerId(data.partner_id)
        }
        // If partner_id is not found, user will need to enter it
      } else {
        setError(data.message || 'Authorization failed. Please ensure your Telegram ID is registered in the system.')
      }
    } catch (err) {
      setError('Failed to authenticate. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  // Add missing dependency for useEffect
  // eslint-disable-next-line react-hooks/exhaustive-deps

  if (isLoading) {
    return <Loading />
  }

  if (error) {
    return <ErrorMessage message={error} />
  }

  if (!isAuthorized) {
    return <ErrorMessage message="You are not authorized to access this application." />
  }

  if (!partnerId) {
    return (
      <div className="partner-id-input">
        <h2>Enter Partner ID</h2>
        <p className="hint">Please enter your Partner ID to view documents</p>
        <input
          type="number"
          placeholder="Partner ID"
          onChange={(e) => {
            const value = e.target.value
            if (value) {
              setPartnerId(parseInt(value))
            }
          }}
        />
        <button onClick={() => {
          const input = document.querySelector('input[type="number"]') as HTMLInputElement
          if (input && input.value) {
            setPartnerId(parseInt(input.value))
          }
        }}>Continue</button>
      </div>
    )
  }

  const handleNavigate = (page: 'reports' | 'shop') => {
    setCurrentPage(page)
  }

  const handleBackToHome = () => {
    setCurrentPage('home')
  }

  if (currentPage === 'home') {
  return (
    <div className="app">
      <HomeScreen onNavigate={handleNavigate} />
    </div>
  )
  }

  if (currentPage === 'shop') {
    return (
      <div className="app">
        <Shop 
          telegramUserId={telegramUserId!} 
          partnerId={partnerId}
          onBack={handleBackToHome}
        />
      </div>
    )
  }

  // Reports page (DocumentList)
  return (
    <div className="app">
      <DocumentList 
        telegramUserId={telegramUserId!} 
        partnerId={partnerId}
        onBack={handleBackToHome}
      />
    </div>
  )
}

function App() {
  return (
    <CartProvider>
      <AppContent />
    </CartProvider>
  )
}

export default App

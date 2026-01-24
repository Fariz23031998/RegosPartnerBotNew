import { useEffect, useState } from 'react'
import DocumentList from './components/DocumentList'
import HomeScreen from './components/HomeScreen'
import Shop from './components/Shop'
import Loading from './components/Loading'
import ErrorMessage from './components/ErrorMessage'
import { CartProvider } from './contexts/CartContext'
import { apiFetch } from './utils/api'
import './App.css'
import { LanguageProvider, useLanguage } from './contexts/LanguageContext'

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
  const [botName, setBotName] = useState<string | null>(null)
  const [currencyName, setCurrencyName] = useState<string>('сум')
  const [showOnlineStore, setShowOnlineStore] = useState<boolean>(true)
  const [currentPage, setCurrentPage] = useState<Page>('home')
  const { t } = useLanguage()

  useEffect(() => {
    // Extract bot_name from URL path: /mini-app/bot_name
    // SECURITY: bot_name is REQUIRED - cannot proceed without it
    const pathParts = window.location.pathname.split('/').filter(p => p)
    let extractedBotName: string | null = null
    
    // Find mini-app in path and get the next part as bot_name
    const miniAppIndex = pathParts.indexOf('mini-app')
    if (miniAppIndex >= 0 && miniAppIndex < pathParts.length - 1) {
      extractedBotName = decodeURIComponent(pathParts[miniAppIndex + 1])
      setBotName(extractedBotName)
    } else {
      // SECURITY: If bot_name is not in URL, show error
      setError(t("app.error.invalid-url", "Invalid URL: bot name is required. Please open this app through your Telegram bot."))
      setIsLoading(false)
      return
    }
    
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
        // Authenticate user with bot_name from URL (REQUIRED)
        authenticateUser(userId, extractedBotName)
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
            authenticateUser(userId, extractedBotName)
            return
          }
        }
      } catch (err) {
        console.error('Error parsing initData:', err)
      }
    }
    
    // If no Telegram data found, show error
    setError(t("app.error.telegram-required", "This app must be opened from Telegram. Please open it through your Telegram bot."))
    setIsLoading(false)
  }, [])

  const authenticateUser = async (userId: number, botName: string | null) => {
    // SECURITY: bot_name is REQUIRED
    if (!botName) {
      setError(t("app.error.bot-name-required", "Bot name is required. Please open this app through your Telegram bot."))
      setIsLoading(false)
      return
    }
    
    try {
      const url = new URL('/telegram-webapp/auth', window.location.origin)
      url.searchParams.set('telegram_user_id', userId.toString())
      url.searchParams.set('bot_name', botName) // REQUIRED - always set
      
      const response = await apiFetch(url.pathname + url.search)
      const data = await response.json()

      if (data.ok) {
        setIsAuthorized(true)
        if (data.partner_id) {
          setPartnerId(data.partner_id)
        }
        const finalBotName = data.bot_name || botName
        if (finalBotName) {
          setBotName(finalBotName)
          // Fetch bot settings to get currency_name and show_online_store immediately after auth
          fetchBotSettings(finalBotName, userId)
        }
        // If partner_id is not found, user will need to enter it
      } else {
        setError(data.message || t("app.error.authorization-failed", "Authorization failed. Please ensure your Telegram ID is registered in the system."))
      }
    } catch (err) {
      setError(t("app.error.authentication-failed", "Failed to authenticate. Please try again."))
    } finally {
      setIsLoading(false)
    }
  }

  const fetchBotSettings = async (currentBotName: string, userId: number) => {
    try {
      const url = new URL('/telegram-webapp/bot-settings', window.location.origin)
      url.searchParams.set('telegram_user_id', userId.toString())
      url.searchParams.set('bot_name', encodeURIComponent(currentBotName))
      
      console.log('Fetching bot settings from:', url.pathname + url.search)
      
      const response = await apiFetch(url.pathname + url.search)
      
      if (!response.ok) {
        console.error(`Failed to fetch bot settings: HTTP ${response.status}`)
        return
      }
      
      const data = await response.json()
      
      console.log('Bot settings response:', JSON.stringify(data, null, 2))
      
      if (data.ok) {
        // Update currency_name if provided in response
        if (data.currency_name !== undefined && data.currency_name !== null) {
          const currency = String(data.currency_name).trim()
          console.log('Setting currency name to:', currency)
          setCurrencyName(currency)
        } else if (data.bot_settings && data.bot_settings.currency_name) {
          console.log('Found currency_name in bot_settings:', data.bot_settings.currency_name)
          setCurrencyName(String(data.bot_settings.currency_name).trim())
        }
        
        // Update show_online_store if provided in response
        if (data.show_online_store !== undefined && data.show_online_store !== null) {
          console.log('Setting show_online_store to:', data.show_online_store)
          setShowOnlineStore(Boolean(data.show_online_store))
        } else {
          // Default to true if not provided
          setShowOnlineStore(true)
        }
      } else {
        console.warn('Bot settings response not ok:', data)
      }
    } catch (err) {
      console.error('Error fetching bot settings:', err)
      // Keep defaults if fetch fails
    }
  }

  // Refetch bot settings when botName or telegramUserId changes
  useEffect(() => {
    if (botName && telegramUserId && isAuthorized) {
      console.log('Refetching bot settings for bot:', botName)
      fetchBotSettings(botName, telegramUserId)
    }
  }, [botName, telegramUserId, isAuthorized])

  if (isLoading) {
    return <Loading />
  }

  if (error) {
    return <ErrorMessage message={error} />
  }

  if (!isAuthorized) {
    return <ErrorMessage message={t("app.error.not-authorized", "You are not authorized to access this application.")} />
  }

  if (!partnerId) {
    return (
      <div className="partner-id-input">
        <h2>{t("app.partner-id.title", "Enter Partner ID")}</h2>
        <p className="hint">{t("app.partner-id.hint", "Please enter your Partner ID to view documents")}</p>
        <input
          type="number"
          placeholder={t("app.partner-id.placeholder", "Partner ID")}
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
        }}>{t("app.partner-id.continue", "Continue")}</button>
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
      <HomeScreen onNavigate={handleNavigate} showOnlineStore={showOnlineStore} />
    </div>
  )
  }

  if (currentPage === 'shop') {
    return (
      <div className="app">
        <Shop 
          telegramUserId={telegramUserId!} 
          partnerId={partnerId}
          botName={botName}
          currencyName={currencyName}
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
        botName={botName}
        onBack={handleBackToHome}
      />
    </div>
  )
}

function App() {
  // Extract bot_name from URL before rendering CartProvider
  const [botName, setBotName] = useState<string | null>(null)

  useEffect(() => {
    // Extract bot_name from URL path: /mini-app/bot_name
    const pathParts = window.location.pathname.split('/').filter(p => p)
    const miniAppIndex = pathParts.indexOf('mini-app')
    if (miniAppIndex >= 0 && miniAppIndex < pathParts.length - 1) {
      const extractedBotName = decodeURIComponent(pathParts[miniAppIndex + 1])
      setBotName(extractedBotName)
    }
  }, [])

  return (
    <CartProvider botName={botName}>
      <LanguageProvider>
        <AppContent />
      </LanguageProvider>
    </CartProvider>
  )
}

export default App

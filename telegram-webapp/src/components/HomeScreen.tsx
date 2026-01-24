import './HomeScreen.css'
import { useLanguage } from "../contexts/LanguageContext"

interface HomeScreenProps {
  onNavigate: (page: 'reports' | 'shop') => void
  showOnlineStore: boolean
}

function HomeScreen({ onNavigate, showOnlineStore }: HomeScreenProps) {
  const { t } = useLanguage()
  return (
    <div className="home-screen">
      <div className="home-container">
        <h1 className="home-title">{t("home.welcome", "Welcome")}</h1>
        <div className="home-icons">
          <button 
            className="home-icon-button"
            onClick={() => onNavigate('reports')}
          >
            <div className="icon-wrapper">
              <span className="icon-large">📊</span>
            </div>
            <span className="icon-label">{t("home.reports", "Отчёты")}</span>
          </button>
          {showOnlineStore && (
            <button 
              className="home-icon-button"
              onClick={() => onNavigate('shop')}
            >
              <div className="icon-wrapper">
                <span className="icon-large">🛒</span>
              </div>
              <span className="icon-label">{t("home.shop", "Магазин")}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default HomeScreen

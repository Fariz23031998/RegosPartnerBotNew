import './HomeScreen.css'

interface HomeScreenProps {
  onNavigate: (page: 'reports' | 'shop') => void
  showOnlineStore: boolean
}

function HomeScreen({ onNavigate, showOnlineStore }: HomeScreenProps) {
  return (
    <div className="home-screen">
      <div className="home-container">
        <h1 className="home-title">Добро пожаловать</h1>
        <div className="home-icons">
          <button 
            className="home-icon-button"
            onClick={() => onNavigate('reports')}
          >
            <div className="icon-wrapper">
              <span className="icon-large">📊</span>
            </div>
            <span className="icon-label">Отчёты</span>
          </button>
          {showOnlineStore && (
            <button 
              className="home-icon-button"
              onClick={() => onNavigate('shop')}
            >
              <div className="icon-wrapper">
                <span className="icon-large">🛒</span>
              </div>
              <span className="icon-label">Магазин</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default HomeScreen

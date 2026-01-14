import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../services/api'
import UserManagement from '../components/UserManagement'
import BotManagement from '../components/BotManagement'
import BotSettingsManagement from '../components/BotSettingsManagement'
import BotScheduleManagement from '../components/BotScheduleManagement'
import ChangePassword from '../components/ChangePassword'
import './Dashboard.css'

interface DashboardStats {
  totalUsers: number
  totalBots: number
  activeBots: number
  registeredBots: number
}

function Dashboard() {
  const { logout, username } = useAuth()
  const [activeTab, setActiveTab] = useState<'users' | 'bots' | 'bot-settings' | 'bot-schedules' | 'change-password'>('users')
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [stats, setStats] = useState<DashboardStats>({
    totalUsers: 0,
    totalBots: 0,
    activeBots: 0,
    registeredBots: 0,
  })

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      const [usersRes, botsRes, registeredBotsRes] = await Promise.all([
        api.get('/users'),
        api.get('/bots'),
        api.get('/registered-bots'),
      ])
      
      const allBots = botsRes.data || []
      const activeBotsCount = allBots.filter((b: any) => b.is_active).length

      setStats({
        totalUsers: usersRes.data?.length || 0,
        totalBots: allBots.length,
        activeBots: activeBotsCount,
        registeredBots: Object.keys(registeredBotsRes.data || {}).length,
      })
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Telegram Bot Admin Panel</h1>
          <div className="header-actions">
            <span className="username">Welcome, {username}</span>
            <button 
              onClick={() => setShowChangePassword(true)} 
              className="change-password-button"
            >
              Change Password
            </button>
            <button onClick={logout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="dashboard-stats">
        <div className="stat-card">
          <h3>Total Users</h3>
          <p className="stat-number">{stats.totalUsers}</p>
        </div>
        <div className="stat-card">
          <h3>Total Bots</h3>
          <p className="stat-number">{stats.totalBots}</p>
        </div>
        <div className="stat-card">
          <h3>Active Bots</h3>
          <p className="stat-number">{stats.activeBots}</p>
        </div>
        <div className="stat-card">
          <h3>Registered Bots</h3>
          <p className="stat-number">{stats.registeredBots}</p>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="tabs">
          <button
            className={`tab-button ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            User Management
          </button>
          <button
            className={`tab-button ${activeTab === 'bots' ? 'active' : ''}`}
            onClick={() => setActiveTab('bots')}
          >
            Bot Management
          </button>
          <button
            className={`tab-button ${activeTab === 'bot-settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('bot-settings')}
          >
            Bot Settings
          </button>
          <button
            className={`tab-button ${activeTab === 'bot-schedules' ? 'active' : ''}`}
            onClick={() => setActiveTab('bot-schedules')}
          >
            Bot Schedules
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'users' && <UserManagement onUpdate={fetchStats} />}
          {activeTab === 'bots' && <BotManagement onUpdate={fetchStats} />}
          {activeTab === 'bot-settings' && <BotSettingsManagement onUpdate={fetchStats} />}
          {activeTab === 'bot-schedules' && <BotScheduleManagement onUpdate={fetchStats} />}
        </div>
      </div>

      {showChangePassword && (
        <div className="modal-overlay" onClick={() => setShowChangePassword(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <ChangePassword 
              onSuccess={() => setShowChangePassword(false)}
            />
            <button 
              className="modal-close-button"
              onClick={() => setShowChangePassword(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard


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
  const { logout, username, isAuthenticated } = useAuth()
  const [activeTab, setActiveTab] = useState<'users' | 'bots' | 'bot-settings' | 'bot-schedules' | 'change-password'>('users')
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [stats, setStats] = useState<DashboardStats>({
    totalUsers: 0,
    totalBots: 0,
    activeBots: 0,
    registeredBots: 0,
  })

  useEffect(() => {
    // Only fetch stats after authentication is confirmed
    if (isAuthenticated) {
      // Small delay to ensure token is fully set in axios
      const timer = setTimeout(() => {
        fetchStats()
      }, 100)
      return () => clearTimeout(timer)
    }
  }, [isAuthenticated])

  const fetchStats = async () => {
    // Ensure token is set before making requests
    const token = localStorage.getItem('token')
    if (token && token !== 'undefined' && token.trim() !== '') {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      console.log('[Dashboard] Token set in axios defaults before fetchStats', {
        tokenPreview: token.substring(0, 20) + '...',
        tokenLength: token.length,
      })
      
      // Small delay to ensure axios defaults are fully propagated
      await new Promise(resolve => setTimeout(resolve, 50))
    } else {
      console.warn('[Dashboard] No valid token found before fetchStats')
      return // Don't make requests without a token
    }

    try {
      // Make requests with individual error handling to prevent one failure from affecting others
      // Add a small delay between requests to avoid race conditions
      const [usersRes, botsRes, registeredBotsRes] = await Promise.all([
        api.get('/users').catch(err => {
          console.error('[Dashboard] Error fetching users:', err)
          return { data: [] }
        }),
        api.get('/bots').catch(err => {
          console.error('[Dashboard] Error fetching bots:', err)
          return { data: [] }
        }),
        api.get('/registered-bots').catch(err => {
          console.error('[Dashboard] Error fetching registered bots:', err)
          return { data: {} }
        }),
      ])
      
      // Ensure responses are arrays/objects, handle errors gracefully
      const usersData = Array.isArray(usersRes.data) ? usersRes.data : []
      const botsData = Array.isArray(botsRes.data) ? botsRes.data : []
      const registeredBotsData = registeredBotsRes.data && typeof registeredBotsRes.data === 'object' 
        ? registeredBotsRes.data 
        : {}
      
      const activeBotsCount = botsData.filter((b: any) => b.is_active).length

      setStats({
        totalUsers: usersData.length,
        totalBots: botsData.length,
        activeBots: activeBotsCount,
        registeredBots: Object.keys(registeredBotsData).length,
      })
    } catch (error: any) {
      console.error('[Dashboard] Error fetching stats:', error)
      // Set stats to 0 on error to prevent map/filter errors
      setStats({
        totalUsers: 0,
        totalBots: 0,
        activeBots: 0,
        registeredBots: 0,
      })
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


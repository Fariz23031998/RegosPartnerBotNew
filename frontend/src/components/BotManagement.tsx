import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import { formatNumber, formatCurrency } from '../utils/formatNumber'
import './BotManagement.css'
import { useLanguage } from "../contexts/LanguageContext"

interface Bot {
  bot_id: number
  user_id: number
  bot_name: string | null
  is_active: boolean
  subscription_active: boolean
  subscription_expires_at: string | null
  subscription_price: number
  created_at: string
}

interface User {
  user_id: number
  username: string | null
  email: string | null
}

interface BotManagementProps {
  onUpdate?: () => void
}

function BotManagement({ onUpdate }: BotManagementProps) {
  const { role, userId } = useAuth()
  const isAdmin = role === 'admin'
  const [bots, setBots] = useState<Bot[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingBot, setEditingBot] = useState<Bot | null>(null)
  const [formData, setFormData] = useState({ user_id: 0, telegram_token: '', regos_integration_token: '', bot_name: '' })
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [subscriptionModal, setSubscriptionModal] = useState<{ show: boolean; bot: Bot | null; action: 'activate' | 'setPrice' }>({ show: false, bot: null, action: 'activate' })
  const [subscriptionMonths, setSubscriptionMonths] = useState(1)
  const [subscriptionPrice, setSubscriptionPrice] = useState(0)
  const [revenueStats, setRevenueStats] = useState<{ total_revenue: number; monthly_revenue: number; active_subscriptions: number; expired_subscriptions: number } | null>(null)
  const { t } = useLanguage()

  useEffect(() => {
    fetchData()
    fetchRevenueStats()
  }, [])

  const fetchRevenueStats = async () => {
    if (!isAdmin) return // Only admins can see revenue stats
    try {
      const response = await api.get('/subscriptions/revenue')
      setRevenueStats(response.data)
    } catch (err: any) {
      console.error('Failed to fetch revenue stats:', err)
    }
  }

  const fetchData = async () => {
    try {
      setLoading(true)
      const requests: Promise<any>[] = [api.get('/bots')]
      
      // Only fetch users for admin
      if (isAdmin) {
        requests.push(api.get('/users'))
      }
      
      const responses = await Promise.all(requests)
      
      // Ensure responses are arrays
      setBots(Array.isArray(responses[0].data) ? responses[0].data : [])
      if (isAdmin) {
        setUsers(Array.isArray(responses[1]?.data) ? responses[1].data : [])
      }
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotManagement.error.fetch-data", "Failed to fetch data"))
      setBots([]) // Set empty arrays on error
      if (isAdmin) {
        setUsers([])
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError('')
      const user_id = isAdmin ? formData.user_id : (userId || 0)
      if (!user_id) {
        setError(t("BotManagement.error.user-id-not-found", "User ID not found"))
        return
      }
      if (!formData.telegram_token) {
        setError(t("BotManagement.warning.enter-telegram-token", "Please enter a Telegram token"))
        return
      }
      await api.post('/bots', {
        user_id: user_id,
        telegram_token: formData.telegram_token,
        bot_name: formData.bot_name || null,
        regos_integration_token: formData.regos_integration_token || null,
      })
      setShowModal(false)
      setFormData({ user_id: 0, telegram_token: '', regos_integration_token: '', bot_name: '' })
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotManagement.error.create-bot", "Failed to create bot"))
    }
  }

  const handleEdit = (bot: Bot) => {
    setEditingBot(bot)
    setFormData({
      user_id: bot.user_id,
      telegram_token: '', // Allow editing - user can enter new token
      regos_integration_token: '', // Will be populated if needed
      bot_name: bot.bot_name || '',
    })
    setShowModal(true)
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingBot) return
    
    try {
      setError('')
      const updateData: any = {}
      
      // Only include telegram_token if provided (not empty)
      // Leave empty to keep current token
      if (formData.telegram_token.trim()) {
        updateData.telegram_token = formData.telegram_token.trim()
      }
      
      // Always include bot_name (can be null/empty)
      updateData.bot_name = formData.bot_name.trim() || null
      
      // Only update regos_integration_token if provided
      // If empty, don't include it in update (keeps existing value)
      if (formData.regos_integration_token.trim()) {
        updateData.regos_integration_token = formData.regos_integration_token.trim()
      }
      // To clear regos_integration_token, user would need to explicitly clear it
      // For now, we only update if a value is provided
      
      await api.patch(`/bots/${editingBot.bot_id}`, updateData)
      setShowModal(false)
      setEditingBot(null)
      setFormData({ user_id: 0, telegram_token: '', regos_integration_token: '', bot_name: '' })
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotManagement.error.update-bot", "Failed to update bot"))
    }
  }

  const handleToggleActive = async (bot: Bot) => {
    try {
      await api.patch(`/bots/${bot.bot_id}`, {
        is_active: !bot.is_active,
      })
      fetchData()
      fetchRevenueStats()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotManagement.error.update-bot-status", "Failed to update bot status"))
    }
  }

  const handleActivateSubscription = async () => {
    if (!subscriptionModal.bot) return
    try {
      setError('')
      await api.post(`/subscriptions/bots/${subscriptionModal.bot.bot_id}/activate`, {
        months: subscriptionMonths
      })
      setSubscriptionModal({ show: false, bot: null, action: 'activate' })
      fetchData()
      fetchRevenueStats()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotManagement.error.activate-subscription", "Failed to activate subscription"))
    }
  }

  const handleSetPrice = async () => {
    if (!subscriptionModal.bot) return
    try {
      setError('')
      await api.post(`/subscriptions/bots/${subscriptionModal.bot.bot_id}/set-price`, {
        price: subscriptionPrice
      })
      setSubscriptionModal({ show: false, bot: null, action: 'activate' })
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotManagement.error.set-subscription", 'Failed to set subscription price'))
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleDateString()
  }

  const isSubscriptionExpired = (bot: Bot) => {
    if (!bot.subscription_expires_at) return false
    return new Date(bot.subscription_expires_at) < new Date()
  }

  const handleDelete = async (botId: number) => {
    if (!window.confirm(t("BotManagement.confirm.delete-bot", "Are you sure you want to delete this bot?"))) {
      return
    }

    try {
      setDeletingId(botId)
      await api.delete(`/bots/${botId}`)
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotManagement.error.delete-bot", 'Failed to delete bot'))
    } finally {
      setDeletingId(null)
    }
  }

  const getUserName = (userId: number) => {
    const user = users.find(u => u.user_id === userId)
    return user ? (user.username || user.email || `User ${userId}`) : `User ${userId}`
  }

  if (loading) {
    return <div className="loading">{t("BotManagement.loading-bots", "Loading bots...")}</div>
  }

  return (
    <div className="bot-management">
      <div className="section-header">
        <h2>{t("BotManagement.bot-management", "Bot Management")}</h2>
        <div className="header-actions-wrapper">
          {revenueStats && (
            <div className="revenue-stats">
              <div className="revenue-stat-item">
                <strong>{t("BotManagement.revenue", "Revenue")}:</strong> {formatCurrency(revenueStats.total_revenue, 'sum')} {t("BotManagement.total", "total")}
              </div>
              <div className="revenue-stat-item">
                {formatCurrency(revenueStats.monthly_revenue, 'sum')} {t("BotManagement.this-month", "this month")}
              </div>
              <div className="revenue-stat-item">
                <strong>{t("BotManagement.active", "Active")}:</strong> {formatNumber(revenueStats.active_subscriptions)} | <strong>{t("BotManagement.expired", "Expired")}:</strong> {formatNumber(revenueStats.expired_subscriptions)}
              </div>
            </div>
          )}
          <button onClick={() => {
            setEditingBot(null)
            setFormData({ 
              user_id: isAdmin ? 0 : (userId || 0), 
              telegram_token: '', 
              regos_integration_token: '', 
              bot_name: '' 
            })
            setShowModal(true)
          }} className="add-button">
            + {t("BotManagement.add-bot", "Add Bot")}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {bots.length === 0 ? (
        <div className="empty-state">{t("BotManagement.warning.no-bots-found", "No bots found. Create your first bot!")}</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              {isAdmin && <th>{t("BotManagement.user", "User")}</th>}
              <th>{t("BotManagement.bot-name", "Bot Name")}</th>
              <th>{t("common.status", "Status")}</th>
              {isAdmin && <th>{t("BotManagement.subscription", "Subscription")}</th>}
              {isAdmin && <th>{t("BotManagement.price", "Price")}</th>}
              {isAdmin && <th>{t("BotManagement.expires", "Expires")}</th>}
              <th>{t("BotManagement.created-at", "Created At")}</th>
              <th>{t("BotManagement.actions", "Actions")}</th>
            </tr>
          </thead>
          <tbody>
            {bots.map((bot) => (
              <tr key={bot.bot_id}>
                <td data-label="ID">{bot.bot_id}</td>
                {isAdmin && <td data-label="User">{getUserName(bot.user_id)}</td>}
                <td data-label="Bot Name">{bot.bot_name || '-'}</td>
                <td data-label="Status">
                  <span className={`status-badge ${bot.is_active ? 'active' : 'inactive'}`}>
                    {bot.is_active ? t("common.active", "Active") : t("common.inactive", "Inactive")}
                  </span>
                </td>
                {isAdmin && (
                  <td data-label="Subscription">
                    <span className={`status-badge ${bot.subscription_active && !isSubscriptionExpired(bot) ? 'active' : 'inactive'}`}>
                      {bot.subscription_active && !isSubscriptionExpired(bot) ? t("common.active", "Active") : isSubscriptionExpired(bot) ? 'Expired' : 'Inactive'}
                    </span>
                  </td>
                )}
                {isAdmin && <td data-label="Price">{formatCurrency(bot.subscription_price, 'sum')}</td>}
                {isAdmin && <td data-label="Expires">{formatDate(bot.subscription_expires_at)}</td>}
                <td data-label="Created At">{new Date(bot.created_at).toLocaleString()}</td>
                <td data-label="Actions">
                  <div className="action-buttons">
                    {isAdmin && (
                      <>
                        <button
                          onClick={() => {
                            setSubscriptionModal({ show: true, bot, action: 'setPrice' })
                            setSubscriptionPrice(bot.subscription_price)
                          }}
                          className="edit-button"
                          style={{ fontSize: '12px', padding: '4px 8px' }}
                        >
                          {t("BotManagement.set-price", "Set Price")}
                        </button>
                        <button
                          onClick={() => {
                            setSubscriptionModal({ show: true, bot, action: 'activate' })
                            setSubscriptionMonths(1)
                          }}
                          className="activate-button"
                          style={{ fontSize: '12px', padding: '4px 8px' }}
                        >
                          {bot.subscription_active && !isSubscriptionExpired(bot) ? t("BotManagement.extend", "Extend") : t("BotManagement.activate", "Activate")}
                        </button>
                      </>
                    )}
                    <button
                      onClick={() => handleToggleActive(bot)}
                      className={`toggle-button ${bot.is_active ? 'deactivate' : 'activate'}`}
                    >
                      {bot.is_active ? t("BotManagement.deactivate", "Deactivate")
                       : t("BotManagement.activate", "Activate")}
                    </button>
                    <button
                      onClick={() => handleEdit(bot)}
                      className="edit-button"
                    >
                      {t("common.edit", "Edit")}
                    </button>
                    {isAdmin && (
                      <button
                        onClick={() => handleDelete(bot.bot_id)}
                        disabled={deletingId === bot.bot_id}
                        className="delete-button"
                      >
                        {deletingId === bot.bot_id ? t("common.deleting", "Deleting...") : t("common.delete", "Delete")}
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={() => {
          setShowModal(false)
          setEditingBot(null)
          setFormData({ user_id: 0, telegram_token: '', regos_integration_token: '', bot_name: '' })
        }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>{editingBot ? t("BotManagement.edit-bot", "Edit Bot") : t("BotManagement.create-new-bot", "Create New Bot")}</h3>
            <form onSubmit={editingBot ? handleUpdate : handleCreate}>
              {!editingBot && isAdmin && (
                <div className="form-group">
                  <label>{t("BotManagement.user", "User")} *</label>
                  <select
                    value={formData.user_id}
                    onChange={(e) => setFormData({ ...formData, user_id: parseInt(e.target.value) })}
                    required
                  >
                    <option value={0}>{t("BotManagement.select-user", "Select a user")}</option>
                    {users.map((user) => (
                      <option key={user.user_id} value={user.user_id}>
                        {user.username || user.email || `${t("BotManagement.user", "User")} ${user.user_id}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>{t("BotManagement.telegram-token", "Telegram Token")} {!editingBot && '*'}</label>
                <input
                  type="text"
                  value={formData.telegram_token}
                  onChange={(e) => setFormData({ ...formData, telegram_token: e.target.value })}
                  placeholder={editingBot ? t("BotManagement.warning.leave-token-empty", "Leave empty to keep current token") : t("BotManagement.telegram-bot-token", "Telegram bot token")}
                  required={!editingBot}
                />
                {editingBot && (
                  <small style={{ color: '#666', display: 'block', marginTop: '4px' }}>
                    {t("BotManagement.message.add-edit-token", "Enter new token to update, or leave empty to keep current token")}
                  </small>
                )}
              </div>
              <div className="form-group">
                <label>{t("BotManagement.bot-name", "Bot Name")}</label>
                <input
                  type="text"
                  value={formData.bot_name}
                  onChange={(e) => setFormData({ ...formData, bot_name: e.target.value })}
                  placeholder={t("BotManagement.optional", "Optional")}
                />
              </div>
              <div className="form-group">
                <label>{t("BotManagement.regos-integration-token", "REGOS Integration Token")}</label>
                <input
                  type="text"
                  value={formData.regos_integration_token}
                  onChange={(e) => setFormData({ ...formData, regos_integration_token: e.target.value })}
                  placeholder={editingBot ? t("BotManagement.warning.leave-token-empty", "Leave empty to keep current token") : t("BotManagement.optional", "Optional")}
                />
                {editingBot && (
                  <small style={{ color: '#666', display: 'block', marginTop: '4px' }}>
                    {t("BotManagement.message.add-edit-token", "Enter new token to update, or leave empty to keep current token")}
                  </small>
                )}
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    setEditingBot(null)
                    setFormData({ user_id: 0, telegram_token: '', regos_integration_token: '', bot_name: '' })
                  }}
                  className="cancel-button"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button type="submit" className="submit-button">
                  {editingBot ? t("common.update", "Update") : t("common.create", "Create")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {subscriptionModal.show && subscriptionModal.bot && (
        <div className="modal-overlay" onClick={() => setSubscriptionModal({ show: false, bot: null, action: 'activate' })}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>
              {subscriptionModal.action === 'activate' 
                ? (subscriptionModal.bot.subscription_active && !isSubscriptionExpired(subscriptionModal.bot) 
                    ? t("BotManagement.extend-subscription", "Extend Subscription") 
                    : t("BotManagement.activate-subscription", "Activate Subscription"))
                : t("BotManagement.set-subscription-price", "Set Subscription Price")}
            </h3>
            {subscriptionModal.action === 'activate' ? (
              <form onSubmit={(e) => { e.preventDefault(); handleActivateSubscription() }}>
                <div className="form-group">
                  <label>{t("common.bot", "Bot")}: {subscriptionModal.bot.bot_name || `Bot ${subscriptionModal.bot.bot_id}`}</label>
                </div>
                <div className="form-group">
                  <label>{t("BotManagement.current-price", "Current Price")}: {formatCurrency(subscriptionModal.bot.subscription_price, '$')}/month</label>
                </div>
                {subscriptionModal.bot.subscription_expires_at && !isSubscriptionExpired(subscriptionModal.bot) && (
                  <div className="form-group">
                    <label>{t("BotManagement.current-expiry", "Current Expiry")}: {formatDate(subscriptionModal.bot.subscription_expires_at)}</label>
                  </div>
                )}
                <div className="form-group">
                  <label>{t("BotManagement.number-of-month", "Number of Months")} *</label>
                  <input
                    type="number"
                    min="1"
                    max="12"
                    value={subscriptionMonths}
                    onChange={(e) => setSubscriptionMonths(parseInt(e.target.value) || 1)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>{t("BotManagement.total-amount", "Total Amount")}: {formatCurrency(subscriptionModal.bot.subscription_price * subscriptionMonths, 'sum')}</label>
                </div>
                <div className="modal-actions">
                  <button
                    type="button"
                    onClick={() => setSubscriptionModal({ show: false, bot: null, action: 'activate' })}
                    className="cancel-button"
                  >
                    {t("common.cancel", "Cancel")}
                  </button>
                  <button type="submit" className="submit-button">
                    {subscriptionModal.bot.subscription_active && !isSubscriptionExpired(subscriptionModal.bot) ? t("BotManagement.extend", "Extend") : t("BotManagement.activate", "Activate")}
                  </button>
                </div>
              </form>
            ) : (
              <form onSubmit={(e) => { e.preventDefault(); handleSetPrice() }}>
                <div className="form-group">
                  <label>{t("common.bot", "Bot")}: {subscriptionModal.bot.bot_name || `Bot ${subscriptionModal.bot.bot_id}`}</label>
                </div>
                <div className="form-group">
                  <label>{t("BotManagement.monthly-subscription-price-total", "Monthly Subscription Price (Sum)")} *</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={subscriptionPrice}
                    onChange={(e) => setSubscriptionPrice(parseFloat(e.target.value) || 0)}
                    required
                  />
                </div>
                <div className="modal-actions">
                  <button
                    type="button"
                    onClick={() => setSubscriptionModal({ show: false, bot: null, action: 'activate' })}
                    className="cancel-button"
                  >
                    {t("common.cancel", "Cancel")}
                  </button>
                  <button type="submit" className="submit-button">
                    {t("BotManagement.set-price", "Set Price")}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default BotManagement


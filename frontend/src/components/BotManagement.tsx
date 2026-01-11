import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import './BotManagement.css'

interface Bot {
  bot_id: number
  user_id: number
  bot_name: string | null
  is_active: boolean
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
  const [bots, setBots] = useState<Bot[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingBot, setEditingBot] = useState<Bot | null>(null)
  const [formData, setFormData] = useState({ user_id: 0, telegram_token: '', regos_integration_token: '', bot_name: '' })
  const [deletingId, setDeletingId] = useState<number | null>(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [botsResponse, usersResponse] = await Promise.all([
        api.get('/bots'),
        api.get('/users'),
      ])
      
      setBots(botsResponse.data)
      setUsers(usersResponse.data)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError('')
      if (!formData.user_id) {
        setError('Please select a user')
        return
      }
      if (!formData.telegram_token) {
        setError('Please enter a Telegram token')
        return
      }
      await api.post('/bots', {
        user_id: formData.user_id,
        telegram_token: formData.telegram_token,
        bot_name: formData.bot_name || null,
        regos_integration_token: formData.regos_integration_token || null,
      })
      setShowModal(false)
      setFormData({ user_id: 0, telegram_token: '', regos_integration_token: '', bot_name: '' })
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create bot')
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
      setError(err.response?.data?.detail || 'Failed to update bot')
    }
  }

  const handleToggleActive = async (bot: Bot) => {
    try {
      await api.patch(`/bots/${bot.bot_id}`, {
        is_active: !bot.is_active,
      })
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update bot status')
    }
  }

  const handleDelete = async (botId: number) => {
    if (!window.confirm('Are you sure you want to delete this bot?')) {
      return
    }

    try {
      setDeletingId(botId)
      await api.delete(`/bots/${botId}`)
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete bot')
    } finally {
      setDeletingId(null)
    }
  }

  const getUserName = (userId: number) => {
    const user = users.find(u => u.user_id === userId)
    return user ? (user.username || user.email || `User ${userId}`) : `User ${userId}`
  }

  if (loading) {
    return <div className="loading">Loading bots...</div>
  }

  return (
    <div className="bot-management">
      <div className="section-header">
        <h2>Bot Management</h2>
        <button onClick={() => {
          setEditingBot(null)
          setFormData({ user_id: 0, telegram_token: '', regos_integration_token: '', bot_name: '' })
          setShowModal(true)
        }} className="add-button">
          + Add Bot
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {bots.length === 0 ? (
        <div className="empty-state">No bots found. Create your first bot!</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Bot Name</th>
              <th>Status</th>
              <th>Created At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {bots.map((bot) => (
              <tr key={bot.bot_id}>
                <td>{bot.bot_id}</td>
                <td>{getUserName(bot.user_id)}</td>
                <td>{bot.bot_name || '-'}</td>
                <td>
                  <span className={`status-badge ${bot.is_active ? 'active' : 'inactive'}`}>
                    {bot.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>{new Date(bot.created_at).toLocaleString()}</td>
                <td>
                  <div className="action-buttons">
                    <button
                      onClick={() => handleToggleActive(bot)}
                      className={`toggle-button ${bot.is_active ? 'deactivate' : 'activate'}`}
                    >
                      {bot.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button
                      onClick={() => handleEdit(bot)}
                      className="edit-button"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(bot.bot_id)}
                      disabled={deletingId === bot.bot_id}
                      className="delete-button"
                    >
                      {deletingId === bot.bot_id ? 'Deleting...' : 'Delete'}
                    </button>
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
            <h3>{editingBot ? 'Edit Bot' : 'Create New Bot'}</h3>
            <form onSubmit={editingBot ? handleUpdate : handleCreate}>
              {!editingBot && (
                <div className="form-group">
                  <label>User *</label>
                  <select
                    value={formData.user_id}
                    onChange={(e) => setFormData({ ...formData, user_id: parseInt(e.target.value) })}
                    required
                  >
                    <option value={0}>Select a user</option>
                    {users.map((user) => (
                      <option key={user.user_id} value={user.user_id}>
                        {user.username || user.email || `User ${user.user_id}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>Telegram Token {!editingBot && '*'}</label>
                <input
                  type="text"
                  value={formData.telegram_token}
                  onChange={(e) => setFormData({ ...formData, telegram_token: e.target.value })}
                  placeholder={editingBot ? "Leave empty to keep current token" : "Telegram bot token"}
                  required={!editingBot}
                />
                {editingBot && (
                  <small style={{ color: '#666', display: 'block', marginTop: '4px' }}>
                    Enter new token to update, or leave empty to keep current token
                  </small>
                )}
              </div>
              <div className="form-group">
                <label>Bot Name</label>
                <input
                  type="text"
                  value={formData.bot_name}
                  onChange={(e) => setFormData({ ...formData, bot_name: e.target.value })}
                  placeholder="Optional"
                />
              </div>
              <div className="form-group">
                <label>REGOS Integration Token</label>
                <input
                  type="text"
                  value={formData.regos_integration_token}
                  onChange={(e) => setFormData({ ...formData, regos_integration_token: e.target.value })}
                  placeholder={editingBot ? "Leave empty to keep current token" : "Optional"}
                />
                {editingBot && (
                  <small style={{ color: '#666', display: 'block', marginTop: '4px' }}>
                    Enter new token to update, or leave empty to keep current token
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
                  Cancel
                </button>
                <button type="submit" className="submit-button">
                  {editingBot ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default BotManagement


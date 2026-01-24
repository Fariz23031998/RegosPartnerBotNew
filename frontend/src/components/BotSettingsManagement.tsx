import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import './BotSettingsManagement.css'
import { useLanguage } from "../contexts/LanguageContext"

interface BotSettings {
  id: number
  bot_id: number
  online_store_stock_id: number | null
  online_store_price_type_id: number | null
  online_store_currency_id: number
  currency_name: string | null
  show_online_store: boolean
  can_register: boolean
  partner_group_id: number
  created_at: string
  updated_at: string
}

interface Bot {
  bot_id: number
  bot_name: string | null
}

interface BotSettingsManagementProps {
  onUpdate?: () => void
}

function BotSettingsManagement({ onUpdate }: BotSettingsManagementProps) {
  const [settings, setSettings] = useState<BotSettings[]>([])
  const [bots, setBots] = useState<Bot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingSettings, setEditingSettings] = useState<BotSettings | null>(null)
  const [formData, setFormData] = useState({ 
    bot_id: 0, 
    online_store_stock_id: '', 
    online_store_price_type_id: '',
    online_store_currency_id: '1',
    currency_name: 'сум',
    show_online_store: true,
    can_register: false,
    partner_group_id: 1
  })
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const { t } = useLanguage()

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [settingsResponse, botsResponse] = await Promise.all([
        api.get('/bot-settings'),
        api.get('/bots'),
      ])
      
      // Ensure responses are arrays
      setSettings(Array.isArray(settingsResponse.data) ? settingsResponse.data : [])
      setBots(Array.isArray(botsResponse.data) ? botsResponse.data : [])
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotSettingsManagement.error.fetch-data", "Failed to fetch data"))
      setSettings([]) // Set empty arrays on error
      setBots([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError('')
      if (!formData.bot_id) {
        setError(t("BotSettingsManagement.message.select-bot", "Please select a bot"))
        return
      }
      await api.post('/bot-settings', {
        bot_id: formData.bot_id,
        online_store_stock_id: formData.online_store_stock_id ? parseInt(formData.online_store_stock_id) : null,
        online_store_price_type_id: formData.online_store_price_type_id ? parseInt(formData.online_store_price_type_id) : null,
        online_store_currency_id: formData.online_store_currency_id ? parseInt(formData.online_store_currency_id) : 1,
        currency_name: formData.currency_name || 'сум',
        show_online_store: formData.show_online_store,
        can_register: formData.can_register,
        partner_group_id: formData.partner_group_id ? parseInt(formData.partner_group_id.toString()) : 1,
      })
      setShowModal(false)
      setFormData({ bot_id: 0, online_store_stock_id: '', online_store_price_type_id: '', online_store_currency_id: '1', currency_name: 'сум', show_online_store: true, can_register: false, partner_group_id: 1 })
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotSettingsManagement.error.create-bot-settings", "Failed to create bot settings"))
    }
  }

  const handleEdit = (setting: BotSettings) => {
    setEditingSettings(setting)
    setFormData({
      bot_id: setting.bot_id,
      online_store_stock_id: setting.online_store_stock_id?.toString() || '',
      online_store_price_type_id: setting.online_store_price_type_id?.toString() || '',
      online_store_currency_id: setting.online_store_currency_id?.toString() || '1',
      currency_name: setting.currency_name || 'сум',
      show_online_store: setting.show_online_store ?? true,
      can_register: setting.can_register ?? false,
      partner_group_id: setting.partner_group_id ?? 1,
    })
    setShowModal(true)
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingSettings) return
    
    try {
      setError('')
      await api.put(`/bot-settings/${editingSettings.id}`, {
        online_store_stock_id: formData.online_store_stock_id ? parseInt(formData.online_store_stock_id) : null,
        online_store_price_type_id: formData.online_store_price_type_id ? parseInt(formData.online_store_price_type_id) : null,
        online_store_currency_id: formData.online_store_currency_id ? parseInt(formData.online_store_currency_id) : 1,
        currency_name: formData.currency_name || 'сум',
        show_online_store: formData.show_online_store,
        can_register: formData.can_register,
        partner_group_id: formData.partner_group_id ? parseInt(formData.partner_group_id.toString()) : 1,
      })
      setShowModal(false)
      setEditingSettings(null)
      setFormData({ bot_id: 0, online_store_stock_id: '', online_store_price_type_id: '', online_store_currency_id: '1', currency_name: 'сум', show_online_store: true, can_register: false, partner_group_id: 1 })
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotSettingsManagement.error.update-bot-settings", "Failed to update bot settings"))
    }
  }

  const handleDelete = async (settingsId: number) => {
    if (!window.confirm(t("BotSettingsManagement.confirm.delete-bot-settings", "Are you sure you want to delete these bot settings?"))) {
      return
    }

    try {
      setDeletingId(settingsId)
      await api.delete(`/bot-settings/${settingsId}`)
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotSettingsManagement.error.delete-bot-settings", "Failed to delete bot settings"))
    } finally {
      setDeletingId(null)
    }
  }

  const getBotName = (botId: number) => {
    const bot = bots.find(b => b.bot_id === botId)
    return bot ? (bot.bot_name || `Bot ${botId}`) : `Bot ${botId}`
  }

  // Get bots that don't have settings yet
  const getAvailableBots = () => {
    const botsWithSettings = new Set(settings.map(s => s.bot_id))
    return bots.filter(b => !botsWithSettings.has(b.bot_id))
  }

  if (loading) {
    return <div className="loading">{t("BotSettingsManagement.loading.loading-bot-settings", "Loading bot settings...")}</div>
  }

  return (
    <div className="bot-settings-management">
      <div className="section-header">
        <h2>{t("BotSettingsManagement.bot-settings-management", "Bot Settings Management")}</h2>
        <button 
          onClick={() => {
            setEditingSettings(null)
            setFormData({ bot_id: 0, online_store_stock_id: '', online_store_price_type_id: '', online_store_currency_id: '1', currency_name: 'сум', show_online_store: true, can_register: false, partner_group_id: 1 })
            setShowModal(true)
          }} 
          className="add-button"
          disabled={getAvailableBots().length === 0}
        >
          + {t("BotSettingsManagement.add-bot-settings", "Add Bot Settings")}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {getAvailableBots().length === 0 && settings.length === 0 && (
        <div className="empty-state">{t("BotSettingsManagement.message.no-bots-available", "No bots available. Create a bot first!")}</div>
      )}

      {settings.length === 0 && getAvailableBots().length > 0 && (
        <div className="empty-state">{t("BotSettingsManagement.message.no-bot-settings-found", "No bot settings found. Create your first settings!")}</div>
      )}

      {settings.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>{t("BotSettingsManagement.table.bot", "Bot")}</th>
              <th>{t("BotSettingsManagement.table.online-store-stock-id", "Online Store Stock ID")}</th>
              <th>{t("BotSettingsManagement.table.online-store-price-type-id", "Online Store Price Type ID")}</th>
              <th>{t("BotSettingsManagement.table.online-store-currency-id", "Online Store Currency ID")}</th>
              <th>{t("BotSettingsManagement.table.currency-name", "Currency Name")}</th>
              <th>{t("BotSettingsManagement.table.show-online-store", "Show Online Store")}</th>
              <th>{t("BotSettingsManagement.table.can-register", "Can Register")}</th>
              <th>{t("BotSettingsManagement.table.partner-group-id", "Partner Group ID")}</th>
              <th>{t("BotSettingsManagement.table.updated-at", "Updated At")}</th>
              <th>{t("BotSettingsManagement.table.actions", "Actions")}</th>
            </tr>
          </thead>
          <tbody>
            {settings.map((setting) => (
              <tr key={setting.id}>
                <td data-label="ID">{setting.id}</td>
                <td data-label="Bot">{getBotName(setting.bot_id)}</td>
                <td data-label="Stock ID">{setting.online_store_stock_id || '-'}</td>
                <td data-label="Price Type ID">{setting.online_store_price_type_id || '-'}</td>
                <td data-label="Currency ID">{setting.online_store_currency_id}</td>
                <td data-label="Currency Name">{setting.currency_name || 'сум'}</td>
                <td data-label="Show Online Store">{setting.show_online_store ? 'Yes' : 'No'}</td>
                <td data-label="Can Register">{setting.can_register ? 'Yes' : 'No'}</td>
                <td data-label="Partner Group ID">{setting.partner_group_id || 1}</td>
                <td data-label="Updated At">{new Date(setting.updated_at).toLocaleString()}</td>
                <td data-label="Actions">
                  <div className="action-buttons">
                    <button
                      onClick={() => handleEdit(setting)}
                      className="edit-button"
                    >
                      {t("common.edit", "Edit")}
                    </button>
                    <button
                      onClick={() => handleDelete(setting.id)}
                      disabled={deletingId === setting.id}
                      className="delete-button"
                    >
                      {deletingId === setting.id ? t("common.deleting", "Deleting...") : t("common.delete", "Delete")}
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
          setEditingSettings(null)
          setFormData({ bot_id: 0, online_store_stock_id: '', online_store_price_type_id: '', online_store_currency_id: '1', currency_name: 'сум', show_online_store: true, can_register: false, partner_group_id: 1 })
        }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>{editingSettings ? t("BotSettingsManagement.modal.edit-bot-settings", "Edit Bot Settings") : t("BotSettingsManagement.modal.create-new-bot-settings", "Create New Bot Settings")}</h3>
            <form onSubmit={editingSettings ? handleUpdate : handleCreate}>
              {!editingSettings && (
                <div className="form-group">
                  <label>{t("BotSettingsManagement.modal.bot", "Bot")} *</label>
                  <select
                    value={formData.bot_id}
                    onChange={(e) => setFormData({ ...formData, bot_id: parseInt(e.target.value) })}
                    required
                  >
                    <option value={0}>Select a bot</option>
                    {getAvailableBots().map((bot) => (
                      <option key={bot.bot_id} value={bot.bot_id}>
                        {bot.bot_name || `${t("common.bot", "Bot")} ${bot.bot_id}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {editingSettings && (
                <div className="form-group">
                  <label>{t("common.bot", "Bot")}</label>
                  <input
                    type="text"
                    value={getBotName(editingSettings.bot_id)}
                    disabled
                    className="disabled-input"
                  />
                </div>
              )}
              <div className="form-group">
                <label>{t("BotSettingsManagement.modal.online-store-stock-id", "Online Store Stock ID")}</label>
                <input
                  type="number"
                  value={formData.online_store_stock_id}
                  onChange={(e) => setFormData({ ...formData, online_store_stock_id: e.target.value })}
                  placeholder={t("common.optional", "Optional")}
                  min="0"
                />
              </div>
              <div className="form-group">
                <label>Online Store Price Type ID</label>
                <input
                  type="number"
                  value={formData.online_store_price_type_id}
                  onChange={(e) => setFormData({ ...formData, online_store_price_type_id: e.target.value })}
                  placeholder={t("common.optional", "Optional")}
                  min="0"
                />
              </div>
              <div className="form-group">
                <label>{t("BotSettingsManagement.modal.online-store-currency-id", "Online Store Currency ID")} *</label>
                <input
                  type="number"
                  value={formData.online_store_currency_id}
                  onChange={(e) => setFormData({ ...formData, online_store_currency_id: e.target.value })}
                  placeholder={t("common.default-one", "Default: 1")}
                  min="1"
                  required
                />
              </div>
              <div className="form-group">
                <label>{t("BotSettingsManagement.modal.currency-name", "Currency Name")} *</label>
                <input
                  type="text"
                  value={formData.currency_name}
                  onChange={(e) => setFormData({ ...formData, currency_name: e.target.value })}
                  placeholder={t("common.default-one", "Default: 1")}
                  required
                />
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.show_online_store}
                    onChange={(e) => setFormData({ ...formData, show_online_store: e.target.checked })}
                  />
                  {' '}{t("BotSettingsManagement.modal.show-online-store", "Show Online Store")}
                </label>
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.can_register}
                    onChange={(e) => setFormData({ ...formData, can_register: e.target.checked })}
                  />
                  {' '}{t("BotSettingsManagement.modal.can-register", "Can Register")}
                </label>
              </div>
              <div className="form-group">
                <label>{t("BotSettingsManagement.modal.partner-group-id", "Partner Group ID")} *</label>
                <input
                  type="number"
                  value={formData.partner_group_id}
                  onChange={(e) => setFormData({ ...formData, partner_group_id: parseInt(e.target.value) || 1 })}
                  placeholder={t("common.default-one", "Default: 1")}
                  min="1"
                  required
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    setEditingSettings(null)
                    setFormData({ bot_id: 0, online_store_stock_id: '', online_store_price_type_id: '', online_store_currency_id: '1', currency_name: 'сум', show_online_store: true, can_register: false, partner_group_id: 1 })
                  }}
                  className="cancel-button"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button type="submit" className="submit-button">
                  {editingSettings ? t("common.update", "Update") : t("common.create", "Create")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default BotSettingsManagement

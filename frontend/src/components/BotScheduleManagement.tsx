import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import './BotScheduleManagement.css'
import { useLanguage } from "../contexts/LanguageContext"

interface BotSchedule {
  id: number
  bot_id: number
  schedule_type: string
  time: string
  enabled: boolean
  schedule_option: string
  schedule_value: number[] | null
  created_at: string
  updated_at: string
}

interface Bot {
  bot_id: number
  bot_name: string | null
}

interface BotScheduleManagementProps {
  onUpdate?: () => void
}

const WEEKDAYS = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
]

function BotScheduleManagement({ onUpdate }: BotScheduleManagementProps) {
  const [schedules, setSchedules] = useState<BotSchedule[]>([])
  const [bots, setBots] = useState<Bot[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState<BotSchedule | null>(null)
  const [formData, setFormData] = useState({
    bot_id: 0,
    schedule_type: 'send_partner_balance',
    time: '09:00',
    schedule_option: 'daily',
    schedule_value: [] as number[],
    enabled: true
  })
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const { t } = useLanguage();

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setLoading(true)
      const [schedulesResponse, botsResponse] = await Promise.all([
        api.get('/bot-schedules'),
        api.get('/bots'),
      ])
      
      // Ensure responses are arrays
      setSchedules(Array.isArray(schedulesResponse.data) ? schedulesResponse.data : [])
      setBots(Array.isArray(botsResponse.data) ? botsResponse.data : [])
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotScheduleManagement.error.fetch-data", "Failed to fetch data"))
      setSchedules([]) // Set empty arrays on error
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
        setError(t("BotScheduleManagement.message.select-bot", "Please select a bot"))
        return
      }
      
      const payload: any = {
        bot_id: formData.bot_id,
        schedule_type: formData.schedule_type,
        time: formData.time,
        schedule_option: formData.schedule_option,
        enabled: formData.enabled
      }
      
      if (formData.schedule_option !== 'daily' && formData.schedule_value.length > 0) {
        payload.schedule_value = formData.schedule_value
      }
      
      await api.post('/bot-schedules', payload)
      setShowModal(false)
      resetForm()
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotScheduleManagement.error.create-bot-schedule", "Failed to create bot schedule"))
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingSchedule) return
    
    try {
      setError('')
      
      const payload: any = {
        schedule_type: formData.schedule_type,
        time: formData.time,
        schedule_option: formData.schedule_option,
        enabled: formData.enabled
      }
      
      if (formData.schedule_option !== 'daily' && formData.schedule_value.length > 0) {
        payload.schedule_value = formData.schedule_value
      } else if (formData.schedule_option === 'daily') {
        payload.schedule_value = null
      }
      
      await api.put(`/bot-schedules/${editingSchedule.id}`, payload)
      setShowModal(false)
      setEditingSchedule(null)
      resetForm()
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotScheduleManagement.error.update-bot-schedule", "Failed to update bot schedule"))
    }
  }

  const handleDelete = async (scheduleId: number) => {
    if (!window.confirm(t("BotScheduleManagement.confirm.delete-bot-schedule", "Are you sure you want to delete this schedule?"))) {
      return
    }

    try {
      setDeletingId(scheduleId)
      await api.delete(`/bot-schedules/${scheduleId}`)
      fetchData()
      onUpdate?.()
    } catch (err: any) {
      setError(err.response?.data?.detail || t("BotScheduleManagement.error.delete-bot-schedule", "Failed to delete bot schedule"))
    } finally {
      setDeletingId(null)
    }
  }

  const handleEdit = (schedule: BotSchedule) => {
    setEditingSchedule(schedule)
    setFormData({
      bot_id: schedule.bot_id,
      schedule_type: schedule.schedule_type,
      time: schedule.time,
      schedule_option: schedule.schedule_option,
      schedule_value: schedule.schedule_value || [],
      enabled: schedule.enabled
    })
    setShowModal(true)
  }

  const resetForm = () => {
    setFormData({
      bot_id: 0,
      schedule_type: 'send_partner_balance',
      time: '09:00',
      schedule_option: 'daily',
      schedule_value: [],
      enabled: true
    })
  }

  const toggleScheduleValue = (value: number) => {
    setFormData(prev => {
      const newValue = prev.schedule_value.includes(value)
        ? prev.schedule_value.filter(v => v !== value)
        : [...prev.schedule_value, value].sort((a, b) => a - b)
      return { ...prev, schedule_value: newValue }
    })
  }

  const getBotName = (botId: number) => {
    const bot = bots.find(b => b.bot_id === botId)
    return bot?.bot_name || `Bot ${botId}`
  }

  const getScheduleOptionLabel = (option: string) => {
    switch (option) {
      case 'daily': return 'Every day'
      case 'weekdays': return 'Specific weekdays'
      case 'monthly': return 'Specific day(s) of the month'
      default: return option
    }
  }

  const formatScheduleValue = (schedule: BotSchedule) => {
    if (!schedule.schedule_value || schedule.schedule_value.length === 0) {
      return '-'
    }
    
    if (schedule.schedule_option === 'weekdays') {
      return schedule.schedule_value
        .map(d => WEEKDAYS.find(w => w.value === d)?.label || d)
        .join(', ')
    } else if (schedule.schedule_option === 'monthly') {
      return schedule.schedule_value.join(', ')
    }
    
    return '-'
  }

  const getAvailableBots = () => {
    return bots.filter(bot => !schedules.some(s => s.bot_id === bot.bot_id && s.schedule_type === formData.schedule_type && (!editingSchedule || s.id !== editingSchedule.id)))
  }

  if (loading) {
    return <div className="loading">{t("BotScheduleManagement.loading-bot-schedules", "Loading bot schedules...")}</div>
  }

  return (
    <div className="bot-schedule-management">
      <div className="section-header">
        <h2>{t("BotScheduleManagement.bot-schedules-management", "Bot Schedules Management")}</h2>
        <button 
          onClick={() => {
            setEditingSchedule(null)
            resetForm()
            setShowModal(true)
          }} 
          className="add-button"
          disabled={bots.length === 0}
        >
          + {t("BotScheduleManagement.add-bot-schedule", "Add Bot Schedule")}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {bots.length === 0 && schedules.length === 0 && (
        <div className="empty-state">{t("BotScheduleManagement.warning.no-bots", "No bots available. Create a bot first!")}</div>
      )}

      {schedules.length === 0 && bots.length > 0 && (
        <div className="empty-state">{t("BotScheduleManagement.not-bot-schedules", "No bot schedules found. Create your first schedule!")}</div>
      )}

      {schedules.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>{t("common.bot", "Bot")}</th>
              <th>{t("BotScheduleManagement.schedule-type", "Schedule Type")}</th>
              <th>{t("common.time", "Time")}</th>
              <th>{t("BotScheduleManagement.schedule-option", "Schedule Option")}</th>
              <th>{t("BotScheduleManagement.schedule-value", "Schedule Value")}</th>
              <th>{t("common.enabled", "Enabled")}</th>
              <th>{t("common.updated-at", "Updated At")}</th>
              <th>{t("common.actions", "Actions")}</th>
            </tr>
          </thead>
          <tbody>
            {schedules.map((schedule) => (
              <tr key={schedule.id}>
                <td data-label="ID">{schedule.id}</td>
                <td data-label="Bot">{getBotName(schedule.bot_id)}</td>
                <td data-label="Schedule Type">{schedule.schedule_type}</td>
                <td data-label="Time">{schedule.time}</td>
                <td data-label="Schedule Option">{getScheduleOptionLabel(schedule.schedule_option)}</td>
                <td data-label="Schedule Value">{formatScheduleValue(schedule)}</td>
                <td data-label="Enabled">{schedule.enabled ? t("common.yes", "Yes") : t("common.no", "No")}</td>
                <td data-label="Updated At">{new Date(schedule.updated_at).toLocaleString()}</td>
                <td data-label="Actions">
                  <div className="action-buttons">
                    <button
                      onClick={() => handleEdit(schedule)}
                      className="edit-button"
                    >
                      {t("common.edit", "Edit")}
                    </button>
                    <button
                      onClick={() => handleDelete(schedule.id)}
                      disabled={deletingId === schedule.id}
                      className="delete-button"
                    >
                      {deletingId === schedule.id ? t("common.deleting", "Deleting...") : t("common.delete", "Delete")}
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
          setEditingSchedule(null)
          resetForm()
        }}>
          <div className="modal-content schedule-modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editingSchedule ? t("BotScheduleManagement.edit-bot-schedule", "Edit Bot Schedule") : t("BotScheduleManagement.create-new-schedule", "Create New Bot Schedule")}</h3>
            <form onSubmit={editingSchedule ? handleUpdate : handleCreate}>
              {!editingSchedule && (
                <div className="form-group">
                  <label>{t("common.bot", "Bot")} *</label>
                  <select
                    value={formData.bot_id}
                    onChange={(e) => setFormData({ ...formData, bot_id: parseInt(e.target.value) })}
                    required
                  >
                    <option value={0}>{t("BotScheduleManagement.select-bot", "Select a bot")}</option>
                    {getAvailableBots().map((bot) => (
                      <option key={bot.bot_id} value={bot.bot_id}>
                        {bot.bot_name || `${t("common.bot", "Bot")} ${bot.bot_id}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {editingSchedule && (
                <div className="form-group">
                  <label>{t("common.bot", "Bot")}</label>
                  <input
                    type="text"
                    value={getBotName(editingSchedule.bot_id)}
                    disabled
                    className="disabled-input"
                  />
                </div>
              )}
              <div className="form-group">
                <label>{t("BotScheduleManagement.schedule-type", "Schedule Type")} *</label>
                <select
                  value={formData.schedule_type}
                  onChange={(e) => setFormData({ ...formData, schedule_type: e.target.value })}
                  required
                >
                  <option value="send_partner_balance">{t("BotScheduleManagement.send-partner-balance", "Send Partner Balance")}</option>
                </select>
              </div>
              <div className="form-group">
                <label>{t("common.time", "Time")} *</label>
                <input
                  type="time"
                  value={formData.time}
                  onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>{t("BotScheduleManagement.schedule-option", "Schedule Option")} *</label>
                <select
                  value={formData.schedule_option}
                  onChange={(e) => {
                    const newOption = e.target.value
                    setFormData({
                      ...formData,
                      schedule_option: newOption,
                      schedule_value: newOption === 'daily' ? [] : formData.schedule_value
                    })
                  }}
                  required
                >
                  <option value="daily">{t("BotScheduleManagement.every-day", "Every day")}</option>
                  <option value="weekdays">{t("BotScheduleManagement.specific-weekdays", "Specific weekdays")}</option>
                  <option value="monthly">{t("BotScheduleManagement.specific-days-of-month", "Specific day(s) of the month")}</option>
                </select>
              </div>
              
              {formData.schedule_option === 'weekdays' && (
                <div className="form-group">
                  <label>{t("common.weekdays", "Weekdays")} *</label>
                  <div className="checkbox-group">
                    {WEEKDAYS.map(day => (
                      <label key={day.value} className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={formData.schedule_value.includes(day.value)}
                          onChange={() => toggleScheduleValue(day.value)}
                        />
                        <span>{day.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              
              {formData.schedule_option === 'monthly' && (
                <div className="form-group">
                  <label>{t("BotScheduleManagement.choose-days-of-month", "Days of Month * (1-31, comma-separated)")}</label>
                  <input
                    type="text"
                    value={formData.schedule_value.map(v => v.toString()).join(',')}
                    onChange={(e) => {
                      const values = e.target.value
                        .split(',')
                        .map(v => parseInt(v.trim()))
                        .filter(v => !isNaN(v) && v >= 1 && v <= 31)
                      setFormData({ ...formData, schedule_value: values })
                    }}
                    placeholder="1, 15, 30"
                  />
                  <small style={{ color: '#666', display: 'block', marginTop: '4px' }}>
                    {t("BotScheduleManagement.enter-day-numbers", "Enter day numbers (1-31) separated by commas")}
                  </small>
                </div>
              )}
              
              <div className="form-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={formData.enabled}
                    onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                  />
                  <span>{t("common.enabled", "Enabled")}</span>
                </label>
              </div>
              
              <div className="modal-actions">
                <button
                  type="button"
                  onClick={() => {
                    setShowModal(false)
                    setEditingSchedule(null)
                    resetForm()
                  }}
                  className="cancel-button"
                >
                  {t("common.cancel", "Cancel")}
                </button>
                <button type="submit" className="submit-button">
                  {editingSchedule ? t("common.update", "Update") : t("common.create", "Create")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default BotScheduleManagement

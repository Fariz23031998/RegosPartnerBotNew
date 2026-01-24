import { useState } from 'react'
import { api } from '../services/api'
import './ChangePassword.css'
import { useLanguage } from "../contexts/LanguageContext"

interface ChangePasswordProps {
  onSuccess?: () => void
}

function ChangePassword({ onSuccess }: ChangePasswordProps) {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { t } = useLanguage()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    // Validation
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError(t("ChangePassword.error.all-fields-required", "All fields are required"))
      return
    }

    if (newPassword.length < 6) {
      setError(t("ChangePassword.error.new-password-must-be-at-least-6-characters-long", "New password must be at least 6 characters long"))
      return
    }

    if (newPassword !== confirmPassword) {
      setError(t("ChangePassword.error.new-passwords-do-not-match", "New passwords do not match"))
      return
    }

    if (currentPassword === newPassword) {
      setError(t("ChangePassword.error.new-password-must-be-different-from-current-password", "New password must be different from current password"))
      return
    }

    setIsSubmitting(true)

    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })

      setSuccess(t("ChangePassword.success.password-changed-successfully", "Password changed successfully!"))
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      
      if (onSuccess) {
        setTimeout(() => {
          onSuccess()
        }, 1500)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || t("ChangePassword.error.failed-to-change-password", "Failed to change password"))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="change-password">
      <h2>{t("ChangePassword.change-password", "Change Password")}</h2>
      
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="current-password">{t("ChangePassword.current-password", "Current Password")}</label>
          <input
            id="current-password"
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder={t("ChangePassword.enter-current-password", "Enter current password")}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="new-password">{t("ChangePassword.new-password", "New Password")}</label>
          <input
            id="new-password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder={t("ChangePassword.enter-new-password-min-6-characters", "Enter new password (min. 6 characters)")}
            required
            minLength={6}
          />
        </div>

        <div className="form-group">
          <label htmlFor="confirm-password">{t("ChangePassword.confirm-new-password", "Confirm New Password")}</label>
          <input
            id="confirm-password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder={t("ChangePassword.confirm-new-password", "Confirm new password")}
            required
            minLength={6}
          />
        </div>

        <div className="form-actions">
          <button
            type="submit"
            className="submit-button"
            disabled={isSubmitting}
          >
            {isSubmitting ? t("ChangePassword.changing", "Changing...") : t("ChangePassword.change-password", "Change Password")}
          </button>
        </div>
      </form>
    </div>
  )
}

export default ChangePassword

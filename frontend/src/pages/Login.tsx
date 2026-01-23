import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'
import './Login.css'
import { useLanguage } from "../contexts/LanguageContext"

function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const { t } = useLanguage()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    console.log('[Login] Form submitted', {
      username,
      passwordLength: password.length,
      timestamp: new Date().toISOString(),
    })

    try {
      await login(username, password)
      console.log('[Login] Login successful, navigating to dashboard')
      navigate('/')
    } catch (err: any) {
      const errorMessage = err.message || 'Login failed. Please check your credentials.'
      console.error('[Login] Login failed', {
        username,
        errorMessage,
        error: err,
      })
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>{t("login.telegram-bot-admin", "Telegram Bot Admin")}</h1>
        <h2>Login</h2>
        <form onSubmit={handleSubmit}>
          {error && <div className="error-message">{error}</div>}
          <div className="form-group">
            <label htmlFor="username">{t("login.username", "Username")}</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              placeholder="Enter username"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">{t("login.password", "Password")}</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder={t("login.enter-password", "Enter password")}
            />
          </div>
          <button type="submit" disabled={loading} className="login-button">
            {loading ? t("login.logging-in", "Logging in...") : t("login.login", "Login")}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Login



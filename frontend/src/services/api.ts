import axios from 'axios'

// Get baseURL from environment variable or use default
// For separate domains, set VITE_API_BASE_URL in .env file
// Examples:
//   VITE_API_BASE_URL=/regos-partner-bot/api (for subpath)
//   VITE_API_BASE_URL=https://api.example.com/api (for separate domain)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/regos-partner-bot/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Clean up invalid tokens on initialization (only in browser)
if (typeof window !== 'undefined') {
  const token = localStorage.getItem('token')
  // Remove invalid tokens (undefined, null strings, or empty)
  if (token === 'undefined' || token === 'null' || (token && token.trim() === '')) {
    localStorage.removeItem('token')
    console.warn('[API] Removed invalid token from localStorage')
  } else if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }
}

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    // Validate token - ensure it's not "undefined" string or empty
    if (token && token !== 'undefined' && token.trim() !== '') {
      config.headers.Authorization = `Bearer ${token}`
      // Debug logging (remove in production)
      console.log('[API Request]', config.method?.toUpperCase(), config.url, {
        hasToken: !!token,
        tokenPreview: token.length > 20 ? token.substring(0, 20) + '...' : token.substring(0, token.length),
        headers: config.headers
      })
    } else {
      // Remove invalid token
      if (token === 'undefined' || token === 'null') {
        localStorage.removeItem('token')
      }
      console.warn('[API Request] No valid token found in localStorage', config.url)
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.error('[API 401 Error]', {
        url: error.config?.url,
        method: error.config?.method,
        headers: error.config?.headers,
        response: error.response?.data,
        requestHeaders: error.request?.headers
      })
      
      // Only redirect if we're not already on the login page
      if (!window.location.pathname.includes('/login')) {
        localStorage.removeItem('token')
        delete api.defaults.headers.common['Authorization']
        // Add a small delay to allow console inspection
        setTimeout(() => {
          window.location.href = '/regos-partner-bot/admin/login'
        }, 2000)
      }
    }
    return Promise.reject(error)
  }
)


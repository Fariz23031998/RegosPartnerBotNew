import axios from 'axios'

export const api = axios.create({
  baseURL: '/regos-partner-bot/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests if available (only in browser)
if (typeof window !== 'undefined') {
  const token = localStorage.getItem('token')
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  }
}

// Request interceptor to add token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
      // Debug logging (remove in production)
      console.log('[API Request]', config.method?.toUpperCase(), config.url, {
        hasToken: !!token,
        tokenPreview: token.substring(0, 20) + '...',
        headers: config.headers
      })
    } else {
      console.warn('[API Request] No token found in localStorage', config.url)
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


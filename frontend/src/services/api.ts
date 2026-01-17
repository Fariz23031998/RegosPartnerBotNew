import axios from 'axios'

// Get baseURL from environment variable or use default
// For separate domains, set VITE_API_BASE_URL in .env file
// Examples:
//   VITE_API_BASE_URL=/api (for same domain)
//   VITE_API_BASE_URL=/regos-partner-bot/api (for subpath)
//   VITE_API_BASE_URL=https://api.example.com/api (for separate domain)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

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
    const fullUrl = `${config.baseURL || api.defaults.baseURL}${config.url}`
    const isAuthRequest = config.url?.includes('/auth/')
    
    // Validate token - ensure it's not "undefined" string or empty
    if (token && token !== 'undefined' && token.trim() !== '') {
      config.headers.Authorization = `Bearer ${token}`
      
      // Enhanced logging for auth requests
      if (isAuthRequest) {
        console.log('[API Request - Auth]', {
          method: config.method?.toUpperCase(),
          url: fullUrl,
          endpoint: config.url,
          hasToken: true,
          tokenPreview: token.length > 20 ? `${token.substring(0, 20)}...` : token.substring(0, token.length),
          requestData: config.data ? (typeof config.data === 'string' ? JSON.parse(config.data) : config.data) : null,
        })
      } else {
        // Regular logging for non-auth requests
        console.log('[API Request]', {
          method: config.method?.toUpperCase(),
          url: fullUrl,
          endpoint: config.url,
          hasToken: true,
          tokenPreview: token.length > 20 ? `${token.substring(0, 20)}...` : token.substring(0, token.length),
          authorizationHeader: config.headers.Authorization ? `${config.headers.Authorization.substring(0, 30)}...` : 'MISSING',
        })
      }
    } else {
      // Remove invalid token
      if (token === 'undefined' || token === 'null') {
        localStorage.removeItem('token')
      }
      
      if (isAuthRequest) {
        console.log('[API Request - Auth]', {
          method: config.method?.toUpperCase(),
          url: fullUrl,
          endpoint: config.url,
          hasToken: false,
          requestData: config.data ? (typeof config.data === 'string' ? JSON.parse(config.data) : config.data) : null,
        })
      } else {
        console.warn('[API Request] No valid token found in localStorage', {
          method: config.method?.toUpperCase(),
          url: fullUrl,
          endpoint: config.url,
        })
      }
    }
    return config
  },
  (error) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// Response interceptor to handle responses and errors
api.interceptors.response.use(
  (response) => {
    const isAuthRequest = response.config.url?.includes('/auth/')
    
    if (isAuthRequest) {
      console.log('[API Response - Auth]', {
        method: response.config.method?.toUpperCase(),
        url: `${response.config.baseURL || api.defaults.baseURL}${response.config.url}`,
        endpoint: response.config.url,
        status: response.status,
        statusText: response.statusText,
        responseData: response.data,
      })
    }
    
    return response
  },
  (error) => {
    const isAuthRequest = error.config?.url?.includes('/auth/')
    const fullUrl = error.config ? `${error.config.baseURL || api.defaults.baseURL}${error.config.url}` : 'N/A'
    
    if (error.response?.status === 401) {
      console.error('[API 401 Error]', {
        url: fullUrl,
        endpoint: error.config?.url,
        method: error.config?.method,
        status: error.response.status,
        statusText: error.response.statusText,
        responseData: error.response?.data,
        isAuthRequest,
        requestHeaders: error.config?.headers,
        authorizationHeaderSent: !!error.config?.headers?.Authorization,
        authorizationHeaderValue: error.config?.headers?.Authorization ? `${error.config.headers.Authorization.substring(0, 30)}...` : 'NOT SENT',
        tokenInStorage: !!localStorage.getItem('token'),
      })
      
      // Only redirect if we're not already on the login page
      if (!window.location.pathname.includes('/login')) {
        localStorage.removeItem('token')
        delete api.defaults.headers.common['Authorization']
        console.log('[API] Redirecting to login page due to 401 error')
        // Add a small delay to allow console inspection
        setTimeout(() => {
        // Redirect to login page using the app's base path
        // The app is deployed at /admin/ so redirect to /admin/login
        window.location.href = '/admin/login'
        }, 2000)
      }
    } else if (isAuthRequest) {
      // Log other auth-related errors
      console.error('[API Response - Auth Error]', {
        url: fullUrl,
        endpoint: error.config?.url,
        method: error.config?.method,
        status: error.response?.status,
        statusText: error.response?.statusText,
        responseData: error.response?.data,
        errorMessage: error.message,
      })
    }
    
    return Promise.reject(error)
  }
)


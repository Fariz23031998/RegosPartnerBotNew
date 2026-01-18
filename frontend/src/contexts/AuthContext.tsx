import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../services/api'

interface AuthContextType {
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  username: string | null
  role: 'admin' | 'user' | null
  userId: number | null
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [username, setUsername] = useState<string | null>(null)
  const [role, setRole] = useState<'admin' | 'user' | null>(null)
  const [userId, setUserId] = useState<number | null>(null)

  useEffect(() => {
    // Check if user is already authenticated
    const token = localStorage.getItem('token')
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      checkAuth()
    }
  }, [])

  const checkAuth = async () => {
    const requestUrl = `${api.defaults.baseURL}/auth/me`
    console.log('[Auth] Checking authentication status...', {
      url: requestUrl,
      hasToken: !!localStorage.getItem('token'),
    })

    try {
      const response = await api.get('/auth/me')
      console.log('[Auth] Authentication check successful', {
        url: requestUrl,
        status: response.status,
        responseData: {
          username: response.data.username,
          role: response.data.role,
          userId: response.data.user_id,
        },
      })
      setIsAuthenticated(true)
      setUsername(response.data.username)
      setRole(response.data.role || 'admin')
      setUserId(response.data.user_id || null)
    } catch (error: any) {
      console.error('[Auth] Authentication check failed', {
        url: requestUrl,
        status: error.response?.status,
        statusText: error.response?.statusText,
        errorData: error.response?.data,
        errorMessage: error.message,
      })
      setIsAuthenticated(false)
      setUsername(null)
      setRole(null)
      setUserId(null)
      localStorage.removeItem('token')
      delete api.defaults.headers.common['Authorization']
    }
  }

  const login = async (username: string, password: string) => {
    const requestUrl = `${api.defaults.baseURL}/auth/login`
    const requestData = { username, password: '***' } // Mask password in logs
    
    console.log('[Auth] Login request initiated', {
      url: requestUrl,
      requestData: {
        username: requestData.username,
        password: requestData.password, // Masked
        passwordLength: password.length, // Log length for debugging
      },
    })

    try {
      const response = await api.post('/auth/login', { username, password })
      const { access_token } = response.data
      
      console.log('[Auth] Login request successful', {
        url: requestUrl,
        status: response.status,
        responseData: {
          hasAccessToken: !!access_token,
          tokenLength: access_token?.length || 0,
          tokenPreview: access_token ? `${access_token.substring(0, 20)}...` : 'N/A',
          tokenType: response.data.token_type,
        },
      })
      
      // Validate token before storing
      if (!access_token || access_token === 'undefined' || access_token.trim() === '') {
        console.error('[Auth] Invalid token received from server', {
          access_token: access_token,
          tokenType: typeof access_token,
        })
        throw new Error('Invalid token received from server')
      }
      
      localStorage.setItem('token', access_token)
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      
      // Fetch user info to get role
      try {
        const userResponse = await api.get('/auth/me')
        setIsAuthenticated(true)
        setUsername(userResponse.data.username)
        setRole(userResponse.data.role || 'admin')
        setUserId(userResponse.data.user_id || null)
        
        console.log('[Auth] Login completed successfully', {
          username: userResponse.data.username,
          role: userResponse.data.role,
          userId: userResponse.data.user_id,
          tokenStored: true,
          authorizationHeaderSet: !!api.defaults.headers.common['Authorization'],
        })
      } catch (error: any) {
        // Fallback to username if /me fails
        setIsAuthenticated(true)
        setUsername(username)
        setRole('admin') // Default to admin for backward compatibility
        setUserId(null)
        
        console.log('[Auth] Login completed (fallback mode)', {
          username,
          tokenStored: true,
          authorizationHeaderSet: !!api.defaults.headers.common['Authorization'],
        })
      }
    } catch (error: any) {
      console.error('[Auth] Login request failed', {
        url: requestUrl,
        status: error.response?.status,
        statusText: error.response?.statusText,
        errorData: error.response?.data,
        errorMessage: error.message,
        requestData: {
          username: requestData.username,
          password: requestData.password, // Masked
        },
      })
      throw new Error(error.response?.data?.detail || 'Login failed')
    }
  }

  const logout = () => {
    console.log('[Auth] Logout initiated', {
      username,
      role,
      hadToken: !!localStorage.getItem('token'),
    })
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    setIsAuthenticated(false)
    setUsername(null)
    setRole(null)
    setUserId(null)
    console.log('[Auth] Logout completed')
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, username, role, userId }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}



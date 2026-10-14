import { create } from 'zustand'
import { apiClient } from '../services/api'

const initialToken = localStorage.getItem('auth_token') || null

const useAuthStore = create((set, get) => ({
  user: null,
  token: initialToken,
  isAuthenticated: !!initialToken,
  isInitialized: !initialToken, // Initialized immediately if no stored token, otherwise after fetchMe
  isLoading: false,
  error: null,
  sessionExpiredMessage: null,

  setSessionExpiredMessage: (msg) => set({ sessionExpiredMessage: msg }),
  clearSessionExpiredMessage: () => set({ sessionExpiredMessage: null }),

  login: async (email, password) => {
    set({ isLoading: true, error: null, sessionExpiredMessage: null })
    try {
      const response = await apiClient.post('/api/v1/auth/login', {
        email,
        password,
      })
      const { access_token, refresh_token, user } = response.data
      localStorage.setItem('auth_token', access_token)
      if (refresh_token) localStorage.setItem('refresh_token', refresh_token)
      set({
        user,
        token: access_token,
        isAuthenticated: true,
        isInitialized: true,
        isLoading: false,
      })
      return { success: true }
    } catch (error) {
      const message =
        error.response?.data?.error || 'Login failed. Please try again.'
      set({ error: message, isLoading: false })
      return { success: false, error: message }
    }
  },

  signup: async (firstName, lastName, email, password, provider = 'viewer') => {
    set({ isLoading: true, error: null, sessionExpiredMessage: null })
    try {
      await apiClient.post('/api/v1/auth/register', {
        email,
        password,
        username: `${firstName.toLowerCase()}.${lastName.toLowerCase()}`,
        role: provider.toLowerCase(),
      })

      const loginResponse = await apiClient.post('/api/v1/auth/login', {
        email,
        password,
      })
      const { access_token, refresh_token, user } = loginResponse.data
      localStorage.setItem('auth_token', access_token)
      if (refresh_token) localStorage.setItem('refresh_token', refresh_token)
      set({
        user,
        token: access_token,
        isAuthenticated: true,
        isInitialized: true,
        isLoading: false,
      })
      return { success: true }
    } catch (error) {
      const message =
        error.response?.data?.errors?.email?.[0] ||
        error.response?.data?.errors?.password?.[0] ||
        error.response?.data?.errors?.username?.[0] ||
        error.response?.data?.error ||
        'Sign up failed. Please try again.'
      set({ error: message, isLoading: false })
      return { success: false, error: message }
    }
  },

  logout: (broadcast = true) => {
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('cloudopt-state-store')
    sessionStorage.clear()

    if (window.__queryClient) {
      window.__queryClient.clear()
    }
    if (window.__resetCloudStore) {
      window.__resetCloudStore()
    }

    set({ user: null, token: null, isAuthenticated: false, isInitialized: true })

    if (broadcast) {
      try {
        if (typeof BroadcastChannel !== 'undefined') {
          const channel = new BroadcastChannel('cloudopt_auth_channel')
          channel.postMessage({ type: 'LOGOUT', timestamp: Date.now() })
          channel.close()
        }
      } catch {
        // Fallback
      }
      try {
        localStorage.setItem('cloudopt_logout_event', Date.now().toString())
      } catch {
        // ignore
      }
    }
  },

  checkSession: () => {
    const token = localStorage.getItem('auth_token')
    if (!token && get().isAuthenticated) {
      get().logout(false)
    }
  },

  handleSessionExpired: (returnTo) => {
    get().logout(true)
    set({ sessionExpiredMessage: 'Your session has expired. Please sign in again.' })
    const target = returnTo ? `/login?returnTo=${encodeURIComponent(returnTo)}` : '/login'
    window.location.replace(target)
  },

  clearError: () => {
    set({ error: null })
  },

  fetchMe: async () => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      set({ user: null, isAuthenticated: false, isInitialized: true })
      return
    }
    try {
      const response = await apiClient.get('/api/v1/auth/me')
      set({ user: response.data.user, isAuthenticated: true, isInitialized: true })
    } catch (error) {
      if (error.response?.status === 401 || error.response?.status === 403) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('cloudopt-state-store')
        set({ user: null, token: null, isAuthenticated: false, isInitialized: true })
        return { success: false, error: 'Your session has expired. Please sign in again.' }
      }
      // Network or other error - preserve session if token exists
      set({ isInitialized: true })
      return { success: false }
    }
  },
}))

export default useAuthStore
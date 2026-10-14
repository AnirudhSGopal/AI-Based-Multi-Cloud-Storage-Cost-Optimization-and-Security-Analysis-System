import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor — attach token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

let activeRefreshPromise = null

async function performSingleRefresh() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  const response = await axios.post(
    `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/v1/auth/refresh`,
    {},
    {
      headers: {
        Authorization: `Bearer ${refreshToken}`,
      },
    }
  )

  const { access_token, refresh_token: newRefreshToken } = response.data
  if (!access_token) {
    throw new Error('No access token returned from refresh')
  }

  localStorage.setItem('auth_token', access_token)
  if (newRefreshToken) {
    localStorage.setItem('refresh_token', newRefreshToken)
  }
  return access_token
}

async function requestTokenRefresh() {
  if (activeRefreshPromise) {
    return activeRefreshPromise
  }

  activeRefreshPromise = (async () => {
    const tokenBefore = localStorage.getItem('auth_token')

    if (typeof navigator !== 'undefined' && navigator.locks?.request) {
      return navigator.locks.request('cloudopt_token_refresh', async () => {
        const tokenNow = localStorage.getItem('auth_token')
        if (tokenNow && tokenNow !== tokenBefore) {
          return tokenNow
        }
        return performSingleRefresh()
      })
    }

    return performSingleRefresh()
  })().finally(() => {
    activeRefreshPromise = null
  })

  return activeRefreshPromise
}

// Response interceptor — automatic token refresh & global 401 handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const requestUrl = originalRequest?.url || ''
    const isAuthEndpoint =
      requestUrl.includes('/auth/login') ||
      requestUrl.includes('/auth/register') ||
      requestUrl.includes('/auth/refresh')

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true

      try {
        const newAccessToken = await requestTokenRefresh()
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return api(originalRequest)
      } catch (refreshError) {
        console.warn('Automatic token refresh failed:', refreshError.message)
        try {
          const authModule = await import('../store/authStore')
          const useAuthStore = authModule.default
          useAuthStore.getState().handleSessionExpired(
            window.location.pathname + window.location.search
          )
        } catch {
          localStorage.removeItem('auth_token')
          localStorage.removeItem('refresh_token')
          window.location.replace('/login')
        }
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export const apiClient = api
export default api
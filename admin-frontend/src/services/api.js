import axios from 'axios'

const DEFAULT_API_URL = import.meta.env.PROD
  ? 'https://cloudopt-api.onrender.com'
  : ''

const API_HOST = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_URL).replace(/\/+$/, '')
const API_BASE = `${API_HOST}/api/v1/admin`

export const adminApi = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach admin token (with aud=admin) to all requests
adminApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('cloudopt_admin_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Intercept responses: on 401/403/404 indicating session invalidation, clear and redirect to login
adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && (error.response.status === 401 || (error.response.status === 404 && error.config.url?.includes('/users')))) {
      // If token expired or admin permissions lost, purge session
      if (localStorage.getItem('cloudopt_admin_token')) {
        localStorage.removeItem('cloudopt_admin_token')
        localStorage.removeItem('cloudopt_admin_user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// 15-minute Inactivity / Idle Auto-Logout Tracker
let idleTimer = null
const IDLE_TIMEOUT_MS = 15 * 60 * 1000 // 15 minutes

export function resetIdleTimer() {
  if (idleTimer) clearTimeout(idleTimer)
  const token = localStorage.getItem('cloudopt_admin_token')
  if (token) {
    idleTimer = setTimeout(() => {
      localStorage.removeItem('cloudopt_admin_token')
      localStorage.removeItem('cloudopt_admin_user')
      alert('Your admin session has timed out due to 15 minutes of inactivity. Please sign in again.')
      window.location.href = '/login'
    }, IDLE_TIMEOUT_MS)
  }
}

// Attach event listeners for user activity
if (typeof window !== 'undefined') {
  const events = ['mousedown', 'keydown', 'scroll', 'touchstart']
  events.forEach((ev) => window.addEventListener(ev, resetIdleTimer, { passive: true }))
  resetIdleTimer()
}


import { adminApi, resetIdleTimer } from './api'

export const authService = {
  async login(email, password, totp_code = '') {
    const payload = { email, password }
    if (totp_code && totp_code.trim()) {
      payload.totp_code = totp_code.trim()
    }
    const response = await adminApi.post('/auth/login', payload)
    const { access_token, user } = response.data
    localStorage.setItem('cloudopt_admin_token', access_token)
    localStorage.setItem('cloudopt_admin_user', JSON.stringify(user))
    resetIdleTimer()
    return { token: access_token, user }
  },

  logout() {
    localStorage.removeItem('cloudopt_admin_token')
    localStorage.removeItem('cloudopt_admin_user')
    window.location.href = '/login'
  },

  getCurrentUser() {
    try {
      const u = localStorage.getItem('cloudopt_admin_user')
      return u ? JSON.parse(u) : null
    } catch {
      return null
    }
  },

  isAuthenticated() {
    return Boolean(localStorage.getItem('cloudopt_admin_token'))
  },
}


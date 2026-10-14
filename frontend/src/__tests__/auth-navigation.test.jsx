import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import { getSafeReturnTo } from '../utils/navigation'
import { ProtectedRoute, PublicOnlyRoute } from '../components/auth/AuthGuards'
import LandingPage from '../pages/LandingPage'
import NotFound from '../pages/NotFound'
import { apiClient } from '../services/api'
import axios from 'axios'

vi.mock('../services/api', () => {
  return {
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    },
    default: {
      get: vi.fn(),
      post: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    },
  }
})

describe('CloudOpt Frontend Navigation & Authentication Flow', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.clearAllMocks()

    useAuthStore.setState({
      user: null,
      token: null,
      isAuthenticated: false,
      isInitialized: true,
      isLoading: false,
      error: null,
      sessionExpiredMessage: null,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 1. LANDING PAGE ("/") SPEC
  // ──────────────────────────────────────────────────────────────────────────
  describe('1. Landing Page ("/")', () => {
    it('is accessible when logged out and shows "Sign In" and "Get Started Free"', () => {
      useAuthStore.setState({ isAuthenticated: false, isInitialized: true })

      render(
        <MemoryRouter initialEntries={['/']}>
          <LandingPage theme="dark" toggleTheme={vi.fn()} />
        </MemoryRouter>
      )

      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /get started free/i })).toBeInTheDocument()
    })

    it('is accessible when logged in (no auto-redirect) and shows "Dashboard" and "Go to Dashboard"', () => {
      useAuthStore.setState({
        isAuthenticated: true,
        isInitialized: true,
        user: { email: 'dev@cloudopt.internal' },
      })

      render(
        <MemoryRouter initialEntries={['/']}>
          <LandingPage theme="dark" toggleTheme={vi.fn()} />
        </MemoryRouter>
      )

      expect(screen.getByRole('button', { name: /^dashboard$/i })).toBeInTheDocument()
      expect(screen.getAllByRole('button', { name: /go to dashboard/i }).length).toBeGreaterThanOrEqual(1)
      expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument()
    })

    it('displays neutral skeleton placeholder when auth state is loading (!isInitialized)', () => {
      useAuthStore.setState({ isAuthenticated: false, isInitialized: false })

      render(
        <MemoryRouter initialEntries={['/']}>
          <LandingPage theme="dark" toggleTheme={vi.fn()} />
        </MemoryRouter>
      )

      // Neutral placeholders exist with aria-label
      const placeholders = screen.getAllByRole('status')
      expect(placeholders.length).toBeGreaterThanOrEqual(1)
      expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /^dashboard$/i })).not.toBeInTheDocument()
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 2. LOGIN AND REGISTER (PublicOnlyRoute)
  // ──────────────────────────────────────────────────────────────────────────
  describe('2. Login and Register Redirection', () => {
    it('redirects authenticated user away from /login to /dashboard with replace', () => {
      useAuthStore.setState({ isAuthenticated: true, isInitialized: true })

      render(
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/login" element={<div>Login Form</div>} />
              <Route path="/register" element={<div>Register Form</div>} />
            </Route>
            <Route path="/dashboard" element={<div>Dashboard Content</div>} />
          </Routes>
        </MemoryRouter>
      )

      expect(screen.getByText('Dashboard Content')).toBeInTheDocument()
      expect(screen.queryByText('Login Form')).not.toBeInTheDocument()
    })

    it('redirects authenticated user away from /register to /dashboard with replace', () => {
      useAuthStore.setState({ isAuthenticated: true, isInitialized: true })

      render(
        <MemoryRouter initialEntries={['/register']}>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/login" element={<div>Login Form</div>} />
              <Route path="/register" element={<div>Register Form</div>} />
            </Route>
            <Route path="/dashboard" element={<div>Dashboard Content</div>} />
          </Routes>
        </MemoryRouter>
      )

      expect(screen.getByText('Dashboard Content')).toBeInTheDocument()
      expect(screen.queryByText('Register Form')).not.toBeInTheDocument()
    })

    it('allows unauthenticated user to access /login and /register', () => {
      useAuthStore.setState({ isAuthenticated: false, isInitialized: true })

      render(
        <MemoryRouter initialEntries={['/login']}>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="/login" element={<div>Login Form</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      )

      expect(screen.getByText('Login Form')).toBeInTheDocument()
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 3. PROTECTED PAGES & SAFE returnTo VALIDATION
  // ──────────────────────────────────────────────────────────────────────────
  describe('3. Protected Routes & Open Redirect Prevention', () => {
    it('redirects unauthenticated user from protected page to /login with returnTo parameter', () => {
      useAuthStore.setState({ isAuthenticated: false, isInitialized: true })

      render(
        <MemoryRouter initialEntries={['/dashboard']}>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<div>Protected Dashboard</div>} />
            </Route>
            <Route path="/login" element={<div>Login Page Target</div>} />
          </Routes>
        </MemoryRouter>
      )

      expect(screen.getByText('Login Page Target')).toBeInTheDocument()
      expect(screen.queryByText('Protected Dashboard')).not.toBeInTheDocument()
    })

    it('validates returnTo strictly to prevent open redirects (getSafeReturnTo)', () => {
      // Safe relative paths
      expect(getSafeReturnTo('/cost-analysis')).toBe('/cost-analysis')
      expect(getSafeReturnTo('/security?tab=alerts#summary')).toBe('/security?tab=alerts#summary')
      expect(getSafeReturnTo('/settings')).toBe('/settings')

      // Malicious / open redirect attempts
      expect(getSafeReturnTo('https://evil.com')).toBe('/dashboard')
      expect(getSafeReturnTo('//evil.com/phish')).toBe('/dashboard')
      expect(getSafeReturnTo('javascript:alert(1)')).toBe('/dashboard')
      expect(getSafeReturnTo('/\\evil.com')).toBe('/dashboard')
      expect(getSafeReturnTo('   ')).toBe('/dashboard')
      expect(getSafeReturnTo(null)).toBe('/dashboard')
      expect(getSafeReturnTo(undefined)).toBe('/dashboard')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 5. LOGOUT & BCACHE PROTECTION
  // ──────────────────────────────────────────────────────────────────────────
  describe('5. Logout and State Cleanup', () => {
    it('clears auth token, refresh token, cloud store state, and query cache on logout', () => {
      localStorage.setItem('auth_token', 'valid_token')
      localStorage.setItem('refresh_token', 'valid_refresh')
      localStorage.setItem('cloudopt-state-store', JSON.stringify({ alerts: ['alert-1'] }))

      const mockQueryClientClear = vi.fn()
      window.__queryClient = { clear: mockQueryClientClear }
      const mockResetCloudStore = vi.fn()
      window.__resetCloudStore = mockResetCloudStore

      useAuthStore.setState({
        token: 'valid_token',
        isAuthenticated: true,
        user: { id: 1, email: 'test@example.com' },
      })

      useAuthStore.getState().logout(false)

      expect(localStorage.getItem('auth_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
      expect(localStorage.getItem('cloudopt-state-store')).toBeNull()
      expect(mockQueryClientClear).toHaveBeenCalled()
      expect(mockResetCloudStore).toHaveBeenCalled()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().user).toBeNull()
    })

    it('checkSession logs out user if token is missing in localStorage (bfcache / popstate check)', () => {
      useAuthStore.setState({
        isAuthenticated: true,
        token: 'token',
        user: { id: 1 },
      })
      localStorage.removeItem('auth_token')

      useAuthStore.getState().checkSession()

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 6. SESSION EXPIRATION & REFRESH HANDLING
  // ──────────────────────────────────────────────────────────────────────────
  describe('6. Session Expiry & Deactivated User Handling', () => {
    it('fetchMe handles 401/403 deactivated user by clearing credentials and setting session state', async () => {
      localStorage.setItem('auth_token', 'expired_token')
      apiClient.get.mockRejectedValueOnce({
        response: { status: 401, data: { error: 'User deactivated' } },
      })

      const res = await useAuthStore.getState().fetchMe()

      expect(res.success).toBe(false)
      expect(localStorage.getItem('auth_token')).toBeNull()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().isInitialized).toBe(true)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 7. 404 NOT FOUND PAGE
  // ──────────────────────────────────────────────────────────────────────────
  describe('7. 404 Not Found Handling', () => {
    it('renders 404 page and shows "Return to Home" button when logged out', () => {
      useAuthStore.setState({ isAuthenticated: false })

      render(
        <MemoryRouter initialEntries={['/some-unknown-deep-route']}>
          <NotFound />
        </MemoryRouter>
      )

      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.getByText('Page Not Found')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /return to home/i })).toBeInTheDocument()
    })

    it('renders 404 page and shows "Go to Dashboard" button when logged in', () => {
      useAuthStore.setState({ isAuthenticated: true })

      render(
        <MemoryRouter initialEntries={['/some-unknown-deep-route']}>
          <NotFound />
        </MemoryRouter>
      )

      expect(screen.getByText('404')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /go to dashboard/i })).toBeInTheDocument()
    })
  })
})

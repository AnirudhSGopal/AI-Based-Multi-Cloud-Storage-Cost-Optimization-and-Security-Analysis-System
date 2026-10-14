import { useEffect } from 'react'
import { Navigate, useLocation, Outlet } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

export function ProtectedRoute({ children }) {
  const { isAuthenticated, isInitialized } = useAuthStore()
  const location = useLocation()

  if (!isInitialized) {
    return (
      <div
        role="status"
        aria-live="polite"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: 'var(--color-bg-base, #07090e)',
          color: 'var(--color-text-secondary, #94a3b8)',
          fontSize: '14px',
          fontFamily: "'Outfit', sans-serif",
        }}
      >
        Checking session…
      </div>
    )
  }

  if (!isAuthenticated) {
    const returnTo = location.pathname + location.search + location.hash
    return (
      <Navigate
        to={`/login?returnTo=${encodeURIComponent(returnTo)}`}
        state={{ from: returnTo }}
        replace
      />
    )
  }

  return children || <Outlet />
}

export function PublicOnlyRoute({ children }) {
  const { isAuthenticated, isInitialized } = useAuthStore()

  if (!isInitialized) {
    return (
      <div
        role="status"
        aria-live="polite"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          background: 'var(--color-bg-base, #07090e)',
          color: 'var(--color-text-secondary, #94a3b8)',
          fontSize: '14px',
          fontFamily: "'Outfit', sans-serif",
        }}
      >
        Checking session…
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return children || <Outlet />
}

const titles = {
  '/': 'CloudOpt · Enterprise Cloud FinOps & Security',
  '/dashboard': 'Dashboard · CloudOpt',
  '/cost-analysis': 'Cost Analysis · CloudOpt',
  '/security': 'Security Audit · CloudOpt',
  '/recommendations': 'Recommendations · CloudOpt',
  '/settings': 'Settings · CloudOpt',
  '/login': 'Sign In · CloudOpt',
  '/register': 'Create Account · CloudOpt',
}

export function RouteAccessibilityTracker() {
  const location = useLocation()

  useEffect(() => {
    // 1. Update document title
    const pageTitle = titles[location.pathname] || 'CloudOpt · Enterprise Cloud FinOps & Security'
    document.title = pageTitle

    // 2. Announce and manage focus on route change
    const mainContent = document.getElementById('main-content')
    if (mainContent) {
      mainContent.focus()
    } else {
      window.scrollTo(0, 0)
    }
  }, [location.pathname])

  return null
}


import { lazy, Suspense, useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'

import useAuthStore from './store/authStore'
import Sidebar from './components/Sidebar'
import Navbar from './components/Navbar'
import { ProtectedRoute, PublicOnlyRoute, RouteAccessibilityTracker } from './components/auth/AuthGuards'

const Login = lazy(() => import('./pages/Login'))
const LandingPage = lazy(() => import('./pages/LandingPage'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const CostAnalysis = lazy(() => import('./pages/CostAnalysis'))
const SecurityAudit = lazy(() => import('./pages/SecurityAudit'))
const Recommendations = lazy(() => import('./pages/Recommendations'))
const Settings = lazy(() => import('./pages/Settings'))
const NotFound = lazy(() => import('./pages/NotFound'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
})

// Attach for logout cache clearing
if (typeof window !== 'undefined') {
  window.__queryClient = queryClient
}

function AppLayout({ theme, toggleTheme }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Navbar theme={theme} toggleTheme={toggleTheme} />
        <main id="main-content" tabIndex="-1" className="page-wrapper">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function App() {
  const { fetchMe } = useAuthStore()
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark' || saved === 'light') return saved
    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark'
    }
    return 'light'
  })

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  // Lifecycle & cross-tab auth synchronization
  useEffect(() => {
    const handlePageShow = () => {
      useAuthStore.getState().checkSession()
    }
    const handlePopState = () => {
      useAuthStore.getState().checkSession()
    }
    const handleStorage = (e) => {
      if (e.key === 'cloudopt_logout_event' || e.key === 'auth_token') {
        useAuthStore.getState().checkSession()
      }
    }

    window.addEventListener('pageshow', handlePageShow)
    window.addEventListener('popstate', handlePopState)
    window.addEventListener('storage', handleStorage)

    let channel
    try {
      if (typeof BroadcastChannel !== 'undefined') {
        channel = new BroadcastChannel('cloudopt_auth_channel')
        channel.onmessage = (event) => {
          if (event.data?.type === 'LOGOUT') {
            useAuthStore.getState().checkSession()
          }
        }
      }
    } catch {
      // BroadcastChannel unsupported
    }

    return () => {
      window.removeEventListener('pageshow', handlePageShow)
      window.removeEventListener('popstate', handlePopState)
      window.removeEventListener('storage', handleStorage)
      if (channel) {
        channel.close()
      }
    }
  }, [])

  const toggleTheme = () =>
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <RouteAccessibilityTracker />
        <Suspense
          fallback={
            <div className="page-content" role="status" aria-live="polite">
              Loading page…
            </div>
          }
        >
          <Routes>
            {/* Landing page is always accessible to everyone */}
            <Route
              path="/"
              element={<LandingPage theme={theme} toggleTheme={toggleTheme} />}
            />

            {/* Public-only routes: logged-in users redirected to /dashboard */}
            <Route element={<PublicOnlyRoute />}>
              <Route path="/login" element={<Login theme={theme} toggleTheme={toggleTheme} />} />
              <Route path="/register" element={<Login theme={theme} toggleTheme={toggleTheme} />} />
            </Route>

            {/* Authenticated Tenant Customer Routes */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout theme={theme} toggleTheme={toggleTheme} />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/cost-analysis" element={<CostAnalysis />} />
                <Route path="/security" element={<SecurityAudit />} />
                <Route path="/recommendations" element={<Recommendations />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Route>

            {/* Catch-all 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: theme === 'dark' ? '#111520' : '#ffffff',
              color: theme === 'dark' ? '#eef0f6' : '#0f1320',
              border: theme === 'dark' ? '1px solid #1e2640' : '1px solid #e2e5f0',
              fontFamily: "'Inter', sans-serif",
              fontSize: '13px',
            },
          }}
        />
      </Router>
    </QueryClientProvider>
  )
}

export default App
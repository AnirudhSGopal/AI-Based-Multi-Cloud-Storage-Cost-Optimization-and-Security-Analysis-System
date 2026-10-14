import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import useAuthStore from '../store/authStore'
import { getSafeReturnTo } from '../utils/navigation'
import { Sun, Moon, Mail, Lock, User, AlertCircle, ShieldCheck } from 'lucide-react'
import Logo from '../components/common/Logo'

const LoginForm = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, isLoading, error, sessionExpiredMessage, clearSessionExpiredMessage } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const searchParams = new URLSearchParams(location.search)
  const returnToParam = searchParams.get('returnTo') || location.state?.from
  const target = getSafeReturnTo(returnToParam, '/dashboard')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) {
      toast.error('Please fill in all fields')
      return
    }
    const result = await login(email, password)
    if (result.success) {
      clearSessionExpiredMessage()
      toast.success('Login successful!')
      navigate(target, { replace: true })
    } else {
      toast.error(result.error)
    }
  }

  return (
    <div className="form-panel">
      <div className="form-heading">Welcome back</div>
      <p className="form-sub">Sign in to view insights for your connected cloud accounts.</p>

      {sessionExpiredMessage && (
        <div
          className="alert-banner"
          style={{
            background: 'rgba(234, 179, 8, 0.12)',
            borderColor: 'rgba(234, 179, 8, 0.35)',
            marginBottom: '14px',
          }}
        >
          <AlertCircle size={14} style={{ color: '#eab308', flexShrink: 0 }} />
          <span style={{ color: '#eab308', fontSize: '13px' }}>{sessionExpiredMessage}</span>
        </div>
      )}

      {error && (
        <div className="alert-banner" style={{ background: 'var(--color-severity-critical-subtle)', borderColor: 'var(--color-severity-critical-border)' }}>
          <AlertCircle size={14} style={{ color: 'var(--color-severity-critical)', flexShrink: 0 }} />
          <span style={{ color: 'var(--color-severity-critical)' }}>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="field">
          <label>Work Email</label>
          <div className="input-wrap">
            <span className="icon"><Mail size={14} /></span>
            <input
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="field">
          <label>Password</label>
          <div className="input-wrap">
            <span className="icon"><Lock size={14} /></span>
            <input
              type="password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="forgot-row">
          <button type="button" className="forgot-link">Forgot password?</button>
        </div>

        <button type="submit" className="submit-btn" disabled={isLoading}>
          {isLoading ? 'Signing in...' : 'Sign In to CloudOpt →'}
        </button>
      </form>
    </div>
  )
}

const SignupForm = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { signup, isLoading, error, clearSessionExpiredMessage } = useAuthStore()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [provider, setProvider] = useState('AWS')
  const providers = ['AWS', 'GCP', 'Azure', 'Multi']

  const searchParams = new URLSearchParams(location.search)
  const returnToParam = searchParams.get('returnTo') || location.state?.from
  const target = getSafeReturnTo(returnToParam, '/dashboard')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!firstName || !lastName || !email || !password) {
      toast.error('Please fill in all fields')
      return
    }
    if (password.length < 12) {
      toast.error('Password must be at least 12 characters')
      return
    }
    const result = await signup(firstName, lastName, email, password, 'viewer')
    if (result.success) {
      clearSessionExpiredMessage()
      toast.success('Account created successfully!')
      navigate(target, { replace: true })
    } else {
      toast.error(result.error)
    }
  }

  return (
    <div className="form-panel">
      <div className="form-heading">Get started free</div>
      <p className="form-sub">Connect your cloud providers in under 2 minutes. No card required.</p>

      {error && (
        <div className="alert-banner" style={{ background: 'var(--color-severity-critical-subtle)', borderColor: 'var(--color-severity-critical-border)' }}>
          <AlertCircle size={14} style={{ color: 'var(--color-severity-critical)', flexShrink: 0 }} />
          <span style={{ color: 'var(--color-severity-critical)' }}>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="field-row">
          <div>
            <label>First Name</label>
            <div className="input-wrap">
              <span className="icon"><User size={14} /></span>
              <input
                type="text"
                placeholder="Alex"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            </div>
          </div>
          <div>
            <label>Last Name</label>
            <div className="input-wrap">
              <span className="icon"><User size={14} /></span>
              <input
                type="text"
                placeholder="Smith"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            </div>
          </div>
        </div>

        <div className="field">
          <label>Work Email</label>
          <div className="input-wrap">
            <span className="icon"><Mail size={14} /></span>
            <input
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="field">
          <label>Password</label>
          <div className="input-wrap">
            <span className="icon"><Lock size={14} /></span>
            <input
              type="password"
              placeholder="Min. 12 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="provider-field">
          <label>Primary cloud provider</label>
          <div className="provider-pills">
            {providers.map((p) => (
              <div
                key={p}
                className={`provider-pill${provider === p ? ' selected' : ''}`}
                onClick={() => setProvider(p)}
              >
                {p}
              </div>
            ))}
          </div>
        </div>

        <button type="submit" className="submit-btn" disabled={isLoading}>
          {isLoading ? 'Creating Account...' : 'Create Account →'}
        </button>
      </form>

      <p className="terms" style={{ marginTop: 16, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textAlign: 'center', lineHeight: 1.6 }}>
        By creating an account you agree to our{' '}
        <a href="#" style={{ color: 'var(--color-accent)', textDecoration: 'none' }}>Terms of Service</a> and{' '}
        <a href="#" style={{ color: 'var(--color-accent)', textDecoration: 'none' }}>Privacy Policy</a>.
      </p>
    </div>
  )
}

export default function Login({ theme: propTheme, toggleTheme: propToggleTheme }) {
  const location = useLocation()
  const isRegister = location.pathname.includes('/register') || new URLSearchParams(location.search).get('tab') === 'signup'
  const [tab, setTab] = useState(isRegister ? 'signup' : 'login')
  const [localTheme, setLocalTheme] = useState(() => {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark' || saved === 'light') return saved
    if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark'
    }
    return 'light'
  })

  const theme = propTheme || localTheme
  const toggleTheme = propToggleTheme || (() => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setLocalTheme(next)
    document.documentElement.setAttribute('data-theme', next)
    localStorage.setItem('theme', next)
  })

  useEffect(() => {
    if (!propTheme) {
      document.documentElement.setAttribute('data-theme', localTheme)
      localStorage.setItem('theme', localTheme)
    }
  }, [propTheme, localTheme])

  return (
    <div className="auth-root">
      {/* Theme Toggle Button */}
      <button
        onClick={toggleTheme}
        style={{
          position: 'absolute',
          top: 20,
          right: 20,
          zIndex: 100,
          width: 36,
          height: 36,
          borderRadius: 'var(--radius-md)',
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          color: 'var(--color-text-secondary)',
          transition: 'all 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--color-bg-subtle)'
          e.currentTarget.style.color = 'var(--color-text-primary)'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'var(--color-bg-surface)'
          e.currentTarget.style.color = 'var(--color-text-secondary)'
        }}
        title="Toggle theme"
        aria-label="Toggle theme"
      >
        {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
      </button>

      <div className="auth-card">
        {/* Centered Brand Logo */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
          <Logo size="lg" subText="Enterprise Cloud FinOps & SecOps" />
        </div>

        {/* Toggle */}
        <div className="toggle-bar">
          <button
            className={`toggle-btn${tab === 'login' ? ' active' : ''}`}
            onClick={() => setTab('login')}
            type="button"
          >
            Sign In
          </button>
          <button
            className={`toggle-btn${tab === 'signup' ? ' active' : ''}`}
            onClick={() => setTab('signup')}
            type="button"
          >
            Create Account
          </button>
        </div>

        {tab === 'login' ? <LoginForm /> : <SignupForm />}

        {/* Enterprise Trust Reassurance */}
        <div
          style={{
            marginTop: 22,
            paddingTop: 16,
            borderTop: '1px solid var(--color-border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            fontSize: 'var(--text-xs)',
            color: 'var(--color-text-muted)',
            fontWeight: 500,
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <ShieldCheck size={13} color="var(--color-success)" /> SOC 2 Type II
          </span>
          <span>•</span>
          <span>256-Bit TLS</span>
          <span>•</span>
          <span>ISO 27001</span>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="ai-bar">
        <div className="ai-bar-left">
          <div className="ai-dot" />
          CloudOpt Enterprise Platform
        </div>
        <div className="ai-bar-right">Continuous Cloud FinOps &amp; Security Posture</div>
      </div>
    </div>
  )
}
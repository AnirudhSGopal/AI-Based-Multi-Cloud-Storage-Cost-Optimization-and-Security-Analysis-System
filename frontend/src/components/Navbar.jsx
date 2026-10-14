import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Bell, RefreshCw, Sun, Moon, LogOut, User } from 'lucide-react'
import useCloudStore from '../store/cloudStore'
import useAuthStore from '../store/authStore'
import toast from 'react-hot-toast'

const pageMeta = {
  '/dashboard':       { title: 'Dashboard',       sub: 'Real-time overview across all cloud providers' },
  '/cost-analysis':   { title: 'Cost Analysis',   sub: 'Detailed spending breakdown by service and provider' },
  '/security':        { title: 'Security Audit',  sub: 'Threats, compliance checks and active alerts' },
  '/recommendations': { title: 'Recommendations', sub: 'AI-powered cost and security optimizations' },
  '/settings':        { title: 'Settings',        sub: 'Cloud credentials and system preferences' },
}

export default function Navbar({ theme, toggleTheme }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { alerts, dismissedAlerts } = useCloudStore()
  const { user, logout } = useAuthStore()
  const [showMenu, setShowMenu] = useState(false)

  const page = pageMeta[pathname] ?? { title: 'CloudOpt', sub: '' }
  const activeAlerts = alerts.filter(a => !dismissedAlerts.includes(a.id))
  const criticalCount = activeAlerts.filter(a => a.type === 'critical').length

  // Derive initials from user data
  const initials = user
    ? (user.username || user.email || 'U').slice(0, 2).toUpperCase()
    : 'AU'

  function handleLogout() {
    logout()
    toast.success('Logged out successfully')
    navigate('/', { replace: true })
    setShowMenu(false)
  }

  return (
    <header className="navbar">
      <div>
        <div className="navbar-title">{page.title}</div>
        {page.sub && <div className="navbar-sub">{page.sub}</div>}
      </div>
      <div className="navbar-actions">
        {/* Real-time SaaS Status Badge */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          borderRadius: 20,
          background: 'var(--bg-elevated, rgba(255,255,255,0.04))',
          border: '1px solid var(--border)',
          fontSize: 11,
          fontWeight: 600,
          color: 'var(--text-secondary)'
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'var(--green, #22c55e)',
            boxShadow: '0 0 6px rgba(34,197,94,0.6)'
          }} />
          <span>Multi-Cloud Live</span>
        </div>

        <button className="nav-icon-btn theme-toggle" onClick={toggleTheme} title="Toggle theme">
          {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
        </button>
        <button className="nav-icon-btn" title="Refresh data">
          <RefreshCw size={13} />
        </button>
        <button className="nav-icon-btn" title={`${activeAlerts.length} active alerts`} style={{ position: 'relative' }}>
          <Bell size={13} />
          {criticalCount > 0 && (
            <span className="notif-dot" style={{
              position: 'absolute', top: 5, right: 5,
              width: 5, height: 5,
              background: 'var(--red)',
              borderRadius: '50%',
              border: '1.5px solid var(--bg-surface)',
            }} />
          )}
        </button>

        {/* Avatar with dropdown */}
        <div style={{ position: 'relative' }}>
          <div
            className="nav-avatar"
            title="User menu"
            onClick={() => setShowMenu(v => !v)}
            style={{ cursor: 'pointer' }}
          >
            <span style={{ fontSize: 10, fontWeight: 700, color: '#fff' }}>{initials}</span>
          </div>

          {showMenu && (
            <>
              {/* backdrop */}
              <div
                style={{ position: 'fixed', inset: 0, zIndex: 99 }}
                onClick={() => setShowMenu(false)}
              />
              {/* dropdown */}
              <div style={{
                position: 'absolute', top: 'calc(100% + 8px)', right: 0,
                zIndex: 100,
                background: 'var(--bg-card)', border: '1px solid var(--border)',
                borderRadius: 10, padding: '6px',
                minWidth: 190,
                boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
              }}>
                {/* user info */}
                <div style={{ padding: '8px 10px 10px', borderBottom: '1px solid var(--border)', marginBottom: 4 }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {user?.username || user?.email || 'User'}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 1 }}>
                    {user?.email || ''}
                  </div>
                </div>
                {/* profile option */}
                <button
                  onClick={() => { navigate('/settings'); setShowMenu(false) }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    width: '100%', padding: '7px 10px', borderRadius: 7,
                    background: 'transparent', border: 'none',
                    fontSize: 12, color: 'var(--text-muted)',
                    cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-card-hover)'; e.currentTarget.style.color = 'var(--text-primary)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)' }}
                >
                  <User size={13} /> Settings
                </button>
                {/* logout option */}
                <button
                  onClick={handleLogout}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    width: '100%', padding: '7px 10px', borderRadius: 7,
                    background: 'transparent', border: 'none',
                    fontSize: 12, color: 'var(--red)',
                    cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                >
                  <LogOut size={13} /> Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
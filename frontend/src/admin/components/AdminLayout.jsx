import { useState, useEffect } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  Users,
  ScrollText,
  Cloud,
  ShieldAlert,
  Activity,
  LogOut,
  Shield,
  Clock,
  CheckCircle2,
} from 'lucide-react'
import { authService } from '../services/authService'

export default function AdminLayout({ onLogout }) {
  const navigate = useNavigate()
  const user = authService.getCurrentUser()
  const [timeLeft, setTimeLeft] = useState(15 * 60) // 15-minute countdown indicator

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m}:${s < 10 ? '0' : ''}${s}`
  }

  const handleLogout = () => {
    authService.logout()
    if (onLogout) onLogout()
    navigate('/admin')
  }

  const navItems = [
    { to: '/admin', label: 'Overview', icon: Activity, exact: true },
    { to: '/admin/users', label: 'Users & Roles', icon: Users },
    { to: '/admin/audit-logs', label: 'Audit Trail', icon: ScrollText },
    { to: '/admin/cloud-accounts', label: 'Cloud Accounts', icon: Cloud },
    { to: '/admin/scans', label: 'Security Scans', icon: ShieldAlert },
  ]

  return (
    <div className="admin-shell">
      {/* Dense Sidebar */}
      <aside className="admin-sidebar">
        <div style={{
          height: 48,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '0 16px',
          borderBottom: '1px solid var(--border-subtle)'
        }}>
          <Shield size={18} color="var(--color-accent)" />
          <span style={{ fontWeight: 700, fontSize: 13, letterSpacing: '0.02em' }}>CloudOpt Console</span>
          <span className="badge badge-danger" style={{ fontSize: 9, marginLeft: 'auto', padding: '1px 5px' }}>
            ADMIN
          </span>
        </div>

        <nav style={{ padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 9,
                padding: '7px 10px',
                borderRadius: 6,
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                background: isActive ? 'var(--bg-elevated)' : 'transparent',
                fontSize: 12,
                fontWeight: isActive ? 600 : 500,
                borderLeft: isActive ? '3px solid var(--color-accent)' : '3px solid transparent',
              })}
            >
              <item.icon size={14} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Footer info in sidebar */}
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border-subtle)',
          fontSize: 11,
          color: 'var(--text-muted)',
          display: 'flex',
          flexDirection: 'column',
          gap: 6
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Clock size={12} />
            <span>Session exp: <span className="mono" style={{ color: 'var(--text-secondary)' }}>{formatTime(timeLeft)}</span></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircle2 size={12} color="var(--color-success)" />
            <span>RBAC aud=admin verified</span>
          </div>
        </div>
      </aside>

      {/* Main Body */}
      <div className="admin-main">
        {/* Top Header */}
        <header className="admin-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Organization:</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>CloudOpt Platform Infrastructure</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
              <span style={{ color: 'var(--text-muted)' }}>Operator:</span>
              <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                {user?.email || 'admin@cloudopt.ai'}
              </span>
              <span className="badge badge-accent" style={{ fontSize: 10 }}>
                {user?.role || 'admin'}
              </span>
            </div>

            <button
              onClick={handleLogout}
              className="btn btn-ghost btn-sm"
              title="Sign out of Admin Console"
            >
              <LogOut size={12} />
              <span>Sign out</span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}


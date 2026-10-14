import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, DollarSign, ShieldCheck, Lightbulb, Settings, Zap, LogOut, ChevronRight } from 'lucide-react'
import useCloudStore from '../store/cloudStore'
import useAuthStore from '../store/authStore'
import toast from 'react-hot-toast'
import Logo from './common/Logo'

function LogoutButton() {
  const navigate = useNavigate()
  const { logout } = useAuthStore()

  function handleLogout() {
    logout()
    toast.success('Logged out successfully')
    navigate('/login')
  }

  return (
    <button
      onClick={handleLogout}
      style={{
        display: 'flex', alignItems: 'center', gap: 8,
        width: '100%', padding: '8px 10px', borderRadius: 7,
        background: 'transparent',
        border: '1px solid var(--border)',
        fontSize: 12, fontWeight: 600,
        color: 'var(--text-muted)',
        cursor: 'pointer',
        transition: 'all 0.18s ease',
        fontFamily: 'inherit',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = 'rgba(239,68,68,0.08)'
        e.currentTarget.style.borderColor = 'rgba(239,68,68,0.3)'
        e.currentTarget.style.color = 'var(--red)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'transparent'
        e.currentTarget.style.borderColor = 'var(--border)'
        e.currentTarget.style.color = 'var(--text-muted)'
      }}
    >
      <LogOut size={13} />
      Sign out
    </button>
  )
}

export default function Sidebar() {
  const { alerts, dismissedAlerts } = useCloudStore()
  const { user } = useAuthStore()
  const activeAlerts = alerts.filter(a => !dismissedAlerts.includes(a.id))
  const criticalCount = activeAlerts.filter(a => a.type === 'critical').length

  const navItems = [
    { to: '/dashboard',       icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/cost-analysis',   icon: DollarSign,      label: 'Cost Analysis' },
    { to: '/security',        icon: ShieldCheck,     label: 'Security Audit',  badge: activeAlerts.length, badgeColor: criticalCount > 0 ? 'var(--red)' : 'var(--yellow)' },
    { to: '/recommendations', icon: Lightbulb,       label: 'Recommendations', badge: 6 },
    { to: '/settings',        icon: Settings,        label: 'Settings' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <Logo size="md" subText="FinOps & SecOps" />
      </div>

      <div style={{
        padding: '10px 12px',
        margin: '8px 10px 6px',
        borderRadius: 8,
        background: 'var(--bg-elevated, rgba(255,255,255,0.03))',
        border: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <div style={{
          width: 22, height: 22, borderRadius: 5,
          background: 'linear-gradient(135deg, #2563eb, #38bdf8)',
          color: '#fff', fontSize: 10, fontWeight: 800,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0
        }}>
          P
        </div>
        <div style={{ flex: 1, minWidth: 0, textAlign: 'left' }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            Production Cloud
          </div>
          <div style={{ fontSize: 9.5, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
            AWS · GCP · Azure
          </div>
        </div>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: 'var(--green, #22c55e)',
          boxShadow: '0 0 6px rgba(34,197,94,0.6)',
          flexShrink: 0
        }} title="3 providers live" />
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ to, icon, label, badge, badgeColor }) => (
          <NavLink key={to} to={to} className={({ isActive }) => isActive ? 'active' : ''}>
            {createElement(icon, { size: 14 })}
            <span style={{ flex: 1 }}>{label}</span>
            {badge > 0 && (
              <span style={{
                fontSize: 10, fontWeight: 700,
                padding: '1px 6px', borderRadius: 99,
                background: badgeColor ? `${badgeColor}22` : 'var(--accent-dim)',
                color: badgeColor || 'var(--accent)',
                border: `1px solid ${badgeColor ? `${badgeColor}44` : 'var(--accent-glow)'}`,
                fontFamily: 'JetBrains Mono, monospace',
                lineHeight: 1.6,
              }}>
                {badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom section: AI status + logout */}
      <div style={{ padding: '10px 18px', borderTop: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '7px 10px', borderRadius: 7,
          background: 'var(--green-dim)', border: '1px solid rgba(46,204,142,0.2)',
          fontSize: 11, color: 'var(--green)', fontWeight: 500,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'var(--green)',
            boxShadow: '0 0 6px var(--green)',
            animation: 'pulse 2s ease-in-out infinite',
            flexShrink: 0,
          }} />
          AI Engine Active
        </div>
        <LogoutButton />
      </div>

      <div className="sidebar-footer">v1.0.0 · 3 providers connected</div>
    </aside>
  )
}
import { createElement } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import { ArrowLeft, Home, LayoutDashboard } from 'lucide-react'

export default function NotFound() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  const destination = isAuthenticated ? '/dashboard' : '/'
  const label = isAuthenticated ? 'Go to Dashboard' : 'Return to Home'
  const Icon = isAuthenticated ? LayoutDashboard : Home

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-bg-base, #07090e)',
        color: 'var(--color-text-primary, #f1f5f9)',
        fontFamily: "'Outfit', sans-serif",
        padding: '24px',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          fontFamily: "'Space Mono', monospace",
          fontSize: '72px',
          fontWeight: 800,
          color: 'var(--color-accent, #3b82f6)',
          lineHeight: 1,
          marginBottom: '16px',
        }}
      >
        404
      </div>
      <h1
        style={{
          fontFamily: "'Syne', sans-serif",
          fontSize: '28px',
          fontWeight: 700,
          marginBottom: '12px',
        }}
      >
        Page Not Found
      </h1>
      <p
        style={{
          fontSize: '15px',
          color: 'var(--color-text-muted, #94a3b8)',
          maxWidth: '440px',
          marginBottom: '32px',
          lineHeight: 1.5,
        }}
      >
        The page you are looking for doesn't exist, has been removed, or was relocated.
      </p>

      <div style={{ display: 'flex', gap: '12px' }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            borderRadius: '8px',
            background: 'var(--color-bg-surface, #0e111a)',
            color: 'var(--color-text-primary, #f1f5f9)',
            border: '1px solid var(--color-border-default, #1e2638)',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'inherit',
          }}
        >
          <ArrowLeft size={16} /> Back
        </button>

        <button
          onClick={() => navigate(destination)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            borderRadius: '8px',
            background: 'var(--color-accent, #3b82f6)',
            color: '#fff',
            border: 'none',
            fontSize: '14px',
            fontWeight: 600,
            cursor: 'pointer',
            fontFamily: 'inherit',
            boxShadow: '0 4px 14px rgba(59,130,246,0.3)',
          }}
        >
          <Icon size={16} /> {label}
        </button>
      </div>
    </div>
  )
}


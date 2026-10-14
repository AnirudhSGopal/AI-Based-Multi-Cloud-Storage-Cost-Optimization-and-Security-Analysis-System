import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, KeyRound, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { authService } from '../services/authService'

export default function AdminLogin({ onLoginSuccess }) {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  const handleLogin = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    setLoading(true)

    try {
      await authService.login(email, password, totpCode)
      toast.success('Admin authentication verified')
      if (onLoginSuccess) {
        onLoginSuccess()
      } else {
        navigate('/admin')
      }
    } catch (err) {
      const status = err.response?.status
      const msg = err.response?.data?.error || 'Authentication failed. Please check credentials.'
      if (status === 429) {
        setErrorMsg('Too many attempts or temporary lockout active. Please wait 15 minutes before retrying.')
      } else {
        setErrorMsg(msg)
      }
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(ellipse at 50% 20%, #172554 0%, #090d16 65%)',
      padding: 20
    }}>
      <div style={{
        width: '100%',
        maxWidth: 400,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-default)',
        borderRadius: 12,
        padding: 32,
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            background: 'var(--color-accent-subtle)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-accent)'
          }}>
            <Shield size={20} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)' }}>CloudOpt Management</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Authorized personnel only</div>
          </div>
        </div>

        {errorMsg && (
          <div style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 8,
            padding: 10,
            borderRadius: 6,
            background: 'var(--color-danger-subtle)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: 'var(--color-danger)',
            fontSize: 12,
            marginBottom: 16
          }}>
            <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 }}>
              ADMINISTRATOR EMAIL
            </label>
            <input
              type="email"
              className="input"
              style={{ width: '100%' }}
              placeholder="admin@cloudopt.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 }}>
              PASSWORD
            </label>
            <input
              type="password"
              className="input"
              style={{ width: '100%' }}
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
              <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>
                MFA / TOTP CODE
              </label>
              <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Optional if unenrolled</span>
            </div>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="input mono"
                style={{ width: '100%', letterSpacing: '0.2em' }}
                placeholder="000 000"
                maxLength={6}
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
              />
              <KeyRound size={13} style={{ position: 'absolute', right: 10, top: 9, color: 'var(--text-muted)' }} />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', height: 36, marginTop: 8 }}
          >
            {loading ? 'Authenticating...' : 'Sign In to Console'}
          </button>
        </form>

        <div style={{ marginTop: 24, paddingTop: 14, borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
            All actions, authentication events, and IP addresses are recorded in immutable audit logs.
          </span>
        </div>
      </div>
    </div>
  )
}


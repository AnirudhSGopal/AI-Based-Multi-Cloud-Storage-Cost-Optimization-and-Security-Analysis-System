import { useState, useEffect } from 'react'
import { adminApi } from '../services/api'
import { Users, Cloud, ShieldAlert, ScrollText, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Overview() {
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsRes, healthRes] = await Promise.all([
        adminApi.get('/stats'),
        adminApi.get('/system-health'),
      ])
      setStats(statsRes.data)
      setHealth(healthRes.data)
    } catch (err) {
      toast.error('Failed to load system metrics: ' + (err.response?.data?.error || err.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700 }}>System Overview & Oversight</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Real-time telemetry and infrastructure state</p>
        </div>
        <button onClick={loadData} className="btn btn-secondary btn-sm" disabled={loading}>
          <RefreshCw size={12} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Stat Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 14, marginBottom: 24 }}>
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>TOTAL TENANT USERS</span>
            <Users size={16} color="var(--color-accent)" />
          </div>
          <div style={{ fontSize: 24, fontWeight: 700 }} className="mono">
            {stats?.total_users ?? (loading ? '—' : '0')}
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-success)', marginTop: 4 }}>
            {stats?.active_users ?? 0} active accounts
          </div>
        </div>

        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>CLOUD ACCOUNTS</span>
            <Cloud size={16} color="#38bdf8" />
          </div>
          <div style={{ fontSize: 24, fontWeight: 700 }} className="mono">
            {stats?.total_cloud_accounts ?? (loading ? '—' : '0')}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            AWS, GCP, Azure connected
          </div>
        </div>

        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>SCANS EXECUTED</span>
            <ShieldAlert size={16} color="var(--color-warning)" />
          </div>
          <div style={{ fontSize: 24, fontWeight: 700 }} className="mono">
            {stats?.total_scans ?? (loading ? '—' : '0')}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
            Static code & dependency audits
          </div>
        </div>

        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>AUDIT LOG RECORDS</span>
            <ScrollText size={16} color="#a855f7" />
          </div>
          <div style={{ fontSize: 24, fontWeight: 700 }} className="mono">
            {stats?.total_audit_events ?? 'Live'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-success)', marginTop: 4 }}>
            Append-only trigger active
          </div>
        </div>
      </div>

      {/* System Health Diagnostics */}
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 8, padding: 18 }}>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Infrastructure Health & Connectivity</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
          {health?.checks ? (
            Object.entries(health.checks).map(([service, status]) => (
              <div key={service} style={{
                padding: 12,
                borderRadius: 6,
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {status?.status === 'ok' ? (
                    <CheckCircle size={16} color="var(--color-success)" />
                  ) : (
                    <AlertCircle size={16} color="var(--color-danger)" />
                  )}
                  <span style={{ fontWeight: 600, fontSize: 12, textTransform: 'capitalize' }}>{service}</span>
                </div>
                <span className={`badge ${status?.status === 'ok' ? 'badge-success' : 'badge-danger'}`}>
                  {status?.status === 'ok' ? 'HEALTHY' : 'DEGRADED'}
                </span>
              </div>
            ))
          ) : (
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Awaiting telemetry handshake...</div>
          )}
        </div>
      </div>
    </div>
  )
}


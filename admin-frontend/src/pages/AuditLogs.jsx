import { useState, useEffect } from 'react'
import { adminApi } from '../services/api'
import { Search, Filter, ShieldCheck, FileJson, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function AuditLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [eventTypeFilter, setEventTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [selectedLog, setSelectedLog] = useState(null)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const res = await adminApi.get('/audit-logs', {
        params: {
          event_type: eventTypeFilter || undefined,
          status: statusFilter || undefined,
          page,
          per_page: 20,
        },
      })
      setLogs(res.data.logs || [])
      setTotalPages(res.data.pages || 1)
    } catch (err) {
      toast.error('Failed to load audit logs: ' + (err.response?.data?.error || err.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [page, eventTypeFilter, statusFilter])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h1 style={{ fontSize: 18, fontWeight: 700 }}>Immutable Platform Audit Trail</h1>
            <span className="badge badge-success" style={{ fontSize: 10 }}>
              <ShieldCheck size={11} /> Append-Only
            </span>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Cryptographically sealed, append-only PostgreSQL ledger of administrative and security events
          </p>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 10 }}>
          <select
            className="select"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Statuses</option>
            <option value="success">Success</option>
            <option value="denied">Denied</option>
          </select>

          <select
            className="select"
            value={eventTypeFilter}
            onChange={(e) => { setEventTypeFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Event Types</option>
            <option value="admin.login_success">admin.login_success</option>
            <option value="admin.login_failed">admin.login_failed</option>
            <option value="admin.access_denied">admin.access_denied</option>
            <option value="admin.reauth_failed">admin.reauth_failed</option>
            <option value="admin.reauth_locked">admin.reauth_locked</option>
            <option value="user.update">user.update</option>
            <option value="user.delete">user.delete</option>
            <option value="auth.refresh_token_reuse">auth.refresh_token_reuse</option>
          </select>
        </div>
      </div>

      {/* Dense 36px Table */}
      <div className="table-container">
        <table className="dense-table">
          <thead>
            <tr>
              <th style={{ width: 170 }}>Timestamp (UTC)</th>
              <th>Event Type</th>
              <th>Status</th>
              <th>Actor</th>
              <th>Target</th>
              <th>IP Address</th>
              <th style={{ textAlign: 'right' }}>Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', height: 60 }}>
                  Loading immutable audit events...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', height: 60 }}>
                  No audit log entries found.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                    {log.created_at ? new Date(log.created_at).toISOString().replace('T', ' ').slice(0, 19) : '—'}
                  </td>
                  <td>
                    <span className="mono" style={{ fontWeight: 600 }}>{log.event_type}</span>
                  </td>
                  <td>
                    <span className={`badge ${log.status === 'success' ? 'badge-success' : 'badge-danger'}`}>
                      {log.status}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className="mono">{log.actor_email || (log.actor_id ? `ID #${log.actor_id}` : 'Anonymous')}</span>
                      <span className="badge badge-neutral" style={{ fontSize: 10 }}>{log.actor_role}</span>
                    </div>
                  </td>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>
                    {log.target_type ? `${log.target_type}:${log.target_id}` : '—'}
                  </td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                    {log.ip_address || '—'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="btn btn-ghost btn-sm"
                      title="Inspect Details"
                    >
                      <FileJson size={12} />
                      <span>Inspect</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 10, marginTop: 14, fontSize: 12 }}>
        <span style={{ color: 'var(--text-muted)' }}>Page {page} of {totalPages}</span>
        <button
          className="btn btn-secondary btn-sm"
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </button>
        <button
          className="btn btn-secondary btn-sm"
          disabled={page >= totalPages}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>

      {/* Details JSON Modal */}
      {selectedLog && (
        <div className="modal-backdrop">
          <div className="modal-dialog" style={{ maxWidth: 540 }}>
            <div className="modal-header">
              <span style={{ fontWeight: 700, fontSize: 13 }}>Audit Event #{selectedLog.id} — {selectedLog.event_type}</span>
              <button onClick={() => setSelectedLog(null)} className="btn btn-ghost btn-sm">✕</button>
            </div>
            <div className="modal-body">
              <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: 8, fontSize: 12 }}>
                <span style={{ color: 'var(--text-muted)' }}>Event:</span>
                <span className="mono">{selectedLog.event_type}</span>
                <span style={{ color: 'var(--text-muted)' }}>Status:</span>
                <span>{selectedLog.status}</span>
                <span style={{ color: 'var(--text-muted)' }}>Timestamp:</span>
                <span className="mono">{selectedLog.created_at}</span>
                <span style={{ color: 'var(--text-muted)' }}>Actor:</span>
                <span className="mono">{selectedLog.actor_email} (Role: {selectedLog.actor_role}, ID: {selectedLog.actor_id})</span>
                <span style={{ color: 'var(--text-muted)' }}>Client IP:</span>
                <span className="mono">{selectedLog.ip_address}</span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  SANITIZED EVENT DETAILS (JSON)
                </label>
                <pre style={{
                  background: 'var(--bg-base)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 6,
                  padding: 12,
                  fontSize: 11,
                  maxHeight: 200,
                  overflow: 'auto',
                  fontFamily: 'var(--font-mono)',
                  color: '#93c5fd'
                }}>
                  {JSON.stringify(selectedLog.details, null, 2)}
                </pre>
              </div>
            </div>
            <div className="modal-footer">
              <button onClick={() => setSelectedLog(null)} className="btn btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}


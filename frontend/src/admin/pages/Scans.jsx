import { useState, useEffect } from 'react'
import { adminApi } from '../services/api'
import { ShieldAlert, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Scans() {
  const [scans, setScans] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const fetchScans = async () => {
    setLoading(true)
    try {
      const res = await adminApi.get('/scans', {
        params: {
          status: statusFilter || undefined,
          page,
          per_page: 15,
        },
      })
      setScans(res.data.scans || [])
      setTotalPages(res.data.pages || 1)
    } catch (err) {
      toast.error('Failed to load security scans: ' + (err.response?.data?.error || err.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchScans()
  }, [page, statusFilter])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700 }}>Tenant Security Scans</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Static analysis and dependency vulnerability scan jobs</p>
        </div>

        {/* Status Filter */}
        <div>
          <select
            className="select"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Dense 36px Table */}
      <div className="table-container">
        <table className="dense-table">
          <thead>
            <tr>
              <th style={{ width: 60 }}>ID</th>
              <th>Repository</th>
              <th>Branch</th>
              <th>Requested By</th>
              <th>Status</th>
              <th>Findings</th>
              <th>Submitted</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', height: 60 }}>
                  Loading security scan jobs...
                </td>
              </tr>
            ) : scans.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', height: 60 }}>
                  No security scans found.
                </td>
              </tr>
            ) : (
              scans.map((scan) => (
                <tr key={scan.id}>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>#{scan.id}</td>
                  <td className="mono" style={{ fontWeight: 500 }}>{scan.repo_url}</td>
                  <td className="mono">{scan.branch}</td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>User #{scan.requested_by}</td>
                  <td>
                    <span className={`badge ${
                      scan.status === 'completed'
                        ? 'badge-success'
                        : scan.status === 'failed'
                        ? 'badge-danger'
                        : scan.status === 'running'
                        ? 'badge-accent'
                        : 'badge-neutral'
                    }`}>
                      {scan.status}
                    </span>
                  </td>
                  <td className="mono">
                    <span style={{ color: scan.findings_count > 0 ? 'var(--color-warning)' : 'var(--text-muted)' }}>
                      {scan.findings_count ?? 0} issues
                    </span>
                  </td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                    {scan.created_at ? new Date(scan.created_at).toLocaleString() : '—'}
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
    </div>
  )
}


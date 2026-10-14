import { useState, useEffect } from 'react'
import { adminApi } from '../services/api'
import { Cloud, Search } from 'lucide-react'
import toast from 'react-hot-toast'

export default function CloudAccounts() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [providerFilter, setProviderFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const fetchAccounts = async () => {
    setLoading(true)
    try {
      const res = await adminApi.get('/cloud-accounts', {
        params: {
          provider: providerFilter || undefined,
          status: statusFilter || undefined,
          page,
          per_page: 15,
        },
      })
      setAccounts(res.data.accounts || [])
      setTotalPages(res.data.pages || 1)
    } catch (err) {
      toast.error('Failed to load cloud accounts: ' + (err.response?.data?.error || err.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAccounts()
  }, [page, providerFilter, statusFilter])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700 }}>Tenant Cloud Accounts</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Multi-cloud tenant connections (AWS, GCP, Azure)</p>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 10 }}>
          <select
            className="select"
            value={providerFilter}
            onChange={(e) => { setProviderFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Providers</option>
            <option value="aws">AWS</option>
            <option value="gcp">GCP</option>
            <option value="azure">Azure</option>
          </select>

          <select
            className="select"
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Statuses</option>
            <option value="connected">Connected</option>
            <option value="pending">Pending</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      {/* Dense 36px Table */}
      <div className="table-container">
        <table className="dense-table">
          <thead>
            <tr>
              <th style={{ width: 60 }}>ID</th>
              <th>Provider</th>
              <th>Account Label</th>
              <th>Owner User ID</th>
              <th>Status</th>
              <th>Storage Size</th>
              <th>Connected</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', height: 60 }}>
                  Loading tenant cloud accounts...
                </td>
              </tr>
            ) : accounts.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', height: 60 }}>
                  No cloud accounts found.
                </td>
              </tr>
            ) : (
              accounts.map((acc) => (
                <tr key={acc.id}>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>#{acc.id}</td>
                  <td>
                    <span className="mono" style={{ textTransform: 'uppercase', fontWeight: 600 }}>
                      {acc.provider}
                    </span>
                  </td>
                  <td style={{ fontWeight: 500 }}>{acc.account_label || 'Default Account'}</td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>User #{acc.user_id}</td>
                  <td>
                    <span className={`badge ${acc.status === 'connected' ? 'badge-success' : acc.status === 'error' ? 'badge-danger' : 'badge-warning'}`}>
                      {acc.status}
                    </span>
                  </td>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>
                    {acc.storage_size_gb ? `${acc.storage_size_gb} GB` : '—'}
                  </td>
                  <td className="mono" style={{ color: 'var(--text-secondary)' }}>
                    {acc.created_at ? new Date(acc.created_at).toLocaleDateString() : '—'}
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


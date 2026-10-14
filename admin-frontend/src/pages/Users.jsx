import { useState, useEffect } from 'react'
import { adminApi } from '../services/api'
import { Search, UserCheck, UserX, Trash2, Shield, AlertTriangle, Key } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Users() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  // Modals state
  const [editModalUser, setEditModalUser] = useState(null)
  const [newRole, setNewRole] = useState('')
  const [newStatus, setNewStatus] = useState(true)
  const [adminPassword, setAdminPassword] = useState('')

  const [deleteModalUser, setDeleteModalUser] = useState(null)
  const [deleteConfirmEmail, setDeleteConfirmEmail] = useState('')
  const [deleteAdminPassword, setDeleteAdminPassword] = useState('')
  const [actionLoading, setActionLoading] = useState(false)

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const res = await adminApi.get('/users', {
        params: {
          search,
          role: roleFilter || undefined,
          page,
          per_page: 15,
        },
      })
      setUsers(res.data.users || [])
      setTotalPages(res.data.pages || 1)
    } catch (err) {
      toast.error('Failed to load users: ' + (err.response?.data?.error || err.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [page, roleFilter])

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    setPage(1)
    fetchUsers()
  }

  const openEditModal = (u) => {
    setEditModalUser(u)
    setNewRole(u.role)
    setNewStatus(u.is_active)
    setAdminPassword('')
  }

  const handleUpdateUser = async (e) => {
    e.preventDefault()
    if (!adminPassword) {
      toast.error('Admin password is required to confirm mutation.')
      return
    }
    setActionLoading(true)
    try {
      await adminApi.patch(`/users/${editModalUser.id}`, {
        role: newRole,
        is_active: newStatus,
        admin_password: adminPassword,
      })
      toast.success(`User ${editModalUser.email} updated successfully`)
      setEditModalUser(null)
      fetchUsers()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to update user')
    } finally {
      setActionLoading(false)
    }
  }

  const openDeleteModal = (u) => {
    setDeleteModalUser(u)
    setDeleteConfirmEmail('')
    setDeleteAdminPassword('')
  }

  const handleDeleteUser = async (e) => {
    e.preventDefault()
    if (deleteConfirmEmail.trim().toLowerCase() !== deleteModalUser.email.trim().toLowerCase()) {
      toast.error('Typed email does not match user email.')
      return
    }
    if (!deleteAdminPassword) {
      toast.error('Admin password is required to delete user.')
      return
    }
    setActionLoading(true)
    try {
      await adminApi.delete(`/users/${deleteModalUser.id}?confirm=true`, {
        data: { admin_password: deleteAdminPassword },
      })
      toast.success(`User ${deleteModalUser.email} permanently deleted`)
      setDeleteModalUser(null)
      fetchUsers()
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to delete user')
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700 }}>Tenant User Management</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Role assignment, access control, and account states</p>
        </div>

        {/* Filter / Search Bar */}
        <div style={{ display: 'flex', gap: 10 }}>
          <select
            className="select"
            value={roleFilter}
            onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
          >
            <option value="">All Roles</option>
            <option value="admin">Admin</option>
            <option value="analyst">Analyst</option>
            <option value="viewer">Viewer</option>
          </select>

          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: 6 }}>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="input"
                placeholder="Search email/username..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ width: 220, paddingLeft: 28 }}
              />
              <Search size={13} style={{ position: 'absolute', left: 9, top: 9, color: 'var(--text-muted)' }} />
            </div>
            <button type="submit" className="btn btn-secondary btn-sm">Filter</button>
          </form>
        </div>
      </div>

      {/* Dense 36px Table */}
      <div className="table-container">
        <table className="dense-table">
          <thead>
            <tr>
              <th style={{ width: 60 }}>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', height: 60 }}>
                  Loading tenant users...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', height: 60 }}>
                  No users found matching query.
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id}>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>#{u.id}</td>
                  <td style={{ fontWeight: 600 }}>{u.username}</td>
                  <td className="mono">{u.email}</td>
                  <td>
                    <span className={`badge ${u.role === 'admin' ? 'badge-accent' : u.role === 'analyst' ? 'badge-warning' : 'badge-neutral'}`}>
                      {u.role}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${u.is_active ? 'badge-success' : 'badge-danger'}`}>
                      {u.is_active ? 'Active' : 'Suspended'}
                    </span>
                  </td>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-flex', gap: 6 }}>
                      <button
                        onClick={() => openEditModal(u)}
                        className="btn btn-secondary btn-sm"
                        title="Edit Role or Status"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => openDeleteModal(u)}
                        className="btn btn-ghost btn-sm"
                        style={{ color: 'var(--color-danger)' }}
                        title="Delete User"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
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

      {/* Role / Status Edit Modal */}
      {editModalUser && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <span style={{ fontWeight: 700, fontSize: 13 }}>Modify Account: {editModalUser.email}</span>
              <button onClick={() => setEditModalUser(null)} className="btn btn-ghost btn-sm">✕</button>
            </div>
            <form onSubmit={handleUpdateUser}>
              <div className="modal-body">
                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 }}>
                    ASSIGNED ROLE
                  </label>
                  <select
                    className="select"
                    style={{ width: '100%' }}
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                  >
                    <option value="viewer">Viewer (Read-only)</option>
                    <option value="analyst">Analyst (Scans & Optimizations)</option>
                    <option value="admin">Administrator (Full Control)</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 }}>
                    ACCOUNT STATUS
                  </label>
                  <select
                    className="select"
                    style={{ width: '100%' }}
                    value={newStatus ? 'active' : 'suspended'}
                    onChange={(e) => setNewStatus(e.target.value === 'active')}
                  >
                    <option value="active">Active (Permitted to sign in)</option>
                    <option value="suspended">Suspended (All sessions revoked)</option>
                  </select>
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 5 }}>
                    <Key size={12} color="var(--color-warning)" />
                    <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>
                      ADMIN PASSWORD RE-ENTRY
                    </label>
                  </div>
                  <input
                    type="password"
                    className="input"
                    style={{ width: '100%' }}
                    placeholder="Enter your admin password"
                    value={adminPassword}
                    onChange={(e) => setAdminPassword(e.target.value)}
                    required
                  />
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                    Password confirmation is required for role modification and privilege changes.
                  </span>
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setEditModalUser(null)} className="btn btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={actionLoading}>
                  {actionLoading ? 'Saving...' : 'Apply Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete User Target-Named Modal */}
      {deleteModalUser && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header" style={{ color: 'var(--color-danger)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <AlertTriangle size={16} />
                <span style={{ fontWeight: 700, fontSize: 13 }}>Confirm Deletion of Tenant Account</span>
              </div>
              <button onClick={() => setDeleteModalUser(null)} className="btn btn-ghost btn-sm">✕</button>
            </div>
            <form onSubmit={handleDeleteUser}>
              <div className="modal-body">
                <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  This action is irreversible. All cloud credentials, metrics, and associated data will be permanently purged.
                </p>

                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 }}>
                    TYPE USER EMAIL TO CONFIRM: <span className="mono" style={{ color: 'var(--color-danger)' }}>{deleteModalUser.email}</span>
                  </label>
                  <input
                    type="text"
                    className="input mono"
                    style={{ width: '100%' }}
                    placeholder={deleteModalUser.email}
                    value={deleteConfirmEmail}
                    onChange={(e) => setDeleteConfirmEmail(e.target.value)}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 }}>
                    ADMIN PASSWORD RE-ENTRY
                  </label>
                  <input
                    type="password"
                    className="input"
                    style={{ width: '100%' }}
                    placeholder="Enter your admin password"
                    value={deleteAdminPassword}
                    onChange={(e) => setDeleteAdminPassword(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" onClick={() => setDeleteModalUser(null)} className="btn btn-secondary">
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={actionLoading || deleteConfirmEmail.trim().toLowerCase() !== deleteModalUser.email.trim().toLowerCase()}
                >
                  {actionLoading ? 'Purging...' : 'Permanently Delete User'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}


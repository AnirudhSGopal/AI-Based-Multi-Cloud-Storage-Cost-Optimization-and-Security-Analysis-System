import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { authService } from './services/authService'
import AdminLogin from './pages/AdminLogin'
import AdminLayout from './components/AdminLayout'
import Overview from './pages/Overview'
import Users from './pages/Users'
import AuditLogs from './pages/AuditLogs'
import CloudAccounts from './pages/CloudAccounts'
import Scans from './pages/Scans'
import './admin.css'

export default function AdminApp() {
  const [isAuthed, setIsAuthed] = useState(() => authService.isAuthenticated())

  if (!isAuthed) {
    return <AdminLogin onLoginSuccess={() => setIsAuthed(true)} />
  }

  return (
    <Routes>
      <Route element={<AdminLayout onLogout={() => setIsAuthed(false)} />}>
        <Route index element={<Overview />} />
        <Route path="users" element={<Users />} />
        <Route path="audit-logs" element={<AuditLogs />} />
        <Route path="cloud-accounts" element={<CloudAccounts />} />
        <Route path="scans" element={<Scans />} />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Route>
    </Routes>
  )
}

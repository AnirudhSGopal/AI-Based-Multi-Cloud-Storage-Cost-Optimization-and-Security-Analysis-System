import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { authService } from './services/authService'
import AdminLogin from './pages/AdminLogin'
import AdminLayout from './components/AdminLayout'
import Overview from './pages/Overview'
import Users from './pages/Users'
import AuditLogs from './pages/AuditLogs'
import CloudAccounts from './pages/CloudAccounts'
import Scans from './pages/Scans'

function RequireAdminAuth({ children }) {
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />
  }
  return children
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<AdminLogin />} />
        <Route
          path="/"
          element={
            <RequireAdminAuth>
              <AdminLayout />
            </RequireAdminAuth>
          }
        >
          <Route index element={<Overview />} />
          <Route path="users" element={<Users />} />
          <Route path="audit-logs" element={<AuditLogs />} />
          <Route path="cloud-accounts" element={<CloudAccounts />} />
          <Route path="scans" element={<Scans />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0f172a',
            color: '#f8fafc',
            border: '1px solid #334155',
            fontFamily: "'Inter', sans-serif",
            fontSize: '12px',
          },
        }}
      />
    </Router>
  )
}


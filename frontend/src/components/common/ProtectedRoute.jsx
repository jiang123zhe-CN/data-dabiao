import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Spin } from 'antd'
import { useAuth } from '../../hooks/useAuth'

export default function ProtectedRoute({ roles }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  // ① 兼容生产（/dam/）与开发（/）两种路径前缀
  const base = location.pathname.startsWith('/dam') ? '/dam' : ''

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!user) return <Navigate to={`${base}/login`} replace />

  if (roles && !roles.includes(user.role)) {
    return <Navigate to={`${base}/`} replace />
  }

  return <Outlet />
}

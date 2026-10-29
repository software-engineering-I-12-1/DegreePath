import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthContext';

export default function AdminRoute() {
  const { user, loading } = useAuth();
  if (loading) return <p className="auth-loading">Loading…</p>;
  if (!user) return <Navigate to="/signin" replace />;
  if (!user.is_staff) return <Navigate to="/" replace />;
  return <Outlet />;
}

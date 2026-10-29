import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p className="auth-loading">Loading…</p>;
  if (!user) return <Navigate to="/signin" replace state={{ from: location }} />;
  return <Outlet />;
}
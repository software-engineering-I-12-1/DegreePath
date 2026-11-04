import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

/** Student-only pages (profile, plans). Admins are sent to their own page. */
export default function StudentRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p className="auth-loading">Loading…</p>;
  if (!user) return <Navigate to="/signin" replace state={{ from: location }} />;
  if (user.is_staff) return <Navigate to="/catalog/import" replace />;
  return <Outlet />;
}
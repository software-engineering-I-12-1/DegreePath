import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import Logo from './Logo';

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <nav className="navbar">
      <Link to="/" className="logo-link" aria-label="DegreePath home">
        <Logo size={32} />
      </Link>
      <span className="navbar-spacer" />
      {user ? (
        <>
          <Link to="/courses">Courses</Link>
          <Link to="/profile">Profile</Link>
          <Link to="/plans">Plans</Link>
          {user.is_staff && <Link to="/catalog/import">Import catalog</Link>}
          <button
            onClick={async () => {
              await logout();
              navigate('/signin');
            }}
          >
            Sign out
          </button>
        </>
      ) : (
        <>
          <Link to="/signin">Sign in</Link>
          <Link to="/register" className="btn">Register</Link>
        </>
      )}
    </nav>
  );
}

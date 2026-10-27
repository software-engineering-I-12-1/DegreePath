import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <nav className="navbar">
      <Link to="/">DegreePath</Link>
      <span className="navbar-spacer" />
      {user ? (
        <>
          <Link to="/profile">Profile</Link>
          <Link to="/plans">Plans</Link>
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
          <Link to="/register">Register</Link>
        </>
      )}
    </nav>
  );
}
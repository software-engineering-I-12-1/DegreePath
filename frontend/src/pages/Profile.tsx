import { useAuth } from '../auth/AuthContext';

export default function Profile() {
  const { user } = useAuth();
  return (
    <main className="auth-card">
      <h1>Your profile</h1>
      <p>Signed in as <strong>{user?.email}</strong></p>
      <p>No completed courses yet.</p>
    </main>
  );
}
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import Logo from '../components/Logo';

export function Home() {
  const { user } = useAuth();
  const [backend, setBackend] = useState<'checking' | 'ok' | 'bad'>('checking');

  useEffect(() => {
    fetch('/api/health/')
      .then((res) => setBackend(res.ok ? 'ok' : 'bad'))
      .catch(() => setBackend('bad'));
  }, []);

  return (
    <>
      <section className="hero">
        <div className="hero-logo">
          <Logo size={72} showText={false} />
        </div>
        <h1>
          Plan your degree. <span>Semester by semester.</span>
        </h1>
        <p>
          DegreePath builds a valid, constraint-aware course roadmap for NYU Computer Science
          students, and explains exactly why when a plan can't work.
        </p>
        <div className="hero-actions">
          {user ? (
            <>
              <Link to="/profile" className="btn">Go to my profile</Link>
              <Link to="/plans" className="btn btn-secondary">My plans</Link>
            </>
          ) : (
            <>
              <Link to="/register" className="btn">Get started</Link>
              <Link to="/signin" className="btn btn-secondary">Sign in</Link>
            </>
          )}
        </div>
      </section>

      <section className="features">
        <div className="feature">
          <h3>Constraint-Based Planning</h3>
          <p>
            Prerequisites, corequisites, seasonal offerings, credit limits and elective pools, solved
            together with Google OR-Tools CP-SAT.
          </p>
        </div>
        <div className="feature">
          <h3>Conflict Explanation</h3>
          <p>
            When graduation on time is impossible, DegreePath pinpoints the smallest set of
            conflicting constraints in plain language.
          </p>
        </div>
        <div className="feature">
          <h3>Independent Validator</h3>
          <p>
            Every plan is double-checked by a separate validator before you see it, so what you get
            is always valid.
          </p>
        </div>
      </section>

      <footer className="site-footer">
        <span className={`status-dot ${backend === 'checking' ? '' : backend}`} />
        {backend === 'ok' ? 'Backend online' : backend === 'bad' ? 'Backend unreachable' : 'Checking backend…'}
        {' · '}NYU Tandon · CS-GY 6063
      </footer>
    </>
  );
}

export default Home;
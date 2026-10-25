import { useState, useEffect } from 'react';
import './App.css';

interface HealthResponse {
  status: string;
  app: string;
  version: string;
  database: string;
}

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/health/')
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data: HealthResponse) => {
        setHealth(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div className="container">
      <header className="header">
        <h1 className="title">🎓 DegreePath</h1>
        <p className="subtitle">
          Automated, Constraint-Aware Academic Planning for NYU Computer Science
        </p>
      </header>

      <div className="status-card">
        <h2>Backend Connection Status</h2>
        {loading && (
          <span className="status-badge loading">Checking backend health...</span>
        )}
        {error && (
          <div>
            <span className="status-badge error">Backend Unreachable</span>
            <p style={{ marginTop: '0.75rem', fontSize: '0.9rem', color: '#dc2626' }}>
              {error}
            </p>
          </div>
        )}
        {health && (
          <div>
            <span className="status-badge healthy">● Connected ({health.status})</span>
            <p style={{ marginTop: '0.75rem', fontSize: '0.9rem' }}>
              App: <strong>{health.app}</strong> | Version: <strong>{health.version}</strong> | Database: <strong>{health.database}</strong>
            </p>
          </div>
        )}
      </div>

      <div className="cards-grid">
        <div className="feature-card">
          <h3>Constraint-Based Planning</h3>
          <p>
            Powered by Google OR-Tools CP-SAT solving prerequisites, corequisites, seasonal term offerings, and credit limits.
          </p>
        </div>
        <div className="feature-card">
          <h3>Conflict Explanation</h3>
          <p>
            Isolates minimal conflict cores (US-12) to explain why a roadmap is infeasible and suggest actionable remedies.
          </p>
        </div>
        <div className="feature-card">
          <h3>Independent Validator</h3>
          <p>
            Guarantees 100% plan validity by double-checking schedules before persistence (NFR-4).
          </p>
        </div>
      </div>
    </div>
  );
}

export default App;

import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiFetch } from '../api';
import ExportCsvButton from '../components/ExportCsvButton';
import './plan.css';

interface SavedPlan {
  id: string;
  name: string;
  created_at: string;
  is_stale: boolean;
  entries: { term: string; course_code: string; title: string; credits: number;
    counted_for?: string | string[] | null }[];
}
export default function Plans() {
  const { planId } = useParams();
  const [plans, setPlans] = useState<SavedPlan[]>([]);
  const [selected, setSelected] = useState<SavedPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setSelected(null);
    setPlans([]);
    const request = planId
      ? apiFetch<SavedPlan>(`/api/plans/${encodeURIComponent(planId)}/`)
      : apiFetch<{ results: SavedPlan[] }>('/api/plans/');
    request.then(data => {
      if (!active || !data) return;
      if ('results' in data) setPlans(data.results);
      else setSelected(data);
    }).catch(reason => {
      if (active) setError(reason instanceof Error ? reason.message : 'Could not load plans.');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [planId]);

  return (
    <main className="auth-card plan-card">
      <h1>{selected?.name ?? 'My plans'}</h1>
      {loading && <p role="status">Loading plans…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && !planId && (
        plans.length ? <ul>{plans.map(plan => (
          <li key={plan.id}>
            <Link to={`/plans/${plan.id}`}>{plan.name}</Link>
            {' · '}{new Date(plan.created_at).toLocaleDateString()}
            {plan.is_stale && <span className="plan-stale-label"> · Out of date</span>}
          </li>
        ))}</ul> : <>
          <p>No plans yet</p>
          <button type="button" disabled>Export CSV</button>
          <Link to="/plans/generate">Generate</Link>
        </>
      )}
      {selected && <>
        <p>Created {new Date(selected.created_at).toLocaleDateString()}</p>
        {selected.is_stale && (
          <div role="alert" className="plan-message plan-stale-warning">
            <p>This plan is out of date because your profile has changed. The saved schedule is shown below.</p>
            <Link to="/plans/generate">Regenerate from your current profile</Link>
          </div>
        )}
        <ExportCsvButton key={selected.id} planId={selected.id} />
        <table className="plan-table">
          <caption>Saved course schedule</caption>
          <thead><tr><th scope="col">Term</th><th scope="col">Course</th><th scope="col">Title</th><th scope="col">Credits</th><th scope="col">Counts toward</th></tr></thead>
          <tbody>{selected.entries.map(entry => (
            <tr key={entry.course_code}>
              <td>{entry.term}</td><td>{entry.course_code}</td><td>{entry.title}</td><td>{entry.credits}</td>
              <td>{Array.isArray(entry.counted_for) ? entry.counted_for.join(', ') : (entry.counted_for ?? '—')}</td>
            </tr>
          ))}</tbody>
        </table>
      </>}
      {planId && <Link to="/plans">Back to my plans</Link>}
    </main>
  );
}

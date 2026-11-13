import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiFetch } from '../api';

interface SavedPlan {
  id: string;
  name: string;
  created_at: string;
  entries: { term: string; course_code: string; title: string; credits: number }[];
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
    <main className="auth-card">
      <h1>{selected?.name ?? 'My plans'}</h1>
      {loading && <p role="status">Loading plans…</p>}
      {error && <p role="alert">{error}</p>}
      {!loading && !error && !planId && (
        plans.length ? <ul>{plans.map(plan => (
          <li key={plan.id}>
            <Link to={`/plans/${plan.id}`}>{plan.name}</Link>
            {' · '}{new Date(plan.created_at).toLocaleDateString()}
          </li>
        ))}</ul> : <>
          <p>No plans yet</p>
          <Link to="/plans/generate">Generate</Link>
        </>
      )}
      {selected && <>
        <p>Created {new Date(selected.created_at).toLocaleDateString()}</p>
        <table>
          <caption>Saved course schedule</caption>
          <thead><tr><th scope="col">Term</th><th scope="col">Course</th><th scope="col">Title</th><th scope="col">Credits</th></tr></thead>
          <tbody>{selected.entries.map(entry => (
            <tr key={entry.course_code}>
              <td>{entry.term}</td><td>{entry.course_code}</td><td>{entry.title}</td><td>{entry.credits}</td>
            </tr>
          ))}</tbody>
        </table>
      </>}
      {planId && <Link to="/plans">Back to my plans</Link>}
    </main>
  );
}

export function GeneratePlan() {
  return <main className="auth-card">
    <h1>Generate a plan</h1>
    <p>Plan generation is awaiting the planner integration.</p>
    <Link to="/profile">Review your profile</Link>
  </main>;
}

import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';

export interface GeneratedPlanEntry {
  term: string;
  course_code: string;
}

export default function SavePlanForm({ entries }: { entries: GeneratedPlanEntry[] }) {
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState('');
  const [error, setError] = useState('');

  useEffect(() => { setSavedId(''); setError(''); }, [entries]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      const plan = await apiFetch<{ id: string }>('/api/plans/', {
        method: 'POST', body: { name, entries },
      });
      setSavedId(plan?.id ?? '');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save the plan.');
    } finally {
      setSaving(false);
    }
  }

  return <form onSubmit={save}>
    <label htmlFor="plan-name">Plan name</label>
    <input id="plan-name" value={name} onChange={event => setName(event.target.value)}
      required maxLength={100} disabled={saving} />
    <button type="submit" disabled={saving || entries.length === 0 || !name.trim()}>
      {saving ? 'Saving…' : 'Save plan'}
    </button>
    {error && <p role="alert">{error}</p>}
    {savedId && <p role="status">Plan saved. <Link to={`/plans/${savedId}`}>Open plan</Link></p>}
  </form>;
}

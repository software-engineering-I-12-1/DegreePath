import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { apiFetch } from '../api';
import './plan.css';
import './compare.css';

interface Scenario {
  credit_limit: number;
  target_term: string;
}

interface Term {
  term: string;
  credits: number;
  courses: { code: string; title: string }[];
}

type Result = { status: 'valid'; terms: Term[] }
  | { status: 'infeasible' | 'timeout'; message: string };
const labels = ['Scenario A', 'Scenario B'];

export default function ComparePlans() {
  const [inputs, setInputs] = useState<Scenario[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    apiFetch<Scenario & { ready: boolean }>('/api/profiles/me/').then(profile => {
      if (!active) return;
      if (!profile?.ready) {
        setError('Complete your profile before comparing scenarios.');
        return;
      }
      const { credit_limit, target_term } = profile;
      setInputs([{ credit_limit, target_term }, { credit_limit: Math.min(credit_limit + 3, 24), target_term }]);
    }).catch(reason => { if (active) setError(reason.message); });
    return () => { active = false; };
  }, []);

  function update(index: number, change: Partial<Scenario>) {
    setInputs(previous => previous.map((input, i) => i === index ? { ...input, ...change } : input));
    setResults([]);
    setError('');
  }

  async function compare(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setResults([]);
    setError('');
    try {
      setResults(await apiFetch<Result[]>('/api/plans/compare/', { method: 'POST', body: inputs }) ?? []);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not compare plans.');
    } finally {
      setBusy(false);
    }
  }

  const schedules = results.map(result => result.status === 'valid'
    ? new Map(result.terms.flatMap(term => term.courses.map(course => [course.code, term.term] as const)))
    : null);
  const [first, second] = schedules;
  const differences = first && second
    ? [...new Set([...first.keys(), ...second.keys()])].filter(code => first.get(code) !== second.get(code))
    : [];

  return <main className="auth-card plan-card">
    <h1>Compare planning scenarios</h1>
    <p>Try different credit limits or target terms using your saved major and completed courses.</p>
    <Link to="/profile">Edit profile</Link>
    {inputs.length === 2 && <form onSubmit={compare}>
      <div className="scenario-columns">
        {inputs.map((input, index) => <fieldset key={labels[index]} disabled={busy}>
          <legend>{labels[index]}</legend>
          <label>Credits per term
            <input type="number" min={1} max={24} required value={input.credit_limit}
              onChange={event => update(index, { credit_limit: Number(event.target.value) })} />
          </label>
          <label>Target term
            <input required placeholder="Spring 2029" maxLength={20} value={input.target_term}
              onChange={event => update(index, { target_term: event.target.value })} />
          </label>
        </fieldset>)}
      </div>
      <button disabled={busy}>{busy ? 'Comparing…' : 'Compare schedules'}</button>
    </form>}
    {error && <p role="alert">{error}</p>}
    <div className="scenario-columns">
      {results.map((result, index) => <section key={labels[index]}>
        <h2>{labels[index]}</h2>
        {result.status === 'valid' ? <>
          <p>{result.terms.reduce((sum, term) => sum + term.credits, 0)} credits scheduled</p>
          {result.terms.filter(term => term.courses.length > 0).map(term => <div key={term.term}>
            <h3>{term.term} ({term.credits} credits)</h3>
            <ul>{term.courses.map(course => <li key={course.code}>{course.code} · {course.title}</li>)}</ul>
          </div>)}
        </> : <p>{result.message}</p>}
      </section>)}
    </div>
    {first && second && <section>
      <h2>Schedule differences</h2>
      {differences.length ? <ul>{differences.map(code => <li key={code}>
        {code} · A: {first.get(code) ?? 'Not scheduled'} · B: {second.get(code) ?? 'Not scheduled'}
      </li>)}</ul> : <p>Both scenarios schedule the same courses in the same terms.</p>}
    </section>}
  </main>;
}

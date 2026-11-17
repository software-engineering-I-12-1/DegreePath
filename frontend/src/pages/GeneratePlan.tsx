import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, apiFetch } from '../api';
import SavePlanForm from '../components/SavePlanForm';
import './plan.css';

interface PlannedCourse {
  code: string;
  title: string;
  credits: number;
  counted_for: string | string[] | null;
}

interface PlanTerm {
  term: string;
  credits: number;
  courses: PlannedCourse[];
}

interface ValidPlan {
  status: 'valid';
  program: string;
  terms: PlanTerm[];
  profile_version: number;
  catalog_version: number;
  unenforced_requirements: string[];
}

interface InfeasiblePlan {
  status: 'infeasible';
  message: string;
}

type GenerateResult = ValidPlan | InfeasiblePlan;

interface Failure {
  code: string;
  message: string;
}

export default function GeneratePlan() {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [failure, setFailure] = useState<Failure | null>(null);
  const entries = useMemo(() => result?.status === 'valid'
    ? result.terms.flatMap(term => term.courses.map(course => ({
      term: term.term, course_code: course.code, counted_for: course.counted_for,
    })))
    : [], [result]);

  async function generate() {
    setBusy(true);
    setResult(null);
    setFailure(null);
    try {
      setResult(await apiFetch<GenerateResult>('/api/plans/generate/', { method: 'POST' }));
    } catch (err) {
      if (err instanceof ApiError) setFailure({ code: err.code, message: err.message });
      else setFailure({ code: '', message: 'Could not reach the server. Please try again.' });
    } finally {
      setBusy(false);
    }
  }

  const total = result?.status === 'valid'
    ? result.terms.reduce((sum, t) => sum + t.credits, 0)
    : 0;

  return (
    <main className="auth-card plan-card">
      <h1>Generate a plan</h1>
      <p className="plan-intro">
        DegreePath builds a semester-by-semester plan from your saved profile: your completed courses,
        major, credit limit and target graduation term. Every plan is checked before it is shown.
      </p>

      <div className="form-actions">
        <button type="button" onClick={generate} disabled={busy}>
          {busy ? 'Planning…' : result ? 'Generate again' : 'Generate plan'}
        </button>
        <Link to="/profile" className="btn btn-secondary">Edit profile</Link>
      </div>

      {busy && <p role="status" className="plan-muted">This can take up to 10 seconds.</p>}

      {failure && (
        <div role="alert" className="form-error plan-message">
          <p>{failure.message}</p>
          {(failure.code === 'PROFILE_INCOMPLETE') && (
            <p><Link to="/profile">Complete your profile</Link> and try again.</p>
          )}
        </div>
      )}

      {result?.status === 'infeasible' && (
        <div role="alert" className="form-error plan-message">
          <p><strong>{result.message}.</strong></p>
          <p>
            Try a later target graduation term or a higher credit limit on your{' '}
            <Link to="/profile">profile</Link>, then generate again.
          </p>
        </div>
      )}

      {result?.status === 'valid' && (
        <section aria-label="Generated plan">
          <p role="status" className="form-success">
            Plan for {result.program}: {result.terms.length} terms, {total} credits.
          </p>
          {result.unenforced_requirements.length > 0 && (
            <p className="plan-note">
              This plan covers your required courses. Not yet included:{' '}
              {result.unenforced_requirements.join(', ')}.
            </p>
          )}
          <ol className="plan-terms">
            {result.terms.map((t) => (
              <li key={t.term} className="plan-term">
                <div className="plan-term-head">
                  <h2>{t.term}</h2>
                  <span className="plan-muted">{t.credits} credits</span>
                </div>
                {t.courses.length === 0 ? (
                  <p className="plan-muted">No courses this term</p>
                ) : (
                  <table className="plan-table">
                    <thead>
                      <tr><th scope="col">Course</th><th scope="col">Title</th><th scope="col">Credits</th><th scope="col">Counts toward</th></tr>
                    </thead>
                    <tbody>
                      {t.courses.map((c) => (
                        <tr key={c.code}>
                          <td className="plan-code">{c.code}</td>
                          <td>{c.title}</td>
                          <td>{c.credits}</td>
                          <td>{Array.isArray(c.counted_for) ? c.counted_for.join(', ') : (c.counted_for ?? '—')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </li>
            ))}
          </ol>
          <SavePlanForm entries={entries} />
        </section>
      )}
    </main>
  );
}

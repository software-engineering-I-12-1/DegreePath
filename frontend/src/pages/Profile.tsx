import { useEffect, useState, type FormEvent, type KeyboardEvent } from 'react';
import { ApiError, apiFetch } from '../api';
import { useAuth } from '../auth/AuthContext';

interface ProfileData {
  id: string | null;
  major: string;
  credit_limit: number | null;
  target_term: string;
  completed_courses: string[];
}

interface Options {
  majors: string[];
  courses: { code: string; title: string }[];
  terms: string[];
}

type Field = 'major' | 'credit_limit' | 'target_term' | 'completed_courses';
type FieldErrors = Partial<Record<Field, string>>;

function normalizeCode(raw: string): string {
  return raw.trim().replace(/\s+/g, ' ').toUpperCase();
}

export default function Profile() {
  const { user } = useAuth();

  const [options, setOptions] = useState<Options>({ majors: [], courses: [], terms: [] });
  const [major, setMajor] = useState('');
  const [creditLimit, setCreditLimit] = useState('');
  const [targetTerm, setTargetTerm] = useState('');
  const [courses, setCourses] = useState<string[]>([]);
  const [courseInput, setCourseInput] = useState('');

  const [snapshot, setSnapshot] = useState<ProfileData | null>(null);
  const [editing, setEditing] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  function applyProfile(p: ProfileData) {
    setMajor(p.major);
    setCreditLimit(p.credit_limit === null ? '' : String(p.credit_limit));
    setTargetTerm(p.target_term);
    setCourses(p.completed_courses);
    setCourseInput('');
    setSnapshot(p);
  }

  useEffect(() => {
    Promise.all([apiFetch<ProfileData>('/api/profile/'), apiFetch<Options>('/api/profile/options/')])
      .then(([profile, opts]) => {
        if (opts) setOptions(opts);
        if (profile) {
          applyProfile(profile);
          setEditing(profile.id === null); // saved profile -> show summary first
        }
      })
      .catch((err) => setFormError(err instanceof Error ? err.message : 'Could not load profile'))
      .finally(() => setLoading(false));
  }, []);

  function addCourse() {
    const code = normalizeCode(courseInput);
    if (code && !courses.includes(code)) setCourses([...courses, code]);
    setCourseInput('');
  }

  function onCourseKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addCourse();
    }
  }

  function cancelEdit() {
    if (snapshot) applyProfile(snapshot);
    setErrors({});
    setFormError(null);
    setEditing(false);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setErrors({});
    setFormError(null);
    setSaved(false);

    const pending = normalizeCode(courseInput);
    const finalCourses = pending && !courses.includes(pending) ? [...courses, pending] : courses;

    setSaving(true);
    try {
      const result = await apiFetch<ProfileData>('/api/profile/', {
        method: 'PUT',
        body: {
          major,
          credit_limit: creditLimit.trim() === '' ? null : Number(creditLimit),
          target_term: targetTerm,
          completed_courses: finalCourses,
        },
      });
      if (result) applyProfile(result);
      setSaved(true);
      setEditing(false);
    } catch (err) {
      if (err instanceof ApiError && Object.keys(err.errors).length > 0) {
        setErrors(err.errors as FieldErrors);
      } else {
        setFormError(err instanceof Error ? err.message : 'Something went wrong');
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="auth-loading">Loading…</p>;

  if (!editing) {
    return (
      <main className="auth-card profile-card">
        <h1>Your profile</h1>
        <p>
          Signed in as <strong>{user?.email}</strong>
        </p>
        {saved && <p role="status" className="form-success">Profile saved</p>}
        <dl className="summary">
          <dt>Major</dt>
          <dd>{major}</dd>
          <dt>Credit limit per term</dt>
          <dd>{creditLimit}</dd>
          <dt>Target graduation term</dt>
          <dd>{targetTerm}</dd>
          <dt>Completed courses</dt>
          <dd>
            {courses.length === 0 ? (
              'None'
            ) : (
              <ul className="chips">
                {courses.map((code) => (
                  <li key={code} className="chip">{code}</li>
                ))}
              </ul>
            )}
          </dd>
        </dl>
        <button
          type="button"
          onClick={() => {
            setSaved(false);
            setEditing(true);
          }}
        >
          Edit profile
        </button>
      </main>
    );
  }

  return (
    <main className="auth-card profile-card">
      <h1>Your profile</h1>
      <p>
        Signed in as <strong>{user?.email}</strong>
      </p>

      <form onSubmit={onSubmit} noValidate>
        <label>
          Major
          <select value={major} onChange={(e) => setMajor(e.target.value)}>
            <option value="">Select a major…</option>
            {options.majors.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          {errors.major && <span role="alert" className="field-error">{errors.major}</span>}
        </label>

        <label>
          Credit limit per term (1–24)
          <input
            type="number"
            inputMode="numeric"
            value={creditLimit}
            onChange={(e) => setCreditLimit(e.target.value)}
          />
          {errors.credit_limit && <span role="alert" className="field-error">{errors.credit_limit}</span>}
        </label>

        <label>
          Target graduation term
          <input
            type="text"
            list="term-options"
            placeholder="Spring 2028"
            value={targetTerm}
            onChange={(e) => setTargetTerm(e.target.value)}
          />
          <datalist id="term-options">
            {options.terms.map((t) => (
              <option key={t} value={t} />
            ))}
          </datalist>
          {errors.target_term && <span role="alert" className="field-error">{errors.target_term}</span>}
        </label>

        <div className="field">
          <label htmlFor="course-input">Completed courses</label>
          <div className="course-add">
            <input
              id="course-input"
              type="text"
              list="course-options"
              placeholder="CS-UY 1134"
              value={courseInput}
              onChange={(e) => setCourseInput(e.target.value)}
              onKeyDown={onCourseKeyDown}
            />
            <button type="button" onClick={addCourse}>Add</button>
          </div>
          <datalist id="course-options">
            {options.courses.map((c) => (
              <option key={c.code} value={c.code}>{c.title}</option>
            ))}
          </datalist>
          {courses.length > 0 && (
            <ul className="chips">
              {courses.map((code) => (
                <li key={code} className="chip">
                  {code}
                  <button
                    type="button"
                    aria-label={`Remove ${code}`}
                    onClick={() => setCourses(courses.filter((c) => c !== code))}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
          {errors.completed_courses && (
            <span role="alert" className="field-error">{errors.completed_courses}</span>
          )}
        </div>

        {formError && <p role="alert" className="form-error">{formError}</p>}

        <div className="form-actions">
          <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button>
          {snapshot?.id && (
            <button type="button" onClick={cancelEdit} disabled={saving}>Cancel</button>
          )}
        </div>
      </form>
    </main>
  );
}
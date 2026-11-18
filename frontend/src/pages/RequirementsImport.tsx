import { useEffect, useState, type FormEvent } from 'react';
import { ApiError, apiFetch } from '../api';

interface RequirementSummary {
  name: string;
  type: 'required' | 'pool' | 'credit_threshold';
  description: string;
  courses: { code: string; title: string; credits: number }[];
}

interface ProgramSummary {
  id: number;
  name: string;
  kind: string;
  max_elective_pools_per_course: number;
  requirements: RequirementSummary[];
}

interface ImportResult {
  message: string;
  summary: ProgramSummary;
}

interface ProgramListItem {
  id: number;
  name: string;
  kind: string;
}

const TYPE_LABELS: Record<RequirementSummary['type'], string> = {
  required: 'Required courses',
  pool: 'Elective pool',
  credit_threshold: 'Credit threshold',
};

export default function RequirementsImport() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [details, setDetails] = useState<ApiError['details']>([]);
  const [programs, setPrograms] = useState<ProgramListItem[]>([]);
  const [summary, setSummary] = useState<ProgramSummary | null>(null);

  async function loadPrograms() {
    try {
      const data = await apiFetch<{ results: ProgramListItem[] }>('/api/programs/');
      setPrograms(data?.results ?? []);
    } catch {
      setPrograms([]);
    }
  }

  useEffect(() => {
    loadPrograms();
  }, []);

  async function showProgram(id: number) {
    setError(null);
    setDetails([]);
    try {
      setSummary(await apiFetch<ProgramSummary>(`/api/programs/${id}/`));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load program');
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    setDetails([]);
    try {
      const body = new FormData();
      body.append('file', file);
      const result = await apiFetch<ImportResult>('/api/admin/requirement-imports/', { method: 'POST', body });
      setMessage(result?.message ?? null);
      setSummary(result?.summary ?? null);
      await loadPrograms();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
      if (err instanceof ApiError) setDetails(err.details);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-card profile-card">
      <h1>Import degree requirements</h1>
      <p>
        Upload a JSON file naming the program and its requirements: required courses, &ldquo;choose N&rdquo;
        pools, and credit thresholds. Optionally set <code>max_elective_pools_per_course</code>
        (1 = single count, 2 = double count). The upload replaces that program&rsquo;s previous requirements.
      </p>
      <form onSubmit={submit}>
        <label htmlFor="requirements-file">Requirements file</label>
        <input id="requirements-file" type="file" accept=".json,application/json"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)} required />
        <button type="submit" disabled={!file || busy}>{busy ? 'Importing…' : 'Import requirements'}</button>
      </form>
      {message && <p role="status" className="form-success">{message}</p>}
      {error && <div role="alert" className="form-error">
        <p>{error}. The previous requirements are unchanged.</p>
        {details.length > 0 && <ul>{details.map((item, index) => <li key={index}>{item.message}</li>)}</ul>}
      </div>}

      {programs.length > 0 && <section aria-label="Degree programs">
        <h2>Programs</h2>
        <ul>{programs.map((program) => (
          <li key={program.id}>
            <button type="button" className="link-button" onClick={() => showProgram(program.id)}>
              {program.name}
            </button> ({program.kind})
          </li>
        ))}</ul>
      </section>}

      {summary && <section aria-label="Requirement summary">
        <h2>{summary.name} requirements</h2>
        <p>
          A course may count toward at most {summary.max_elective_pools_per_course} elective
          pool{summary.max_elective_pools_per_course === 1 ? '' : 's'}.
        </p>
        {summary.requirements.map((rule) => (
          <div key={rule.name}>
            <h3>{rule.name} <small>· {TYPE_LABELS[rule.type]}</small></h3>
            <p>{rule.description}</p>
            {rule.courses.length > 0 && <ul>{rule.courses.map((course) => (
              <li key={course.code}>{course.code} — {course.title} ({course.credits} credits)</li>
            ))}</ul>}
          </div>
        ))}
      </section>}
    </main>
  );
}

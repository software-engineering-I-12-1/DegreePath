import { useState, type FormEvent } from 'react';
import { ApiError, apiFetch } from '../api';

interface ImportResult {
  message: string;
  imported: number;
  created: number;
  updated: number;
}

interface CatalogCourse {
  code: string;
  title: string;
  credits: number;
}

export default function CatalogImport() {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [details, setDetails] = useState<ApiError['details']>([]);
  const [courses, setCourses] = useState<CatalogCourse[]>([]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setResult(null);
    setError(null);
    setDetails([]);
    setCourses([]);
    try {
      const body = new FormData();
      body.append('file', file);
      const imported = await apiFetch<ImportResult>('/api/admin/catalog-imports/', { method: 'POST', body });
      setResult(imported);
      try {
        const catalog = await apiFetch<{ results: CatalogCourse[] }>('/api/courses/');
        setCourses(catalog?.results ?? []);
      } catch {
        setCourses([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
      if (err instanceof ApiError) setDetails(err.details);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-card profile-card">
      <h1>Import course catalog</h1>
      <p>Upload a CSV or JSON file with course code, title, credits, and term offerings.</p>
      <form onSubmit={submit}>
        <label htmlFor="catalog-file">Course file</label>
        <input id="catalog-file" type="file" accept=".csv,.json,text/csv,application/json"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)} required />
        <button type="submit" disabled={!file || busy}>{busy ? 'Importing…' : 'Import courses'}</button>
      </form>
      {result && <p role="status" className="form-success">{result.message} ({result.created} new, {result.updated} updated)</p>}
      {error && <div role="alert" className="form-error">
        <p>{error}. No courses were imported.</p>
        {details.length > 0 && <ul>{details.map((item, index) => (
          <li key={index}>Row {item.row ?? '?'}{item.column ? `, ${item.column}` : ''}: {item.message}</li>
        ))}</ul>}
      </div>}
      {courses.length > 0 && <section aria-label="Catalog courses">
        <h2>Catalog courses</h2>
        <ul>{courses.map((course) => (
          <li key={course.code}>{course.code} — {course.title} ({course.credits} credits)</li>
        ))}</ul>
      </section>}
    </main>
  );
}

import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

interface ExportStatus {
  has_plan: boolean;
  plan_id: string | null;
  name: string | null;
  exportable: boolean;
  reason: string | null;
  course_count: number;
  term_count: number;
}

export default function Plans() {
  const [status, setStatus] = useState<ExportStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ExportStatus>('/api/plan-export/status/')
      .then(setStatus)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load your plan'))
      .finally(() => setLoading(false));
  }, []);

  async function onExport() {
    if (!status?.plan_id) return;
    setError(null);
    setDownloading(true);
    try {
      const res = await fetch(`/api/plan-export/${status.plan_id}/csv/`, { credentials: 'same-origin' });
      if (res.status === 401) {
        window.location.assign('/signin');
        return;
      }
      if (!res.ok) {
        let message = 'Export failed';
        try {
          message = (await res.json())?.error?.message ?? message;
        } catch {
          /* keep default */
        }
        throw new Error(message);
      }
      const url = URL.createObjectURL(await res.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = 'degreepath-plan.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setDownloading(false);
    }
  }

  if (loading) return <p className="auth-loading">Loading…</p>;

  const exportable = status?.exportable ?? false;

  return (
    <main className="auth-card profile-card">
      <h1>Your plans</h1>

      {status?.has_plan ? (
        <p>
          <strong>{status.name}</strong>: {status.course_count} courses over {status.term_count} terms
        </p>
      ) : (
        <p>No saved plans yet.</p>
      )}

      <div className="form-actions">
        <button type="button" onClick={onExport} disabled={!exportable || downloading}>
          {downloading ? 'Exporting…' : 'Export CSV'}
        </button>
      </div>

      {!exportable && status?.reason && (
        <p role="status" className="field-error">Export unavailable: {status.reason}</p>
      )}
      {error && <p role="alert" className="form-error">{error}</p>}
    </main>
  );
}
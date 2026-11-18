import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

interface ExportStatus {
  exportable: boolean;
  reason: string | null;
}

export default function ExportCsvButton({ planId }: { planId: string }) {
  const [status, setStatus] = useState<ExportStatus | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ExportStatus>(`/api/plan-export/status/?plan_id=${planId}`)
      .then(setStatus)
      .catch(() => setStatus({ exportable: false, reason: 'Could not check this plan' }));
  }, [planId]);

  async function onExport() {
    setError(null);
    setDownloading(true);
    try {
      const res = await fetch(`/api/plan-export/${planId}/csv/`, { credentials: 'same-origin' });
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

  const exportable = status?.exportable ?? false;
  return (
    <div>
      <button type="button" onClick={onExport} disabled={!exportable || downloading}>
        {downloading ? 'Exporting…' : 'Export CSV'}
      </button>
      {status && !exportable && status.reason && (
        <p role="status" className="field-error">Export unavailable: {status.reason}</p>
      )}
      {error && <p role="alert" className="form-error">{error}</p>}
    </div>
  );
}
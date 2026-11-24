import { useState } from 'react';

export default function CalendarExport({ planId, terms }: { planId: string; terms: string[] }) {
  const [dates, setDates] = useState<Record<string, string>>({});
  if (!terms.length) return null;

  return <details className="calendar-export">
    <summary>Export registration calendar</summary>
    <p>Enter the registration dates you want to include. Leave unknown dates blank.</p>
    <form action={`/api/plan-export/${encodeURIComponent(planId)}/calendar/`} method="get">
      {terms.map(term => <label key={term}>{term}
        <input type="date" name={term} value={dates[term] ?? ''}
          onChange={event => setDates(previous => ({ ...previous, [term]: event.target.value }))} />
      </label>)}
      <button type="submit" disabled={!terms.some(term => dates[term])}>Download .ics</button>
    </form>
  </details>;
}

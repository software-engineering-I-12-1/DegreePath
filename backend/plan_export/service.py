import csv
import io
from dataclasses import dataclass, field

from profiles import terms

from . import adapters

HEADER = ['term', 'course_code', 'title', 'credits']
_FORMULA_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


@dataclass
class Exportability:
    ok: bool
    reason: str | None = None
    problems: list = field(default_factory=list)


def check_exportable(plan, profile):
    """Exportable only for a persisted plan that passes full validation against the current profile, catalog and rules."""
    if plan is None:
        return Exportability(False, 'No saved plan')
    try:
        problems = adapters.validate_plan(plan['rows'], profile)
    except adapters.ValidationUnavailable as error:
        return Exportability(False, f'Validation unavailable: {error}')
    if problems:
        return Exportability(False, 'Plan fails validation', problems)
    return Exportability(True)


def ordered_rows(rows):
    """Chronological by term (not alphabetical, so Fall 2026 < Spring 2027 < Fall 2027), then by course code."""
    def key(row):
        index = terms.parse_term(str(row['term']))
        return (index if index is not None else float('inf'), row['course_code'])

    out = []
    for row in sorted(rows, key=key):
        index = terms.parse_term(str(row['term']))
        out.append({**row, 'term': terms.format_term(index) if index is not None else row['term']})
    return out


def _safe(value):
    """Stop spreadsheet formula injection: a leading = + - @ would run as a formula in Excel."""
    text = str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def build_csv(rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(HEADER)
    for row in rows:
        writer.writerow([_safe(row['term']), _safe(row['course_code']), _safe(row['title']), int(row['credits'])])
    return buffer.getvalue()
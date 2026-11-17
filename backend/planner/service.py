"""
Validation entry point for saved plans and exports (US-10 save, US-13 export).

validate_entries() reloads the student's current snapshot and runs the same independent
validator that checks every generated plan, so a plan edited in the browser cannot pass.
"""

from .loader import load_snapshot
from .snapshot import PlanEntry, Term
from .validator import validate


def _term(value):
    if isinstance(value, dict):
        value = f"{value.get('season', '')} {value.get('year', '')}"
    return Term.parse(value) if isinstance(value, str) else None


def validate_entries(profile, entries):
    """
    entries: [{"course_code": "CS-UY 1114", "term": "Fall 2027" or {"season", "year"},
               "counted_for": pool name or None}]

    Returns a list of {"code", "course", "message"}; empty means the plan is valid.
    Raises loader.ProfileIncomplete or loader.ProgramNotImported like generation does.
    """
    snapshot = load_snapshot(profile)
    problems = []
    plan = []
    for raw in entries:
        code = str(raw.get('course_code', '')).strip().upper()
        term = _term(raw.get('term'))
        if term is None:
            problems.append({'code': 'INVALID_TERM', 'course': code, 'message': f'{code} has an invalid term'})
            continue
        plan.append(PlanEntry(code, term, raw.get('counted_for') or None))

    problems += [{'code': v.code, 'course': v.course, 'message': v.detail} for v in validate(plan, snapshot)]
    return sorted(problems, key=lambda p: (p['code'], p['course'] or ''))

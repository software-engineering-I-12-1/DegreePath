"""
Bridges plan export to the saved-plan app (US-10) and the shared independent validator (US-09).
Nothing here invents data: no saved plan means no export, and an unavailable validator means no export.
"""

import uuid

from planner.loader import ProfileIncomplete, ProgramNotImported
from planner.service import validate_entries
from plans.models import Plan


class ValidationUnavailable(Exception):
    """The validator cannot run (profile incomplete, or the degree program is not imported)."""


def _to_dict(plan):
    # entries are the snapshot stored at save time: {course_code, term, counted_for, title, credits}
    return {'id': str(plan.id), 'name': plan.name, 'owner_id': plan.user_id, 'rows': plan.entries}


def get_current_plan(user):
    """The student's newest saved plan, or None. Never builds a plan."""
    plan = Plan.objects.filter(user=user).first()  # Plan.Meta.ordering is newest first
    return _to_dict(plan) if plan else None


def get_plan(plan_id):
    """A persisted plan by id (any owner), or None if it does not exist."""
    try:
        pk = uuid.UUID(str(plan_id))
    except ValueError:
        return None
    plan = Plan.objects.filter(pk=pk).first()
    return _to_dict(plan) if plan else None


def validate_plan(rows, profile):
    """Run the shared validator on exactly these rows. Returns problem messages (empty = valid)."""
    if profile is None:
        raise ValidationUnavailable('No student profile')
    try:
        violations = validate_entries(profile, rows)
    except (ProfileIncomplete, ProgramNotImported) as error:
        raise ValidationUnavailable(str(error)) from error
    return [v['message'] for v in violations]
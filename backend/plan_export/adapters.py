"""
STUBS for US-10 (saved plans) and US-09 (plan validator).

When those stories merge, rewrite only get_current_plan(), get_plan() and validate_plan() here.
A plan is a dict: {id, name, feasible, owner_id, rows: [{term, course_code, title, credits}]}.
"""

import uuid

from catalog.models import Course
from profiles import catalog as profile_catalog
from profiles import terms
from profiles.models import Profile


def _build_plan(profile):
    """STUB for US-10: a demo plan filling the student's remaining catalog courses, one term at a time."""
    if not profile.is_ready:
        return None
    done = set(profile.completed_courses)
    courses = [c for c in Course.objects.order_by('code') if c.code not in done]
    if not courses:
        return None

    index = terms.current_term_index()
    rows, used = [], 0
    for course in courses:
        if used and used + course.credits > profile.credit_limit:
            index += 1
            used = 0
        rows.append({
            'term': terms.format_term(index),
            'course_code': course.code,
            'title': course.title,
            'credits': course.credits,
        })
        used += course.credits

    return {
        'id': str(profile.id),  # stub: one plan per student, plan id == profile id
        'name': 'Demo plan (stub)',
        'feasible': True,
        'owner_id': profile.user_id,
        'rows': rows,
    }


def get_current_plan(user):
    """STUB for US-10: the student's saved plan, or None."""
    profile = Profile.objects.filter(user=user).first()
    return _build_plan(profile) if profile else None


def get_plan(plan_id):
    """STUB for US-10: any saved plan by id (any owner), or None if it doesn't exist."""
    try:
        pk = uuid.UUID(str(plan_id))
    except ValueError:
        return None
    profile = Profile.objects.filter(pk=pk).first()
    return _build_plan(profile) if profile else None


def validate_plan(rows, profile):
    """
    STUB for US-09 PlanValidator: returns a list of problems (empty list = valid).
    Checks catalog membership, duplicates, already-completed, term window and the credit limit.
    It does NOT check prerequisites or corequisites; US-09 will.
    """
    if profile is None:
        return ['No student profile']

    problems = []
    completed = set(profile.completed_courses)
    known = profile_catalog.existing_codes({r['course_code'] for r in rows})
    current = terms.current_term_index()
    target = terms.parse_term(profile.target_term) if profile.target_term else None
    seen = set()
    credits_by_term = {}

    for r in rows:
        code = r['course_code']
        if code not in known:
            problems.append(f'{code} is not in the catalog')
        if code in completed:
            problems.append(f'{code} is already completed')
        if code in seen:
            problems.append(f'{code} is scheduled more than once')
        seen.add(code)

        index = terms.parse_term(str(r['term']))
        if index is None:
            problems.append(f'Unknown term "{r["term"]}"')
            continue
        if index < current:
            problems.append(f'{r["term"]} is in the past')
        if target is not None and index > target:
            problems.append(f'{r["term"]} is after the target term {profile.target_term}')
        try:
            credits_by_term[index] = credits_by_term.get(index, 0) + int(r['credits'])
        except (TypeError, ValueError):
            problems.append(f'{code} has invalid credits')

    limit = profile.credit_limit
    if limit:
        for index, total in sorted(credits_by_term.items()):
            if total > limit:
                problems.append(f'{terms.format_term(index)} has {total} credits, over the limit of {limit}')
    return problems
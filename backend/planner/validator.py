"""
Independent plan validator (design §5.5, IF-2).

It never calls the solver or the database, so a bug in the CP-SAT model shows up as a
validator failure in tests, not as a wrong plan on screen (NFR-4).
This module must not import OR-Tools or Django.
"""

from collections import defaultdict

from . import requirements
from .snapshot import Violation


def validate(entries, snapshot) -> list:
    """Every rule the plan breaks, sorted by (code, course). Empty means valid."""
    courses = snapshot.courses
    window = {t.index for t in snapshot.terms()}
    term_of = {}
    violations = []

    seen = set()
    for e in entries:
        c = courses.get(e.course)
        if c is None:
            violations.append(Violation('UNKNOWN_COURSE', e.course, f'{e.course} is not in the catalog'))
            continue
        if e.course in seen:
            violations.append(Violation('DUPLICATE', e.course, f'{e.course} is scheduled more than once'))
            continue
        seen.add(e.course)
        term_of[e.course] = e.term
        if e.course in snapshot.completed:
            violations.append(Violation('ALREADY_COMPLETED', e.course, f'{e.course} is already completed'))
        if e.term.index not in window:
            violations.append(Violation('OUT_OF_WINDOW', e.course, f'{e.course} is outside the planning window'))
        if e.term.season not in c.offered:
            violations.append(Violation('NOT_OFFERED', e.course, f'{e.course} is not offered in {e.term.season}'))
        if c.manual_review:
            violations.append(Violation('MANUAL_REVIEW', e.course, f'{e.course} needs a manual prerequisite review'))

    violations += _credit_cap(term_of, snapshot)
    violations += _prerequisites(term_of, snapshot)
    violations += _corequisites(term_of, snapshot)
    violations += requirements.check(entries, snapshot)
    return sorted(violations, key=lambda v: (v.code, v.course or ''))


def _credit_cap(term_of, snapshot):
    load = defaultdict(int)
    for code, term in term_of.items():
        load[term] += snapshot.courses[code].credits
    return [
        Violation('CREDIT_CAP', None, f'{term} has {credits} credits; the limit is {snapshot.credit_limit}')
        for term, credits in sorted(load.items())
        if credits > snapshot.credit_limit
    ]


def _prerequisites(term_of, snapshot):
    violations = []
    for code, term in term_of.items():
        for clause in snapshot.courses[code].prereqs:
            met = any(
                d in snapshot.completed or (d in term_of and term_of[d] < term)
                for d in clause
            )
            if not met:
                violations.append(Violation(
                    'PREREQ', code, f'{code} needs one of {", ".join(clause)} in an earlier term',
                ))
                break
    return violations


def _corequisites(term_of, snapshot):
    violations = []
    for a, b in sorted(snapshot.corequisites):
        for course, partner in ((a, b), (b, a)):
            if course in term_of and partner not in snapshot.completed and term_of.get(partner) != term_of[course]:
                violations.append(Violation(
                    'COREQ', course, f'{course} and {partner} must be taken in the same term',
                ))
    return violations

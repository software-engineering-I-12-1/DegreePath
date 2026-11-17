"""
Builders for planner tests. Not a test module: the file name does not start with "test".
"""

import re
from dataclasses import replace

from .snapshot import SEASONS, Course, PlanningInput, Requirement, Term


def _level(code: str) -> int:
    match = re.search(r'(\d)\d{3}', code)
    return int(match.group(1)) * 1000 if match else 1000


def course(code, credits=4, *, offered=('Fall', 'Spring'), prereqs=(), manual_review=False, level=None):
    return Course(
        code=code,
        title=code,
        credits=credits,
        level=_level(code) if level is None else level,
        offered=frozenset(offered),
        prereqs=tuple(tuple(clause) for clause in prereqs),
        manual_review=manual_review,
    )


def required(name, *codes):
    return Requirement(name=name, kind='required', courses=tuple(codes))


def pool(name, choose_n, *codes):
    return Requirement(name=name, kind='pool', courses=tuple(codes), choose_n=choose_n)


def threshold(name, min_credits, min_level):
    return Requirement(name=name, kind='credit_threshold', min_credits=min_credits, min_level=min_level)


def snapshot(*courses, requirements=(), corequisites=(), completed=(), credit_limit=16,
             first=Term('Fall', 2026), target=Term('Spring', 2028)):
    return PlanningInput(
        courses={c.code: c for c in courses},
        corequisites=frozenset(tuple(sorted(pair)) for pair in corequisites),
        requirements=tuple(requirements),
        completed=frozenset(completed),
        credit_limit=credit_limit,
        first_term=first,
        target_term=target,
        program='Test program',
    )


# Pilot major: 8 required courses, one OR group, a Fall-only and a Spring-only course,
# a corequisite lab, an elective pool, a credit threshold and a manual-review course.
_FS = ('Fall', 'Spring')
_PILOT_COURSES = (
    course('CS-UY 1114'),
    course('CS-UY 1134', prereqs=(('CS-UY 1114',),)),
    course('CS-UY 2124', prereqs=(('CS-UY 1134',),)),
    course('CS-UY 2214', prereqs=(('CS-UY 1114',),)),
    course('CS-UY 2204', prereqs=(('CS-UY 1114',),)),
    course('MA-UY 1024'),
    course('MA-UY 2314', prereqs=(('MA-UY 1024',),)),
    course('CS-UY 2413', prereqs=(('CS-UY 1134',), ('CS-UY 2204', 'MA-UY 2314'))),
    course('CS-UY 3224', offered=('Fall',), prereqs=(('CS-UY 2214',), ('CS-UY 2124',))),
    course('CS-UY 3083', offered=('Spring',), prereqs=(('CS-UY 1134',),)),
    course('CS-UY 3084', 1, offered=('Spring',)),
    course('CS-UY 4513', prereqs=(('CS-UY 2124',),)),
    course('CS-UY 3393', offered=('Fall',), prereqs=(('CS-UY 2214',),)),
    course('CS-UY 3923', offered=('Spring',), prereqs=(('CS-UY 2214',),)),
    course('CS-UY 4523', prereqs=(('CS-UY 2413',),)),
    course('CS-UY 4563', prereqs=(('CS-UY 2413',),)),
    course('CS-UY 4613', offered=('Spring',), prereqs=(('CS-UY 2413',),)),
    course('CS-UY 3943', offered=('Fall',), prereqs=(('CS-UY 3224',),)),
    course('CS-UY 3113', prereqs=(('CS-UY 1134',),)),
    course('CS-UY 4973', manual_review=True),
)
PILOT_REQUIRED = ('CS-UY 1114', 'CS-UY 1134', 'CS-UY 2124', 'CS-UY 2214',
                  'CS-UY 2413', 'CS-UY 3224', 'CS-UY 3083', 'CS-UY 4513')


def pilot_major(**overrides):
    """First term Fall 2026, target Spring 2029 (6 terms), 16 credits per term, nothing completed."""
    options = dict(
        requirements=(
            required('Core courses', *PILOT_REQUIRED),
            pool('Systems electives', 3, 'CS-UY 3393', 'CS-UY 3923', 'CS-UY 4523',
                 'CS-UY 4563', 'CS-UY 4613', 'CS-UY 3943'),
            threshold('Upper-level credits', 12, 3000),
        ),
        corequisites=(('CS-UY 3083', 'CS-UY 3084'),),
        target=Term('Spring', 2029),
    )
    options.update(overrides)
    return snapshot(*_PILOT_COURSES, **options)


def restrict(snap, keep):
    """
    The snapshot with only the explainable constraints in `keep` (ConstraintRef.ref ids)
    still in force; hard rules (completed courses, the first term) are untouched. Used to
    check conflict sets with the generator, independently of the explainer's own model.
    """
    keep = set(keep)
    courses = {}
    for code, c in snap.courses.items():
        courses[code] = replace(
            c,
            prereqs=tuple(cl for i, cl in enumerate(c.prereqs) if f'prereq:{code}:{i}' in keep),
            offered=c.offered if f'offering:{code}' in keep else frozenset(SEASONS),
            manual_review=c.manual_review and f'manual_review:{code}' in keep,
        )
    requirements = tuple(
        replace(r, courses=tuple(code for code in r.courses if f'required:{r.name}:{code}' in keep))
        if r.kind == 'required' else r
        for r in snap.requirements
        if (r.kind == 'required'
            or (r.kind == 'pool' and f'pool:{r.name}' in keep)
            or (r.kind == 'credit_threshold' and f'threshold:{r.name}' in keep))
    )
    target = snap.target_term
    if 'profile.target_term' not in keep:
        target = Term.from_index(max(target.index, snap.first_term.index + 2 * len(courses) + 1))
    return replace(
        snap,
        courses=courses,
        corequisites=frozenset(p for p in snap.corequisites if f'coreq:{p[0]}:{p[1]}' in keep),
        requirements=requirements,
        credit_limit=snap.credit_limit if 'profile.credit_limit' in keep
        else sum(c.credits for c in courses.values()) + 1,
        target_term=target,
    )

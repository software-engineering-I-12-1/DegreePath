"""
Conflict-set entries (US-12; design §5.4).

A ConstraintRef is one constraint the student could change, shown when no plan exists:
{type, ref, text}. type is one of the nine TYPES, ref is a stable id for the row it comes
from, and text is the line shown on screen. Refs starting with "profile." point at the
student's own profile fields.

Three rules are hard and never appear here, because a student cannot change them: a
course is scheduled at most once, completed courses are not rescheduled, and nothing is
scheduled before the next term.

Pure Python: requirements.py (and so the validator) imports this module.
"""

from dataclasses import dataclass, field

from .snapshot import SEASONS

TYPES = ('CREDIT_CAP', 'TARGET_TERM', 'PREREQ', 'COREQ', 'OFFERING',
         'REQUIRED_COURSE', 'POOL', 'CREDIT_THRESHOLD', 'MANUAL_REVIEW')


@dataclass(frozen=True)
class ConstraintRef:
    type: str
    ref: str
    text: str = field(default='', compare=False)

    def sort_key(self):
        return TYPES.index(self.type), self.ref

    def as_dict(self):
        return {'type': self.type, 'ref': self.ref, 'text': self.text}


def credit_cap(snapshot):
    return ConstraintRef('CREDIT_CAP', 'profile.credit_limit', f'At most {snapshot.credit_limit} credits per term')


def target_term(snapshot):
    left = len(snapshot.terms())
    count = 'no terms' if left == 0 else '1 term' if left == 1 else f'{left} terms'
    return ConstraintRef('TARGET_TERM', 'profile.target_term', f'Graduate by {snapshot.target_term} ({count} left)')


def prereq(course, position):
    """The course's prerequisite clause at `position` (a PrereqClause row)."""
    options = sorted(course.prereqs[position])
    needed = options[0] if len(options) == 1 else 'one of ' + ', '.join(options)
    return ConstraintRef('PREREQ', f'prereq:{course.code}:{position}', f'{course.code} needs {needed} in an earlier term')


def coreq(a, b):
    a, b = sorted((a, b))
    return ConstraintRef('COREQ', f'coreq:{a}:{b}', f'{a} and {b} must be taken in the same term')


def offering(course):
    seasons = [s for s in SEASONS if s in course.offered]
    if seasons:
        text = f'{course.code} is offered only in {" and ".join(seasons)}'
    else:
        text = f'{course.code} is not offered in any term'
    return ConstraintRef('OFFERING', f'offering:{course.code}', text)


def required_course(requirement, code):
    return ConstraintRef('REQUIRED_COURSE', f'required:{requirement.name}:{code}', f'{requirement.name}: {code}')


def pool(requirement):
    """For US-18."""
    return ConstraintRef('POOL', f'pool:{requirement.name}',
                         f'{requirement.name}: choose {requirement.choose_n} of {len(requirement.courses)}')


def credit_threshold(requirement):
    """For US-18."""
    return ConstraintRef('CREDIT_THRESHOLD', f'threshold:{requirement.name}',
                         f'At least {requirement.min_credits} credits at {requirement.min_level}-level or above')


def manual_review(course):
    return ConstraintRef('MANUAL_REVIEW', f'manual_review:{course.code}',
                         f'{course.code} needs instructor permission, which DegreePath cannot check')

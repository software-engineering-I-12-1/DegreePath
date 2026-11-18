"""
Reads a PlanningInput snapshot from the database (design §6.1, Figure 4).

The profile, catalog and requirement rows are read in one transaction, so an import committed
mid-read cannot mix two catalog versions. On PostgreSQL the transaction is REPEATABLE READ.
"""

from django.db import connection, transaction

from catalog.models import CatalogState, Corequisite, Course, DegreeProgram
from profiles import terms as profile_terms

from .snapshot import Course as PlanCourse
from .snapshot import PlanningInput, Requirement, Term


class ProfileIncomplete(Exception):
    """Program, credit limit or target term is missing (US-09 AC3, DR-12)."""

    def __init__(self, missing):
        self.missing = list(missing)
        super().__init__('Profile incomplete: ' + ', '.join(self.missing))


class ProgramNotImported(Exception):
    """The student's major has no imported degree requirements (US-08)."""

    def __init__(self, program):
        self.program = program
        super().__init__(f'No degree requirements imported for {program}')


def first_planning_term() -> Term:
    """Plans start in the term after the current one (design §5.4)."""
    return Term.from_index(profile_terms.current_term_index() + 1)


def load_snapshot(profile) -> PlanningInput:
    missing = [name for name in ('major', 'credit_limit', 'target_term') if not getattr(profile, name)]
    target = Term.parse(profile.target_term) if profile.target_term else None
    if profile.target_term and target is None:
        missing.append('target_term')
    if missing:
        raise ProfileIncomplete(missing)

    with transaction.atomic():
        if connection.vendor == 'postgresql' and not _in_outer_transaction():
            with connection.cursor() as cursor:
                cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        return _read(profile, target)


def _in_outer_transaction() -> bool:
    # SET TRANSACTION must be the first statement; inside a savepoint (tests, nested atomic) skip it.
    return len(connection.savepoint_ids) > 0


def _read(profile, target):
    profile.refresh_from_db()
    program = (
        DegreeProgram.objects.filter(name__iexact=profile.major.strip())
        .prefetch_related('requirements__requirement_courses__course')
        .first()
    )
    if program is None:
        raise ProgramNotImported(profile.major)

    courses = {}
    for c in Course.objects.prefetch_related('offerings', 'prereq_clauses__options__required_course'):
        clauses = tuple(
            tuple(sorted(option.required_course.code for option in clause.options.all()))
            for clause in sorted(c.prereq_clauses.all(), key=lambda cl: cl.position)
        )
        courses[c.code] = PlanCourse(
            code=c.code,
            title=c.title,
            credits=c.credits,
            level=c.level,
            offered=frozenset(o.season for o in c.offerings.all()),
            prereqs=tuple(clause for clause in clauses if clause),
            manual_review=c.prereq_manual_review,
        )

    corequisites = frozenset(
        tuple(sorted(pair)) for pair in Corequisite.objects.values_list('course__code', 'coreq_course__code')
    )

    requirements = tuple(
        Requirement(
            name=r.name,
            kind=r.type,
            courses=tuple(sorted(rc.course.code for rc in r.requirement_courses.all())),
            choose_n=r.choose_n or 0,
            min_credits=r.min_credits or 0,
            min_level=r.min_level or 0,
        )
        for r in sorted(program.requirements.all(), key=lambda r: (r.position, r.name))
    )

    catalog_version = CatalogState.objects.filter(pk=1).values_list('catalog_version', flat=True).first()

    return PlanningInput(
        courses=courses,
        corequisites=corequisites,
        requirements=requirements,
        completed=frozenset(profile.completed_courses or ()),
        credit_limit=profile.credit_limit,
        first_term=first_planning_term(),
        target_term=target,
        program=program.name,
        max_pools_per_course=program.max_elective_pools_per_course,
        profile_version=profile.profile_version,
        catalog_version=catalog_version or 1,
    )

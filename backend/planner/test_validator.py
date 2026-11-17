from django.test import SimpleTestCase

from planner.fixtures import course, pool, required, snapshot
from planner.snapshot import PlanEntry, Term
from planner.validator import validate

F26, S27, F27, S28 = Term('Fall', 2026), Term('Spring', 2027), Term('Fall', 2027), Term('Spring', 2028)


def codes(violations):
    return [(v.code, v.course) for v in violations]


class ValidatorTests(SimpleTestCase):
    def setUp(self):
        self.courses = (
            course('A'),
            course('B', prereqs=(('A',),)),
            course('C'),
            course('D', prereqs=(('A', 'F'),)),
            course('F', offered=('Fall',)),
            course('S', offered=('Spring',)),
            course('X'),
            course('Y'),
            course('M', manual_review=True),
        )

    def snap(self, **kwargs):
        kwargs.setdefault('credit_limit', 8)
        kwargs.setdefault('corequisites', (('X', 'Y'),))
        return snapshot(*self.courses, **kwargs)

    def check(self, entries, **kwargs):
        return codes(validate([PlanEntry(c, t) for c, t in entries], self.snap(**kwargs)))

    def test_valid_plan_has_no_violations(self):
        self.assertEqual(self.check([('A', F26), ('B', S27)]), [])

    def test_prerequisite_in_same_term(self):
        self.assertEqual(self.check([('A', F26), ('B', F26)]), [('PREREQ', 'B')])

    def test_prerequisite_missing(self):
        self.assertEqual(self.check([('B', F26)]), [('PREREQ', 'B')])

    def test_completed_prerequisite_satisfies_clause(self):
        self.assertEqual(self.check([('B', F26)], completed=('A',)), [])

    def test_or_clause_satisfied_by_any_alternative(self):
        self.assertEqual(self.check([('F', F26), ('D', S27)]), [])

    def test_corequisites_in_different_terms(self):
        self.assertEqual(self.check([('X', F26), ('Y', S27)]), [('COREQ', 'X'), ('COREQ', 'Y')])

    def test_corequisite_partner_missing(self):
        self.assertEqual(self.check([('X', F26)]), [('COREQ', 'X')])

    def test_corequisite_partner_completed_is_satisfied(self):
        self.assertEqual(self.check([('X', F26)], completed=('Y',)), [])

    def test_course_in_unoffered_season(self):
        self.assertEqual(self.check([('F', S27)]), [('NOT_OFFERED', 'F')])

    def test_course_offered_in_no_season(self):
        snap = snapshot(course('N', offered=()))
        self.assertEqual(codes(validate([PlanEntry('N', F26)], snap)), [('NOT_OFFERED', 'N')])

    def test_term_over_credit_limit(self):
        self.assertEqual(self.check([('A', F26), ('C', F26), ('F', F26)]), [('CREDIT_CAP', None)])

    def test_completed_course_rescheduled(self):
        self.assertEqual(self.check([('A', F26)], completed=('A',)), [('ALREADY_COMPLETED', 'A')])

    def test_course_scheduled_twice(self):
        self.assertEqual(self.check([('A', F26), ('A', S27)]), [('DUPLICATE', 'A')])

    def test_term_outside_window(self):
        self.assertEqual(
            self.check([('A', Term('Spring', 2026)), ('C', Term('Fall', 2028))]),
            [('OUT_OF_WINDOW', 'A'), ('OUT_OF_WINDOW', 'C')],
        )

    def test_manual_review_course_scheduled(self):
        self.assertEqual(self.check([('M', F26)]), [('MANUAL_REVIEW', 'M')])

    def test_unknown_course(self):
        self.assertEqual(self.check([('ZZ 9999', F26)]), [('UNKNOWN_COURSE', 'ZZ 9999')])

    def test_missing_required_course(self):
        reqs = (required('Core', 'A', 'B'),)
        self.assertEqual(self.check([('A', F26)], requirements=reqs), [('REQUIRED_COURSE', 'B')])

    def test_completed_required_course_counts(self):
        reqs = (required('Core', 'A', 'B'),)
        self.assertEqual(self.check([('B', F26)], requirements=reqs, completed=('A',)), [])

    def test_counted_for_must_name_a_pool_containing_the_course(self):
        snap = self.snap(requirements=(pool('P', 1, 'A', 'C'),))
        entries = [PlanEntry('A', F26, 'P'), PlanEntry('F', F26, 'P'), PlanEntry('C', S27, 'Nope')]
        self.assertEqual(
            codes(validate(entries, snap)), [('POOL_ALLOCATION', 'C'), ('POOL_ALLOCATION', 'F')]
        )

    def test_violations_sorted_by_code_then_course(self):
        found = self.check([('M', F26), ('B', F26), ('ZZ 1', F26)])
        self.assertEqual(found, sorted(found, key=lambda v: (v[0], v[1] or '')))

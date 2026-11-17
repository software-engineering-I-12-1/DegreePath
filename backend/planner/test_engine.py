from dataclasses import replace

from django.test import SimpleTestCase

from planner import requirements
from planner.engine import (
    INFEASIBLE_MESSAGE, Infeasible, PlannerBug, PlannerTimeout, SolverLimits, ValidPlan, generate,
)
from planner.fixtures import PILOT_REQUIRED, course, pilot_major, required, snapshot
from planner.snapshot import PlanEntry, Term, Violation
from planner.validator import validate


def planned(plan):
    return {e.course for e in plan.entries}


class GenerateFeasibleTests(SimpleTestCase):
    def test_pilot_plan_has_every_required_course_and_passes_validator(self):   # US-09 AC1, AC2
        snap = pilot_major()
        plan = generate(snap)
        self.assertIsInstance(plan, ValidPlan)
        self.assertEqual(validate(plan.entries, snap), [])
        self.assertTrue(set(PILOT_REQUIRED) <= planned(plan))

    def test_plan_respects_prerequisite_order_offerings_and_corequisites(self):   # US-09 AC2
        plan = generate(pilot_major())
        term = {e.course: e.term for e in plan.entries}
        self.assertLess(term['CS-UY 1114'], term['CS-UY 1134'])
        self.assertEqual(term['CS-UY 3224'].season, 'Fall')
        self.assertEqual(term['CS-UY 3083'].season, 'Spring')
        self.assertEqual(term['CS-UY 3083'], term['CS-UY 3084'])
        # CS-UY 2413 needs CS-UY 2204 or MA-UY 2314: exactly one of them is planned.
        self.assertEqual(len(planned(plan) & {'CS-UY 2204', 'MA-UY 2314'}), 1)

    def test_per_term_credit_limit_is_honored(self):                                 # US-09 AC2
        snap = pilot_major(credit_limit=8)
        plan = generate(snap)
        self.assertIsInstance(plan, ValidPlan)
        for t in snap.terms():
            self.assertLessEqual(sum(snap.courses[e.course].credits for e in plan.entries if e.term == t), 8)

    def test_completed_courses_are_not_rescheduled(self):                           # US-09 AC2
        plan = generate(pilot_major(completed=('CS-UY 1114', 'CS-UY 1134')))
        self.assertFalse({'CS-UY 1114', 'CS-UY 1134'} & planned(plan))
        self.assertIn('CS-UY 2124', {e.course for e in plan.entries if e.term == Term('Fall', 2026)})

    def test_generation_is_deterministic(self):
        self.assertEqual(generate(pilot_major()), generate(pilot_major()))

    def test_unneeded_courses_are_not_scheduled(self):
        plan = generate(pilot_major())
        self.assertNotIn('CS-UY 3113', planned(plan))
        self.assertNotIn('CS-UY 4973', planned(plan))

    def test_fewer_credits_beat_an_earlier_finish(self):
        # X needs H (4 credits, any term) or L (1 credit, Spring only). Taking H finishes a
        # term earlier, but the objective puts total credits first, so L is chosen.
        snap = snapshot(course('H 1001', 4), course('L 1002', 1, offered=('Spring',)),
                        course('X 2001', prereqs=(('H 1001', 'L 1002'),)),
                        requirements=(required('Core', 'X 2001'),))
        self.assertEqual(generate(snap).entries, (
            PlanEntry('L 1002', Term('Spring', 2027)), PlanEntry('X 2001', Term('Fall', 2027)),
        ))

    def test_courses_go_in_the_earliest_possible_term(self):
        plan = generate(snapshot(course('A 1001'), requirements=(required('Core', 'A 1001'),)))
        self.assertEqual(plan.entries, (PlanEntry('A 1001', Term('Fall', 2026)),))

    def test_entries_ordered_by_term_then_code(self):
        entries = generate(pilot_major()).entries
        self.assertEqual(list(entries), sorted(entries, key=lambda e: (e.term.index, e.course)))

    def test_plan_carries_snapshot_versions(self):
        plan = generate(replace(pilot_major(), profile_version=3, catalog_version=7))
        self.assertEqual((plan.profile_version, plan.catalog_version), (3, 7))

    def test_everything_completed_gives_empty_plan(self):
        snap = snapshot(course('A 1001'), requirements=(required('Core', 'A 1001'),), completed=('A 1001',))
        self.assertEqual(generate(snap).entries, ())

    def test_all_completed_with_empty_window_gives_empty_plan(self):
        snap = snapshot(course('A 1001'), requirements=(required('Core', 'A 1001'),),
                        completed=('A 1001',), target=Term('Spring', 2026))
        self.assertEqual(generate(snap).entries, ())

    def test_corequisite_partner_completed_schedules_course_alone(self):
        snap = snapshot(course('X 1001'), course('Y 1002'), requirements=(required('Core', 'X 1001'),),
                        corequisites=(('X 1001', 'Y 1002'),), completed=('Y 1002',))
        self.assertEqual([e.course for e in generate(snap).entries], ['X 1001'])

    def test_all_imported_requirement_types_are_enforced(self):
        self.assertEqual(requirements.unenforced(pilot_major()), ())
        plan = generate(pilot_major())
        self.assertIsInstance(plan, ValidPlan)
        self.assertEqual(validate(plan.entries, pilot_major()), [])


class GenerateInfeasibleTests(SimpleTestCase):                                       # US-09 AC3
    def assertInfeasible(self, snap):
        result = generate(snap)
        self.assertIsInstance(result, Infeasible)
        self.assertEqual(result.message, INFEASIBLE_MESSAGE)

    def test_window_too_short_for_prerequisite_chain(self):
        self.assertInfeasible(pilot_major(target=Term('Spring', 2027)))

    def test_required_course_heavier_than_credit_limit(self):
        self.assertInfeasible(snapshot(course('X 1001', 6), requirements=(required('Core', 'X 1001'),),
                                       credit_limit=4))

    def test_required_course_never_offered(self):
        self.assertInfeasible(snapshot(course('X 1001', offered=()), requirements=(required('Core', 'X 1001'),)))

    def test_required_course_behind_manual_review(self):
        snap = snapshot(course('M 1001', manual_review=True), course('X 2001', prereqs=(('M 1001',),)),
                        requirements=(required('Core', 'X 2001'),))
        self.assertInfeasible(snap)

    def test_required_manual_review_course(self):
        self.assertInfeasible(snapshot(course('M 1001', manual_review=True),
                                       requirements=(required('Core', 'M 1001'),)))

    def test_required_course_missing_from_catalog(self):
        self.assertInfeasible(snapshot(course('A 1001'), requirements=(required('Core', 'Z 9999'),)))

    def test_corequisites_offered_in_different_seasons(self):
        snap = snapshot(course('X 1001', offered=('Fall',)), course('Y 1002', offered=('Spring',)),
                        requirements=(required('Core', 'X 1001'),), corequisites=(('X 1001', 'Y 1002'),))
        self.assertInfeasible(snap)

    def test_empty_window_with_work_left(self):
        self.assertInfeasible(snapshot(course('A 1001'), requirements=(required('Core', 'A 1001'),),
                                       target=Term('Spring', 2026)))


class GenerateFailureTests(SimpleTestCase):
    def test_time_limit_reached_returns_timeout(self):                               # US-09 AC3, NFR-3
        self.assertEqual(generate(pilot_major(), limits=SolverLimits(0.0, 0.0)), PlannerTimeout())

    def test_validator_rejection_raises_planner_bug_with_codes_only(self):           # NFR-4, NFR-5
        def reject(entries, snap):
            return [Violation('PREREQ', 'CS-UY 1134', 'CS-UY 1134 needs CS-UY 1114')]

        with self.assertLogs('planner.engine', level='ERROR') as logs:
            with self.assertRaises(PlannerBug) as caught:
                generate(pilot_major(), validator=reject)
        self.assertEqual(caught.exception.codes, ['PREREQ'])
        self.assertNotIn('CS-UY', str(caught.exception))
        self.assertNotIn('CS-UY', ' '.join(logs.output))

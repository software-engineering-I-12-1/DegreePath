"""US-18: degree rules must agree in generation and independent validation."""

from dataclasses import replace

from django.test import SimpleTestCase

from planner.engine import Infeasible, ValidPlan, generate
from planner.fixtures import course, pool, required, snapshot, threshold
from planner.snapshot import PlanEntry, Term
from planner.validator import validate

FIRST = Term('Fall', 2026)


def violations(entries, snap):
    return {problem.code for problem in validate(entries, snap)}


class DegreeRequirementTests(SimpleTestCase):
    def test_overlapping_pools_use_distinct_courses_when_limit_is_one(self):
        snap = snapshot(course('A 3001'), course('B 3002'),
                        requirements=(pool('Systems', 1, 'A 3001', 'B 3002'),
                                      pool('Theory', 1, 'A 3001', 'B 3002')))
        plan = generate(snap)
        self.assertIsInstance(plan, ValidPlan)
        self.assertEqual({entry.course for entry in plan.entries}, {'A 3001', 'B 3002'})
        self.assertEqual({entry.counted_for for entry in plan.entries}, {'Systems', 'Theory'})
        self.assertEqual(validate(plan.entries, snap), [])

    def test_one_course_cannot_fill_two_pools_with_single_counting(self):
        snap = snapshot(course('A 3001'),
                        requirements=(pool('Systems', 1, 'A 3001'), pool('Theory', 1, 'A 3001')))
        self.assertIsInstance(generate(snap), Infeasible)
        self.assertIn('POOL_MINIMUM', violations([PlanEntry('A 3001', FIRST, 'Systems')], snap))

    def test_program_can_allow_the_same_course_in_two_pools(self):
        snap = replace(snapshot(course('A 3001'),
                                requirements=(pool('Systems', 1, 'A 3001'),
                                              pool('Theory', 1, 'A 3001'))), max_pools_per_course=2)
        plan = generate(snap)
        self.assertIsInstance(plan, ValidPlan)
        self.assertEqual(plan.entries, (PlanEntry('A 3001', FIRST, ('Systems', 'Theory')),))
        self.assertEqual(validate(plan.entries, snap), [])
        self.assertEqual(validate([PlanEntry('A 3001', FIRST, ['Systems', 'Theory'])], snap), [])

    def test_completed_course_fills_a_pool_without_being_rescheduled(self):
        snap = snapshot(course('A 3001'), requirements=(pool('Systems', 1, 'A 3001'),),
                        completed=('A 3001',))
        self.assertEqual(generate(snap).entries, ())
        self.assertEqual(validate([], snap), [])

    def test_completed_course_cannot_double_count_when_limit_is_one(self):
        snap = snapshot(course('A 3001'),
                        requirements=(pool('Systems', 1, 'A 3001'), pool('Theory', 1, 'A 3001')),
                        completed=('A 3001',))
        self.assertIsInstance(generate(snap), Infeasible)
        self.assertIn('POOL_MINIMUM', violations([], snap))
        self.assertEqual(validate([], replace(snap, max_pools_per_course=2)), [])

    def test_completed_courses_can_be_reallocated_between_overlapping_pools(self):
        snap = snapshot(course('A 3001'), course('B 3002'),
                        requirements=(pool('Systems', 1, 'A 3001', 'B 3002'),
                                      pool('Theory', 1, 'A 3001')),
                        completed=('A 3001', 'B 3002'))
        self.assertEqual(validate([], snap), [])

    def test_completed_and_scheduled_credits_reach_threshold_once_each(self):
        snap = snapshot(course('A 3001', 4), course('B 3002', 4), course('C 1001', 1),
                        requirements=(threshold('Upper', 8, 3000),), completed=('A 3001',))
        plan = generate(snap)
        self.assertIsInstance(plan, ValidPlan)
        self.assertEqual([entry.course for entry in plan.entries], ['B 3002'])
        self.assertEqual(validate(plan.entries, snap), [])
        self.assertIn('CREDIT_THRESHOLD', violations([], snap))
        self.assertIsInstance(generate(replace(snap, requirements=(threshold('Upper', 12, 3000),))),
                              Infeasible)

    def test_required_and_pool_courses_can_also_supply_upper_level_credits(self):
        snap = snapshot(course('A 3001', 4), course('B 3002', 4),
                        requirements=(required('Core', 'A 3001'), pool('Electives', 1, 'B 3002'),
                                      threshold('Upper', 8, 3000)))
        plan = generate(snap)
        self.assertIsInstance(plan, ValidPlan)
        self.assertEqual({entry.course for entry in plan.entries}, {'A 3001', 'B 3002'})
        self.assertEqual(validate(plan.entries, snap), [])

    def test_validator_rejects_invalid_pool_assignment_and_missing_minimum(self):
        snap = snapshot(course('A 3001'), course('B 3002'),
                        requirements=(pool('Systems', 1, 'A 3001'), pool('Theory', 1, 'B 3002')))
        self.assertEqual(violations([PlanEntry('A 3001', FIRST, 'Theory')], snap),
                         {'POOL_ALLOCATION', 'POOL_MINIMUM'})
        self.assertIn('POOL_ALLOCATION', violations([PlanEntry('A 3001', FIRST, ('Systems', 'Systems'))], snap))
        self.assertIn('POOL_ALLOCATION', violations([PlanEntry('A 3001', FIRST, ('Systems', 'Theory'))], snap))

    def test_unreachable_pool_or_threshold_is_infeasible_by_target(self):
        snap = snapshot(course('A 3001', 4, offered=('Spring',)),
                        requirements=(pool('Electives', 1, 'A 3001'), threshold('Upper', 4, 3000)),
                        target=FIRST)
        self.assertIsInstance(generate(snap), Infeasible)

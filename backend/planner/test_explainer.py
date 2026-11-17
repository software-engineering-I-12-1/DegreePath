"""
Conflict explainer (US-12; design §5.4, §6.3 and Figure 7).

Every scenario declares its conflict set up front. The explainer's answer must equal it
(AC3), and minimality is checked with the generator, not the explainer's own model: the
declared set alone admits no plan, and dropping any one constraint from it leaves a set
that does (AC2).
"""

import time
from dataclasses import replace

from django.test import SimpleTestCase

from planner import conflicts
from planner.engine import Infeasible, ValidPlan, generate
from planner.explainer import Explanation, explain
from planner.fixtures import course, pilot_major, pool, required, restrict, snapshot, threshold
from planner.snapshot import Term

FALL_26 = Term('Fall', 2026)
SPRING_27 = Term('Spring', 2027)
FALL_27 = Term('Fall', 2027)
SPRING_28 = Term('Spring', 2028)


def explain_now(snap):
    return explain(snap, deadline=time.monotonic() + 28)


def refs(explanation):
    return {c.ref for c in explanation.conflicts}


def chain(prefix, length, **options):
    """prefix 1001 -> prefix 1002 -> ... each needing the previous one."""
    codes = [f'{prefix} {1000 + i}' for i in range(1, length + 1)]
    return [course(code, prereqs=((codes[i - 1],),) if i else (), **options) for i, code in enumerate(codes)]


# name: (snapshot, acceptable conflict sets). Most scenarios have exactly one minimal set;
# two have independent problems or a doubly-required course, so either answer is minimal.
SCENARIOS = {
    'prerequisite chain longer than the window': (
        snapshot(*chain('A', 5), course('N 1001', offered=('Fall',)),
                 requirements=(required('Core', 'A 1005', 'N 1001'),), target=SPRING_28),
        [{'profile.target_term', 'prereq:A 1002:0', 'prereq:A 1003:0', 'prereq:A 1004:0',
          'prereq:A 1005:0', 'required:Core:A 1005'}],
    ),
    'course heavier than the credit limit': (
        snapshot(course('X 1001', 6), course('Y 1002'), requirements=(required('Core', 'X 1001', 'Y 1002'),),
                 credit_limit=4),
        [{'profile.credit_limit', 'required:Core:X 1001'}],
    ),
    'course never offered': (
        snapshot(course('X 1001', offered=()), requirements=(required('Core', 'X 1001'),)),
        [{'offering:X 1001', 'required:Core:X 1001'}],
    ),
    'required course needs instructor permission': (
        snapshot(course('M 1001', manual_review=True), requirements=(required('Core', 'M 1001'),)),
        [{'manual_review:M 1001', 'required:Core:M 1001'}],
    ),
    'required course behind a manual-review course': (
        snapshot(course('M 1001', manual_review=True), course('X 2001', prereqs=(('M 1001',),)),
                 requirements=(required('Core', 'X 2001'),)),
        [{'manual_review:M 1001', 'prereq:X 2001:0', 'required:Core:X 2001'}],
    ),
    'corequisites offered in different seasons': (
        snapshot(course('X 1001', offered=('Fall',)), course('Y 1002', offered=('Spring',)),
                 requirements=(required('Core', 'X 1001'),), corequisites=(('X 1001', 'Y 1002'),)),
        [{'offering:X 1001', 'offering:Y 1002', 'coreq:X 1001:Y 1002', 'required:Core:X 1001'}],
    ),
    'target term already passed': (
        snapshot(course('A 1001'), requirements=(required('Core', 'A 1001'),), target=Term('Spring', 2026)),
        [{'profile.target_term', 'required:Core:A 1001'}],
    ),
    'too many credits for the window': (
        snapshot(course('A 1001'), course('B 1002'), course('C 1003'),
                 requirements=(required('Core', 'A 1001', 'B 1002', 'C 1003'),),
                 credit_limit=4, target=SPRING_27),
        [{'profile.credit_limit', 'profile.target_term', 'required:Core:A 1001',
          'required:Core:B 1002', 'required:Core:C 1003'}],
    ),
    'fall-only course after a prerequisite': (
        snapshot(course('A 1001', offered=('Fall',)), course('B 2001', offered=('Fall',), prereqs=(('A 1001',),)),
                 requirements=(required('Core', 'B 2001'),), target=SPRING_27),
        [{'offering:B 2001', 'prereq:B 2001:0', 'profile.target_term', 'required:Core:B 2001'}],
    ),
    'both options of an OR prerequisite blocked': (
        snapshot(course('P 1001', manual_review=True), course('Q 1002', offered=()),
                 course('X 2001', prereqs=(('P 1001', 'Q 1002'),)), requirements=(required('Core', 'X 2001'),)),
        [{'prereq:X 2001:0', 'manual_review:P 1001', 'offering:Q 1002', 'required:Core:X 2001'}],
    ),
    'lecture and lab together exceed the credit limit': (
        snapshot(course('L 3001', 4, offered=('Spring',)), course('B 3002', 1, offered=('Spring',)),
                 requirements=(required('Core', 'L 3001'),), corequisites=(('L 3001', 'B 3002'),), credit_limit=4),
        [{'profile.credit_limit', 'coreq:B 3002:L 3001', 'required:Core:L 3001'}],
    ),
    'second prerequisite clause blocked after the first is completed': (
        snapshot(course('A 1001'), course('B 1002', manual_review=True),
                 course('X 2001', prereqs=(('A 1001',), ('B 1002',))),
                 requirements=(required('Core', 'X 2001'),), completed=('A 1001',)),
        [{'manual_review:B 1002', 'prereq:X 2001:1', 'required:Core:X 2001'}],
    ),
    'corequisite partner never offered': (
        snapshot(course('X 1001'), course('Y 1002', offered=()),
                 requirements=(required('Core', 'X 1001'),), corequisites=(('X 1001', 'Y 1002'),)),
        [{'offering:Y 1002', 'coreq:X 1001:Y 1002', 'required:Core:X 1001'}],
    ),
    'spring-only course with only a fall term left': (
        snapshot(course('X 1001', offered=('Spring',)), requirements=(required('Core', 'X 1001'),), target=FALL_26),
        [{'offering:X 1001', 'profile.target_term', 'required:Core:X 1001'}],
    ),
    'heavy prerequisite': (
        snapshot(course('A 1001', 5), course('B 2001', 4, prereqs=(('A 1001',),)),
                 requirements=(required('Core', 'B 2001'),), credit_limit=4),
        [{'profile.credit_limit', 'prereq:B 2001:0', 'required:Core:B 2001'}],
    ),
    'corequisite that is also a prerequisite': (
        snapshot(course('A 1001'), course('B 1002', prereqs=(('A 1001',),)),
                 requirements=(required('Core', 'A 1001'),), corequisites=(('A 1001', 'B 1002'),)),
        [{'coreq:A 1001:B 1002', 'prereq:B 1002:0', 'required:Core:A 1001'}],
    ),
    'two independent problems': (
        snapshot(course('X 1001', 6), course('Z 1002', offered=()),
                 requirements=(required('Core', 'X 1001', 'Z 1002'),), credit_limit=4),
        [{'profile.credit_limit', 'required:Core:X 1001'}, {'offering:Z 1002', 'required:Core:Z 1002'}],
    ),
    'course required by two requirements': (
        snapshot(course('X 1001', offered=()), requirements=(required('Core', 'X 1001'), required('Math', 'X 1001'))),
        [{'offering:X 1001', 'required:Core:X 1001'}, {'offering:X 1001', 'required:Math:X 1001'}],
    ),
}


# US-18 AC3: when the degree rules cannot be met, the conflict names the unmet requirement.
REQUIREMENT_SCENARIOS = {
    'elective pool cannot be filled': (
        snapshot(course('A 3001'), course('B 3002', offered=()), requirements=(pool('Systems', 2, 'A 3001', 'B 3002'),)),
        [{'pool:Systems', 'offering:B 3002'}],
    ),
    'not enough upper-level credits exist': (
        snapshot(course('A 3001'), course('B 3002'), course('C 3003', offered=()),
                 requirements=(threshold('Upper-level credits', 12, 3000),)),
        [{'threshold:Upper-level credits', 'offering:C 3003'}],
    ),
    'one course cannot fill two pools': (
        snapshot(course('A 3001'), requirements=(pool('Systems', 1, 'A 3001'), pool('Theory', 1, 'A 3001'))),
        [{'pool:Systems', 'pool:Theory'}],
    ),
    'upper-level credits do not fit the window': (
        snapshot(course('A 3001'), course('B 3002'), course('C 3003'),
                 requirements=(threshold('Upper-level credits', 12, 3000),), credit_limit=4, target=SPRING_27),
        [{'threshold:Upper-level credits', 'profile.credit_limit', 'profile.target_term'}],
    ),
}


class ConflictScenarioTests(SimpleTestCase):
    def assertMinimal(self, snap, conflict_refs):
        """Checked with the generator: the set alone is infeasible, and every one-smaller subset is feasible."""
        self.assertIsInstance(generate(restrict(snap, conflict_refs)), Infeasible)
        for ref in sorted(conflict_refs):
            with self.subTest(dropped=ref):
                self.assertIsInstance(generate(restrict(snap, conflict_refs - {ref})), ValidPlan)

    def test_scenarios_are_infeasible_as_built(self):
        self.assertGreaterEqual(len(SCENARIOS), 15)
        for name, (snap, _) in SCENARIOS.items():
            with self.subTest(name):
                self.assertIsInstance(generate(snap), Infeasible)

    def test_declared_conflict_sets_are_minimal(self):
        # Guards the fixtures themselves: a wrong declaration would make the next test meaningless.
        for name, (snap, declared) in SCENARIOS.items():
            for expected in declared:
                with self.subTest(name, expected=sorted(expected)):
                    self.assertMinimal(snap, expected)

    def test_reported_set_is_a_declared_conflict(self):                              # US-12 AC3
        for name, (snap, declared) in SCENARIOS.items():
            with self.subTest(name):
                explanation = explain_now(snap)
                self.assertIn(refs(explanation), declared)
                self.assertFalse(explanation.possibly_non_minimal)

    def test_reported_set_is_minimal(self):                                          # US-12 AC2
        for name, (snap, _) in SCENARIOS.items():
            with self.subTest(name):
                self.assertMinimal(snap, refs(explain_now(snap)))

    def test_unmet_degree_requirement_is_named(self):                                # US-18 AC3
        for name, (snap, declared) in REQUIREMENT_SCENARIOS.items():
            with self.subTest(name):
                self.assertIsInstance(generate(snap), Infeasible)
                explanation = explain_now(snap)
                self.assertIn(refs(explanation), declared)
                self.assertMinimal(snap, refs(explanation))

    def test_program_allowing_double_counting_has_no_pool_conflict(self):
        snap, _ = REQUIREMENT_SCENARIOS['one course cannot fill two pools']
        self.assertIsInstance(generate(replace(snap, max_pools_per_course=2)), ValidPlan)

    def test_pool_and_threshold_texts(self):
        self.assertEqual(conflicts.pool(pool('Systems electives', 3, 'A', 'B', 'C', 'D', 'E', 'F')).text,
                         'Systems electives: choose 3 of 6')
        self.assertEqual(conflicts.credit_threshold(threshold('Upper', 12, 3000)).text,
                         'At least 12 credits at 3000-level or above')


class ConflictExplanationTests(SimpleTestCase):
    def test_chain_longer_than_window_lists_only_chain_and_target(self):            # US-12 AC1
        snap, _ = SCENARIOS['prerequisite chain longer than the window']
        explanation = explain_now(snap)
        self.assertEqual([c.type for c in explanation.conflicts],
                         ['TARGET_TERM', 'PREREQ', 'PREREQ', 'PREREQ', 'PREREQ', 'REQUIRED_COURSE'])
        self.assertNotIn('N 1001', ' '.join(c.text for c in explanation.conflicts))

    def test_pilot_major_with_too_early_target_is_minimal(self):                     # US-12 AC2
        snap = pilot_major(target=SPRING_27)
        explanation = explain_now(snap)
        self.assertIn('profile.target_term', refs(explanation))
        ConflictScenarioTests.assertMinimal(self, snap, refs(explanation))

    def test_deadline_reached_labels_result_possibly_non_minimal(self):              # US-12 AC4
        snap, declared = SCENARIOS['prerequisite chain longer than the window']
        explanation = explain(snap, deadline=time.monotonic() - 1)
        self.assertTrue(explanation.possibly_non_minimal)
        self.assertTrue(declared[0] <= refs(explanation))
        self.assertIsInstance(generate(restrict(snap, refs(explanation))), Infeasible)

    def test_deadline_reached_during_deletion_pass_keeps_untested_constraints(self): # US-12 AC4
        snap, declared = SCENARIOS['prerequisite chain longer than the window']
        ticks = iter([0.0, 0.0] + [100.0] * 50)   # room for the first solve only
        explanation = explain(snap, deadline=50.0, clock=lambda: next(ticks))
        self.assertTrue(explanation.possibly_non_minimal)
        self.assertTrue(declared[0] <= refs(explanation))

    def test_deadline_reached_at_the_target_term_check_keeps_the_target_term(self):  # US-12 AC4
        # 'course never offered': one window solve, two deletion solves, then the target check.
        snap, declared = SCENARIOS['course never offered']
        ticks = iter([0.0, 0.0, 0.0] + [100.0] * 10)
        explanation = explain(snap, deadline=50.0, clock=lambda: next(ticks))
        self.assertTrue(explanation.possibly_non_minimal)
        self.assertEqual(refs(explanation), declared[0] | {'profile.target_term'})

    def test_explanation_is_deterministic(self):
        snap, _ = SCENARIOS['two independent problems']
        self.assertEqual(explain_now(snap), explain_now(snap))

    def test_conflicts_are_listed_in_type_order(self):
        snap, _ = SCENARIOS['fall-only course after a prerequisite']
        self.assertEqual([c.type for c in explain_now(snap).conflicts],
                         ['TARGET_TERM', 'PREREQ', 'OFFERING', 'REQUIRED_COURSE'])

    def test_explanation_shape(self):
        snap, _ = SCENARIOS['course never offered']
        explanation = explain_now(snap)
        self.assertIsInstance(explanation, Explanation)
        self.assertEqual(explanation.conflicts[0].as_dict(),
                         {'type': 'OFFERING', 'ref': 'offering:X 1001', 'text': 'X 1001 is not offered in any term'})

    def test_explain_logs_no_course_codes(self):                                      # NFR-5
        snap = pilot_major(target=SPRING_27)
        with self.assertNoLogs('planner', level='DEBUG'):
            explain_now(snap)


class ConstraintTextTests(SimpleTestCase):
    def test_texts_match_design_section_5_4(self):
        snap = snapshot(course('A 1001'), course('B 1002'), course('C 2001', offered=('Fall',),
                        prereqs=(('A 1001', 'B 1002'), ('A 1001',))), credit_limit=12, target=SPRING_28)
        c = snap.courses['C 2001']
        self.assertEqual(conflicts.credit_cap(snap).text, 'At most 12 credits per term')
        self.assertEqual(conflicts.target_term(snap).text, 'Graduate by Spring 2028 (4 terms left)')
        self.assertEqual(conflicts.prereq(c, 0).text, 'C 2001 needs one of A 1001, B 1002 in an earlier term')
        self.assertEqual(conflicts.prereq(c, 1).text, 'C 2001 needs A 1001 in an earlier term')
        self.assertEqual(conflicts.coreq('A 1001', 'B 1002').text, 'A 1001 and B 1002 must be taken in the same term')
        self.assertEqual(conflicts.offering(c).text, 'C 2001 is offered only in Fall')
        self.assertEqual(conflicts.required_course(required('Core courses', 'A 1001'), 'A 1001').text,
                         'Core courses: A 1001')
        self.assertEqual(conflicts.manual_review(course('M 4973', manual_review=True)).text,
                         'M 4973 needs instructor permission, which DegreePath cannot check')

    def test_target_term_text_counts_terms(self):
        self.assertEqual(conflicts.target_term(snapshot(target=FALL_26)).text, 'Graduate by Fall 2026 (1 term left)')
        self.assertEqual(conflicts.target_term(snapshot(target=Term('Spring', 2026))).text,
                         'Graduate by Spring 2026 (no terms left)')

    def test_refs_compare_by_type_and_ref_only(self):
        a = conflicts.ConstraintRef('CREDIT_CAP', 'profile.credit_limit', 'At most 12 credits per term')
        b = conflicts.ConstraintRef('CREDIT_CAP', 'profile.credit_limit', 'other text')
        self.assertEqual(a, b)
        self.assertEqual(len({a, b}), 1)

    def test_nine_types_in_design_order(self):
        self.assertEqual(conflicts.TYPES, ('CREDIT_CAP', 'TARGET_TERM', 'PREREQ', 'COREQ', 'OFFERING',
                                           'REQUIRED_COURSE', 'POOL', 'CREDIT_THRESHOLD', 'MANUAL_REVIEW'))

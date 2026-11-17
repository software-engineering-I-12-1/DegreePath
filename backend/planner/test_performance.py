from django.test import SimpleTestCase

from planner.benchmark import P95_TARGET_SECONDS, benchmark_catalog, representative_profiles, run
from planner.engine import ValidPlan, generate
from planner.validator import validate


class PerformanceTests(SimpleTestCase):
    def test_p95_over_20_representative_profiles_within_10_seconds(self):   # US-09 AC4, NFR-3
        profiles = representative_profiles(20)
        result = run(profiles)
        self.assertEqual(result['runs'], 20)
        self.assertLessEqual(result['p95'], P95_TARGET_SECONDS)
        self.assertNotIn('PlannerTimeout', result['outcomes'])
        self.assertGreaterEqual(result['outcomes'].get('ValidPlan', 0), 15)

    def test_profiles_are_varied_and_reproducible(self):
        profiles = representative_profiles(20)
        self.assertEqual(profiles, representative_profiles(20))
        self.assertGreater(len({p.completed for p in profiles}), 15)
        self.assertGreater(len({p.credit_limit for p in profiles}), 3)
        self.assertEqual(len(benchmark_catalog().courses), 80)

    def test_every_benchmark_plan_passes_the_validator(self):                  # NFR-4
        for snap in representative_profiles(20):
            plan = generate(snap)
            if isinstance(plan, ValidPlan):
                self.assertEqual(validate(plan.entries, snap), [])

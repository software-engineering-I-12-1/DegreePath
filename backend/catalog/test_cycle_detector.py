from django.test import SimpleTestCase

from catalog.cycle_detector import (
    COREQUISITE_CONTRADICTION,
    PREREQUISITE_CYCLE,
    CatalogCycle,
    detect_cycle,
)


class CycleDetectorTests(SimpleTestCase):
    """US-07: import-time integrity rules 3 and 4 (Sprint 2 design, Section 4.5)."""

    def test_prerequisite_cycle_is_rejected_with_its_path(self):
        """US-07 AC1: A requires B, B requires C, C requires A is reported as 'A → B → C → A'."""
        cycle = detect_cycle({'A': [['B']], 'B': [['C']], 'C': [['A']]}, [])

        self.assertEqual(cycle, CatalogCycle(PREREQUISITE_CYCLE, 'A → B → C → A'))
        self.assertIn('A → B → C → A', cycle.message)

    def test_reported_path_does_not_depend_on_row_order(self):
        """The same catalog listed in a different row order reports the same path."""
        cycle = detect_cycle({'C': [['A']], 'B': [['C']], 'A': [['B']]}, [])

        self.assertEqual(cycle, CatalogCycle(PREREQUISITE_CYCLE, 'A → B → C → A'))

    def test_choice_between_two_cycles_does_not_depend_on_row_order(self):
        """With two separate cycles, the same one is reported whichever is listed first."""
        cycle = detect_cycle({'C': [['D']], 'D': [['C']], 'A': [['B']], 'B': [['A']]}, [])

        self.assertEqual(cycle, CatalogCycle(PREREQUISITE_CYCLE, 'A → B → A'))

    def test_acyclic_prerequisite_chain_is_accepted(self):
        """A requires B and C, B requires C: no cycle, so the import may proceed."""
        self.assertIsNone(detect_cycle({'A': [['B'], ['C']], 'B': [['C']]}, []))

    def test_loop_through_an_or_alternative_is_accepted(self):
        """A requires (B or C) and B requires A is valid: A can still be taken after C."""
        self.assertIsNone(detect_cycle({'A': [['B', 'C']], 'B': [['A']]}, []))

    def test_mutual_corequisites_are_not_a_cycle(self):
        """US-07 AC3: X and Y list each other as corequisites, with no prerequisite cycle."""
        cycle = detect_cycle({'X': [['W']], 'Y': [['W']]}, [('X', 'Y'), ('Y', 'X')])

        self.assertIsNone(cycle)

    def test_prerequisite_chain_between_corequisites_is_rejected(self):
        """US-07 AC4: A requires B, B requires C, C corequisite of A is reported as 'A → B → C ⇄ A'."""
        cycle = detect_cycle({'A': [['B']], 'B': [['C']]}, [('A', 'C')])

        self.assertEqual(cycle, CatalogCycle(COREQUISITE_CONTRADICTION, 'A → B → C ⇄ A'))
        self.assertIn('A → B → C ⇄ A', cycle.message)

    def test_course_requiring_its_own_corequisite_is_rejected(self):
        """A requires B while A and B are corequisites: they cannot share a term."""
        cycle = detect_cycle({'A': [['B']]}, [('A', 'B')])

        self.assertEqual(cycle, CatalogCycle(COREQUISITE_CONTRADICTION, 'A → B ⇄ A'))

    def test_corequisite_pairs_sharing_a_course_form_one_group(self):
        """X ⇄ Y and Y ⇄ Z put X and Z in the same term, so X requiring Z is rejected."""
        cycle = detect_cycle({'X': [['Z']]}, [('X', 'Y'), ('Y', 'Z')])

        self.assertEqual(cycle, CatalogCycle(COREQUISITE_CONTRADICTION, 'X → Z ⇄ Y ⇄ X'))

    def test_loop_through_two_corequisite_groups_is_rejected(self):
        """A ⇄ B and C ⇄ D with A requiring C and D requiring B forces both pairs apart."""
        cycle = detect_cycle({'A': [['C']], 'D': [['B']]}, [('A', 'B'), ('C', 'D')])

        self.assertEqual(cycle, CatalogCycle(COREQUISITE_CONTRADICTION, 'A → C ⇄ D → B ⇄ A'))

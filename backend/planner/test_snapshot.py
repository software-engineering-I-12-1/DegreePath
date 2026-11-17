from django.test import SimpleTestCase

from planner.snapshot import Term, terms_from


class TermTests(SimpleTestCase):
    def test_terms_alternate_spring_and_fall(self):
        self.assertEqual(
            terms_from(Term('Fall', 2026), Term('Fall', 2027)),
            [Term('Fall', 2026), Term('Spring', 2027), Term('Fall', 2027)],
        )

    def test_spring_comes_before_fall_in_the_same_year(self):
        self.assertLess(Term('Spring', 2027), Term('Fall', 2027))
        self.assertLess(Term('Fall', 2026), Term('Spring', 2027))

    def test_terms_from_empty_when_last_before_first(self):
        self.assertEqual(terms_from(Term('Fall', 2026), Term('Spring', 2026)), [])

    def test_term_is_shown_as_season_and_year(self):
        self.assertEqual(str(Term('Fall', 2027)), 'Fall 2027')

    def test_index_matches_profile_term_numbering(self):
        # profiles.terms numbers terms as year * 2, plus 1 for Fall.
        self.assertEqual(Term('Spring', 2028).index, 4056)
        self.assertEqual(Term.from_index(4057), Term('Fall', 2028))

    def test_parse_accepts_profile_format(self):
        self.assertEqual(Term.parse('spring 2028'), Term('Spring', 2028))
        self.assertIsNone(Term.parse('Summer 2028'))

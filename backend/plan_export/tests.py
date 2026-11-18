import csv
import io
from unittest.mock import patch

from catalog.models import Course
from django.contrib.auth import get_user_model
from planner.loader import ProgramNotImported
from plans.models import Plan
from profiles.models import Profile
from rest_framework.test import APIClient, APITestCase

STATUS = '/api/plan-export/status/'
HEADER = 'term,course_code,title,credits'
User = get_user_model()


def csv_url(plan_id):
    return f'/api/plan-export/{plan_id}/csv/'


def parse(response):
    return list(csv.DictReader(io.StringIO(response.content.decode('utf-8'))))


def entry(term, code, title='Title', credits=4, counted_for=None):
    return {'term': term, 'course_code': code, 'title': title, 'credits': credits, 'counted_for': counted_for}


ENTRIES = [
    entry('Spring 2027', 'CS-UY 2134', 'Advanced Data Structures'),
    entry('Fall 2026', 'CS-UY 2124', 'Object-Oriented Programming'),
    entry('Fall 2026', 'CS-UY 1134', 'Data Structures and Algorithms'),
]


def validator(result=None, error=None):
    """Patch the shared validator that the adapter calls."""
    return patch('plan_export.adapters.validate_entries', return_value=result or [], side_effect=error)


class ExportTests(APITestCase):
    def setUp(self):
        self.client_a, self.user_a = self.signup('a@nyu.edu')
        self.plan = self.make_plan(self.user_a)

    def signup(self, email):
        client = APIClient()
        res = client.post('/api/auth/register/', {'email': email, 'password': 'password123'}, format='json')
        self.assertEqual(res.status_code, 201)
        return client, User.objects.get(email=email)

    def make_plan(self, user, entries=None, name='My plan'):
        return Plan.objects.create(
            user=user, name=name, entries=ENTRIES if entries is None else entries,
            profile_version_at_gen=1, catalog_version_at_gen=1,
        )

    # AC1: header, one row per course, ordered by term, from the persisted plan
    def test_export_downloads_csv_with_header_and_ordered_rows(self):
        with validator():
            res = self.client_a.get(csv_url(self.plan.id))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res['Content-Type'].startswith('text/csv'))
        self.assertIn('attachment', res['Content-Disposition'])
        self.assertEqual(res.content.decode('utf-8').splitlines()[0], HEADER)
        self.assertEqual(
            [(r['term'], r['course_code'], r['title'], r['credits']) for r in parse(res)],
            [
                ('Fall 2026', 'CS-UY 1134', 'Data Structures and Algorithms', '4'),
                ('Fall 2026', 'CS-UY 2124', 'Object-Oriented Programming', '4'),
                ('Spring 2027', 'CS-UY 2134', 'Advanced Data Structures', '4'),
            ],
        )

    def test_rows_are_ordered_chronologically_not_alphabetically(self):
        plan = self.make_plan(self.user_a, [
            entry('Fall 2027', 'CS-UY 2124'), entry('Spring 2027', 'CS-UY 2134'), entry('Fall 2026', 'CS-UY 1134'),
        ])
        with validator():
            res = self.client_a.get(csv_url(plan.id))
        self.assertEqual([r['term'] for r in parse(res)], ['Fall 2026', 'Spring 2027', 'Fall 2027'])

    def test_titles_with_commas_and_quotes_survive(self):
        title = 'Algorithms, Part "II"'
        plan = self.make_plan(self.user_a, [entry('Fall 2026', 'CS-UY 1134', title)])
        with validator():
            res = self.client_a.get(csv_url(plan.id))
        self.assertEqual(parse(res)[0]['title'], title)

    def test_formula_injection_is_neutralised(self):
        title = '=HYPERLINK("http://evil")'
        plan = self.make_plan(self.user_a, [entry('Fall 2026', 'CS-UY 1134', title)])
        with validator():
            res = self.client_a.get(csv_url(plan.id))
        self.assertEqual(parse(res)[0]['title'], "'" + title)

    def test_empty_schedule_exports_header_only(self):
        plan = self.make_plan(self.user_a, [])  # completed courses already satisfy the degree
        with validator():
            res = self.client_a.get(csv_url(plan.id))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode('utf-8').strip(), HEADER)

    def test_export_uses_the_saved_snapshot_not_current_catalog(self):
        Course.objects.create(code='CS-UY 1134', title='Renamed Course', credits=3)
        plan = self.make_plan(self.user_a, [entry('Fall 2026', 'CS-UY 1134', 'Original Title', 4)])
        with validator():
            row = parse(self.client_a.get(csv_url(plan.id)))[0]
        self.assertEqual((row['title'], row['credits']), ('Original Title', '4'))

    # AC2: the shared independent validator runs on exactly the exported entries
    def test_validator_receives_the_exact_saved_entries_and_the_profile(self):
        with validator() as shared:
            res = self.client_a.get(csv_url(self.plan.id))
        self.assertEqual(res.status_code, 200)
        shared.assert_called_once()
        profile, entries = shared.call_args.args
        self.assertEqual(profile, Profile.objects.get(user=self.user_a))
        self.assertEqual(entries, self.plan.entries)

    def test_plan_failing_the_validator_returns_no_csv(self):
        violations = [{'code': 'PREREQ_NOT_MET', 'course': 'CS-UY 2134', 'message': 'CS-UY 2134 needs CS-UY 1134 first'}]
        with validator(violations):
            res = self.client_a.get(csv_url(self.plan.id))
        self.assertEqual(res.status_code, 409)
        self.assertNotIn('Content-Disposition', res)
        error = res.json()['error']
        self.assertEqual(error['code'], 'PLAN_NOT_EXPORTABLE')
        self.assertEqual(error['details'], [{'message': 'CS-UY 2134 needs CS-UY 1134 first'}])

    def test_validation_unavailable_returns_no_csv(self):
        with validator(error=ProgramNotImported('Program not imported')):
            res = self.client_a.get(csv_url(self.plan.id))
        self.assertEqual(res.status_code, 409)
        self.assertNotIn('Content-Disposition', res)
        self.assertIn('Validation unavailable', res.json()['error']['message'])

    # AC3: nothing to export unless a plan was actually saved and it validates
    def test_profile_with_zero_saved_plans_cannot_export(self):
        client, user = self.signup('ready@nyu.edu')
        Profile.objects.filter(user=user).update(credit_limit=15, target_term='Spring 2028')  # ready-ish; no plan saved
        self.assertEqual(Plan.objects.filter(user=user).count(), 0)

        data = client.get(STATUS).json()
        self.assertFalse(data['has_plan'])
        self.assertFalse(data['exportable'])
        self.assertEqual(data['reason'], 'No saved plan')
        self.assertEqual(client.get(csv_url('11111111-1111-4111-8111-111111111111')).status_code, 404)
        self.assertEqual(Plan.objects.filter(user=user).count(), 0)  # nothing was generated

    def test_status_reports_a_valid_saved_plan_as_exportable(self):
        with validator():
            data = self.client_a.get(STATUS).json()
        self.assertTrue(data['exportable'])
        self.assertEqual(data['plan_id'], str(self.plan.id))
        self.assertEqual((data['course_count'], data['term_count']), (3, 2))

    def test_status_for_a_specific_plan(self):
        other = self.make_plan(self.user_a, [entry('Fall 2026', 'CS-UY 1134')], name='Older plan')
        with validator():
            data = self.client_a.get(STATUS, {'plan_id': str(other.id)}).json()
        self.assertEqual(data['plan_id'], str(other.id))
        self.assertEqual(data['course_count'], 1)

    def test_status_not_exportable_when_validation_fails_or_is_unavailable(self):
        with validator([{'code': 'X', 'course': None, 'message': 'bad'}]):
            data = self.client_a.get(STATUS).json()
        self.assertFalse(data['exportable'])
        self.assertEqual(data['reason'], 'Plan fails validation')

        with validator(error=ProgramNotImported('nope')):
            data = self.client_a.get(STATUS).json()
        self.assertFalse(data['exportable'])
        self.assertIn('Validation unavailable', data['reason'])

    # Access control (NFR-1)
    def test_anonymous_gets_401(self):
        self.assertEqual(APIClient().get(STATUS).status_code, 401)
        self.assertEqual(APIClient().get(csv_url(self.plan.id)).status_code, 401)

    def test_other_students_plan_returns_403_not_owner(self):
        client_b, _ = self.signup('b@nyu.edu')
        for res in (client_b.get(csv_url(self.plan.id)), client_b.get(STATUS, {'plan_id': str(self.plan.id)})):
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.json()['error']['code'], 'NOT_OWNER')

    def test_unknown_or_malformed_plan_id_returns_404(self):
        for plan_id in ('11111111-1111-4111-8111-111111111111', 'not-a-uuid'):
            res = self.client_a.get(csv_url(plan_id))
            self.assertEqual(res.status_code, 404, plan_id)
            self.assertEqual(res.json()['error']['code'], 'NOT_FOUND')

    def test_admin_has_no_plan(self):
        User.objects.create_superuser(email='admin@nyu.edu', password='password123')
        admin = APIClient()
        admin.post('/api/auth/login/', {'email': 'admin@nyu.edu', 'password': 'password123'}, format='json')
        data = admin.get(STATUS).json()
        self.assertFalse(data['has_plan'])
        self.assertFalse(data['exportable'])
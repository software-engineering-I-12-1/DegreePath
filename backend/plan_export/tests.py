import csv
import io
from datetime import date
from unittest.mock import patch

from catalog.models import Course
from django.contrib.auth import get_user_model
from profiles.models import Profile
from rest_framework.test import APIClient, APITestCase

from . import adapters

STATUS = '/api/plan-export/status/'
HEADER = 'term,course_code,title,credits'


def csv_url(plan_id):
    return f'/api/plan-export/{plan_id}/csv/'


def parse(response):
    return list(csv.DictReader(io.StringIO(response.content.decode('utf-8'))))


def row(term, code, title='Title', credits=4):
    return {'term': term, 'course_code': code, 'title': title, 'credits': credits}


def fake_plan(profile, rows, feasible=True):
    return {'id': str(profile.id), 'name': 'Test plan', 'feasible': feasible, 'owner_id': profile.user_id, 'rows': rows}


class ExportTests(APITestCase):
    def setUp(self):
        patcher = patch('profiles.terms.today', return_value=date(2026, 10, 27))
        patcher.start()
        self.addCleanup(patcher.stop)
        for code, title in [
            ('CS-UY 1134', 'Data Structures and Algorithms'),
            ('CS-UY 2124', 'Object-Oriented Programming'),
            ('CS-UY 2134', 'Advanced Data Structures'),
            ('MA-UY 1024', 'Calculus I'),
        ]:
            Course.objects.create(code=code, title=title, credits=4)
        self.client_a, self.profile_a = self.signup('a@nyu.edu')

    def signup(self, email, ready=True):
        client = APIClient()
        res = client.post('/api/auth/register/', {'email': email, 'password': 'password123'}, format='json')
        self.assertEqual(res.status_code, 201)
        if ready:
            res = client.put('/api/profiles/me/', {
                'major': 'Computer Science (BS)',
                'credit_limit': 8,
                'target_term': 'Spring 2028',
                'completed_courses': ['MA-UY 1024'],
            }, format='json')
            self.assertEqual(res.status_code, 200)
        return client, Profile.objects.get(user__email=email)

    # AC1: header, one row per course, ordered by term
    def test_export_downloads_csv_with_header_and_ordered_rows(self):
        res = self.client_a.get(csv_url(self.profile_a.id))
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
        rows = [row('Fall 2027', 'CS-UY 2124'), row('Spring 2027', 'CS-UY 2134'), row('Fall 2026', 'CS-UY 1134')]
        with patch('plan_export.adapters.get_plan', return_value=fake_plan(self.profile_a, rows)):
            res = self.client_a.get(csv_url(self.profile_a.id))
        self.assertEqual([r['term'] for r in parse(res)], ['Fall 2026', 'Spring 2027', 'Fall 2027'])

    def test_titles_with_commas_and_quotes_survive(self):
        title = 'Algorithms, Part "II"'
        with patch('plan_export.adapters.get_plan', return_value=fake_plan(self.profile_a, [row('Fall 2026', 'CS-UY 1134', title)])):
            res = self.client_a.get(csv_url(self.profile_a.id))
        self.assertEqual(parse(res)[0]['title'], title)

    def test_formula_injection_is_neutralised(self):
        title = '=HYPERLINK("http://evil")'
        with patch('plan_export.adapters.get_plan', return_value=fake_plan(self.profile_a, [row('Fall 2026', 'CS-UY 1134', title)])):
            res = self.client_a.get(csv_url(self.profile_a.id))
        self.assertEqual(parse(res)[0]['title'], "'" + title)

    # AC2: the exported schedule passes the validator with the student's profile
    def test_exported_schedule_passes_the_validator(self):
        res = self.client_a.get(csv_url(self.profile_a.id))
        self.assertEqual(adapters.validate_plan(parse(res), self.profile_a), [])

    def test_validator_catches_bad_schedules(self):
        p = self.profile_a  # limit 8, target Spring 2028, completed MA-UY 1024, today = Fall 2026
        cases = {
            'not in the catalog': [row('Fall 2026', 'CS-UY 9999')],
            'already completed': [row('Fall 2026', 'MA-UY 1024')],
            'more than once': [row('Fall 2026', 'CS-UY 1134'), row('Spring 2027', 'CS-UY 1134')],
            'in the past': [row('Spring 2026', 'CS-UY 1134')],
            'after the target': [row('Fall 2028', 'CS-UY 1134')],
            'over the limit': [row('Fall 2026', 'CS-UY 1134'), row('Fall 2026', 'CS-UY 2124'), row('Fall 2026', 'CS-UY 2134')],
            'Unknown term': [row('Winter 2027', 'CS-UY 1134')],
        }
        for expected, rows in cases.items():
            problems = adapters.validate_plan(rows, p)
            self.assertTrue(any(expected in x for x in problems), f'{expected}: {problems}')

    # AC3: no export without a saved valid plan
    def test_status_exportable_for_valid_plan(self):
        data = self.client_a.get(STATUS).json()
        self.assertTrue(data['exportable'])
        self.assertTrue(data['has_plan'])
        self.assertEqual(data['plan_id'], str(self.profile_a.id))
        self.assertEqual((data['course_count'], data['term_count']), (3, 2))

    def test_no_saved_plan_is_not_exportable(self):
        client, profile = self.signup('new@nyu.edu', ready=False)
        data = client.get(STATUS).json()
        self.assertFalse(data['has_plan'])
        self.assertFalse(data['exportable'])
        self.assertEqual(data['reason'], 'No saved plan')
        self.assertEqual(client.get(csv_url(profile.id)).status_code, 404)

    def test_infeasible_plan_is_not_exportable(self):
        plan = fake_plan(self.profile_a, [row('Fall 2026', 'CS-UY 1134')], feasible=False)
        with patch('plan_export.adapters.get_current_plan', return_value=plan):
            data = self.client_a.get(STATUS).json()
        self.assertFalse(data['exportable'])
        self.assertEqual(data['reason'], 'Plan is infeasible')

        with patch('plan_export.adapters.get_plan', return_value=plan):
            res = self.client_a.get(csv_url(self.profile_a.id))
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()['error']['code'], 'PLAN_NOT_EXPORTABLE')
        self.assertNotIn('Content-Disposition', res)

    def test_plan_failing_validation_is_not_exportable(self):
        rows = [row('Fall 2026', 'CS-UY 1134'), row('Fall 2026', 'CS-UY 2124'), row('Fall 2026', 'CS-UY 2134')]
        with patch('plan_export.adapters.get_plan', return_value=fake_plan(self.profile_a, rows)):
            res = self.client_a.get(csv_url(self.profile_a.id))
        self.assertEqual(res.status_code, 409)
        error = res.json()['error']
        self.assertEqual(error['code'], 'PLAN_NOT_EXPORTABLE')
        self.assertTrue(any('over the limit' in d['message'] for d in error['details']))

    # Access control (NFR-1)
    def test_anonymous_gets_401(self):
        self.assertEqual(APIClient().get(STATUS).status_code, 401)
        self.assertEqual(APIClient().get(csv_url(self.profile_a.id)).status_code, 401)

    def test_other_students_plan_returns_403_not_owner(self):
        client_b, _ = self.signup('b@nyu.edu')
        res = client_b.get(csv_url(self.profile_a.id))
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.json()['error']['code'], 'NOT_OWNER')

    def test_unknown_or_malformed_plan_id_returns_404(self):
        for plan_id in ('11111111-1111-4111-8111-111111111111', 'not-a-uuid'):
            res = self.client_a.get(csv_url(plan_id))
            self.assertEqual(res.status_code, 404, plan_id)
            self.assertEqual(res.json()['error']['code'], 'NOT_FOUND')

    def test_admin_has_no_plan(self):
        get_user_model().objects.create_superuser(email='admin@nyu.edu', password='password123')
        admin = APIClient()
        admin.post('/api/auth/login/', {'email': 'admin@nyu.edu', 'password': 'password123'}, format='json')
        data = admin.get(STATUS).json()
        self.assertFalse(data['has_plan'])
        self.assertFalse(data['exportable'])
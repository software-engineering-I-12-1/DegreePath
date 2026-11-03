from datetime import date
from unittest.mock import patch

from rest_framework.test import APIClient, APITestCase
from catalog.models import Course

from .models import Profile

ME = '/api/profiles/me/'
REGISTER = '/api/auth/register/'
LOGIN = '/api/auth/login/'
LOGOUT = '/api/auth/logout/'

VALID = {
    'major': 'Computer Science (BS)',
    'credit_limit': 15,
    'target_term': 'Spring 2028',
    'completed_courses': ['CS-UY 1134', 'MA-UY 1024'],
}


def fields(res):
    """Field names that have an error in the response details."""
    return {d['field'] for d in res.json()['error']['details']}


class ProfileTests(APITestCase):
    def setUp(self):
        patcher = patch('profiles.terms.today', return_value=date(2026, 10, 27))
        patcher.start()
        self.addCleanup(patcher.stop)
        Course.objects.create(code='CS-UY 1134', title='Data Structures and Algorithms', credits=4)
        Course.objects.create(code='MA-UY 1024', title='Calculus II', credits=4)

    def signup(self, email='maitri@nyu.edu'):
        client = APIClient()
        res = client.post(REGISTER, {'email': email, 'password': 'password123'}, format='json')
        self.assertEqual(res.status_code, 201)
        return client

    # NFR-1
    def test_anonymous_gets_401(self):
        self.assertEqual(APIClient().get(ME).status_code, 401)
        self.assertEqual(APIClient().put(ME, VALID, format='json').status_code, 401)

    def test_new_user_has_empty_profile_from_registration(self):
        client = self.signup()
        self.assertEqual(Profile.objects.count(), 1)
        data = client.get(ME).json()
        self.assertEqual(data['completed_courses'], [])
        self.assertIsNone(data['credit_limit'])
        self.assertFalse(data['ready'])
        self.assertEqual(data['profile_version'], 1)
        self.assertTrue(data['updated_at'])

    # AC1
    def test_values_survive_sign_out_and_sign_in(self):
        client = self.signup()
        res = client.put(ME, VALID, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['id']), 36)
        self.assertTrue(res.json()['ready'])

        client.post(LOGOUT)
        self.assertEqual(client.get(ME).status_code, 401)

        client.post(LOGIN, {'email': 'maitri@nyu.edu', 'password': 'password123'}, format='json')
        data = client.get(ME).json()
        self.assertEqual(data['major'], 'Computer Science (BS)')
        self.assertEqual(data['credit_limit'], 15)
        self.assertEqual(data['target_term'], 'Spring 2028')
        self.assertEqual(data['completed_courses'], ['CS-UY 1134', 'MA-UY 1024'])

    def test_codes_are_normalised_and_deduplicated(self):
        client = self.signup()
        body = {**VALID, 'completed_courses': ['cs-uy  1134', 'CS-UY 1134', ' ma-uy 1024 ']}
        res = client.put(ME, body, format='json')
        self.assertEqual(res.json()['completed_courses'], ['CS-UY 1134', 'MA-UY 1024'])

    def test_update_does_not_create_second_profile(self):
        client = self.signup()
        client.put(ME, VALID, format='json')
        client.put(ME, {**VALID, 'credit_limit': 12}, format='json')
        self.assertEqual(Profile.objects.count(), 1)
        self.assertEqual(client.get(ME).json()['credit_limit'], 12)

    def test_profile_version_bumps_only_when_a_field_changes(self):
        client = self.signup()
        self.assertEqual(client.put(ME, VALID, format='json').json()['profile_version'], 2)

        # same data again: no bump
        self.assertEqual(client.put(ME, VALID, format='json').json()['profile_version'], 2)

        # same courses, different order and formatting: no bump
        body = {**VALID, 'completed_courses': ['ma-uy 1024', 'CS-UY 1134']}
        self.assertEqual(client.put(ME, body, format='json').json()['profile_version'], 2)

        # real changes: bump each time
        self.assertEqual(client.put(ME, {**VALID, 'credit_limit': 12}, format='json').json()['profile_version'], 3)
        self.assertEqual(
            client.put(ME, {**VALID, 'credit_limit': 12, 'target_term': 'Fall 2028'}, format='json').json()['profile_version'],
            4,
        )
        body = {**VALID, 'credit_limit': 12, 'target_term': 'Fall 2028', 'completed_courses': ['CS-UY 1134']}
        self.assertEqual(client.put(ME, body, format='json').json()['profile_version'], 5)
    def test_rejected_save_does_not_bump_version(self):
        client = self.signup()
        client.put(ME, {**VALID, 'credit_limit': 0}, format='json')
        self.assertEqual(client.get(ME).json()['profile_version'], 1)

    # AC2
    def test_unknown_course_rejected_and_profile_unchanged(self):
        client = self.signup()
        client.put(ME, VALID, format='json')

        bad = {**VALID, 'credit_limit': 18, 'completed_courses': ['CS-UY 1134', 'CS-UY 9999']}
        res = client.put(ME, bad, format='json')
        self.assertEqual(res.status_code, 400)
        error = res.json()['error']
        self.assertEqual(error['code'], 'UNKNOWN_COURSE')
        self.assertIn('CS-UY 9999', error['message'])
        self.assertEqual(fields(res), {'completed_courses'})

        data = client.get(ME).json()
        self.assertEqual(data['credit_limit'], 15)
        self.assertEqual(data['completed_courses'], ['CS-UY 1134', 'MA-UY 1024'])

    # AC3
    def test_credit_limit_out_of_range_or_not_whole(self):
        client = self.signup()
        for value in (0, 30, 25, 15.5, 'abc', None):
            res = client.put(ME, {**VALID, 'credit_limit': value}, format='json')
            self.assertEqual(res.status_code, 400, value)
            self.assertEqual(res.json()['error']['code'], 'VALIDATION_ERROR', value)
            self.assertIn('credit_limit', fields(res), value)
        profile = Profile.objects.get()
        self.assertIsNone(profile.credit_limit)
        self.assertEqual(profile.profile_version, 1)

    def test_credit_limit_boundaries_accepted(self):
        client = self.signup()
        for value in (1, 24):
            self.assertEqual(client.put(ME, {**VALID, 'credit_limit': value}, format='json').status_code, 200)

    def test_past_target_term_rejected(self):
        client = self.signup()
        res = client.put(ME, {**VALID, 'target_term': 'Spring 2026'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('target_term', fields(res))
        self.assertEqual(Profile.objects.get().target_term, '')

    def test_current_term_accepted(self):
        client = self.signup()
        res = client.put(ME, {**VALID, 'target_term': 'fall 2026'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['target_term'], 'Fall 2026')

    def test_malformed_term_rejected(self):
        client = self.signup()
        res = client.put(ME, {**VALID, 'target_term': 'Winter 2028'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('target_term', fields(res))

    def test_multiple_field_errors_reported_together(self):
        client = self.signup()
        res = client.put(ME, {**VALID, 'credit_limit': 0, 'target_term': 'Spring 2020'}, format='json')
        self.assertEqual(res.json()['error']['code'], 'VALIDATION_ERROR')
        self.assertEqual(fields(res), {'credit_limit', 'target_term'})

    # NFR-1: ownership
    def test_users_cannot_see_each_others_profiles_via_me(self):
        a = self.signup('a@nyu.edu')
        b = self.signup('b@nyu.edu')
        a.put(ME, VALID, format='json')
        self.assertEqual(b.get(ME).json()['completed_courses'], [])
        self.assertNotEqual(a.get(ME).json()['id'], b.get(ME).json()['id'])

    def test_owner_can_get_and_put_by_id(self):
        client = self.signup()
        pid = client.get(ME).json()['id']
        self.assertEqual(client.get(f'/api/profiles/{pid}/').status_code, 200)
        res = client.put(f'/api/profiles/{pid}/', VALID, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['credit_limit'], 15)

    def test_other_students_profile_id_returns_403_not_owner(self):
        a = self.signup('a@nyu.edu')
        b = self.signup('b@nyu.edu')
        a.put(ME, VALID, format='json')
        a_id = a.get(ME).json()['id']

        for res in (b.get(f'/api/profiles/{a_id}/'), b.put(f'/api/profiles/{a_id}/', {**VALID, 'credit_limit': 3}, format='json')):
            self.assertEqual(res.status_code, 403)
            self.assertEqual(res.json()['error']['code'], 'NOT_OWNER')
        self.assertEqual(a.get(ME).json()['credit_limit'], 15)

    def test_unknown_profile_id_returns_404(self):
        client = self.signup()
        res = client.get('/api/profiles/11111111-1111-4111-8111-111111111111/')
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()['error']['code'], 'NOT_FOUND')

    def test_anonymous_gets_401_on_profile_by_id(self):
        pid = self.signup().get(ME).json()['id']
        self.assertEqual(APIClient().get(f'/api/profiles/{pid}/').status_code, 401)
        self.assertEqual(APIClient().put(f'/api/profiles/{pid}/', VALID, format='json').status_code, 401)
from datetime import date
from unittest.mock import patch

from rest_framework.test import APIClient, APITestCase
from catalog.models import Course

from .models import Profile

PROFILE = '/api/profile/'
REGISTER = '/api/auth/register/'
LOGIN = '/api/auth/login/'
LOGOUT = '/api/auth/logout/'

VALID = {
    'major': 'Computer Science (BS)',
    'credit_limit': 15,
    'target_term': 'Spring 2028',
    'completed_courses': ['CS-UY 1134', 'MA-UY 1024'],
}


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
        self.assertEqual(APIClient().get(PROFILE).status_code, 401)
        self.assertEqual(APIClient().put(PROFILE, VALID, format='json').status_code, 401)

    def test_new_user_sees_empty_profile(self):
        res = self.signup().get(PROFILE)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['completed_courses'], [])
        self.assertIsNone(res.json()['credit_limit'])

    # AC1
    def test_values_survive_sign_out_and_sign_in(self):
        client = self.signup()
        res = client.put(PROFILE, VALID, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()['id']), 36)

        client.post(LOGOUT)
        self.assertEqual(client.get(PROFILE).status_code, 401)

        client.post(LOGIN, {'email': 'maitri@nyu.edu', 'password': 'password123'}, format='json')
        data = client.get(PROFILE).json()
        self.assertEqual(data['major'], 'Computer Science (BS)')
        self.assertEqual(data['credit_limit'], 15)
        self.assertEqual(data['target_term'], 'Spring 2028')
        self.assertEqual(data['completed_courses'], ['CS-UY 1134', 'MA-UY 1024'])

    def test_codes_are_normalised_and_deduplicated(self):
        client = self.signup()
        body = {**VALID, 'completed_courses': ['cs-uy  1134', 'CS-UY 1134', ' ma-uy 1024 ']}
        res = client.put(PROFILE, body, format='json')
        self.assertEqual(res.json()['completed_courses'], ['CS-UY 1134', 'MA-UY 1024'])

    def test_update_does_not_create_second_profile(self):
        client = self.signup()
        client.put(PROFILE, VALID, format='json')
        client.put(PROFILE, {**VALID, 'credit_limit': 12}, format='json')
        self.assertEqual(Profile.objects.count(), 1)
        self.assertEqual(client.get(PROFILE).json()['credit_limit'], 12)

    # AC2
    def test_unknown_course_rejected_and_profile_unchanged(self):
        client = self.signup()
        client.put(PROFILE, VALID, format='json')

        bad = {**VALID, 'credit_limit': 18, 'completed_courses': ['CS-UY 1134', 'CS-UY 9999']}
        res = client.put(PROFILE, bad, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('CS-UY 9999', res.json()['errors']['completed_courses'])

        data = client.get(PROFILE).json()
        self.assertEqual(data['credit_limit'], 15)
        self.assertEqual(data['completed_courses'], ['CS-UY 1134', 'MA-UY 1024'])

    # AC3
    def test_credit_limit_out_of_range_or_not_whole(self):
        client = self.signup()
        for value in (0, 30, 25, 15.5, 'abc', None):
            res = client.put(PROFILE, {**VALID, 'credit_limit': value}, format='json')
            self.assertEqual(res.status_code, 400, value)
            self.assertIn('credit_limit', res.json()['errors'], value)
        self.assertEqual(Profile.objects.count(), 0)

    def test_credit_limit_boundaries_accepted(self):
        client = self.signup()
        for value in (1, 24):
            self.assertEqual(client.put(PROFILE, {**VALID, 'credit_limit': value}, format='json').status_code, 200)

    def test_past_target_term_rejected(self):
        client = self.signup()
        res = client.put(PROFILE, {**VALID, 'target_term': 'Spring 2026'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('target_term', res.json()['errors'])
        self.assertEqual(Profile.objects.count(), 0)

    def test_current_term_accepted(self):
        client = self.signup()
        res = client.put(PROFILE, {**VALID, 'target_term': 'fall 2026'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['target_term'], 'Fall 2026')

    def test_malformed_term_rejected(self):
        client = self.signup()
        res = client.put(PROFILE, {**VALID, 'target_term': 'Winter 2028'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('target_term', res.json()['errors'])

    def test_multiple_field_errors_reported_together(self):
        client = self.signup()
        res = client.put(PROFILE, {**VALID, 'credit_limit': 0, 'target_term': 'Spring 2020'}, format='json')
        self.assertEqual(set(res.json()['errors']), {'credit_limit', 'target_term'})

    # NFR-1
    def test_users_cannot_see_each_others_profiles(self):
        a = self.signup('a@nyu.edu')
        b = self.signup('b@nyu.edu')
        a.put(PROFILE, VALID, format='json')
        self.assertEqual(b.get(PROFILE).json()['completed_courses'], [])
        self.assertIsNone(b.get(PROFILE).json()['id'])

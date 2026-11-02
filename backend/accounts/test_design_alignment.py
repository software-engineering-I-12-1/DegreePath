from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from profiles.models import Profile

User = get_user_model()

REGISTER = '/api/auth/register/'
LOGIN = '/api/auth/login/'


class DesignAlignmentTests(APITestCase):
    def register(self, email='maitri@nyu.edu', password='password123'):
        return self.client.post(REGISTER, {'email': email, 'password': password}, format='json')

    def test_register_returns_user_id_role_and_profile_id(self):
        body = self.register().json()
        self.assertEqual(body['user_id'], User.objects.get().pk)
        self.assertEqual(body['role'], 'student')
        self.assertEqual(body['profile_id'], str(Profile.objects.get().id))

    def test_register_creates_empty_profile(self):
        self.register()
        profile = Profile.objects.get()
        self.assertEqual(profile.user.email, 'maitri@nyu.edu')
        self.assertEqual(profile.major, '')
        self.assertIsNone(profile.credit_limit)
        self.assertEqual(profile.completed_courses, [])
        self.assertFalse(profile.is_ready)

    def test_failed_registration_creates_no_profile(self):
        self.register(password='short')
        self.assertEqual(Profile.objects.count(), 0)

    def test_invalid_email_error_envelope(self):
        err = self.register(email='nope').json()['error']
        self.assertEqual(err['code'], 'INVALID_EMAIL')
        self.assertTrue(err['message'])
        self.assertIsInstance(err['details'], list)

    def test_password_too_short_error_envelope(self):
        res = self.register(password='short')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error']['code'], 'PASSWORD_TOO_SHORT')

    def test_email_taken_error_envelope(self):
        self.register()
        res = self.register(email='MAITRI@nyu.edu')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()['error']['code'], 'EMAIL_TAKEN')

    def test_invalid_credentials_error_envelope(self):
        self.register()
        res = APIClient().post(LOGIN, {'email': 'maitri@nyu.edu', 'password': 'wrongpass1'}, format='json')
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()['error']['code'], 'INVALID_CREDENTIALS')

    def test_admin_role(self):
        User.objects.create_superuser(email='admin@nyu.edu', password='password123')
        res = APIClient().post(LOGIN, {'email': 'admin@nyu.edu', 'password': 'password123'}, format='json')
        self.assertEqual(res.json()['role'], 'admin')
from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

REGISTER = '/api/auth/register/'
LOGIN = '/api/auth/login/'
LOGOUT = '/api/auth/logout/'
ME = '/api/auth/me/'


class AuthTests(APITestCase):
    def register(self, client=None, email='maitri@nyu.edu', password='password123'):
        client = client or self.client
        return client.post(REGISTER, {'email': email, 'password': password}, format='json')

    # AC1
    def test_register_creates_account_and_signs_in(self):
        res = self.register()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.count(), 1)
        self.assertIn('_auth_user_id', self.client.session)
        me = self.client.get(ME)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['email'], 'maitri@nyu.edu')

    def test_register_rejects_short_password(self):
        res = self.register(password='short12')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_register_rejects_invalid_email(self):
        res = self.register(email='not-an-email')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    # AC2
    def test_wrong_password_gives_error_and_no_session(self):
        self.register()
        client = APIClient()
        res = client.post(LOGIN, {'email': 'maitri@nyu.edu', 'password': 'wrongpass1'}, format='json')
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()['error'], 'Incorrect email or password')
        self.assertNotIn('_auth_user_id', client.session)

    def test_unknown_email_gives_same_error(self):
        res = APIClient().post(LOGIN, {'email': 'nobody@nyu.edu', 'password': 'password123'}, format='json')
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.json()['error'], 'Incorrect email or password')

    def test_login_with_correct_password(self):
        self.register()
        client = APIClient()
        res = client.post(LOGIN, {'email': 'Maitri@NYU.edu', 'password': 'password123'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(client.get(ME).status_code, 200)

    # AC3
    def test_duplicate_email_rejected_case_insensitive(self):
        self.register()
        res = self.register(client=APIClient(), email='MAITRI@nyu.edu')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()['error'], 'Email already registered')
        self.assertEqual(User.objects.count(), 1)

    # AC4 (backend half: anonymous gets 401; frontend does the redirect)
    def test_anonymous_me_is_401(self):
        self.assertEqual(APIClient().get(ME).status_code, 401)

    def test_logout_ends_session(self):
        self.register()
        self.assertEqual(self.client.post(LOGOUT).status_code, 204)
        self.assertEqual(self.client.get(ME).status_code, 401)

    # NFR-2
    def test_password_is_argon2id_hashed(self):
        self.register()
        user = User.objects.get()
        self.assertTrue(user.password.startswith('argon2$argon2id$'))
        self.assertNotIn('password123', user.password)

    def test_session_cookie_24h_and_httponly(self):
        self.register()
        cookie = self.client.cookies['sessionid']
        self.assertEqual(int(cookie['max-age']), 86400)
        self.assertTrue(cookie['httponly'])

    def test_csrf_enforced_on_register(self):
        client = APIClient(enforce_csrf_checks=True)
        res = client.post(REGISTER, {'email': 'a@nyu.edu', 'password': 'password123'}, format='json')
        self.assertEqual(res.status_code, 403)
        client.get('/api/auth/csrf/')
        token = client.cookies['csrftoken'].value
        res = client.post(
            REGISTER,
            {'email': 'a@nyu.edu', 'password': 'password123'},
            format='json',
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(res.status_code, 201)
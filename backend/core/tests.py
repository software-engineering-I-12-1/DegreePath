from django.test import TestCase, Client
from django.conf import settings
from django.urls import reverse

class HealthCheckAndConfigTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_check_endpoint(self):
        """Verify the health check endpoint returns status 200 and database is healthy."""
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertEqual(data.get('app'), 'DegreePath')
        self.assertEqual(data.get('database'), 'healthy')

    def test_csrf_cookie_endpoint(self):
        """Verify GET /api/auth/csrf/ returns 204 and sets csrftoken cookie."""
        response = self.client.get(reverse('csrf_cookie'))
        self.assertEqual(response.status_code, 204)
        self.assertIn('csrftoken', response.cookies)

    def test_nfr2_argon2_password_hasher(self):
        """Verify NFR-2: Argon2id is configured as the primary password hasher."""
        primary_hasher = settings.PASSWORD_HASHERS[0]
        self.assertEqual(
            primary_hasher,
            'django.contrib.auth.hashers.Argon2PasswordHasher',
            "Argon2id must be the primary password hasher according to NFR-2"
        )

    def test_nfr2_session_duration(self):
        """Verify NFR-2: Sessions expire after 24 hours (86,400 seconds)."""
        self.assertEqual(settings.SESSION_COOKIE_AGE, 86400)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)

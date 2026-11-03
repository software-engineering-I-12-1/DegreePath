from rest_framework.test import APIClient, APITestCase


class ErrorEnvelopeTests(APITestCase):
    def assert_envelope(self, res, http_status, code):
        self.assertEqual(res.status_code, http_status)
        error = res.json()['error']
        self.assertEqual(error['code'], code)
        self.assertTrue(error['message'])
        self.assertIsInstance(error['details'], list)

    def test_anonymous_request_is_401_envelope(self):
        self.assert_envelope(APIClient().get('/api/profiles/me/'), 401, 'UNAUTHENTICATED')

    def test_missing_csrf_token_is_403_envelope(self):
        client = APIClient(enforce_csrf_checks=True)
        res = client.post('/api/auth/register/', {'email': 'a@nyu.edu', 'password': 'password123'}, format='json')
        self.assert_envelope(res, 403, 'FORBIDDEN')

    def test_malformed_json_is_400_envelope(self):
        res = APIClient().post('/api/auth/login/', data='{bad json', content_type='application/json')
        self.assert_envelope(res, 400, 'VALIDATION_ERROR')

    def test_non_uuid_profile_id_is_404_envelope(self):
        client = APIClient()
        client.post('/api/auth/register/', {'email': 'a@nyu.edu', 'password': 'password123'}, format='json')
        self.assert_envelope(client.get('/api/profiles/not-a-uuid/'), 404, 'NOT_FOUND')
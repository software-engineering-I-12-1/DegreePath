import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Course
from profiles.models import Profile
from .models import Plan


class SavedPlanTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('owner@example.com', 'password123')
        self.other = get_user_model().objects.create_user('other@example.com', 'password123')
        self.profile = Profile.objects.create(
            user=self.user, major='Computer Science', credit_limit=15, target_term='Spring 2028',
        )
        self.course = Course.objects.create(code='CS 1000', title='Programming', credits=4)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.payload = {'name': 'Graduation plan', 'entries': [
            {'term': 'Spring 2028', 'course_code': 'cs 1000'},
        ]}

    def create_saved_plan(self):
        with patch('plans.views.validate_plan', return_value=[]) as validator:
            response = self.client.post('/api/plans/', self.payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        validator.assert_called_once()
        return response.data

    def test_save_and_reopen_after_new_session_and_catalog_edit(self):
        saved = self.create_saved_plan()
        self.course.title = 'Changed title'
        self.course.credits = 3
        self.course.save()
        self.client.force_authenticate(user=None)
        self.client.login(email='owner@example.com', password='password123')
        response = self.client.get(f"/api/plans/{saved['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, saved)
        self.assertEqual(saved['entries'][0]['title'], 'Programming')
        self.assertEqual(saved['entries'][0]['credits'], 4)
        self.assertEqual(saved['profile_version_at_gen'], self.profile.profile_version)

    def test_lists_only_own_plans_and_denies_other_owner(self):
        saved = self.create_saved_plan()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/plans/').data, {'results': []})
        response = self.client.get(f"/api/plans/{saved['id']}/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['error']['code'], 'NOT_OWNER')
        self.assertNotIn('entries', response.data)

    def test_unavailable_validator_prevents_persistence(self):
        response = self.client.post('/api/plans/', self.payload, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['error']['code'], 'VALIDATION_UNAVAILABLE')
        self.assertFalse(Plan.objects.exists())

    def test_invalid_plan_is_revalidated_and_not_saved(self):
        violations = [{'field': 'entries', 'message': 'Degree pool minimum not met.'}]
        with patch('plans.views.validate_plan', return_value=violations):
            response = self.client.post('/api/plans/', self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['details'], violations)
        self.assertFalse(Plan.objects.exists())

    def test_validator_failure_rolls_back(self):
        with patch('plans.views.validate_plan', side_effect=RuntimeError('Validation failed')):
            with self.assertRaises(RuntimeError):
                self.client.post('/api/plans/', self.payload, format='json')
        self.assertFalse(Plan.objects.exists())

    def test_rejects_malformed_and_duplicate_entries(self):
        invalid = [[], {}, None, [{'term': 'Tomorrow', 'course_code': 'CS 1000'}],
                   self.payload['entries'] * 2]
        for entries in invalid:
            with self.subTest(entries=entries):
                response = self.client.post('/api/plans/', {**self.payload, 'entries': entries}, format='json')
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Plan.objects.exists())

    def test_unknown_course_is_not_saved(self):
        self.payload['entries'][0]['course_code'] = 'UNKNOWN'
        with patch('plans.views.validate_plan', return_value=[]):
            response = self.client.post('/api/plans/', self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Plan.objects.exists())

    def test_requires_ready_profile(self):
        self.profile.credit_limit = None
        self.profile.save()
        response = self.client.post('/api/plans/', self.payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'PROFILE_INCOMPLETE')

    def test_unknown_plan_returns_404(self):
        response = self.client.get(f'/api/plans/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, 404)

    def test_anonymous_and_admin_access(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get('/api/plans/').status_code, 401)
        self.assertEqual(self.client.post('/api/plans/', self.payload, format='json').status_code, 401)
        self.user.is_staff = True
        self.user.save()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/api/plans/').status_code, 403)
        self.assertEqual(self.client.post('/api/plans/', self.payload, format='json').status_code, 403)

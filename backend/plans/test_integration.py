from copy import deepcopy
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Corequisite, DegreeProgram
from planner.test_api import add_course, add_requirement
from profiles.models import Profile
from .models import Plan


class SaveGeneratedPlanTests(TestCase):
    def setUp(self):
        clock = patch('profiles.terms.today', return_value=date(2026, 11, 17))
        clock.start()
        self.addCleanup(clock.stop)
        add_course('CS 1000', 'Programming')
        add_course('CS 2000', 'Data Structures', prereqs=(('CS 1000',),))
        lecture = add_course('CS 3000', 'Databases', seasons=('Spring',), prereqs=(('CS 2000',),))
        lab = add_course('CS 3001', 'Database Lab', credits=1, seasons=('Spring',))
        Corequisite.objects.create(course=lecture, coreq_course=lab)
        self.program = DegreeProgram.objects.create(name='CS Demo', max_elective_pools_per_course=2)
        add_requirement(self.program, 'Core', 'required', ['CS 1000', 'CS 2000', 'CS 3000'], 0)
        add_requirement(self.program, 'Systems', 'pool', ['CS 3000'], 1, choose_n=1)
        add_requirement(self.program, 'Practical', 'pool', ['CS 3000'], 2, choose_n=1)
        add_requirement(self.program, 'Upper-level', 'credit_threshold', [], 3,
                        min_credits=4, min_level=3000)
        self.user = get_user_model().objects.create_user('integration@example.com', 'password123')
        self.profile = Profile.objects.create(
            user=self.user, major='CS Demo', credit_limit=12, target_term='Fall 2028',
        )
        self.client = APIClient()
        self.client.force_login(self.user)

    def generate_entries(self):
        response = self.client.post('/api/plans/generate/', format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'valid')
        return [
            {'course_code': course['code'], 'term': term['term'], 'counted_for': course['counted_for']}
            for term in response.data['terms'] for course in term['courses']
        ]

    def save(self, entries):
        return self.client.post('/api/plans/', {'name': 'My degree plan', 'entries': entries}, format='json')

    def test_generate_save_sign_in_list_and_reopen_with_multiple_pools(self):
        entries = self.generate_entries()
        self.assertEqual(self.client.get('/api/plans/').data, {'results': []})
        response = self.save(entries)
        self.assertEqual(response.status_code, 201, response.data)
        saved = response.data
        database = next(entry for entry in saved['entries'] if entry['course_code'] == 'CS 3000')
        self.assertEqual(set(database['counted_for']), {'Systems', 'Practical'})
        self.client.logout()
        self.assertEqual(self.client.get(f"/api/plans/{saved['id']}/").status_code, 401)
        self.assertTrue(self.client.login(email=self.user.email, password='password123'))
        self.assertEqual(self.client.get('/api/plans/').data['results'], [saved])
        self.assertEqual(self.client.get(f"/api/plans/{saved['id']}/").data, saved)

    def test_tampered_schedule_cannot_be_saved(self):
        original = self.generate_entries()
        cases = {}
        entries = deepcopy(original)
        next(entry for entry in entries if entry['course_code'] == 'CS 2000')['term'] = 'Spring 2027'
        cases['PREREQ'] = entries
        entries = deepcopy(original)
        next(entry for entry in entries if entry['course_code'] == 'CS 3000')['term'] = 'Fall 2028'
        cases['NOT_OFFERED'] = entries
        entries = deepcopy(original)
        for entry in entries:
            entry['counted_for'] = None
        cases['POOL_MINIMUM'] = entries
        cases['COREQ'] = [entry for entry in original if entry['course_code'] != 'CS 3001']
        for code, entries in cases.items():
            with self.subTest(code=code):
                response = self.save(entries)
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn(code, {error['code'] for error in response.data['error']['details']})
                self.assertFalse(Plan.objects.exists())

    def test_current_profile_is_used_when_saving_an_older_generated_plan(self):
        entries = self.generate_entries()
        self.profile.credit_limit = 1
        self.profile.profile_version += 1
        self.profile.save()
        response = self.save(entries)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Plan.objects.exists())

    def test_current_requirement_definition_is_used_before_saving(self):
        entries = self.generate_entries()
        self.program.max_elective_pools_per_course = 1
        self.program.save()
        response = self.save(entries)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('POOL_ALLOCATION', {error['code'] for error in response.data['error']['details']})
        self.assertFalse(Plan.objects.exists())

    def test_empty_generated_schedule_saves_when_degree_is_already_complete(self):
        self.profile.completed_courses = ['CS 1000', 'CS 2000', 'CS 3000', 'CS 3001']
        self.profile.save()
        entries = self.generate_entries()
        self.assertEqual(entries, [])
        response = self.save(entries)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['entries'], [])

    def test_malformed_pool_allocations_return_400(self):
        entries = self.generate_entries()
        for value in ({'pool': 'Systems'}, [1], True, ['Systems', 'Systems']):
            with self.subTest(value=value):
                entries[0]['counted_for'] = value
                self.assertEqual(self.save(entries).status_code, 400)
        self.assertFalse(Plan.objects.exists())

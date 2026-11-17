"""The larger CSV demo can be imported and planned through the public APIs."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase

from catalog.models import Course, DegreeProgram
from profiles.models import Profile


HERE = Path(__file__).resolve().parent
PROGRAM = 'Computer Science (BS Demo)'


class FullMajorDemoTests(APITestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user(
            email='demo-admin@example.com', password='password123', is_staff=True,
        )
        admin_client = APIClient()
        admin_client.force_login(admin)
        for filename, url in (
            ('demo_full_major_courses.csv', '/api/admin/catalog-imports/'),
            ('demo_full_major_requirements.json', '/api/admin/requirement-imports/'),
        ):
            response = admin_client.post(
                url,
                {'file': SimpleUploadedFile(filename, (HERE / filename).read_bytes())},
                format='multipart',
            )
            self.assertEqual(response.status_code, 201, response.json())

    def test_csv_and_requirements_import(self):
        self.assertEqual(Course.objects.count(), 25)
        program = DegreeProgram.objects.get(name=PROGRAM)
        self.assertEqual(program.max_elective_pools_per_course, 2)
        self.assertEqual(program.requirements.count(), 6)
        self.assertEqual(
            set(Course.objects.get(code='CS-UY 4711').offerings.values_list('season', flat=True)),
            {'Fall'},
        )

    def test_plan_shows_double_counting(self):
        student = get_user_model().objects.create_user(
            email='demo-student@example.com', password='password123',
        )
        profile, _ = Profile.objects.get_or_create(user=student)
        profile.major = PROGRAM
        profile.credit_limit = 12
        profile.target_term = 'Spring 2031'
        profile.save()
        student_client = APIClient()
        student_client.force_login(student)
        with patch('profiles.terms.today', return_value=date(2026, 11, 16)):
            response = student_client.post('/api/plans/generate/', format='json')

        self.assertEqual(response.status_code, 200, response.json())
        plan = response.json()
        self.assertEqual(plan['status'], 'valid')
        self.assertEqual(plan['unenforced_requirements'], [])
        courses = [course for term in plan['terms'] for course in term['courses']]
        self.assertGreaterEqual(sum(course['credits'] for course in courses), 36)
        capstone = next(course for course in courses if course['code'] == 'CS-UY 4713')
        self.assertEqual(capstone['counted_for'], ['Advanced core', 'Capstone'])

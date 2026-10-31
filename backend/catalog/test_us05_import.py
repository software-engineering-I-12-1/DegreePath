"""US-05 acceptance tests for CSV/JSON import and admin permissions."""

import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase

from .models import Course, CourseOffering, PrereqClause


IMPORT_URL = '/api/admin/catalog-imports/'


def upload(name, content):
    return SimpleUploadedFile(name, content.encode('utf-8'))


class CatalogImportTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            email='admin@nyu.edu', password='password123', is_staff=True,
        )
        self.student = user_model.objects.create_user(
            email='student@nyu.edu', password='password123',
        )
        self.client.force_login(self.admin)

    def test_ac1_csv_import_reports_three_courses_and_lists_them(self):
        csv_text = (
            'code,title,credits,offerings\n'
            'CS-UY 1114,Intro to Programming,4,"Fall,Spring"\n'
            'CS-UY 1134,Data Structures,4,Spring\n'
            'MA-UY 1024,Calculus II,4,Fall\n'
        )
        response = self.client.post(IMPORT_URL, {'file': upload('courses.csv', csv_text)}, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['message'], '3 courses imported')
        self.assertEqual(Course.objects.count(), 3)
        self.assertEqual(len(self.client.get('/api/courses/').json()['results']), 3)
        self.assertEqual(
            list(CourseOffering.objects.filter(course__code='CS-UY 1114').values_list('season', flat=True)),
            ['Fall', 'Spring'],
        )

    def test_json_file_import_is_supported(self):
        data = [{'code': 'CS-UY 1114', 'title': 'Intro', 'credits': 4, 'offerings': ['Fall']}]
        response = self.client.post(
            IMPORT_URL, {'file': upload('courses.json', json.dumps({'courses': data}))}, format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Course.objects.get().code, 'CS-UY 1114')

    def test_ac2_missing_or_non_numeric_credits_rolls_back_batch(self):
        for bad in ('', 'abc'):
            with self.subTest(bad=bad):
                csv_text = (
                    'code,title,credits,offerings\n'
                    'CS-UY 1114,Intro,4,Fall\n'
                    f'CS-UY 1134,Data Structures,{bad},Spring\n'
                )
                response = self.client.post(IMPORT_URL, {'file': upload('bad.csv', csv_text)}, format='multipart')
                self.assertEqual(response.status_code, 400)
                self.assertIn({'row': 3, 'column': 'credits'}, [
                    {'row': e['row'], 'column': e['column']} for e in response.json()['error']['details']
                ])
                self.assertEqual(Course.objects.count(), 0)

    def test_ac3_existing_course_is_updated_without_duplicate(self):
        Course.objects.create(code='CS-UY 1114', title='Old title', credits=3)
        response = self.client.post(
            IMPORT_URL,
            {'file': upload('update.csv', 'code,title,credits,offerings\nCS-UY 1114,Intro,4,Spring\n')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['updated'], 1)
        self.assertEqual(Course.objects.count(), 1)
        course = Course.objects.get()
        self.assertEqual(course.credits, 4)
        self.assertEqual(list(course.offerings.values_list('season', flat=True)), ['Spring'])

    def test_reimport_without_prerequisites_keeps_existing_requirements(self):
        earlier = Course.objects.create(code='CS-UY 1114', title='Intro', credits=4)
        advanced = Course.objects.create(code='CS-UY 1134', title='Data Structures', credits=4)
        clause = PrereqClause.objects.create(course=advanced, position=0)
        clause.options.create(required_course=earlier)
        response = self.client.post(
            IMPORT_URL,
            {'file': upload('update.csv', 'code,title,credits,offerings\nCS-UY 1134,Data Structures,4,Fall\n')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(advanced.prereq_clauses.count(), 1)

    def test_ac4_student_cannot_import(self):
        client = APIClient()
        client.force_login(self.student)
        response = client.post(
            IMPORT_URL,
            {'file': upload('courses.csv', 'code,title,credits,offerings\nCS-UY 1114,Intro,4,Fall\n')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Course.objects.count(), 0)

    def test_anonymous_cannot_import(self):
        self.assertEqual(APIClient().post(IMPORT_URL, [], format='json').status_code, 401)

    def test_ac5_invalid_offering_reports_row_and_value_and_rolls_back(self):
        response = self.client.post(
            IMPORT_URL,
            {'file': upload('bad.csv',
                'code,title,credits,offerings\n'
                'CS-UY 1114,Intro,4,Fall\n'
                'CS-UY 1134,Data Structures,4,Summer\n')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            {'row': 3, 'column': 'offerings', 'value': 'Summer'},
            [{key: e[key] for key in ('row', 'column', 'value')} for e in response.json()['error']['details']],
        )
        self.assertEqual(Course.objects.count(), 0)

    def test_imported_courses_feed_student_profile_options(self):
        self.client.post(
            IMPORT_URL,
            {'file': upload('courses.csv', 'code,title,credits,offerings\nCS-UY 1114,Intro,4,Fall\n')},
            format='multipart',
        )
        self.client.force_login(self.student)
        options = self.client.get('/api/profile/options/').json()
        self.assertEqual(options['courses'], [{'code': 'CS-UY 1114', 'title': 'Intro'}])

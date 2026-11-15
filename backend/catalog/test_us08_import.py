"""US-08 acceptance tests: importing degree requirements (required courses, pools, credit thresholds)."""

import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase

from .models import CatalogImport, CatalogState, Course, DegreeProgram, Requirement, RequirementCourse


IMPORT_URL = '/api/admin/requirement-imports/'
PROGRAMS_URL = '/api/programs/'

CORE = [f'CS-UY {n}' for n in (1114, 1134, 2124, 2214, 2413, 3224, 3393, 4513)]
SYSTEMS = [f'CS-UY {n}' for n in (3083, 3254, 3314, 3923, 4523, 4793)]


def upload(name, content):
    return SimpleUploadedFile(name, content.encode('utf-8'))


def pilot_major(**overrides):
    """The AC1 definition: 8 required courses, choose 3 from 6, and 12 credits at 3000-level or above."""
    data = {
        'program': 'Computer Science (BS)',
        'kind': 'major',
        'requirements': [
            {'name': 'Core courses', 'type': 'required', 'courses': CORE},
            {'name': 'Systems electives', 'type': 'pool', 'choose_n': 3, 'courses': SYSTEMS},
            {'name': 'Upper-level credits', 'type': 'credit_threshold', 'min_credits': 12, 'min_level': 3000},
        ],
    }
    data.update(overrides)
    return data


class RequirementImportTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(email='admin@nyu.edu', password='password123', is_staff=True)
        self.student = user_model.objects.create_user(email='student@nyu.edu', password='password123')
        for code in CORE + SYSTEMS:
            Course.objects.create(code=code, title=f'Course {code}', credits=4)
        self.client.force_login(self.admin)

    def import_file(self, data, name='requirements.json'):
        return self.client.post(IMPORT_URL, {'file': upload(name, json.dumps(data))}, format='multipart')

    def stored_rules(self):
        """Everything a rejected import must leave untouched: programs, rules, rule courses and the catalog version."""
        return (
            sorted(DegreeProgram.objects.values_list('name', 'kind')),
            sorted(Requirement.objects.values_list('program__name', 'name', 'type', 'choose_n', 'min_credits', 'min_level')),
            sorted(RequirementCourse.objects.values_list('requirement__name', 'course__code')),
            list(CatalogState.objects.values_list('catalog_version', flat=True)),
        )

    def assert_rejected(self, response, message):
        self.assertEqual(response.status_code, 400)
        error = response.json()['error']
        self.assertEqual(error['code'], 'IMPORT_REJECTED')
        self.assertIn(message, [detail['message'] for detail in error['details']])
        self.assertEqual(CatalogImport.objects.get(id=error['import_id']).status, 'rejected')

    def test_ac1_summary_shows_required_pool_and_threshold_rules(self):
        response = self.import_file(pilot_major())

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['message'], '3 requirements imported for Computer Science (BS)')
        rules = {rule['name']: rule for rule in body['summary']['requirements']}
        self.assertEqual(rules['Core courses']['type'], 'required')
        self.assertEqual(rules['Core courses']['description'], 'All 8 courses required')
        self.assertEqual([c['code'] for c in rules['Core courses']['courses']], sorted(CORE))
        self.assertEqual(rules['Systems electives']['type'], 'pool')
        self.assertEqual(rules['Systems electives']['description'], 'Choose 3 of 6')
        self.assertEqual(rules['Upper-level credits']['type'], 'credit_threshold')
        self.assertEqual(rules['Upper-level credits']['description'], 'At least 12 credits at 3000-level or above')
        self.assertEqual(CatalogImport.objects.get(id=body['import_id']).kind, 'requirements')

    def test_ac1_summary_page_is_served_by_the_programs_endpoints(self):
        program_id = self.import_file(pilot_major()).json()['program_id']
        student = APIClient()
        student.force_login(self.student)

        listing = student.get(PROGRAMS_URL)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()['results'], [{'id': program_id, 'name': 'Computer Science (BS)', 'kind': 'major'}])

        detail = student.get(f'{PROGRAMS_URL}{program_id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(
            [(rule['type'], rule['description']) for rule in detail.json()['requirements']],
            [
                ('required', 'All 8 courses required'),
                ('pool', 'Choose 3 of 6'),
                ('credit_threshold', 'At least 12 credits at 3000-level or above'),
            ],
        )

    def test_ac2_pool_choosing_more_courses_than_it_has_is_rejected_naming_the_pool(self):
        self.import_file(pilot_major())
        before = self.stored_rules()
        oversized = pilot_major(requirements=[
            {'name': 'Theory electives', 'type': 'pool', 'choose_n': 5, 'courses': SYSTEMS[:4]},
        ])

        response = self.import_file(oversized)

        self.assert_rejected(response, 'Pool "Theory electives" asks to choose 5 from 4 courses')
        self.assertEqual(self.stored_rules(), before)

    def test_ac3_unknown_course_is_rejected_naming_the_course(self):
        before = self.stored_rules()
        data = pilot_major()
        data['requirements'][0]['courses'] = CORE[:7] + ['CS-UY 9999']

        response = self.import_file(data)

        self.assert_rejected(response, 'Requirement "Core courses" references CS-UY 9999, which is not in the catalog')
        self.assertEqual(self.stored_rules(), before)

    def test_ac4_student_upload_returns_403(self):
        student = APIClient()
        student.force_login(self.student)

        response = student.post(IMPORT_URL, {'file': upload('requirements.json', json.dumps(pilot_major()))}, format='multipart')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(DegreeProgram.objects.exists())

    def test_anonymous_cannot_import_or_read_programs(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.post(IMPORT_URL, pilot_major(), format='json').status_code, 401)
        self.assertEqual(anonymous.get(PROGRAMS_URL).status_code, 401)

    def test_reimport_replaces_the_previous_definition(self):
        self.import_file(pilot_major())
        version = CatalogState.objects.get().catalog_version
        revised = pilot_major(requirements=[
            {'name': 'Core courses', 'type': 'required', 'courses': CORE[:2]},
            {'name': 'Upper-level credits', 'type': 'credit_threshold', 'min_credits': 16, 'min_level': 3000},
        ])

        response = self.import_file(revised)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(DegreeProgram.objects.count(), 1)
        self.assertEqual(
            sorted(Requirement.objects.values_list('name', 'min_credits')),
            [('Core courses', None), ('Upper-level credits', 16)],
        )
        self.assertEqual(RequirementCourse.objects.count(), 2)
        self.assertEqual(response.json()['catalog_version'], version + 1)

    def test_json_body_is_accepted_without_a_file(self):
        response = self.client.post(IMPORT_URL, pilot_major(), format='json')
        self.assertEqual(response.status_code, 201)

    def test_course_codes_are_normalized(self):
        data = pilot_major()
        data['requirements'][0]['courses'] = ['  cs-uy   1114 '] + CORE[1:]
        response = self.import_file(data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(RequirementCourse.objects.filter(course__code='CS-UY 1114').exists())

    def test_invalid_rules_are_rejected_with_every_problem_listed(self):
        data = pilot_major(requirements=[
            {'name': 'Electives', 'type': 'pool', 'courses': SYSTEMS},
            {'name': 'Upper-level credits', 'type': 'credit_threshold', 'min_credits': 0},
            {'name': 'Mystery', 'type': 'elective', 'courses': CORE},
        ])

        response = self.import_file(data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            [detail['column'] for detail in response.json()['error']['details']],
            ['choose_n', 'min_credits', 'type'],
        )
        self.assertFalse(DegreeProgram.objects.exists())

    def test_non_json_file_is_unsupported(self):
        response = self.client.post(IMPORT_URL, {'file': upload('requirements.csv', 'a,b\n')}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'UNSUPPORTED_FILE')

    def test_malformed_json_is_unsupported(self):
        response = self.client.post(IMPORT_URL, {'file': upload('requirements.json', '{"program": ')}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error']['code'], 'UNSUPPORTED_FILE')

    def test_unknown_program_returns_404(self):
        response = self.client.get(f'{PROGRAMS_URL}999/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['error']['code'], 'NOT_FOUND')

"""US-07 acceptance tests: imports with prerequisite cycles are rejected (Sprint 2 design, Section 4.5 rules 3 and 4)."""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import CatalogImport, CatalogState, Corequisite, Course, PrereqClauseCourse


IMPORT_URL = '/api/admin/catalog-imports/'


def course(code, prerequisites=None, corequisites=None, **fields):
    row = {'code': code, 'title': code, 'credits': 4, 'offerings': ['Fall'], **fields}
    if prerequisites is not None:
        row['prerequisites'] = prerequisites
    if corequisites is not None:
        row['corequisites'] = corequisites
    return row


class ImportCycleTests(APITestCase):
    def setUp(self):
        admin = get_user_model().objects.create_user(email='admin@nyu.edu', password='password123', is_staff=True)
        self.client.force_login(admin)

    def import_rows(self, rows):
        return self.client.post(IMPORT_URL, rows, format='json')

    def catalog(self):
        """Everything a rejected import must leave untouched: courses, rules and the catalog version."""
        return (
            sorted(Course.objects.values_list('code', 'title', 'credits')),
            sorted(PrereqClauseCourse.objects.values_list('clause__course__code', 'clause__position', 'required_course__code')),
            sorted(Corequisite.objects.values_list('course__code', 'coreq_course__code')),
            list(CatalogState.objects.values_list('catalog_version', flat=True)),
        )

    def assert_rejected(self, response, detail):
        self.assertEqual(response.status_code, 400)
        error = response.json()['error']
        self.assertEqual(error['code'], 'IMPORT_REJECTED')
        self.assertEqual(error['details'], [detail])

    def test_ac1_prerequisite_cycle_is_rejected_with_its_path(self):
        """AC1: A requires B, B requires C and C requires A is rejected, showing 'A → B → C → A'."""
        response = self.import_rows([
            course('CS-1001', 'CS-1002'),
            course('CS-1002', 'CS-1003'),
            course('CS-1003', 'CS-1001'),
        ])

        self.assert_rejected(response, {
            'row': None,
            'column': 'prerequisites',
            'value': 'CS-1001 → CS-1002 → CS-1003 → CS-1001',
            'message': 'Prerequisite cycle detected: CS-1001 → CS-1002 → CS-1003 → CS-1001',
        })
        self.assertFalse(Course.objects.exists())

    def test_ac2_rejected_import_leaves_catalog_unchanged(self):
        """AC2: after a rejected import the catalog has the same courses, rules and version as before."""
        self.assertEqual(self.import_rows([course('CS-1001'), course('CS-1002', 'CS-1001')]).status_code, 201)
        before = self.catalog()

        response = self.import_rows([
            course('CS-1001', 'CS-1003', credits=3),
            course('CS-1003', 'CS-1002'),
        ])

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.catalog(), before)
        self.assertEqual(CatalogImport.objects.order_by('-id').first().status, 'rejected')

    def test_cycle_through_a_rule_already_in_the_catalog_is_rejected(self):
        """A cycle split across two imports is caught: the check sees the stored catalog plus the file."""
        self.import_rows([course('CS-1001'), course('CS-1002', 'CS-1001')])

        response = self.import_rows([course('CS-1001', 'CS-1003'), course('CS-1003', 'CS-1002')])

        self.assert_rejected(response, {
            'row': None,
            'column': 'prerequisites',
            'value': 'CS-1001 → CS-1003 → CS-1002 → CS-1001',
            'message': 'Prerequisite cycle detected: CS-1001 → CS-1003 → CS-1002 → CS-1001',
        })

    def test_ac3_mutual_corequisites_are_accepted(self):
        """AC3: X and Y list each other as corequisites with no prerequisite cycle, so the import succeeds."""
        response = self.import_rows([
            course('MA-1024'),
            course('PHYS-101', 'MA-1024', corequisites=['PHYS-101L']),
            course('PHYS-101L', corequisites=['PHYS-101']),
        ])

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Corequisite.objects.count(), 1)

    def test_ac4_prerequisite_chain_between_corequisites_is_rejected(self):
        """AC4: A requires B, B requires C and C is a corequisite of A is rejected, showing 'A → B → C ⇄ A'."""
        response = self.import_rows([
            course('CS-1001', 'CS-1002', corequisites=['CS-1003']),
            course('CS-1002', 'CS-1003'),
            course('CS-1003'),
        ])

        self.assert_rejected(response, {
            'row': None,
            'column': 'corequisites',
            'value': 'CS-1001 → CS-1002 → CS-1003 ⇄ CS-1001',
            'message': 'Corequisite contradiction detected: CS-1001 → CS-1002 → CS-1003 ⇄ CS-1001',
        })
        self.assertFalse(Course.objects.exists())

    def test_loop_through_an_or_alternative_is_accepted(self):
        """A requires (B or C) and B requires A is valid (design, Section 6.2): A can still be taken after C."""
        response = self.import_rows([
            course('CS-1001', 'CS-1002 OR CS-1003'),
            course('CS-1002', 'CS-1001'),
            course('CS-1003'),
        ])

        self.assertEqual(response.status_code, 201)

"""
Comprehensive Test Suite for US-06: AND/OR Prerequisite Groups and Corequisites.
Verifies AC1 through AC4 and ADR-04 (Conjunctive Normal Form Tables).
"""

from django.test import TestCase
from catalog.models import Course, CourseOffering, PrereqClause, PrereqClauseCourse, Corequisite, CatalogState
from catalog.services import import_course_catalog, CatalogImportError
from catalog.prereq_parser import parse_prerequisite_string, UnknownCourseError, PrereqParseError


class US06PrerequisiteAndCorequisiteTests(TestCase):
    def setUp(self):
        CatalogState.objects.get_or_create(id=1, defaults={'catalog_version': 1})

    def test_ac1_cnf_and_or_prerequisite_structure(self):
        """
        AC1: Given a file with prerequisite 'A AND (B OR C),' when imported,
        then the course shows A as required and B or C as alternatives in CNF.
        """
        batch = [
            {'code': 'CS-1114', 'title': 'Intro to CS', 'credits': 4, 'offerings': ['Fall', 'Spring']},
            {'code': 'CS-2124', 'title': 'OOP', 'credits': 4, 'offerings': ['Fall', 'Spring']},
            {'code': 'CS-2134', 'title': 'Data Structures Accelerated', 'credits': 4, 'offerings': ['Fall', 'Spring']},
            {
                'code': 'CS-3114',
                'title': 'Advanced Algorithms',
                'credits': 4,
                'offerings': ['Spring'],
                'prerequisites': 'CS-1114 AND (CS-2124 OR CS-2134)'
            }
        ]

        report = import_course_catalog(batch)
        self.assertEqual(report['imported'], 4)

        cs3114 = Course.objects.get(code='CS-3114')
        clauses = cs3114.prereq_clauses.order_by('position').all()

        # Must have exactly 2 AND-ed clauses in CNF
        self.assertEqual(clauses.count(), 2)

        # Clause 0: CS-1114 (single mandatory requirement)
        clause0_courses = [opt.required_course.code for opt in clauses[0].options.all()]
        self.assertEqual(clause0_courses, ['CS-1114'])

        # Clause 1: (CS-2124 OR CS-2134) (OR-ed alternatives)
        clause1_courses = sorted([opt.required_course.code for opt in clauses[1].options.all()])
        self.assertEqual(clause1_courses, ['CS-2124', 'CS-2134'])

    def test_ac2_mutual_corequisites_accepted_without_cycle_error(self):
        """
        AC2: Given courses X and Y list each other as corequisites,
        when imported, then the import is accepted with no duplicate or cycle error.
        """
        batch = [
            {
                'code': 'PHYS-101',
                'title': 'Physics I Lecture',
                'credits': 3,
                'offerings': ['Fall'],
                'corequisites': ['PHYS-101L']
            },
            {
                'code': 'PHYS-101L',
                'title': 'Physics I Lab',
                'credits': 1,
                'offerings': ['Fall'],
                'corequisites': ['PHYS-101']
            }
        ]

        report = import_course_catalog(batch)
        self.assertEqual(report['imported'], 2)

        # Corequisite table must have exactly 1 canonical record
        self.assertEqual(Corequisite.objects.count(), 1)
        coreq = Corequisite.objects.first()
        self.assertLess(coreq.course_id, coreq.coreq_course_id)
        codes = {coreq.course.code, coreq.coreq_course.code}
        self.assertEqual(codes, {'PHYS-101', 'PHYS-101L'})

    def test_ac3_prose_prerequisite_flagged_for_manual_review(self):
        """
        AC3: Given a prerequisite written as prose such as 'instructor permission,'
        when imported, then the course is imported, flagged 'manual review' in the
        import report, and not treated as a satisfied prerequisite.
        """
        batch = [
            {
                'code': 'CS-4999',
                'title': 'Special Topics',
                'credits': 4,
                'offerings': ['Spring'],
                'prerequisites': 'Instructor permission required'
            }
        ]

        report = import_course_catalog(batch)
        self.assertEqual(report['imported'], 1)
        self.assertIn('CS-4999', report['manual_review'])

        course = Course.objects.get(code='CS-4999')
        self.assertTrue(course.prereq_manual_review)
        self.assertEqual(course.prereq_raw_text, 'Instructor permission required')
        # No automated prerequisite clauses created
        self.assertEqual(course.prereq_clauses.count(), 0)

    def test_ac4_unknown_course_code_in_prerequisite_rejected(self):
        """
        AC4: Given a prerequisite refers to a course code not in the catalog,
        then the import is rejected and the message names the unknown code.
        """
        batch = [
            {'code': 'CS-1001', 'title': 'Basics', 'credits': 3, 'offerings': ['Fall']},
            {
                'code': 'CS-2001',
                'title': 'Advanced Basics',
                'credits': 3,
                'offerings': ['Spring'],
                'prerequisites': 'CS-1001 AND CS-NONEXISTENT'
            }
        ]

        with self.assertRaises(CatalogImportError) as ctx:
            import_course_catalog(batch)

        err_msg = str(ctx.exception)
        self.assertIn('CS-NONEXISTENT', err_msg)

        # All-or-nothing rollback (NFR-4): zero courses should remain
        self.assertEqual(Course.objects.count(), 0)

    def test_self_referencing_prerequisite_rejected(self):
        """
        Edge case: A course cannot list itself as a prerequisite.
        """
        batch = [
            {
                'code': 'CS-1114',
                'title': 'Intro to CS',
                'credits': 4,
                'offerings': ['Fall'],
                'prerequisites': 'CS-1114'
            }
        ]

        with self.assertRaises(CatalogImportError) as ctx:
            import_course_catalog(batch)

        self.assertIn('cannot require itself', str(ctx.exception))
        self.assertEqual(Course.objects.count(), 0)

    def test_reimport_existing_course_updates_prerequisites_idempotently(self):
        """
        US-05 AC3: Re-importing updates prerequisites without creating duplicate clauses.
        """
        batch_1 = [
            {'code': 'CS-101', 'title': 'CS 101', 'credits': 3, 'offerings': ['Fall']},
            {'code': 'CS-102', 'title': 'CS 102', 'credits': 3, 'offerings': ['Spring'], 'prerequisites': 'CS-101'}
        ]
        import_course_catalog(batch_1)
        cs102 = Course.objects.get(code='CS-102')
        self.assertEqual(cs102.prereq_clauses.count(), 1)

        # Re-import with updated prerequisite
        batch_2 = [
            {'code': 'CS-101', 'title': 'CS 101', 'credits': 3, 'offerings': ['Fall']},
            {'code': 'CS-103', 'title': 'CS 103', 'credits': 3, 'offerings': ['Fall']},
            {'code': 'CS-102', 'title': 'CS 102 Updated', 'credits': 4, 'offerings': ['Spring'], 'prerequisites': 'CS-101 AND CS-103'}
        ]
        import_course_catalog(batch_2)
        cs102.refresh_from_db()
        self.assertEqual(cs102.title, 'CS 102 Updated')
        self.assertEqual(cs102.credits, 4)
        # Prereq clauses updated to 2 clauses without duplicate accumulation
        self.assertEqual(cs102.prereq_clauses.count(), 2)

    def test_api_catalog_import_and_course_search(self):
        """
        Integration test: Upload courses via POST /api/admin/catalog-imports/
        and search courses via GET /api/courses/?q=algorithms (US-04, US-06).
        """
        payload = [
            {'code': 'CS-1114', 'title': 'Intro to Programming', 'credits': 4, 'offerings': ['Fall', 'Spring']},
            {'code': 'CS-1124', 'title': 'Intro to CS Accelerated', 'credits': 4, 'offerings': ['Fall', 'Spring']},
            {
                'code': 'CS-3083',
                'title': 'Design and Analysis of Algorithms',
                'credits': 4,
                'offerings': ['Spring'],
                'prerequisites': 'CS-1114 OR CS-1124'
            }
        ]

        # 1. Test POST import
        response = self.client.post(
            '/api/admin/catalog-imports/',
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['imported'], 3)

        # 2. Test GET course search
        search_res = self.client.get('/api/courses/?q=algorithms')
        self.assertEqual(search_res.status_code, 200)
        results = search_res.json()['results']
        self.assertEqual(len(results), 1)
        algo_course = results[0]
        self.assertEqual(algo_course['code'], 'CS-3083')
        # Formatted CNF string check (US-04 AC1)
        self.assertEqual(algo_course['prerequisites'], '(CS-1114 OR CS-1124)')


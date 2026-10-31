"""
US-04 automated test suite: Course Catalog Search and Constraints Display.
Verifies AC1 through AC4:
- AC1: Search by title/code returns matching courses with credits, CNF prerequisites, corequisites, and terms offered.
- AC2: Search matching nothing returns empty results list with 200 OK.
- AC3: Unauthenticated API access returns HTTP 401 Unauthorized.
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from catalog.models import Course, CourseOffering, PrereqClause, PrereqClauseCourse, Corequisite


class CourseCatalogSearchTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.student = User.objects.create_user(
            email='student.search@nyu.edu',
            password='password123'
        )
        self.client.force_login(self.student)

        # Create foundational courses
        self.cs1114 = Course.objects.create(code='CS-UY 1114', title='Introduction to Programming', credits=4)
        CourseOffering.objects.create(course=self.cs1114, season='Fall')
        CourseOffering.objects.create(course=self.cs1114, season='Spring')

        self.cs1134 = Course.objects.create(code='CS-UY 1134', title='Data Structures and Algorithms', credits=4)
        CourseOffering.objects.create(course=self.cs1134, season='Spring')

        self.cs2413 = Course.objects.create(code='CS-UY 2413', title='Design and Analysis of Algorithms', credits=3)
        CourseOffering.objects.create(course=self.cs2413, season='Fall')

        self.phys101 = Course.objects.create(code='PHYS-UY 101', title='Physics I Lecture', credits=3)
        self.phys101l = Course.objects.create(code='PHYS-UY 101L', title='Physics I Laboratory', credits=1)
        CourseOffering.objects.create(course=self.phys101, season='Fall')
        CourseOffering.objects.create(course=self.phys101l, season='Fall')

        # Corequisite pair between Physics Lecture and Lab
        Corequisite.objects.create(course=self.phys101, coreq_course=self.phys101l)

        # Prerequisite CNF for CS-UY 2413: CS-UY 1114 AND CS-UY 1134
        clause1 = PrereqClause.objects.create(course=self.cs2413, position=0)
        PrereqClauseCourse.objects.create(clause=clause1, required_course=self.cs1114)
        clause2 = PrereqClause.objects.create(course=self.cs2413, position=1)
        PrereqClauseCourse.objects.create(clause=clause2, required_course=self.cs1134)

    def test_ac1_search_by_title_returns_matching_courses_with_all_constraints(self):
        """
        AC1: Given the catalog is loaded, when I search 'algorithms,' then I see
        matching courses with credits, prerequisites written as e.g. 'A AND (B OR C),'
        corequisites, and terms offered.
        """
        response = self.client.get('/api/courses/?q=algorithms')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        results = data['results']

        codes = [c['code'] for c in results]
        self.assertIn('CS-UY 1134', codes)
        self.assertIn('CS-UY 2413', codes)
        self.assertNotIn('CS-UY 1114', codes)

        algo = next(c for c in results if c['code'] == 'CS-UY 2413')
        self.assertEqual(algo['title'], 'Design and Analysis of Algorithms')
        self.assertEqual(algo['credits'], 3)
        self.assertEqual(algo['offerings'], ['Fall'])
        self.assertEqual(algo['prerequisites'], 'CS-UY 1114 AND CS-UY 1134')

    def test_ac1_search_shows_corequisites_bidirectionally(self):
        """
        AC1: Corequisites are rendered cleanly in course search results.
        """
        response = self.client.get('/api/courses/?q=Physics')
        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        lecture = next(c for c in results if c['code'] == 'PHYS-UY 101')
        lab = next(c for c in results if c['code'] == 'PHYS-UY 101L')

        self.assertIn('PHYS-UY 101L', lecture['corequisites'])
        self.assertIn('PHYS-UY 101', lab['corequisites'])

    def test_ac2_search_no_match_returns_empty_results_cleanly(self):
        """
        AC2: Given my search matches nothing, then I see 'No courses found'
        and no error page.
        """
        response = self.client.get('/api/courses/?q=NonExistentSubject9999')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, {'results': []})

    def test_ac3_unauthenticated_user_rejected_with_401(self):
        """
        AC3: Given I am not signed in, when I send an API request to access the catalog,
        then the API returns HTTP 401 Unauthorized and does not return catalog data.
        """
        anon_client = APIClient()
        response = anon_client.get('/api/courses/')
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('results', response.json())

    def test_search_by_course_code_is_case_insensitive(self):
        """
        Search by course code prefix works regardless of case.
        """
        response = self.client.get('/api/courses/?q=cs-uy 11')
        self.assertEqual(response.status_code, 200)
        codes = [c['code'] for c in response.json()['results']]
        self.assertIn('CS-UY 1114', codes)
        self.assertIn('CS-UY 1134', codes)

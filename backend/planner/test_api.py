"""POST /api/plans/generate/ (US-09) and the shared validation entry point for saved plans."""

from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from catalog.models import (
    CatalogState, Corequisite, Course, CourseOffering, DegreeProgram, PrereqClause, PrereqClauseCourse,
    Requirement, RequirementCourse,
)
from planner import engine
from planner.engine import PlannerBug, PlannerTimeout
from planner.loader import load_snapshot
from planner.service import validate_entries
from planner.snapshot import Term
from profiles.models import Profile

GENERATE = '/api/plans/generate/'
PROGRAM = 'Computer Science (BS)'


def add_course(code, title, credits=4, seasons=('Fall', 'Spring'), prereqs=(), manual_review=False):
    c = Course.objects.create(code=code, title=title, credits=credits, prereq_manual_review=manual_review)
    for season in seasons:
        CourseOffering.objects.create(course=c, season=season)
    for position, clause in enumerate(prereqs):
        row = PrereqClause.objects.create(course=c, position=position)
        for option in clause:
            PrereqClauseCourse.objects.create(clause=row, required_course=Course.objects.get(code=option))
    return c


def add_requirement(program, name, kind, codes, position, **extra):
    r = Requirement.objects.create(program=program, name=name, type=kind, position=position, **extra)
    for code in codes:
        RequirementCourse.objects.create(requirement=r, course=Course.objects.get(code=code))
    return r


class GeneratePlanApiTests(APITestCase):
    def setUp(self):
        # Today is in Fall 2026, so plans start in Spring 2027 (the next term).
        patcher = patch('profiles.terms.today', return_value=date(2026, 11, 16))
        patcher.start()
        self.addCleanup(patcher.stop)

        add_course('CS-UY 1114', 'Intro to Programming')
        add_course('CS-UY 1134', 'Data Structures', prereqs=(('CS-UY 1114',),))
        add_course('MA-UY 1024', 'Calculus I')
        add_course('CS-UY 2413', 'Algorithms', seasons=('Fall',), prereqs=(('CS-UY 1134',), ('MA-UY 1024',)))
        lecture = add_course('CS-UY 3083', 'Databases', seasons=('Spring',), prereqs=(('CS-UY 1134',),))
        lab = add_course('CS-UY 3084', 'Databases Lab', credits=1, seasons=('Spring',))
        Corequisite.objects.create(course=lecture, coreq_course=lab)
        add_course('CS-UY 3943', 'Special Topics', manual_review=True)
        add_course('CS-UY 4563', 'Machine Learning', prereqs=(('CS-UY 2413',),))
        CatalogState.objects.create(id=1, catalog_version=5)

        program = DegreeProgram.objects.create(name=PROGRAM, kind='major')
        add_requirement(program, 'Core courses', 'required', ['CS-UY 1114', 'CS-UY 1134', 'CS-UY 2413', 'CS-UY 3083'], 0)
        add_requirement(program, 'Electives', 'pool', ['CS-UY 4563', 'CS-UY 3943'], 1, choose_n=1)

        User = get_user_model()
        self.student = User.objects.create_user(email='student@nyu.edu', password='password123')
        self.profile, _ = Profile.objects.get_or_create(user=self.student)
        self.set_profile(major=PROGRAM, credit_limit=12, target_term='Fall 2028', completed_courses=[])
        self.client = APIClient()
        self.client.force_login(self.student)

    def set_profile(self, **fields):
        for name, value in fields.items():
            setattr(self.profile, name, value)
        self.profile.save()

    def generate(self):
        return self.client.post(GENERATE, format='json')

    def test_valid_plan_lists_every_term_through_the_target(self):                   # US-09 AC1
        res = self.generate()
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body['status'], 'valid')
        self.assertEqual(body['program'], PROGRAM)
        self.assertEqual([t['term'] for t in body['terms']], ['Spring 2027', 'Fall 2027', 'Spring 2028', 'Fall 2028'])
        self.assertEqual(body['terms'][0], {
            'term': 'Spring 2027', 'credits': 8,
            'courses': [
                {'code': 'CS-UY 1114', 'title': 'Intro to Programming', 'credits': 4, 'counted_for': None},
                {'code': 'MA-UY 1024', 'title': 'Calculus I', 'credits': 4, 'counted_for': None},
            ],
        })
        planned = [c['code'] for t in body['terms'] for c in t['courses']]
        self.assertEqual(sorted(planned), ['CS-UY 1114', 'CS-UY 1134', 'CS-UY 2413', 'CS-UY 3083', 'CS-UY 3084', 'MA-UY 1024'])
        self.assertEqual(body['profile_version'], self.profile.profile_version)
        self.assertEqual(body['catalog_version'], 5)
        self.assertEqual(body['unenforced_requirements'], ['Electives'])

    def test_plan_honors_prerequisites_offerings_and_corequisites(self):             # US-09 AC2
        term_of = {c['code']: t['term'] for t in self.generate().json()['terms'] for c in t['courses']}
        self.assertEqual(term_of['CS-UY 1134'], 'Fall 2027')       # after CS-UY 1114
        self.assertEqual(term_of['CS-UY 2413'], 'Fall 2028')       # Fall only, after CS-UY 1134
        self.assertEqual(term_of['CS-UY 3083'], 'Spring 2028')     # Spring only
        self.assertEqual(term_of['CS-UY 3084'], term_of['CS-UY 3083'])

    def test_completed_courses_are_left_out(self):                                   # US-09 AC2
        self.set_profile(completed_courses=['CS-UY 1114', 'MA-UY 1024'])
        planned = {c['code'] for t in self.generate().json()['terms'] for c in t['courses']}
        self.assertFalse({'CS-UY 1114', 'MA-UY 1024'} & planned)
        self.assertIn('CS-UY 1134', planned)

    def test_plan_from_api_passes_shared_validation(self):                           # NFR-4, for US-10/US-13
        entries = [{'course_code': c['code'], 'term': t['term'], 'counted_for': c['counted_for']}
                   for t in self.generate().json()['terms'] for c in t['courses']]
        self.assertEqual(validate_entries(self.profile, entries), [])

    def test_shared_validation_reports_broken_plans(self):
        entries = [{'course_code': 'CS-UY 1134', 'term': 'Spring 2027'},
                   {'course_code': 'CS-UY 1114', 'term': 'Spring 2027'},
                   {'course_code': 'CS-UY 9999', 'term': 'Fall 2027'},
                   {'course_code': 'MA-UY 1024', 'term': 'Summer 2027'}]
        found = {(v['code'], v['course']) for v in validate_entries(self.profile, entries)}
        self.assertIn(('PREREQ', 'CS-UY 1134'), found)
        self.assertIn(('UNKNOWN_COURSE', 'CS-UY 9999'), found)
        self.assertIn(('INVALID_TERM', 'MA-UY 1024'), found)
        self.assertIn(('REQUIRED_COURSE', 'CS-UY 2413'), found)

    def test_infeasible_profile_returns_infeasible_status(self):                     # US-09 AC3
        self.set_profile(target_term='Fall 2027')
        res = self.generate()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {'status': 'infeasible', 'message': 'No valid plan exists for these constraints'})

    def test_timeout_returns_504(self):                                              # US-09 AC3, NFR-3
        with patch('planner.views.generate', return_value=PlannerTimeout()):
            res = self.generate()
        self.assertEqual(res.status_code, 504)
        self.assertEqual(res.json()['error']['code'], 'PLANNER_TIMEOUT')

    def test_real_solver_time_limit_returns_504(self):
        with patch('planner.views.GENERATION_LIMITS', engine.SolverLimits(0.0, 0.0)):
            res = self.generate()
        self.assertEqual(res.status_code, 504)

    def test_validator_rejection_returns_500_without_a_plan(self):                   # NFR-4
        with patch('planner.views.generate', side_effect=PlannerBug(['PREREQ'])):
            res = self.generate()
        self.assertEqual(res.status_code, 500)
        self.assertEqual(res.json()['error']['code'], 'INTERNAL_ERROR')
        self.assertNotIn('terms', res.json())

    def test_incomplete_profile_returns_409_listing_missing_fields(self):            # design §6.1, DR-12
        self.set_profile(major='', credit_limit=None, target_term='')
        res = self.generate()
        self.assertEqual(res.status_code, 409)
        error = res.json()['error']
        self.assertEqual(error['code'], 'PROFILE_INCOMPLETE')
        self.assertEqual([d['field'] for d in error['details']], ['major', 'credit_limit', 'target_term'])

    def test_program_without_imported_requirements_returns_409(self):
        self.set_profile(major='Computer Science (BA)')
        res = self.generate()
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.json()['error']['code'], 'PROGRAM_NOT_IMPORTED')

    def test_admin_gets_403(self):                                                   # NFR-1, design §5.2
        admin = get_user_model().objects.create_user(email='admin@nyu.edu', password='password123', is_staff=True)
        client = APIClient()
        client.force_login(admin)
        res = client.post(GENERATE, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertFalse(Profile.objects.filter(user=admin).exists())

    def test_signed_out_gets_401(self):                                              # US-01 AC4
        self.assertEqual(APIClient().post(GENERATE, format='json').status_code, 401)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(GENERATE).status_code, 405)


class LoaderTests(APITestCase):
    def setUp(self):
        patcher = patch('profiles.terms.today', return_value=date(2027, 3, 1))   # Spring 2027
        patcher.start()
        self.addCleanup(patcher.stop)
        add_course('A-UY 1001', 'A')
        add_course('B-UY 1002', 'B', seasons=('Fall',))
        add_course('C-UY 2003', 'C', prereqs=(('A-UY 1001', 'B-UY 1002'),), manual_review=True)
        Corequisite.objects.create(course=Course.objects.get(code='A-UY 1001'), coreq_course=Course.objects.get(code='B-UY 1002'))
        program = DegreeProgram.objects.create(name=PROGRAM, kind='major', max_elective_pools_per_course=2)
        add_requirement(program, 'Core', 'required', ['A-UY 1001'], 0)
        add_requirement(program, 'Upper', 'credit_threshold', [], 1, min_credits=8, min_level=2000)
        user = get_user_model().objects.create_user(email='s@nyu.edu', password='password123')
        self.profile, _ = Profile.objects.get_or_create(user=user)
        for k, v in dict(major='computer science (bs)', credit_limit=10, target_term='Spring 2029',
                         completed_courses=['B-UY 1002']).items():
            setattr(self.profile, k, v)
        self.profile.save()

    def test_snapshot_reads_catalog_requirements_and_profile(self):
        snap = load_snapshot(self.profile)
        self.assertEqual(snap.first_term, Term('Fall', 2027))
        self.assertEqual(snap.target_term, Term('Spring', 2029))
        self.assertEqual(snap.credit_limit, 10)
        self.assertEqual(snap.completed, frozenset({'B-UY 1002'}))
        self.assertEqual(snap.program, PROGRAM)                       # matched without regard to case
        self.assertEqual(snap.max_pools_per_course, 2)
        c = snap.courses['C-UY 2003']
        self.assertEqual((c.prereqs, c.manual_review, c.level), ((('A-UY 1001', 'B-UY 1002'),), True, 2000))
        self.assertEqual(snap.courses['B-UY 1002'].offered, frozenset({'Fall'}))
        self.assertEqual(snap.corequisites, frozenset({('A-UY 1001', 'B-UY 1002')}))
        self.assertEqual([(r.name, r.kind, r.courses, r.min_credits, r.min_level) for r in snap.requirements],
                         [('Core', 'required', ('A-UY 1001',), 0, 0), ('Upper', 'credit_threshold', (), 8, 2000)])
        self.assertEqual(snap.catalog_version, 1)                     # no import recorded yet

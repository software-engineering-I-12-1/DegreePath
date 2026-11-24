from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import (
    Corequisite, Course, CourseOffering, DegreeProgram, PrereqClause, PrereqClauseCourse,
    Requirement, RequirementCourse,
)
from plans.models import Plan
from profiles.models import Profile


def entry(term, course):
    return {'term': term, 'course_code': course.code, 'title': course.title, 'credits': course.credits,
            'counted_for': None}


class RealValidatorExportTests(TestCase):
    """No mocks: export runs the shared planner validator against real catalog and degree rules."""

    def setUp(self):
        patcher = patch('profiles.terms.today', return_value=date(2026, 10, 27))
        patcher.start()
        self.addCleanup(patcher.stop)

        self.user = get_user_model().objects.create_user('owner@example.com', 'password123')
        Profile.objects.create(
            user=self.user, major='Computer Science', credit_limit=15, target_term='Spring 2028',
        )

        # Intro course and its dependent course, both offered in Spring only.
        self.intro = Course.objects.create(code='CS 1000', title='Intro Programming', credits=4)
        self.next = Course.objects.create(code='CS 2000', title='Data Structures', credits=4)
        for course in (self.intro, self.next):
            CourseOffering.objects.create(course=course, season='Spring')
        clause = PrereqClause.objects.create(course=self.next, position=0)
        PrereqClauseCourse.objects.create(clause=clause, required_course=self.intro)

        self.program = DegreeProgram.objects.create(name='Computer Science')
        self.core = Requirement.objects.create(program=self.program, name='Core', type='required')
        for course in (self.intro, self.next):
            RequirementCourse.objects.create(requirement=self.core, course=course)

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def save(self, entries):
        return Plan.objects.create(
            user=self.user, name='Plan', entries=entries, profile_version_at_gen=1, catalog_version_at_gen=1,
        )

    def export(self, plan):
        return self.client.get(f'/api/plan-export/{plan.id}/csv/')

    def assert_rejected(self, plan):
        res = self.export(plan)
        self.assertEqual(res.status_code, 409)
        self.assertNotIn('Content-Disposition', res)  # no CSV attachment
        error = res.json()['error']
        self.assertEqual(error['code'], 'PLAN_NOT_EXPORTABLE')
        self.assertTrue(error['details'], 'the validator should say why')
        status = self.client.get('/api/plan-export/status/', {'plan_id': str(plan.id)}).json()
        self.assertFalse(status['exportable'])

    def valid_entries(self):
        return [entry('Spring 2027', self.intro), entry('Spring 2028', self.next)]

    def test_calendar_includes_only_supplied_dates(self):
        plan = self.save(self.valid_entries())
        response = self.client.get(f'/api/plan-export/{plan.id}/calendar/', {'Spring 2027': '2026-11-24'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/calendar'))
        self.assertIn(b'DTSTART;VALUE=DATE:20261124\r\n', response.content)
        self.assertEqual(response.content.count(b'BEGIN:VEVENT'), 1)
        self.assertNotIn(b'Spring 2028', response.content)

    def test_calendar_requires_at_least_one_valid_date(self):
        plan = self.save(self.valid_entries())
        url = f'/api/plan-export/{plan.id}/calendar/'
        for dates, code in (
            ({}, 'REGISTRATION_DATE_REQUIRED'),
            ({'Spring 2027': '2026-02-30'}, 'INVALID_DATE'),
        ):
            with self.subTest(dates=dates):
                response = self.client.get(url, dates)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data['error']['code'], code)

    def test_calendar_rejects_invalid_or_other_students_plans(self):
        plan = self.save([])
        url = f'/api/plan-export/{plan.id}/calendar/'
        self.assertEqual(self.client.get(url).status_code, 409)
        other = get_user_model().objects.create_user('calendar-other@example.com')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_valid_schedule_downloads(self):
        res = self.export(self.save(self.valid_entries()))
        self.assertEqual(res.status_code, 200)
        self.assertIn('attachment', res['Content-Disposition'])
        lines = res.content.decode('utf-8').splitlines()
        self.assertEqual(lines[0], 'term,course_code,title,credits')
        self.assertEqual(lines[1:], ['Spring 2027,CS 1000,Intro Programming,4', 'Spring 2028,CS 2000,Data Structures,4'])

    def test_spring_only_courses_scheduled_in_fall_are_rejected(self):
        # Omkar's reproduction: intro course and its dependent together in Fall.
        self.assert_rejected(self.save([entry('Fall 2027', self.intro), entry('Fall 2027', self.next)]))

    def test_prerequisite_in_the_same_term_is_rejected(self):
        self.assert_rejected(self.save([entry('Spring 2027', self.intro), entry('Spring 2027', self.next)]))

    def test_missing_prerequisite_is_rejected(self):
        self.assert_rejected(self.save([entry('Spring 2028', self.next)]))

    def test_unmet_degree_requirement_is_rejected(self):
        self.assert_rejected(self.save([entry('Spring 2027', self.intro)]))  # CS 2000 is required too

    def test_missing_corequisite_is_rejected(self):
        co = Course.objects.create(code='CS 1001', title='Intro Lab', credits=1)  # created after, so id is larger
        CourseOffering.objects.create(course=co, season='Spring')
        Corequisite.objects.create(course=self.intro, coreq_course=co)
        self.assert_rejected(self.save(self.valid_entries()))

    def test_degree_rules_changed_after_saving_are_rejected(self):
        plan = self.save(self.valid_entries())
        self.assertEqual(self.export(plan).status_code, 200)

        extra = Course.objects.create(code='CS 3000', title='Algorithms', credits=4)
        CourseOffering.objects.create(course=extra, season='Spring')
        RequirementCourse.objects.create(requirement=self.core, course=extra)  # new required course
        self.assert_rejected(plan)

    def test_profile_change_after_saving_is_rejected(self):
        plan = self.save(self.valid_entries())
        Profile.objects.filter(user=self.user).update(credit_limit=3)  # one 4-credit course no longer fits
        self.assert_rejected(plan)

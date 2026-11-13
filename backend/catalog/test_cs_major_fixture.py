from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .models import Course, CourseOffering, Corequisite, PrereqClause, PrereqClauseCourse


class CsMajorFixtureTests(TestCase):
    fixtures = ['cs_major_catalog']

    def test_fixture_loads_repeatedly_without_duplicates(self):
        call_command('loaddata', 'cs_major_catalog', stdout=StringIO())
        self.assertEqual(Course.objects.count(), 25)
        for model in (Course, CourseOffering, Corequisite, PrereqClause, PrereqClauseCourse):
            for record in model.objects.all():
                record.full_clean()

    def test_alternatives_and_required_clause_are_preserved(self):
        course = Course.objects.get(code='CS-UY 2134')
        clauses = [
            set(clause.options.values_list('required_course__code', flat=True))
            for clause in course.prereq_clauses.all()
        ]
        self.assertEqual(clauses, [{'CS-UY 1134', 'CS-UY 2124'}, {'MA-UY 2314'}])

    def test_offerings_and_corequisite_pair(self):
        offerings = {
            tuple(course.offerings.values_list('season', flat=True))
            for course in Course.objects.all()
        }
        self.assertEqual(offerings, {('Fall',), ('Spring',), ('Fall', 'Spring')})
        pair = Corequisite.objects.get()
        self.assertEqual((pair.course.code, pair.coreq_course.code), ('CS-UY 4713', 'CS-UY 4711'))

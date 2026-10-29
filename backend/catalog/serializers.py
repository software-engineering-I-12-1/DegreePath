"""
Serializers for Course Catalog and CNF Prerequisite rendering (US-04, US-05, US-06).
"""

from rest_framework import serializers
from .models import Course, CourseOffering, PrereqClause, PrereqClauseCourse, Corequisite, CatalogImport


class CourseSerializer(serializers.ModelSerializer):
    offerings = serializers.SerializerMethodField()
    prerequisites = serializers.SerializerMethodField()
    corequisites = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'code',
            'title',
            'credits',
            'level',
            'prerequisites',
            'corequisites',
            'offerings',
            'prereq_manual_review',
            'prereq_raw_text'
        ]

    def get_offerings(self, obj: Course):
        return list(obj.offerings.values_list('season', flat=True))

    def get_prerequisites(self, obj: Course) -> str:
        """
        Renders normalized CNF database clauses back into human-readable prerequisite logic:
        e.g. 'CS-1114 AND (CS-2124 OR CS-2134)' (US-04 AC1, US-06 AC1)
        """
        if obj.prereq_manual_review and obj.prereq_raw_text:
            return obj.prereq_raw_text

        clause_strings = []
        for clause in obj.prereq_clauses.order_by('position').prefetch_related('options__required_course'):
            options = [opt.required_course.code for opt in clause.options.all()]
            if not options:
                continue
            if len(options) == 1:
                clause_strings.append(options[0])
            else:
                clause_strings.append(f"({' OR '.join(options)})")

        return " AND ".join(clause_strings)

    def get_corequisites(self, obj: Course):
        """
        Returns all courses connected by canonical corequisite pairs.
        """
        outgoing = obj.corequisites_outgoing.values_list('coreq_course__code', flat=True)
        incoming = obj.corequisites_incoming.values_list('course__code', flat=True)
        return sorted(list(set(list(outgoing) + list(incoming))))

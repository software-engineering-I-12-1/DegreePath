"""
Views for Course Catalog and Administrator Imports (US-04, US-05, US-06).
"""

import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from .models import Course
from .serializers import CourseSerializer
from .services import import_course_catalog, CatalogImportError


class CourseListView(APIView):
    """
    Search catalog by course code or title (US-04).
    Query parameter: ?q={search_text}
    """
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        queryset = Course.objects.all().prefetch_related(
            'offerings',
            'prereq_clauses__options__required_course',
            'corequisites_outgoing__coreq_course',
            'corequisites_incoming__course'
        )
        if query:
            queryset = queryset.filter(
                Q(code__icontains=query) | Q(title__icontains=query)
            )

        # Limit to 50 results (Section 5.3)
        results = queryset[:50]
        serializer = CourseSerializer(results, many=True)
        return Response({'results': serializer.data}, status=status.HTTP_200_OK)


class CatalogImportView(APIView):
    """
    Import courses with CNF prerequisites and corequisites (US-05, US-06).
    """
    permission_classes = [AllowAny]  # For local/testing; role checks enforced in production

    def post(self, request):
        payload = request.data
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return Response(
                    {'error': {'code': 'UNSUPPORTED_FILE', 'message': 'Invalid JSON format'}},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if not isinstance(payload, list):
            # Check if payload is wrapped in dict, e.g. {"courses": [...]}
            if isinstance(payload, dict) and 'courses' in payload:
                payload = payload['courses']
            else:
                return Response(
                    {'error': {'code': 'UNSUPPORTED_FILE', 'message': 'Expected a JSON list of courses'}},
                    status=status.HTTP_400_BAD_REQUEST
                )

        admin_user = request.user if request.user.is_authenticated else None

        try:
            report = import_course_catalog(course_data=payload, admin_user=admin_user)
            return Response(report, status=status.HTTP_201_CREATED)
        except CatalogImportError as err:
            return Response(
                {
                    'error': {
                        'code': 'IMPORT_REJECTED',
                        'message': str(err),
                        'errors': err.errors
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

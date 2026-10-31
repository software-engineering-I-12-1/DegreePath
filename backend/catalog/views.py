"""
Views for Course Catalog and Administrator Imports (US-04, US-05, US-06).
"""

import csv
import io
import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from django.db.models import Q
from .models import Course
from .serializers import CourseSerializer
from .services import import_course_catalog, CatalogImportError


def _bad_file(message, details=None):
    return Response(
        {'error': {'code': 'UNSUPPORTED_FILE', 'message': message, 'details': details or []}},
        status=status.HTTP_400_BAD_REQUEST,
    )


class CourseListView(APIView):
    """
    Search catalog by course code or title (US-04).
    Query parameter: ?q={search_text}
    """
    permission_classes = [IsAuthenticated]

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
    """Import a CSV/JSON course file; only staff accounts may change the catalog."""

    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        uploaded = request.FILES.get('file')
        first_row_number = 1

        if uploaded is not None:
            name = uploaded.name.lower()
            if not name.endswith(('.csv', '.json')):
                return _bad_file('Upload a .csv or .json file')
            try:
                content = uploaded.read().decode('utf-8-sig')
            except UnicodeDecodeError:
                return _bad_file('File must be UTF-8 encoded')

            if name.endswith('.csv'):
                try:
                    reader = csv.DictReader(io.StringIO(content, newline=''))
                    required = {'code', 'title', 'credits', 'offerings'}
                    missing = sorted(required - set(reader.fieldnames or []))
                    if missing:
                        return _bad_file(
                            'Missing required CSV columns',
                            [{'row': 1, 'column': column, 'message': f'Missing column {column}'} for column in missing],
                        )
                    payload = list(reader)
                    first_row_number = 2
                except csv.Error as exc:
                    return _bad_file(f'Invalid CSV: {exc}')
            else:
                try:
                    payload = json.loads(content)
                except json.JSONDecodeError as exc:
                    return _bad_file(f'Invalid JSON: {exc.msg}')
        else:
            # Existing US-06 callers send the course list directly as JSON.
            payload = request.data

        if isinstance(payload, dict) and 'courses' in payload:
            payload = payload['courses']
        if not isinstance(payload, list):
            return _bad_file('Expected a list of courses or an object with a courses list')

        try:
            report = import_course_catalog(payload, admin_user=request.user, first_row_number=first_row_number)
        except CatalogImportError as err:
            return Response(
                {'error': {'code': 'IMPORT_REJECTED', 'message': str(err), 'details': err.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'message': f"{report['imported']} courses imported", **report}, status=status.HTTP_201_CREATED)

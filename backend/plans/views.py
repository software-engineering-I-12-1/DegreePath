from django.db import transaction
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import CatalogState, Course
from core.errors import api_error
from profiles.models import Profile
from profiles.terms import parse_term

from .models import Plan
from .serializers import SavePlanSerializer
from .validation import PlanValidationUnavailable, validate_plan


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return not request.user.is_staff and not request.user.is_superuser


def serialize_plan(plan):
    return {
        'id': str(plan.id),
        'name': plan.name,
        'entries': plan.entries,
        'created_at': plan.created_at.isoformat(),
        'profile_version_at_gen': plan.profile_version_at_gen,
        'catalog_version_at_gen': plan.catalog_version_at_gen,
    }


class PlanListView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request):
        plans = Plan.objects.filter(user=request.user)
        return Response({'results': [serialize_plan(plan) for plan in plans]})

    def post(self, request):
        serializer = SavePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            profile = Profile.objects.select_for_update().filter(user=request.user).first()
            if profile is None or not profile.is_ready:
                return api_error('PROFILE_INCOMPLETE', 'Complete your profile before saving a plan.', 400)
            state, _ = CatalogState.objects.get_or_create(pk=1)
            state = CatalogState.objects.select_for_update().get(pk=state.pk)
            entries = serializer.validated_data['entries']
            try:
                violations = validate_plan(entries, profile)
            except PlanValidationUnavailable as error:
                return api_error('VALIDATION_UNAVAILABLE', str(error), status.HTTP_503_SERVICE_UNAVAILABLE)
            if violations:
                return api_error('INVALID_PLAN', 'The plan does not pass validation.', 400, violations)
            courses = Course.objects.in_bulk([entry['course_code'] for entry in entries], field_name='code')
            unknown = sorted({entry['course_code'] for entry in entries} - courses.keys())
            if unknown:
                return api_error('UNKNOWN_COURSE', 'Course not in the catalog: ' + ', '.join(unknown), 400)
            # Preserve display values so reopening a saved plan is stable after catalog edits.
            snapshot = [
                {**entry, 'title': courses[entry['course_code']].title,
                 'credits': courses[entry['course_code']].credits}
                for entry in entries
            ]
            snapshot.sort(key=lambda entry: (parse_term(entry['term']), entry['course_code']))
            plan = Plan.objects.create(
                user=request.user, name=serializer.validated_data['name'], entries=snapshot,
                profile_version_at_gen=profile.profile_version, catalog_version_at_gen=state.catalog_version,
            )
        return Response(serialize_plan(plan), status=status.HTTP_201_CREATED)


class PlanDetailView(APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    def get(self, request, plan_id):
        plan = Plan.objects.filter(pk=plan_id).first()
        if plan is None:
            return api_error('NOT_FOUND', 'Plan not found.', 404)
        if plan.user_id != request.user.pk:
            return api_error('NOT_OWNER', 'You do not have access to this plan.', 403)
        return Response(serialize_plan(plan))

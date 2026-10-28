from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import catalog, terms
from .models import Profile
from .validators import validate_profile


def _serialize(profile):
    if profile is None:
        return {'id': None, 'major': '', 'credit_limit': None, 'target_term': '', 'completed_courses': []}
    return {
        'id': str(profile.id),
        'major': profile.major,
        'credit_limit': profile.credit_limit,
        'target_term': profile.target_term,
        'completed_courses': profile.completed_courses,
    }


class ProfileView(APIView):
    """The profile is always looked up from the session user, so there is no ID to tamper with (NFR-1)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = Profile.objects.filter(user=request.user).first()
        return Response(_serialize(profile))

    def put(self, request):
        if not isinstance(request.data, dict):
            return Response({'error': 'Invalid request body', 'errors': {}}, status=status.HTTP_400_BAD_REQUEST)

        cleaned, errors = validate_profile(request.data)
        if errors:
            return Response(
                {'error': 'Please fix the highlighted fields', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            profile, _ = Profile.objects.update_or_create(user=request.user, defaults=cleaned)
        return Response(_serialize(profile))


class OptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'majors': catalog.get_majors(),
            'courses': catalog.get_courses(),
            'terms': terms.upcoming_terms(),
        })
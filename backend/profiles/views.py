from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import api_error

from . import catalog, terms
from .models import Profile
from .validators import validate_profile


def _serialize(profile):
    return {
        'id': str(profile.id),
        'major': profile.major,
        'credit_limit': profile.credit_limit,
        'target_term': profile.target_term,
        'completed_courses': profile.completed_courses,
        'profile_version': profile.profile_version,
        'ready': profile.is_ready,
        'updated_at': profile.updated_at.isoformat(),
    }


def _own_profile(user):
    # Registration creates the profile; get_or_create also covers accounts made before that existed.
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile


def _apply_update(request, profile):
    if not isinstance(request.data, dict):
        return api_error('VALIDATION_ERROR', 'Invalid request body', status.HTTP_400_BAD_REQUEST)

    cleaned, errors, unknown = validate_profile(request.data)
    if errors:
        details = [{'field': field, 'message': message} for field, message in errors.items()]
        if unknown and set(errors) == {'completed_courses'}:
            return api_error(
                'UNKNOWN_COURSE',
                'Course not in the catalog: ' + ', '.join(unknown),
                status.HTTP_400_BAD_REQUEST,
                details,
            )
        return api_error(
            'VALIDATION_ERROR', 'Please fix the highlighted fields', status.HTTP_400_BAD_REQUEST, details,
        )

    with transaction.atomic():
        for field, value in cleaned.items():
            setattr(profile, field, value)
        profile.profile_version = F('profile_version') + 1
        profile.save()
        profile.refresh_from_db()
    return Response(_serialize(profile))


class MyProfileView(APIView):
    """GET/PUT /api/profiles/me/: always the session user's own profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_serialize(_own_profile(request.user)))

    def put(self, request):
        return _apply_update(request, _own_profile(request.user))


class ProfileDetailView(APIView):
    """GET/PUT /api/profiles/{id}/: 404 if unknown, 403 NOT_OWNER if it belongs to someone else (NFR-1)."""

    permission_classes = [IsAuthenticated]

    def _load(self, request, profile_id):
        profile = Profile.objects.filter(pk=profile_id).first()
        if profile is None:
            return None, api_error('NOT_FOUND', 'Profile not found', status.HTTP_404_NOT_FOUND)
        if profile.user_id != request.user.pk:
            return None, api_error('NOT_OWNER', 'You do not have access to this profile', status.HTTP_403_FORBIDDEN)
        return profile, None

    def get(self, request, profile_id):
        profile, error = self._load(request, profile_id)
        return error or Response(_serialize(profile))

    def put(self, request, profile_id):
        profile, error = self._load(request, profile_id)
        return error or _apply_update(request, profile)


class OptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'majors': catalog.get_majors(),
            'courses': catalog.get_courses(),
            'terms': terms.upcoming_terms(),
        })
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import api_error
from profiles.models import Profile

from .authentication import CSRFOnlyAuthentication

User = get_user_model()

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
MAX_EMAIL_LENGTH = 254


def _field(request, name):
    data = request.data
    value = data.get(name) if hasattr(data, 'get') else None
    return value if isinstance(value, str) else ''


def _user_payload(user):
    return {
        'id': user.pk,
        'user_id': user.pk,
        'email': user.email,
        'is_staff': user.is_staff,
        'role': 'admin' if user.is_staff else 'student',
    }


class RegisterView(APIView):
    authentication_classes = [CSRFOnlyAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        email = _field(request, 'email').strip().lower()
        password = _field(request, 'password')

        try:
            validate_email(email)
            if len(email) > MAX_EMAIL_LENGTH:
                raise ValidationError('too long')
        except ValidationError:
            return api_error(
                'INVALID_EMAIL', 'Enter a valid email address', status.HTTP_400_BAD_REQUEST,
                [{'field': 'email', 'message': 'Enter a valid email address'}],
            )

        if len(password) < MIN_PASSWORD_LENGTH:
            return api_error(
                'PASSWORD_TOO_SHORT', 'Password must be at least 8 characters', status.HTTP_400_BAD_REQUEST,
                [{'field': 'password', 'message': 'Password must be at least 8 characters'}],
            )
        if len(password) > MAX_PASSWORD_LENGTH:
            return api_error(
                'VALIDATION_ERROR', 'Password must be at most 128 characters', status.HTTP_400_BAD_REQUEST,
                [{'field': 'password', 'message': 'Password must be at most 128 characters'}],
            )

        if User.objects.filter(email__iexact=email).exists():
            return api_error('EMAIL_TAKEN', 'Email already registered', status.HTTP_409_CONFLICT)

        try:
            with transaction.atomic():
                user = User.objects.create_user(email=email, password=password)
                profile = Profile.objects.create(user=user)  # empty StudentProfile (DR-12)
        except IntegrityError:  # two simultaneous registrations
            return api_error('EMAIL_TAKEN', 'Email already registered', status.HTTP_409_CONFLICT)

        login(request, user)
        return Response(
            {**_user_payload(user), 'profile_id': str(profile.id)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    authentication_classes = [CSRFOnlyAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        email = _field(request, 'email').strip().lower()
        password = _field(request, 'password')

        user = authenticate(request, email=email, password=password)
        if user is None:
            return api_error('INVALID_CREDENTIALS', 'Incorrect email or password', status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        return Response(_user_payload(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(_user_payload(request.user))
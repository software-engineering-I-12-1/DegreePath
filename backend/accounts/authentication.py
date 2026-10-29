from rest_framework.authentication import SessionAuthentication


class Session401Authentication(SessionAuthentication):
    """Session auth that answers anonymous requests with 401 instead of 403 (NFR-1)."""

    def authenticate_header(self, request):
        return 'Session'


class CSRFOnlyAuthentication(SessionAuthentication):
    """For register/login: no user is authenticated yet, but CSRF is still enforced (NFR-2)."""

    def authenticate(self, request):
        self.enforce_csrf(request)
        return None

    def authenticate_header(self, request):
        return 'Session'
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def api_error(code, message, http_status, details=None):
    """Design §5.1 error envelope: {"error": {"code", "message", "details"}}."""
    return Response(
        {'error': {'code': code, 'message': message, 'details': details or []}},
        status=http_status,
    )


_CODES = (
    (exceptions.NotAuthenticated, 'UNAUTHENTICATED'),
    (exceptions.AuthenticationFailed, 'UNAUTHENTICATED'),
    (exceptions.PermissionDenied, 'FORBIDDEN'),
    (exceptions.NotFound, 'NOT_FOUND'),
    (exceptions.MethodNotAllowed, 'METHOD_NOT_ALLOWED'),
    (exceptions.UnsupportedMediaType, 'UNSUPPORTED_MEDIA_TYPE'),
    (exceptions.Throttled, 'THROTTLED'),
    (exceptions.ParseError, 'VALIDATION_ERROR'),
    (exceptions.ValidationError, 'VALIDATION_ERROR'),
)

_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: 'VALIDATION_ERROR',
    status.HTTP_401_UNAUTHORIZED: 'UNAUTHENTICATED',
    status.HTTP_403_FORBIDDEN: 'FORBIDDEN',
    status.HTTP_404_NOT_FOUND: 'NOT_FOUND',
}


def _flatten(data):
    if isinstance(data, dict):
        out = []
        for field, value in data.items():
            message = ' '.join(str(v) for v in value) if isinstance(value, (list, tuple)) else str(value)
            out.append({'field': field, 'message': message})
        return out
    if isinstance(data, (list, tuple)):
        return [{'message': str(item)} for item in data]
    return [{'message': str(data)}]


def custom_exception_handler(exc, context):
    """Wrap every DRF-raised error (401, 403 CSRF, 400 parse, 404 ...) in the design envelope."""
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    code = next((c for cls, c in _CODES if isinstance(exc, cls)), None)
    code = code or _BY_STATUS.get(response.status_code, 'ERROR')

    if isinstance(exc, exceptions.ValidationError):
        message, details = 'Invalid request', _flatten(response.data)
    else:
        data = response.data
        message = str(data.get('detail', exc)) if isinstance(data, dict) else str(data)
        details = []

    response.data = {'error': {'code': code, 'message': message, 'details': details}}
    return response
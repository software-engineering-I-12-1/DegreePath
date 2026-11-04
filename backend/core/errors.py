from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import exceptions, status


def api_error(code, message, http_status, details=None):
    """Design §5.1 error envelope: {"error": {"code", "message", "details"}}."""
    return Response(
        {'error': {'code': code, 'message': message, 'details': details or []}},
        status=http_status,
    )


def custom_exception_handler(exc, context):
    """Standardizes DRF framework exceptions into Design §5.1 envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    # Already formatted with design error envelope
    if isinstance(response.data, dict) and 'error' in response.data:
        return response

    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        code = 'UNAUTHENTICATED'
    elif isinstance(exc, exceptions.PermissionDenied):
        code = 'FORBIDDEN'
    elif isinstance(exc, exceptions.NotFound):
        code = 'NOT_FOUND'
    elif isinstance(exc, exceptions.ParseError):
        code = 'INVALID_JSON'
    elif isinstance(exc, exceptions.ValidationError):
        code = 'VALIDATION_ERROR'
    elif response.status_code == 401:
        code = 'UNAUTHENTICATED'
    elif response.status_code == 403:
        code = 'FORBIDDEN'
    elif response.status_code == 404:
        code = 'NOT_FOUND'
    else:
        code = 'REQUEST_FAILED'

    message = ''
    if isinstance(response.data, dict) and 'detail' in response.data:
        message = str(response.data['detail'])
    elif isinstance(response.data, list):
        message = '; '.join(str(item) for item in response.data)
    else:
        message = str(response.data)

    return Response(
        {'error': {'code': code, 'message': message, 'details': []}},
        status=response.status_code,
    )

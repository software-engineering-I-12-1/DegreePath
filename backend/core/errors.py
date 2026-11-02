from rest_framework.response import Response


def api_error(code, message, http_status, details=None):
    """Design §5.1 error envelope: {"error": {"code", "message", "details"}}."""
    return Response(
        {'error': {'code': code, 'message': message, 'details': details or []}},
        status=http_status,
    )
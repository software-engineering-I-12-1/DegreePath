from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for deployment monitoring and frontend status.
    """
    db_status = "healthy"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return Response({
        "status": "ok",
        "app": "DegreePath",
        "version": "0.1.0",
        "database": db_status
    })

@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf_cookie(request):
    """
    Sets the csrftoken cookie for React client requests (Section 5.3 / API-14 / DR-10).
    """
    return HttpResponse(status=204)

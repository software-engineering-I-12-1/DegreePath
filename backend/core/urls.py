from django.urls import path
from .views import health_check, csrf_cookie

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('auth/csrf/', csrf_cookie, name='csrf_cookie'),
]

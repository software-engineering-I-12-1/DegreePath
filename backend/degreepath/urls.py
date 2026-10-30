"""
URL configuration for DegreePath.
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.http import JsonResponse
from pathlib import Path
from django.conf import settings

def index_fallback(request):
    index_file = settings.BASE_DIR.parent / 'frontend' / 'dist' / 'index.html'
    if index_file.exists():
        return TemplateView.as_view(template_name='index.html')(request)
    return JsonResponse({
        'message': 'DegreePath Backend API is running.',
        'health_check': '/api/health/',
        'docs': 'See docs/ for architecture specification.'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/profile/', include('profiles.urls')),
    path('api/', include('core.urls')),
    path('api/', include('catalog.urls')),
    # Catch-all for React SPA frontend routing
    re_path(r'^(?!api/|admin/|static/).*$', index_fallback, name='spa_index'),
]

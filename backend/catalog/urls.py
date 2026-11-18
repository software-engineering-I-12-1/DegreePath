from django.urls import path
from .views import (
    CourseListView, CatalogImportView, RequirementImportView, ProgramListView, ProgramDetailView,
)

urlpatterns = [
    path('courses/', CourseListView.as_view(), name='course_list'),
    path('admin/catalog-imports/', CatalogImportView.as_view(), name='catalog_import'),
    path('admin/requirement-imports/', RequirementImportView.as_view(), name='requirement_import'),
    path('programs/', ProgramListView.as_view(), name='program_list'),
    path('programs/<int:program_id>/', ProgramDetailView.as_view(), name='program_detail'),
]

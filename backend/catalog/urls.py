from django.urls import path
from .views import CourseListView, CatalogImportView

urlpatterns = [
    path('courses/', CourseListView.as_view(), name='course_list'),
    path('admin/catalog-imports/', CatalogImportView.as_view(), name='catalog_import'),
]

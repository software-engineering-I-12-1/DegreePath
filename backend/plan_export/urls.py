from django.urls import path

from .views import ExportCalendarView, ExportCsvView, ExportStatusView

urlpatterns = [
    path('status/', ExportStatusView.as_view(), name='plan_export_status'),
    path('<str:plan_id>/csv/', ExportCsvView.as_view(), name='plan_export_csv'),
    path('<str:plan_id>/calendar/', ExportCalendarView.as_view(), name='plan_export_calendar'),
]

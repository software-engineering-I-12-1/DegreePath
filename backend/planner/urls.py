from django.urls import path

from .views import ComparePlansView, GeneratePlanView

urlpatterns = [
    path('plans/generate/', GeneratePlanView.as_view(), name='plan_generate'),
    path('plans/compare/', ComparePlansView.as_view(), name='plan_compare'),
]

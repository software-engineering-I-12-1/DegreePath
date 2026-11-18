from django.urls import path

from .views import GeneratePlanView

urlpatterns = [
    path('plans/generate/', GeneratePlanView.as_view(), name='plan_generate'),
]

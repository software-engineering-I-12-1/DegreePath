from django.urls import path

from .views import OptionsView, ProfileView

urlpatterns = [
    path('', ProfileView.as_view(), name='profile'),
    path('options/', OptionsView.as_view(), name='profile_options'),
]
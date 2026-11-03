from django.urls import path

from .views import MyProfileView, OptionsView, ProfileDetailView

urlpatterns = [
    path('me/', MyProfileView.as_view(), name='profile_me'),
    path('options/', OptionsView.as_view(), name='profile_options'),
    path('<str:profile_id>/', ProfileDetailView.as_view(), name='profile_detail'),
]
from django.urls import path
from .views import UserProfileView, SubmitTestView, DashboardStatsView

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='profile_me'),
    path('test/submit/', SubmitTestView.as_view(), name='profile_test_submit'),
    path('dashboard/', DashboardStatsView.as_view(), name='profile_dashboard'),
]
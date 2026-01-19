from django.urls import path
from .views import UserProfileView, SubmitTestView, DashboardStatsView, GenerateTestView

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='profile_me'),
    path('test/generate/', GenerateTestView.as_view(), name='profile_test_generate'),
    path('test/submit/', SubmitTestView.as_view(), name='profile_test_submit'),
    path('dashboard/', DashboardStatsView.as_view(), name='profile_dashboard'),
]
from django.urls import path
from .views import StartSimulationView, GetSimulationView, SendMessageView, PerformActionView, HistoryListView

urlpatterns = [
    path('start/', StartSimulationView.as_view(), name='simu_start'),
    path('<uuid:uuid>/', GetSimulationView.as_view(), name='simu_detail'),
    path('<uuid:session_uuid>/message/', SendMessageView.as_view(), name='simu_message'),
    path('<uuid:session_uuid>/action/', PerformActionView.as_view(), name='simu_action'),
    path('history/', HistoryListView.as_view(), name='simu_history'),
]
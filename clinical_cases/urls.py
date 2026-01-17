from django.urls import path
from .views import ClinicalCaseListView, ClinicalCaseDetailView

urlpatterns = [
    path('', ClinicalCaseListView.as_view(), name='case_list'),
    path('<uuid:uuid>/', ClinicalCaseDetailView.as_view(), name='case_detail'),
]
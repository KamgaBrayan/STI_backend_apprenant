from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import ClinicalCase
from .serializers import ClinicalCaseListSerializer, ClinicalCaseDetailSerializer

class ClinicalCaseListView(generics.ListAPIView):
    """
    Retourne la liste des cas disponibles pour le Dashboard.
    Peut être filtré par ?specialty=Cardiologie
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ClinicalCaseListSerializer

    def get_queryset(self):
        queryset = ClinicalCase.objects.filter(is_active=True)
        specialty = self.request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(specialty=specialty)
        return queryset

class ClinicalCaseDetailView(generics.RetrieveAPIView):
    """
    Retourne le détail complet d'un cas via son UUID pour la Simulation.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ClinicalCaseDetailSerializer
    lookup_field = 'uuid'
    queryset = ClinicalCase.objects.filter(is_active=True)
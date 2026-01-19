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
        specialty_param = self.request.query_params.get('specialty')
        
        if specialty_param:
            # Mapping Frontend (slug) -> Backend (Nom BDD)
            # C'est important car sync_validated_cases.py stocke en Français capitalisé
            MAPPING = {
                'cardiology': 'Cardiologie',
                'pulmonology': 'Pneumologie',
                'gastroenterology': 'Gastro-entérologie',
                'neurology': 'Neurologie',
                'emergency': 'Urgence',
                'general': 'Médecine Générale'
            }
            
            # On essaie de mapper, sinon on prend la valeur brute
            target_specialty = MAPPING.get(specialty_param.lower(), specialty_param)
            
            # Filtrage insensible à la casse (__iexact)
            queryset = queryset.filter(specialty__iexact=target_specialty)
            
        return queryset

class ClinicalCaseDetailView(generics.RetrieveAPIView):
    """
    Retourne le détail complet d'un cas via son UUID pour la Simulation.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ClinicalCaseDetailSerializer
    lookup_field = 'uuid'
    queryset = ClinicalCase.objects.filter(is_active=True)
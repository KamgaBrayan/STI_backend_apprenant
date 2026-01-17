from rest_framework import serializers
from .models import ClinicalCase

class ClinicalCaseListSerializer(serializers.ModelSerializer):
    """Pour la liste dans le Dashboard (Cartes légères)"""
    class Meta:
        model = ClinicalCase
        fields = ['uuid', 'title', 'description', 'specialty', 'difficulty']

class ClinicalCaseDetailSerializer(serializers.ModelSerializer):
    """Pour la Simulation (Données complètes)"""
    class Meta:
        model = ClinicalCase
        fields = ['uuid', 'title', 'specialty', 'difficulty', 'case_data']
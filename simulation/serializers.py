from rest_framework import serializers
from .models import SimulationSession, ChatMessage, ActionLog
from clinical_cases.serializers import ClinicalCaseDetailSerializer

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'timestamp']

class ActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionLog
        fields = ['id', 'action_type', 'details', 'timestamp']

class SimulationSessionSerializer(serializers.ModelSerializer):
    # On inclut les détails du cas pour l'affichage initial
    clinical_case_title = serializers.CharField(source='clinical_case.title', read_only=True)
    
    class Meta:
        model = SimulationSession
        fields = ['uuid', 'clinical_case', 'clinical_case_title', 'start_time', 'status', 'score_rime']
        read_only_fields = ['uuid', 'start_time', 'score_rime']

class SimulationDetailSerializer(serializers.ModelSerializer):
    """Pour reprendre une simulation en cours : charge tout l'historique"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    actions = ActionLogSerializer(many=True, read_only=True)
    case_data = serializers.JSONField(source='clinical_case.case_data', read_only=True)

    class Meta:
        model = SimulationSession
        fields = ['uuid', 'status', 'messages', 'actions', 'case_data']
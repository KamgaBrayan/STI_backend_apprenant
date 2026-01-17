import uuid
from django.db import models
from django.conf import settings
from clinical_cases.models import ClinicalCase

class SimulationSession(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='simulations')
    clinical_case = models.ForeignKey(ClinicalCase, on_delete=models.CASCADE)
    
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Scores finaux (Calculés à la fin)
    score_rime = models.FloatField(default=0.0) # Global 0-100
    details_rime = models.JSONField(default=dict, blank=True) # {"R": 80, "I": 60, "M": 40, "E": 20}
    
    status = models.CharField(
        max_length=20, 
        choices=[('EN_COURS', 'En cours'), ('TERMINEE', 'Terminée')],
        default='EN_COURS'
    )

    def __str__(self):
        return f"Simu {self.uuid} - {self.user.nom}"

class ChatMessage(models.Model):
    session = models.ForeignKey(SimulationSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=[('doctor', 'Doctor'), ('patient', 'Patient'), ('system', 'System')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

class ActionLog(models.Model):
    session = models.ForeignKey(SimulationSession, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=50) # EXAMEN, DIAGNOSTIC, TRAITEMENT, NOTE
    details = models.JSONField() # Ex: {"exam_id": "1", "exam_name": "ECG"}
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Pour le calcul RIME instantané (optionnel)
    impact_score = models.FloatField(default=0.0)
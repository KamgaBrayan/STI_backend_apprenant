from django.db import models
from django.conf import settings

class LearnerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    
    # --- Etape 1 : Identité ---
    study_level = models.CharField(max_length=50, blank=True, null=True)  # L2, M1, Interne...
    specialty = models.CharField(max_length=100, blank=True, null=True)   # Cardio, Pneumo...
    objectives = models.JSONField(default=list, blank=True)               # ["clinical_reasoning", ...]
    
    # --- Etape 2 : Comportement ---
    clinical_experience = models.CharField(max_length=50, blank=True, null=True) # junior, senior...
    learning_method = models.CharField(max_length=50, blank=True, null=True)     # visual, practical...
    challenges = models.JSONField(default=list, blank=True)                      # ["cognitive_bias", ...]
    
    # --- Etape 3 : Motivation ---
    motivation = models.TextField(blank=True, null=True)
    
    # --- Etape 4 & 5 : Calibration (Test de positionnement) ---
    test_score = models.FloatField(default=0.0) # Score en %
    calibrated_level = models.CharField(max_length=50, default="Novice") # Niveau calculé par le système (Novice, Intermédiaire, Expert)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profil de {self.user.email}"
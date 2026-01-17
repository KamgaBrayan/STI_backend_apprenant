import uuid
from django.db import models

class ClinicalCase(models.Model):
    # Identifiants et Méta-données pour le Dashboard
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255)  # Ex: "Douleur Thoracique Aiguë"
    description = models.TextField(blank=True) # Ex: "Patient de 45 ans..."
    
    # Filtres pour le moteur de recommandation (Redis-like)
    SPECIALTIES = [
        ('Cardiologie', 'Cardiologie'),
        ('Pneumologie', 'Pneumologie'),
        ('Gastro-entérologie', 'Gastro-entérologie'),
        ('Neurologie', 'Neurologie'),
        ('Urgence', 'Urgence'),
    ]
    specialty = models.CharField(max_length=50, choices=SPECIALTIES)
    
    DIFFICULTIES = [
        ('Novice', 'Novice'),
        ('Intermédiaire', 'Intermédiaire'),
        ('Expert', 'Expert'),
    ]
    difficulty = models.CharField(max_length=20, choices=DIFFICULTIES, default='Novice')
    
    # LE COEUR DU SUJET : Contenu JSON complet (IFinalClinicalCase)
    # Contient: anamnèse, constantes, la vérité terrain (diagnostic correct), etc.
    case_data = models.JSONField() 

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.specialty}] {self.title} ({self.difficulty})"
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from clinical_cases.models import ClinicalCase

# Données simulées basées sur src/types/clinicalCase.ts
CASE_42_DATA = {
    "codeUUID": "case-42-thoracique",
    "ageTranche": "40-50",
    "sexe": "M",
    "parametresVitaux": {
        "FC": "98", "TA": "145/90", "Temp": "38.2", "SpO2": "98"
    },
    "symptomes": [
        {
            "nomDuSymptome": "Douleur Thoracique",
            "localisationSymptome": "Retrosternale",
            "dureeSymptome": "2 heures",
            "degreDIntensite": "8/10",
            "activitesDeclenchantes": "Repos",
            "frequence": "Continue",
            "dateDeDebutSymptome": "2023-10-27"
        }
    ],
    "antecedentsFamiliaux": "Père décédé IDM à 55 ans",
    "allergies": [{"nom": "Pénicilline", "reaction": "Oedème"}],
    "maladies": [
        {
            "nom": "Hypertension Artérielle",
            "dateDeDebut": "2018",
            "traitementsSuivis": "Ramipril"
        }
    ],
    "chirurgie": [],
    "diagnosticNom": "Syndrome Coronarien Aigu",
    "diagnosticResultat": "Positif",
    "diagnosticObservation": "Infarctus du myocarde ST+",
    "specialiteDiagnostic": "Cardiologie",
    "diagnosticPrincipalPathologie": "Infarctus",
    "examens": [{"nom": "ECG"}, {"nom": "Troponine"}],
    "traitementsMedicamenteux": [],
    "traitementsChirurgicaux": [],
    "voyage": "Néant",
    "habitat": "Urbain",
    "activitePhysique": {"niveau": "Faible"},
    "addiction": {},
    "animauxDeCompagnie": "Aucun"
}

def seed():
    print("Suppression des anciens cas...")
    ClinicalCase.objects.all().delete()

    print("Création du Cas #42...")
    ClinicalCase.objects.create(
        title="Douleur Thoracique Aiguë",
        description="Patient de 45 ans présentant une douleur constrictive irradiant dans le bras gauche.",
        specialty="Cardiologie",
        difficulty="Intermédiaire",
        case_data=CASE_42_DATA
    )
    
    print("Création du Cas #402 (Abdominal)...")
    ClinicalCase.objects.create(
        title="Douleur Abdominale FID",
        description="Douleur fosse iliaque droite avec fièvre légère.",
        specialty="Urgence",
        difficulty="Novice",
        case_data={**CASE_42_DATA, "diagnosticNom": "Appendicite Aiguë"} # Simplifié pour l'exemple
    )

    print("Terminé ! 2 cas injectés.")

if __name__ == '__main__':
    seed()
import os
import requests
import json
from django.core.management.base import BaseCommand
from clinical_cases.models import ClinicalCase

# URL du Backend Expert
DATA_BACKEND_URL = os.environ.get('DATA_BACKEND_URL', 'https://sti-5i2r.onrender.com/api/v1/cases/validated/')

class Command(BaseCommand):
    help = 'Synchronise les cas cliniques validés depuis le module Expert.'

    def handle(self, *args, **options):
        endpoint = DATA_BACKEND_URL
        self.stdout.write(self.style.WARNING(f"📡 Connexion au Backend Data : {endpoint}"))

        try:
            response = requests.get(endpoint, timeout=15)
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"❌ Erreur API ({response.status_code})"))
                return

            cases_list = response.json()
            # Gestion pagination DRF standard
            if isinstance(cases_list, dict) and 'results' in cases_list:
                cases_list = cases_list['results']

            self.stdout.write(self.style.SUCCESS(f"✅ {len(cases_list)} cas trouvés."))

            count = 0
            for remote in cases_list:
                # 1. Filtrage : On ignore les cas marqués "DELETED" ou "REJECTED" si nécessaire
                # Mais la route s'appelle /validated/, donc on suppose qu'on prend tout ce qui arrive.
                
                # 2. Extraction des données
                uuid = remote.get('patient_uuid')
                raw_info = remote.get('patient_info_raw') or {}
                
                # Gestion Motifs (Titre)
                motifs = remote.get('motif_consultation', [])
                titre_cas = "Consultation Standard"
                histoire = ""
                
                if motifs and len(motifs) > 0:
                    premier_motif = motifs[0]
                    titre_cas = premier_motif.get('motif', titre_cas)
                    # Concaténation des notes pour le contexte LLM
                    for note in premier_motif.get('notes', []):
                        histoire += f"{note.get('contenu', '')} "

                # Gestion Spécialité (Mapping important)
                source_specialty = remote.get('specialite_confirmee', 'general_medicine')
                mapped_specialty = self._map_specialty(source_specialty)

                # Gestion Difficulté (Non fournie, on déduit ou met par défaut)
                difficulty = "Intermédiaire"

                # 3. Construction du JSONB interne (Pour la simulation)
                # On nettoie et restructure pour notre Frontend
                case_data_clean = {
                    "codeUUID": uuid,
                    "ageTranche": remote.get('age_tranche', '?'),
                    "sexe": remote.get('sexe', 'X'),
                    "contexteVrai": histoire.strip(),
                    "parametresVitaux": self._extract_vitals(raw_info),
                    "symptomes": self._extract_symptomes(motifs),
                    "antecedentsFamiliaux": remote.get('antecedents', {}).get('antecedentsFamiliaux', ''),
                    "allergies": [{"nom": remote.get('antecedents', {}).get('allergies', 'Aucune')}],
                    "maladies": [{"nom": remote.get('antecedents', {}).get('maladiesChroniques', '')}],
                    "chirurgie": [{"nom": remote.get('antecedents', {}).get('chirurgiesAnterieures', '')}],
                    "traitementsMedicamenteux": [{"nom": remote.get('antecedents', {}).get('traitementsActuels', '')}],
                    
                    # Vérité terrain
                    "diagnosticNom": remote.get('diagnostic_final'),
                    "specialiteDiagnostic": mapped_specialty,
                    "examens": remote.get('examens', [])
                }

                # 4. Upsert en BDD
                ClinicalCase.objects.update_or_create(
                    uuid=uuid,
                    defaults={
                        "title": titre_cas[:255],
                        "description": f"Patient {remote.get('age_tranche')} - {remote.get('sexe')}. {histoire[:100]}...",
                        "specialty": mapped_specialty,
                        "difficulty": difficulty,
                        "case_data": case_data_clean,
                        "is_active": True
                    }
                )
                count += 1

            self.stdout.write(self.style.SUCCESS(f"🎉 Sync terminée : {count} cas traités."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erreur : {e}"))

    def _map_specialty(self, source):
        """Mappe 'general_medicine' -> 'Médecine Générale' pour correspondre au modèle Django"""
        mapping = {
            "general_medicine": "Médecine Générale",
            "cardiology": "Cardiologie",
            "pneumology": "Pneumologie",
            "gastroenterology": "Gastro-entérologie",
            "neurology": "Neurologie",
            "emergency": "Urgence"
        }
        # Retourne la valeur mappée ou 'Urgence' par défaut si inconnu
        return mapping.get(source, "Urgence")

    def _extract_vitals(self, raw_info):
        # Le JSON montre parametresVitaux comme une liste
        vitals_list = raw_info.get('parametresVitaux', [])
        if not vitals_list: return {}
        last = vitals_list[0] # On prend le plus récent
        return {
            "FC": str(last.get('frequenceCardiaqueBpm', '?')),
            "TA": str(last.get('tensionArterielle', '?')),
            "Temp": str(last.get('temperatureCelsius', '?')),
            "SpO2": "N/A" # Pas dans le JSON fourni
        }

    def _extract_symptomes(self, motifs):
        symptomes = []
        if not motifs: return symptomes
        
        # On regarde dans 'enrichissement_ia'
        ia_data = motifs[0].get('enrichissement_ia', {})
        symps_ia = ia_data.get('symptomes_detectes', {})
        
        # Le format dans l'exemple est un objet unique, pas une liste ? 
        # "symptomes_detectes": { "localisation": "..." }
        # On gère les deux cas (liste ou objet)
        if isinstance(symps_ia, dict) and symps_ia:
            symptomes.append({
                "nomDuSymptome": symps_ia.get('localisation', 'Symptôme'),
                "localisationSymptome": symps_ia.get('localisation', ''),
                "dureeSymptome": str(symps_ia.get('duree', '')),
                "degreDIntensite": str(symps_ia.get('degre_intensite', ''))
            })
        elif isinstance(symps_ia, list):
            for s in symps_ia:
                symptomes.append({"nomDuSymptome": str(s)})
                
        return symptomes
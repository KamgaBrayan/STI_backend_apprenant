import os
import requests
import json
from django.core.management.base import BaseCommand
from clinical_cases.models import ClinicalCase

# URL de ton PREMIER backend (celui qui a les données Fultang)
# Assure-toi que l'autre serveur tourne sur ce port (ex: 8000)
DATA_BACKEND_URL = os.environ.get('DATA_BACKEND_URL', 'https://sti-5i2r.onrender.com/api/v1/cases/validated/')

class Command(BaseCommand):
    help = 'Récupère les cas validés depuis le Backend Data et peuple la base de simulation.'

    def handle(self, *args, **options):
        endpoint = f"{DATA_BACKEND_URL}/api/v1/cases/validated/"
        
        self.stdout.write(self.style.WARNING(f"📡 Connexion au Backend Data : {endpoint}"))

        try:
            response = requests.get(endpoint, timeout=10)
            
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"❌ Erreur API ({response.status_code}) : {response.text}"))
                return

            cases_list = response.json()
            # Si l'API retourne une pagination {results: [...]}, on gère
            if isinstance(cases_list, dict) and 'results' in cases_list:
                cases_list = cases_list['results']
            
            self.stdout.write(self.style.SUCCESS(f"✅ {len(cases_list)} cas validés trouvés. Début du traitement..."))

            count_created = 0
            count_updated = 0

            for remote_case in cases_list:
                # --- 1. MAPPING DES DONNÉES ---
                # On transforme le format "Data Backend" en format "Simulation Backend"
                
                patient_uuid = remote_case.get('patient_uuid')
                specialty = remote_case.get('specialite_confirmee', 'Urgence')
                
                # Extraction des motifs
                motifs = remote_case.get('motif_consultation', [])
                primary_motif = "Consultation générale"
                history_text = ""
                
                if motifs and len(motifs) > 0:
                    last_motif = motifs[-1]
                    primary_motif = last_motif.get('motif', primary_motif)
                    # On concatène les notes pour faire une description
                    notes = last_motif.get('notes', [])
                    for n in notes:
                        history_text += f"{n.get('contenu', '')} "

                # Titre & Description
                title = f"{primary_motif}"
                age = remote_case.get('age_tranche', '?')
                sexe = remote_case.get('sexe', 'X')
                
                description = (
                    f"Patient(e) (Tranche d'âge: {age}, Sexe: {sexe}). "
                    f"Motif: {primary_motif}. "
                    f"Diagnostic confirmé: {remote_case.get('diagnostic_final', 'En cours')}."
                )

                # --- 2. CONSTRUCTION DU JSON COMPLEXE (case_data) ---
                # C'est ce JSON qui sera donné au LLM (Gemini) pour jouer le patient.
                
                # Récupération des constantes (on prend les dernières dispos)
                raw_info = remote_case.get('patient_info_raw', {})
                vitals_list = raw_info.get('parametresVitaux', [])
                last_vitals = vitals_list[0] if vitals_list else {}
                
                # Mapping des symptômes (venant de l'IA du backend précédent ou bruts)
                symptomes_mapped = []
                # Si l'IA du backend précédent a enrichi les données :
                if motifs:
                    enrichissement = motifs[-1].get('enrichissement_ia', {})
                    if enrichissement:
                        symps_ia = enrichissement.get('symptomes_detectes', [])
                        if isinstance(symps_ia, list):
                            for s in symps_ia:
                                if isinstance(s, str): # Cas simple liste de strings
                                    symptomes_mapped.append({"nomDuSymptome": s})
                                elif isinstance(s, dict): # Cas détaillé
                                    symptomes_mapped.append({
                                        "nomDuSymptome": s.get('localisation', 'Symptôme'),
                                        "localisationSymptome": s.get('localisation'),
                                        "dureeSymptome": s.get('duree'),
                                        "frequence": s.get('frequence')
                                    })

                antecedents_source = remote_case.get('antecedents', {})
                
                case_data_structure = {
                    "codeUUID": patient_uuid,
                    "ageTranche": age,
                    "sexe": sexe,
                    "contexteVrai": history_text.strip(), # Pour aider le LLM a avoir du contexte
                    "parametresVitaux": {
                        "FC": str(last_vitals.get('frequenceCardiaqueBpm', '?')),
                        "TA": str(last_vitals.get('tensionArterielle', '?')),
                        "Temp": str(last_vitals.get('temperatureCelsius', '?')),
                        "Poids": str(last_vitals.get('poidsKg', '?')),
                        "SpO2": "N/A" # Souvent manquant dans Fultang
                    },
                    "symptomes": symptomes_mapped,
                    "antecedentsFamiliaux": antecedents_source.get('antecedentsFamiliaux', 'Non renseigné'),
                    "allergies": antecedents_source.get('allergies', 'Aucune'),
                    "maladies": [{"nom": antecedents_source.get('maladiesChroniques', '')}],
                    "chirurgie": [{"nom": antecedents_source.get('chirurgiesAnterieures', '')}],
                    "traitementsMedicamenteux": [{"nom": antecedents_source.get('traitementsActuels', '')}],
                    
                    # Vérité Terrain
                    "diagnosticNom": remote_case.get('diagnostic_final'),
                    "specialiteDiagnostic": specialty,
                    "examens": remote_case.get('examens', []), # On garde la liste brute
                }

                # --- 3. SAUVEGARDE EN BDD ---
                
                obj, created = ClinicalCase.objects.update_or_create(
                    uuid=patient_uuid,
                    defaults={
                        "title": title[:255],
                        "description": description,
                        "specialty": self._map_specialty(specialty),
                        "difficulty": "Intermédiaire", # Par défaut, car Fultang ne donne pas la difficulté
                        "case_data": case_data_structure,
                        "is_active": True
                    }
                )

                if created:
                    count_created += 1
                    self.stdout.write(f"   ➕ Créé: {title}")
                else:
                    count_updated += 1
                    self.stdout.write(f"   🔄 Mis à jour: {title}")

            self.stdout.write(self.style.SUCCESS(f"\n🎉 Sync terminée : {count_created} créés, {count_updated} mis à jour."))

        except requests.exceptions.ConnectionError:
            self.stdout.write(self.style.ERROR(f"❌ Impossible de se connecter à {DATA_BACKEND_URL}. Vérifie que l'autre serveur tourne."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erreur inattendue : {e}"))

    def _map_specialty(self, source_specialty):
        """Mappe les spécialités texte libre vers les choix du modèle"""
        # SPECIALTIES = [('Cardiologie', 'Cardiologie'), ('Pneumologie', 'Pneumologie')...]
        # On essaie de trouver une correspondance
        
        valid_specialties = [
            'Cardiologie', 'Pneumologie', 'Gastro-entérologie', 
            'Neurologie', 'Urgence'
        ]
        
        if not source_specialty:
            return 'Urgence'
            
        source_clean = source_specialty.capitalize()
        
        # Mapping approximatif
        if "Cardio" in source_clean: return "Cardiologie"
        if "Pneumo" in source_clean: return "Pneumologie"
        if "Gastro" in source_clean: return "Gastro-entérologie"
        if "Neuro" in source_clean: return "Neurologie"
        
        if source_clean in valid_specialties:
            return source_clean
            
        return 'Urgence' # Fallback
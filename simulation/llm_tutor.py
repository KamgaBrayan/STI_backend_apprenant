# backend_apprenant/simulation/llm_tutor.py

import json
import logging
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# On utilise une configuration JSON stricte pour le Tuteur
client = genai.Client(api_key=settings.GOOGLE_API_KEY)

def generate_adaptive_test(profile_data):
    """
    Génère un QCM adaptatif basé sur le profil de l'étudiant.
    Retourne un JSON strict.
    """
    
    # 1. Extraction du contexte apprenant
    niveau = profile_data.get('study_level', 'Non défini')
    specialite = profile_data.get('specialty', 'Médecine Générale')
    objectifs = ", ".join(profile_data.get('objectives', []))
    
    # 2. Prompt Engineering pour le Tuteur
    system_instruction = f"""
    RÔLE : Tu es un Professeur de Médecine Expert chargé d'évaluer un étudiant.
    
    CONTEXTE ÉTUDIANT :
    - Niveau : {niveau}
    - Spécialité visée : {specialite}
    - Objectifs : {objectifs}
    
    TÂCHE :
    Génère un Quiz de positionnement de 3 questions à choix multiples (QCM).
    Les questions doivent être adaptées au niveau et à la spécialité.
    - Question 1 : Diagnostic / Clinique
    - Question 2 : Pharmacologie / Traitement
    - Question 3 : Raisonnement / Physiopathologie
    
    FORMAT DE SORTIE ATTENDU (JSON STRICT) :
    Doit être une liste d'objets avec cette structure exacte, sans markdown autour :
    [
        {{
            "id": "q1",
            "category": "Diagnostic",
            "question": "L'énoncé de la question...",
            "options": {{ "a": "Choix 1", "b": "Choix 2", "c": "Choix 3", "d": "Choix 4" }},
            "correct_answer": "b",
            "explanation": "Pourquoi c'est la bonne réponse."
        }},
        ...
    ]
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Plus intelligent pour suivre des instructions JSON
            contents="Génère le test maintenant.",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", # Force le JSON
                temperature=0.5, # Créatif mais précis
            )
        )
        
        # Nettoyage et parsing
        content = response.text
        # Parfois les LLM mettent ```json ... ```, on nettoie au cas où
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        return json.loads(content)

    except Exception as e:
        logger.error(f"Erreur Tuteur Génération Test : {e}")
        # Fallback en cas d'erreur (Questions statiques de secours)
        return [
            {
                "id": "q1", 
                "category": "Général", 
                "question": "Erreur de génération IA. Quelle est la conduite à tenir ?", 
                "options": {"a": "Réessayer", "b": "Attendre"}, 
                "correct_answer": "a"
            }
        ]

def evaluate_test_results(learner_answers, test_questions, profile_data):
    """
    Le Tuteur corrige le test et commente la performance.
    """
    score = 0
    total = len(test_questions)
    
    # Correction technique simple
    # On suppose que test_questions est la liste des objets générés précédemment
    # Note : Dans une vraie implémentation, il faudrait stocker le test généré en session ou DB pour comparer.
    
    # Pour l'instant, on va demander au LLM d'analyser la cohérence globale
    # C'est une approche "Tuteur" : il regarde le niveau déclaré vs résultats
    
    pass # On implémentera ça dans la vue, c'est plus simple de compter les points en Python direct.

MODEL_NAME = 'gemini-2.5-flash' 

def evaluate_session(case_data, chat_history, actions_log):
    """
    Analyse une session complète et génère un rapport RIME structuré.
    """
    
    # 1. Préparation du contexte pour le Tuteur
    actions_text = "\n".join([f"- {a['type']} : {a['details']}" for a in actions_log])
    
    chat_text = ""
    for msg in chat_history:
        role = "Médecin (Étudiant)" if msg['role'] == 'doctor' else "Patient"
        chat_text += f"{role}: {msg['content']}\n"

    system_instruction = f"""
    RÔLE : Tu es un Professeur de Médecine Expert évaluant un étudiant sur un cas clinique simulé.
    
    CAS CLINIQUE (VÉRITÉ TERRAIN) :
    {json.dumps(case_data, ensure_ascii=False)}
    
    TRACE DE LA SESSION ÉTUDIANT :
    --- CONVERSATION ---
    {chat_text}
    
    --- ACTIONS / EXAMENS / DIAGNOSTIC ---
    {actions_text}
    
    TA MISSION :
    Évalue la performance de l'étudiant selon le modèle R.I.M.E.
    
    CRITÈRES DE NOTATION (0 à 100) :
    - REPORTER (R) : A-t-il bien posé les questions pour recueillir l'anamnèse ? A-t-il identifié les signes clés ?
    - INTERPRETER (I) : A-t-il demandé les bons examens complémentaires justifiés par l'anamnèse ?
    - MANAGER (M) : Le diagnostic final est-il correct ? Le traitement est-il adapté ?
    - EDUCATOR (E) : Le ton était-il professionnel ? A-t-il expliqué les choses au patient ? (Note arbitraire si peu de données).
    
    FORMAT DE SORTIE (JSON STRICT) :
    {{
        "global_score": 75,
        "rime_details": {{
            "R": 80,
            "I": 60,
            "M": 70,
            "E": 90
        }},
        "feedback_text": "Commentaire pédagogique constructif adressé à l'étudiant (tutoiement). Mentionne les points forts et les erreurs critiques (ex: oubli d'un examen vital)."
    }}
    """

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="Procède à l'évaluation maintenant.",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.3, # Faible température pour une notation rigoureuse
            )
        )
        
        # Parsing du JSON
        content = response.text.strip()
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0]
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0]
            
        return json.loads(content)

    except Exception as e:
        logger.error(f"Erreur Tuteur Évaluation : {e}")
        # Fallback pour ne pas planter l'application
        return {
            "global_score": 0,
            "rime_details": {"R": 0, "I": 0, "M": 0, "E": 0},
            "feedback_text": "Erreur lors de la génération du rapport par le Tuteur. Veuillez contacter l'administrateur."
        }
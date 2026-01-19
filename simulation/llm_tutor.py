# backend_apprenant/simulation/llm_tutor.py

import json
import logging
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# On utilise une configuration JSON stricte pour le Tuteur
# Initialisation du client
try:
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"Erreur init Client Gemini: {e}")

def get_client():
    """Récupère le client de manière sécurisée"""
    api_key = getattr(settings, 'GOOGLE_API_KEY', None)
    if not api_key:
        print("⚠️ CLÉ API MANQUANTE")
        return None
    return genai.Client(api_key=api_key)

def extract_json_from_text(text):
    """
    Extrait un bloc JSON (liste ou objet) d'une chaîne de texte brute
    même si elle contient du Markdown ```json ... ``` ou du texte autour.
    """
    text = text.strip()
    try:
        # 1. Tentative directe
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Recherche de pattern Markdown ```json ... ```
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Recherche brute des crochets [...] pour une liste
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError("Aucun JSON valide trouvé dans la réponse LLM")


def generate_adaptive_test(profile_data):
    """
    Génère un QCM adaptatif basé sur le profil de l'étudiant.
    Retourne un JSON strict.
    """
    client = get_client()
    if not client:
        return fallback_questions("Clé API manquante")
    
    # Gestion de la langue
    raw_lang = profile_data.get('language', 'fr')
    langue_instruction = "FRANÇAIS (French)" if raw_lang == 'fr' else "ANGLAIS (English)"
    
    # Gestion des objectifs
    niveau = profile_data.get('study_level', 'Interne')
    raw_spec = profile_data.get('specialty', 'general')
    specialty_map = {
        'cardiology': 'Cardiologie (Cœur, Vaisseaux)',
        'pulmonology': 'Pneumologie (Poumons, Respiration)',
        'emergency': 'Médecine d\'Urgence (Soins critiques)',
        'neurology': 'Neurologie (Cerveau, Système nerveux)',
        'gastroenterology': 'Gastro-entérologie',
        'general': 'Médecine Générale'
    }
    # On prend le mapping ou la valeur brute si non trouvée, en s'assurant que c'est une string
    specialite_humaine = specialty_map.get(str(raw_spec).lower(), str(raw_spec))

    objs = profile_data.get('objectives', [])
    objectifs = ", ".join(profile_data.get('objectives', []))
    
    # 2. Prompt Engineering pour le Tuteur
    system_instruction = f"""
    RÔLE : Tu es un Professeur de Médecine Expert spécialisé en {specialite_humaine}. Tu es chargé d'évaluer un étudiant.
    
    RÈGLES CRITIQUES (NON NÉGOCIABLES) :
    1. LANGUE DE SORTIE : Tu dois IMPÉRATIVEMENT écrire en {langue_instruction}.
    2. DOMAINE UNIQUE : Toutes les questions doivent porter EXCLUSIVEMENT sur : {specialite_humaine}.
       - Si le domaine est 'Cardiologie', ne pose PAS de questions sur une fracture du pied.
       - Si le domaine est 'Pneumologie', reste sur les poumons/respiration.
    3. NIVEAU : Adapte la difficulté pour un niveau : {niveau}.
    4. Objectifs de l'étudiant : {objectifs}
    
    IMPORTANT : TOUT LE CONTENU GÉNÉRÉ DOIT ÊTRE EN : {langue_instruction.upper()}

    TÂCHE :
    Génère un Quiz de positionnement de 15 questions à choix multiples (QCM).
    Les questions doivent être adaptées au niveau et à la spécialité choisié (une spécialité).
    Chaque question doit avoir 4 options (a, b, c, d) avec une seule bonne réponse.
    Fournis également une explication brève pour chaque bonne réponse.
    
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

    Ne mets PAS de texte avant ou après le JSON. Fournis uniquement le JSON.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Plus intelligent pour suivre des instructions JSON
            contents="Génère le test maintenant.",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json", # Force le JSON
                temperature=0.5, # Créatif mais précis
            )
        )
        
        # Log pour le debug (visible dans Render logs)
        print(f"DEBUG LLM RAW OUTPUT: {response.text}")

        # Nettoyage et parsing
        content = extract_json_from_text(response.text)
        
        # Validation minimale
        if not isinstance(content, list) or len(content) == 0:
            raise ValueError("Le LLM a renvoyé un format inattendu (pas une liste)")
            
        return content

    except Exception as e:
        logger.error(f"Erreur Tuteur Génération Test : {e}")
        # Fallback en cas d'erreur (Questions statiques de secours)
        return [
            {
                "id": "q1", 
                "category": "Général", 
                "question": "Erreur de Tuteur pour vous proposer le test. Quelle est la conduite à tenir ?", 
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
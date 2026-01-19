import os
import json
import logging
import asyncio
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_random_exponential, retry_if_exception_type

# --- NOUVEAUX IMPORTS GOOGLE GEN AI ---
from google import genai
from google.genai import types, errors

logger = logging.getLogger(__name__)

def get_client():
    api_key = getattr(settings, 'GOOGLE_API_KEY', None)
    if not api_key:
        # Fallback pour le dev local si settings échoue (mais .env est mieux)
        api_key = os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        print("⚠️ ERREUR CRITIQUE: Clé API Google manquante !")
        return None
        
    return genai.Client(api_key=api_key)

# Configuration de sécurité (Pour éviter les blocages sur des termes médicaux)
SAFETY_SETTINGS = [
    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
]

def build_system_instruction(case_data):
    """Construit le prompt système avec les données JSON injectées."""
    return f"""
    RÔLE : Tu es un patient simulé.
    CONTEXTE : Examen médical virtuel.
    
    DONNÉES CLINIQUES (VÉRITÉ TERRAIN) :
    {json.dumps(case_data, ensure_ascii=False, indent=2)}

    RÈGLES IMPÉRATIVES :
    1. INCARNATION : Tu es le patient, pas une IA. Parle simplement.
    2. FIDÉLITÉ : Ne mentionne JAMAIS un symptôme absent du JSON. Si on te demande un truc que tu n'as pas, dis "Non".
    3. VOCABULAIRE : Utilise des termes profanes ("J'ai mal au ventre" et non "Douleur abdominale").
    4. ÉTAT D'ESPRIT : Adapte ton stress selon la douleur (0-10) indiquée dans le dossier.
    5. INCONNU : Pour les détails de vie privée non spécifiés (métier, nom du chien), invente quelque chose de cohérent.
    """

# --- GESTION DES RETRIES (TENACITY) ---
# On cible les erreurs spécifiques du nouveau SDK (errors.APIError)
@retry(
    wait=wait_random_exponential(multiplier=1, max=10),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(errors.APIError) # Catch les erreurs 429/500/503
)
async def call_gemini_async(contents, system_instruction):
    """
    Appel ASYNC au modèle avec le nouveau SDK google-genai.
    """
    client = get_client() # <-- Ajout
    if not client: raise ValueError("Client Google non initialisé")
    
    try:
        # On utilise le client async (client.aio)
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash', # Version stable et rapide
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=300,
                safety_settings=SAFETY_SETTINGS
            )
        )
        return response.text
    except Exception as e:
        logger.error(f"Erreur lors de l'appel Gemini: {e}")
        raise e # On relève pour que Tenacity déclenche le retry

async def get_patient_response_async(case_data, messages_history, user_message_content):
    """
    Point d'entrée principal.
    Transforme les données brutes en objets `types.Content` pour le SDK.
    """

    # Initialisation du client ICI
    client = get_client()
    if not client:
        return "Erreur technique : Le simulateur n'est pas configuré (Clé API manquante)."

    # 1. Préparer le System Prompt
    sys_instruction = build_system_instruction(case_data)
    
    # 1. Préparer le System Prompt
    sys_instruction = build_system_instruction(case_data)
    
    # 2. Convertir l'historique DB en objets types.Content
    # Le SDK veut une liste de types.Content(role='...', parts=[...])
    formatted_contents = []

    if messages_history:
        current_role = None
        current_parts = []

        for msg in messages_history:
            # Mapping des rôles : 'doctor' -> 'user', 'patient' -> 'model'
            sdk_role = 'user' if msg['role'] == 'doctor' else 'model'
            
            # Gestion de la fusion des messages consécutifs (User -> User interdit)
            if sdk_role == current_role:
                current_parts.append(msg['content'])
            else:
                if current_role:
                    # On finalise le bloc précédent
                    formatted_contents.append(types.Content(
                        role=current_role,
                        parts=[types.Part.from_text(text="\n".join(current_parts))]
                    ))
                current_role = sdk_role
                current_parts = [msg['content']]
        
        # Ajouter le dernier bloc en attente
        if current_role and current_parts:
            formatted_contents.append(types.Content(
                role=current_role,
                parts=[types.Part.from_text(text="\n".join(current_parts))]
            ))

    # 3. Ajouter le message actuel de l'utilisateur à la fin de la liste 'contents'
    # Contrairement à l'ancien SDK où on utilisait chat.send_message, ici generate_content
    # est stateless, on lui donne TOUTE la conversation + le nouveau message d'un coup.
    
    # Si le dernier message de l'historique était déjà 'user', on le fusionne, sinon on l'ajoute.
    # (Gemini n'aime pas finir par 'model' puis ajouter 'user', il préfère l'alternance stricte,
    # mais generate_content accepte généralement que le dernier soit 'user')
    
    formatted_contents.append(types.Content(
        role='user',
        parts=[types.Part.from_text(text=user_message_content)]
    ))

    # 4. Exécuter l'appel sécurisé
    try:
        response_text = await call_gemini_async(formatted_contents, sys_instruction)
        return response_text
    except Exception:
        # Fallback ultime si les 5 retries échouent
        return "(Le patient semble confus et ne répond pas. Vérifiez la connexion.)"
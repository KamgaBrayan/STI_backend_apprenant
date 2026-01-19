from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from asgiref.sync import sync_to_async

from .models import SimulationSession, ChatMessage, ActionLog
from .serializers import SimulationSessionSerializer, SimulationDetailSerializer, ChatMessageSerializer
from clinical_cases.models import ClinicalCase
from .llm_service import get_patient_response_async
from .llm_tutor import evaluate_session

from rest_framework import generics

class StartSimulationView(APIView):
    """Démarre une session pour un cas donné (UUID du cas en body)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        case_uuid = request.data.get('case_uuid')
        clinical_case = get_object_or_404(ClinicalCase, uuid=case_uuid)
        
        # Vérifie si une session est déjà en cours pour ce cas (optionnel)
        # session, created = SimulationSession.objects.get_or_create(...)
        
        session = SimulationSession.objects.create(
            user=request.user,
            clinical_case=clinical_case
        )
        
        # Message système initial
        ChatMessage.objects.create(
            session=session,
            role='system',
            content="Le patient est entré dans la salle."
        )

        return Response(SimulationSessionSerializer(session).data, status=status.HTTP_201_CREATED)

class GetSimulationView(generics.RetrieveAPIView):
    """Récupère l'état complet d'une session (Chat + Actions)"""
    permission_classes = [IsAuthenticated]
    serializer_class = SimulationDetailSerializer
    queryset = SimulationSession.objects.all()
    lookup_field = 'uuid'

class SendMessageView(APIView):
    permission_classes = [] 

    @sync_to_async
    def get_session_and_history(self, session_uuid, user):
        """Récupère tout ce dont on a besoin en un seul appel DB (ou presque)"""
        session = get_object_or_404(SimulationSession, uuid=session_uuid, user=user)
        
        # Force la récupération des données JSON
        case_data = session.clinical_case.case_data
        
        # Récupère l'historique sous forme de liste de dicts (plus léger pour l'async)
        # On exclut 'system' car on le gère via system_instruction
        msgs = session.messages.exclude(role='system').order_by('timestamp')
        history = [{'role': m.role, 'content': m.content} for m in msgs]
        
        return session, case_data, history

    @sync_to_async
    def save_message(self, session, role, content):
        return ChatMessage.objects.create(session=session, role=role, content=content)

    async def post(self, request, session_uuid):
        # 1. Validation basique
        content = request.data.get('content')
        if not content:
            return Response({"error": "Message vide"}, status=400)

        try:
            # 2. Récupération contexte (DB Sync -> Async)
            session, case_data, history = await self.get_session_and_history(session_uuid, request.user)

            # 3. Sauvegarde message User
            doctor_msg = await self.save_message(session, 'doctor', content)

            # 4. Appel LLM (C'est ici que la magie Async opère)
            # On ne bloque pas le thread Django principal
            ai_response = await get_patient_response_async(case_data, history, content)

            # 5. Sauvegarde réponse IA
            patient_msg = await self.save_message(session, 'patient', ai_response)

            # 6. Réponse API
            return Response({
                "doctor_message": {
                    "role": doctor_msg.role, 
                    "content": doctor_msg.content, 
                    "timestamp": doctor_msg.timestamp
                },
                "patient_message": {
                    "role": patient_msg.role, 
                    "content": patient_msg.content, 
                    "timestamp": patient_msg.timestamp
                }
            })

        except Exception as e:
            print(f"Erreur critique View: {e}")
            return Response({"error": "Erreur serveur"}, status=500)

    
class HistoryListView(generics.ListAPIView):
    """
    Retourne la liste des simulations terminées de l'utilisateur.
    Formaté pour le tableau 'Historique de Travail' du Front.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SimulationSessionSerializer # On réutilise le serializer de base pour l'instant

    def get_queryset(self):
        # On ne veut que les sessions de l'utilisateur courant
        # Optionnel : filtrer seulement les 'TERMINEE'
        return SimulationSession.objects.filter(user=self.request.user).order_by('-start_time')
    
    # Si le format du Front (HistoryItem) est très différent du Serializer par défaut,
    # on peut surcharger 'list' pour formater manuellement :
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = []
        for session in queryset:
            # Calcul du statut texte (ex: ACQUISE > 80%)
            statut_text = "NON MAÎTRISE"
            if session.score_rime >= 80:
                statut_text = "ACQUISE"
            elif session.score_rime >= 50:
                statut_text = "PARTIELLE"

            data.append({
                "id": str(session.uuid),
                "casClinique": session.clinical_case.title, # Titre du cas
                "type": session.clinical_case.specialty,    # Spécialité ou Type
                "date": session.start_time.strftime("%Y-%m-%d %H:%M"),
                "scoreRIME": int(session.score_rime),
                "statut": statut_text
            })
        return Response(data)
    

class PerformActionView(APIView):
    """Enregistre une action et déclenche l'évaluation si c'est la fin."""
    permission_classes = [IsAuthenticated]

    # Helpers asynchrones pour la base de données
    @sync_to_async
    def get_session_data(self, session_uuid, user):
        session = get_object_or_404(SimulationSession, uuid=session_uuid, user=user)
        # On force le chargement des relations pour éviter les erreurs sync/async
        case_data = session.clinical_case.case_data
        
        # Récupération historique chat
        chat_msgs = list(session.messages.all().values('role', 'content'))
        
        # Récupération historique actions
        actions = list(session.actions.all().values('action_type', 'details'))
        
        return session, case_data, chat_msgs, actions

    @sync_to_async
    def save_action(self, session, action_type, details):
        ActionLog.objects.create(session=session, action_type=action_type, details=details)

    @sync_to_async
    def close_session_with_score(self, session, evaluation):
        session.status = 'TERMINEE'
        session.end_time = timezone.now()
        session.score_rime = evaluation.get('global_score', 0)
        session.details_rime = evaluation.get('rime_details', {})
        # On pourrait stocker le feedback_text quelque part, par exemple dans details_rime ou un nouveau champ
        # Pour l'instant, on l'ajoute dans details_rime pour qu'il soit sauvegardé
        session.details_rime['feedback_text'] = evaluation.get('feedback_text', "")
        session.save()

    async def post(self, request, session_uuid):
        try:
            action_type = request.data.get('action_type')
            details = request.data.get('details')
            
            # 1. Récupération Session
            session, case_data, chat_history, actions_log = await self.get_session_data(session_uuid, request.user)
            
            # 2. Sauvegarde de l'action courante
            await self.save_action(session, action_type, details)
            
            # 3. Si c'est la fin, on lance le Tuteur
            if action_type == 'DIAGNOSTIC_FINAL':
                # On ajoute l'action courante aux logs pour l'évaluation
                actions_log.append({'type': action_type, 'details': details})
                
                # APPEL AU TUTEUR (Prend ~3-5 secondes)
                evaluation = await sync_to_async(evaluate_session)(case_data, chat_history, actions_log)
                
                # Sauvegarde du score
                await self.close_session_with_score(session, evaluation)
                
                return Response({
                    "status": "Simulation terminée",
                    "evaluation": evaluation
                }, status=status.HTTP_200_OK)

            return Response({"status": "Action enregistrée"}, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Erreur PerformAction: {e}")
            return Response({"error": str(e)}, status=500)
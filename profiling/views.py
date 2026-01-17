from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import LearnerProfile
from .serializers import LearnerProfileSerializer
from django.db.models import Avg, Count
from simulation.models import SimulationSession

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Permet de récupérer et mettre à jour le profil (Etapes 1 à 3 du wizard)
    """
    serializer_class = LearnerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Crée le profil s'il n'existe pas encore (lazy creation)
        profile, created = LearnerProfile.objects.get_or_create(user=self.request.user)
        return profile

class SubmitTestView(APIView):
    """
    Etape 4 & 5 : Reçoit les réponses du test, calcule le score et met à jour le niveau.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        answers = request.data.get('answers', {})
        # Logique de correction (Réponses hardcodées basées sur votre fichier en.json du Front)
        # Q1: ECG (b), Q2: Bradycardie/Hypotension (a ou c selon contexte, disons a), Q3: Pneumothorax (c)
        # Adaptons selon votre JSON Front : q1->b, q2->b (selon step4/page.tsx), q3->c
        
        correct_answers = {
            'q1': 'b', 
            'q2': 'b', 
            'q3': 'c'
        }
        
        score = 0
        total = len(correct_answers)

        for key, correct_val in correct_answers.items():
            if answers.get(key) == correct_val:
                score += 1
        
        final_score_percent = (score / total) * 100
        
        # Algorithme simple de calibration (STI Logique Moteur)
        calibrated_level = "Novice"
        if final_score_percent > 80:
            calibrated_level = "Expert"
        elif final_score_percent > 40:
            calibrated_level = "Intermédiaire"

        # Sauvegarde
        profile, _ = LearnerProfile.objects.get_or_create(user=request.user)
        profile.test_score = final_score_percent
        profile.calibrated_level = calibrated_level
        profile.save()

        return Response({
            "test_score": final_score_percent,
            "calibrated_level": calibrated_level,
            "message": "Profil calibré avec succès."
        }, status=status.HTTP_200_OK)


class DashboardStatsView(APIView):
    """
    Agrégation complète pour le Tableau de Bord (Vue 1).
    Retourne : Profil, Score Global, Stats par patho, Recommandation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        sessions = SimulationSession.objects.filter(user=user, status='TERMINEE')

        # 1. Calcul du Score Global RIME (Moyenne des sessions)
        global_score = sessions.aggregate(Avg('score_rime'))['score_rime__avg'] or 0
        
        # 2. Stats par Pathologie (Pour le tableau 'PathologyStats')
        # On groupe par spécialité du cas clinique
        stats_by_specialty = []
        # Note: Pour faire un GROUP BY propre via Django ORM sur une FK, c'est un peu verbeux.
        # On va faire simple pour l'exemple : itérer sur les spécialités connues.
        specialties = ["Cardiologie", "Pneumologie", "Urgence", "Gastro-entérologie"]
        
        for spec in specialties:
            spec_sessions = sessions.filter(clinical_case__specialty=spec)
            count = spec_sessions.count()
            if count > 0:
                avg_perf = spec_sessions.aggregate(Avg('score_rime'))['score_rime__avg'] or 0
                stats_by_specialty.append({
                    "specialty": spec,
                    "attempts": count,
                    "performance": int(avg_perf),
                    # Logique simple pour couleur
                    "color": "bg-primary" if avg_perf > 70 else "bg-accent-warning"
                })

        # 3. Détails RIME (Pour 'CompetenceDetailsCard')
        # Ici on simule une répartition fixe ou aléatoire car on n'a pas encore stocké le détail RIME fin partout
        # Idéalement, on ferait la moyenne des JSONField 'details_rime'
        rime_details = {
            "reporter": 0, "interpreter": 0, "manager": 0, "educator": 0
        }
        if sessions.exists():
            # Exemple de calcul simplifié (à améliorer si vous stockez le détail)
            rime_details = {
                "reporter": int(global_score + 5) if global_score < 95 else 100,
                "interpreter": int(global_score),
                "manager": int(global_score - 10) if global_score > 10 else 0,
                "educator": int(global_score - 20) if global_score > 20 else 0,
            }

        return Response({
            "user_name": user.nom,
            "global_score": int(global_score),
            "rime_details": rime_details,
            "pathology_stats": stats_by_specialty,
            # Recommandation factice (Mock)
            "recommended_case": {
                "id": "42",
                "title": "Douleur Thoracique",
                "reason": "Pour améliorer votre score Manager"
            }
        })
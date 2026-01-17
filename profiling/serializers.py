from rest_framework import serializers
from .models import LearnerProfile

class LearnerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearnerProfile
        fields = [
            'study_level', 'specialty', 'objectives',
            'clinical_experience', 'learning_method', 'challenges',
            'motivation', 'test_score', 'calibrated_level'
        ]
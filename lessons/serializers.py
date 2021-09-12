from rest_framework import serializers
from .models import Lesson, UserLessonProgress
import logging
logger = logging.getLogger("django.server")

class UserLessonProgressSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserLessonProgress
        fields = '__all__'

class AdminLessonSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.sequence_no = instance.max_seq_no
        instance.save()
        return instance
    
    
    class Meta:
        model = Lesson
        fields = '__all__'

class LessonSerializer(serializers.ModelSerializer):
    user_progress = serializers.SerializerMethodField()

    def get_user_progress(self, obj): 
        
        return UserLessonProgressSerializer(obj.get_user_progress(self.context['request'].user)).data
    
    
    class Meta:
        model = Lesson
        fields = '__all__'


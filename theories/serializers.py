from rest_framework import serializers
from .models import TheoryChapter


class TheoryChapterSerializer(serializers.ModelSerializer):
    
    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.sequence_no = instance.max_seq_no
        instance.save()
        return instance
        
    class Meta:
        model = TheoryChapter
        fields = '__all__'
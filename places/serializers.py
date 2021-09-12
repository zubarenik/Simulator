from rest_framework import serializers
from .models import Place
from characters.serializers import CharacterSerializer
from characters.models import Character
from django.db.models import Max
import logging
logger = logging.getLogger("django.server")


class PlaceJsonInfoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Place
        fields = '__all__'

class PlaceUserInfoSerializer(serializers.ModelSerializer):
    character = serializers.SerializerMethodField()
    parent_message = serializers.SerializerMethodField()

    def get_parent_message(self, obj):
        if obj.parent_message:
            return PlaceUserInfoSerializer(obj.parent_message).data
        return None
        
    def get_character(self, obj):
        if obj.character:
            character = obj.character
            if obj.forced_role:
                character.default_role = obj.forced_role
            return CharacterSerializer(character).data
        return None

    class Meta:
        model = Place
        exclude = ("node_info", )


class PlaceSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.page.append_place(instance)
        return instance
    
    def update(self, instance, validated_data):
        instance = super(PlaceSerializer, self).update(instance, validated_data)
        instance.page.update_place(instance)
        return instance

    class Meta:
        model = Place
        fields = '__all__'
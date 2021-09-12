from django.contrib.postgres import fields
from pages.models import Page
from rest_framework import serializers

from simulator_groups.serializers import SimulatorGroupInfoSerializer
from .models import Simulator, SimulatorUser
from characters.models import Character


class AdminSimulatorSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.create_onboarding()        
        
        instance.sequence_no = instance.max_seq_no
        instance.save()
        return instance
    
    class Meta:
        model = Simulator
        exclude = ('completed_by_user_set', )


class SimulatorSerializer(serializers.ModelSerializer):
    onboarding_id = serializers.ReadOnlyField()
    group_info = serializers.SerializerMethodField()

    def get_group_info(self, obj):
        return SimulatorGroupInfoSerializer(obj.group).data
    
    class Meta:
        model = Simulator
        exclude = ('completed_by_user_set', 'pay_TerminalKey', 'pay_EmailCompany', 'pay_password', 'token')


class SimulatorUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulatorUser
        fields = "__all__"

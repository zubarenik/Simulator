import logging

from simulators.models import Simulator, SimulatorUser
from simulators.serializers import SimulatorUserSerializer
from rest_framework import fields, serializers
from django.contrib.auth import get_user_model
from simulator_groups.models import SimulatorGroup
from .models import AuthAttempt

User = get_user_model()
logger = logging.getLogger("django.server")


class AdminUserSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        instance = super(AdminUserSerializer, self).create(validated_data)
        instance.set_password(validated_data['password'])
        instance.is_admin_user = True
        instance.save()
        default_group = SimulatorGroup()
        default_group.owner = instance
        default_group.save()
        return instance

    def validate(self, data):
        if "re_password" not in self.context.get("request").data or data["password"] != self.context.get("request").data['re_password']:
            raise serializers.ValidationError({
                    're_password': 'Пароли не совпадают'
                })
        return data

    class Meta:
        model = User
        fields = '__all__'


class UserCreateSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        instance = super(UserCreateSerializer, self).create(validated_data)
        instance.set_password(validated_data['password'])
        simulators = Simulator.objects.filter(group=self.context['request'].simulator.group)
        logger.info(simulators)
        for simulator in simulators:
            sim_user = SimulatorUser(
                simulator=simulator,
                user=instance
            )
            sim_user.save()
        instance.save()

        self.context['request'].simulator.send_email(0, instance)
        return instance

    def validate(self, data):
        if "re_password" not in self.context.get("request").data or data["password"] != self.context.get("request").data['re_password']:
            raise serializers.ValidationError({
                    're_password': 'Пароли не совпадают'
                })
        return data

    class Meta:
        model = User
        fields = ("password", "username", "email")


class UserInfoSerializer(serializers.ModelSerializer):
    sim_info = serializers.SerializerMethodField()

    def get_sim_info(self, obj):
        sim_user = SimulatorUser.objects.filter(user=obj, simulator=self.context['request'].simulator).first()
        logger.info(obj)
        logger.info(self.context['request'].simulator)
        if sim_user:
            return SimulatorUserSerializer(sim_user).data
        return None

    def validate_email(self, value):
        user = self.context['request'].user
        simulator = self.context['request'].simulator

        if SimulatorUser.objects.filter(user__email=value, simulator=simulator).exclude(user=user).exists():
            raise serializers.ValidationError("Такая учетная запись уже существует")

        postfix = ''
        if simulator.group:
            postfix = '+{}'.format(simulator.group.id)
        user.username = value + postfix
        user.save()

        return value

    class Meta:
        model = User
        exclude = ("password", "username", 'user_permissions', 'groups', 'api_key', 'last_login', 'is_active', 'is_superuser', 'is_admin_user')


class AuthAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthAttempt
        fields = "__all__"

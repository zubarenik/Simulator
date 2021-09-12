from rest_framework import serializers
from .models import Payment, PromoCode
from simulators.models import Simulator


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    content_type = serializers.SerializerMethodField()

    def get_status(self, obj):
        return obj.check_bank_transaction_status(simulator=Simulator.objects.get(simulator=obj.content_object))

    def get_content_type(self, obj):
        return obj.content_type.name

    class Meta:
        model = Payment
        fields = ('id', 'creation_time', 'status', 'content_type', 'object_id')

import logging

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer

from backend.application_viewset import AdminApplicationViewset
from simulators.models import Simulator, SimulatorUser
from .models import PromoCode, Payment
from .serializers import PromoCodeSerializer, PaymentSerializer
from .permissions import PromoCodePermissions

logger = logging.getLogger("django.server")


class AdminPromoCodeViewSet(AdminApplicationViewset):
    pagination_class = None
    serializer_class = PromoCodeSerializer
    permission_classes = [PromoCodePermissions]

    def get_queryset(self):
        if "simulator" in self.params:
            queryset = PromoCode.objects.filter(simulator__id=self.params.get('simulator'))
        else:
            queryset = PromoCode.objects.all()
        return queryset


class PaymentViewSet(viewsets.GenericViewSet):
    pagination_class = None
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()
    template_name = 'cloud_payment.html'

    @action(detail=False, methods=['post'])
    def pay(self, request, *args, **kwargs):
        if "simulator" in request.data:
            content_object = get_object_or_404(Simulator, pk=int(request.data['simulator']))
            price = content_object.price
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        promo_code = None
        if "promo_code" in request.data:
            slug = request.data['promo_code']
            promo_code = get_object_or_404(PromoCode, slug=slug)

            if (not content_object) or (content_object == promo_code.simulator):
                content_object = promo_code.simulator
                if promo_code.activate(request.user):
                    price = promo_code.price

        user = SimulatorUser.objects.filter(simulator=content_object, user=request.user).first()
        payment = Payment.objects.create(
            user=user,
            sum=price,
            description=content_object.name if not promo_code else 'Promo code: {}'.format(promo_code.slug),
            content_object=content_object,
            return_url=content_object.alias if content_object.alias else content_object.domain,
            promo_code=promo_code,
            backend=content_object.pay_type
        )
        payment.save()
        payment.init_bank_transaction(content_object)

        # content_object.send_email(1, user.user.email)
        return Response({'id': payment.id, 'confirmation_url': payment.confirmation_url})

    @action(detail=False, methods=['post'])
    def activate_promo_code(self, request, *args, **kwargs):
        if "simulator" in request.data:
            pk = int(request.data['simulator'])
            content_object = get_object_or_404(Simulator, pk=pk)
        else:
            content_object = None

        slug = request.data['promo_code']
        promo_code = get_object_or_404(PromoCode, slug=slug)

        content_object_match = promo_code.simulator == content_object
        if not content_object_match:
            return Response({'success': False, 'price': promo_code.price, 'promo_code': slug})

        success = promo_code.activate(request.user)
        return Response({'success': success, 'price': promo_code.price, 'promo_code': slug})

    @action(detail=True, methods=['get'], renderer_classes=[TemplateHTMLRenderer])
    def pay_cloudpayments(self, request, *args, **kwargs):
        payment = self.get_object()
        return Response({
            'publicId': payment.content_object.pay_TerminalKey,
            'name': payment.description,
            'amount': payment.sum,
            'accountId': payment.user.user.email,
            'invoiceId': payment.id,
            'vat': payment.content_object.get_vat(),
        })

    @action(detail=False, methods=['post'])
    def complete_cloudpayments(self, request, *args, **kwargs):
        context = request.data
        payment = Payment.objects.get(pk=int(context['InvoiceId']))

        if 'Status' not in context:
            context['Status'] = 'Fail'

        payment.check_bank_transaction_status(status=context['Status'])
        return Response({'code': 0})

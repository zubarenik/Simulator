import requests, json, logging
from datetime import datetime, timezone
from copy import deepcopy
from hashlib import sha256

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from backend.settings import HOST_URL

User = get_user_model()

CONTENT_TYPE_PAYMENT_CHOICES = (
    models.Q(app_label='api_admin', model='simulator')
)


class PromoCode(models.Model):
    simulator = models.ForeignKey('simulators.Simulator', on_delete=models.CASCADE, null=True, blank=True)
    slug = models.CharField(max_length=40)
    text = models.TextField(null=True, blank=True)
    price = models.PositiveIntegerField()
    content_type = models.ForeignKey(
        ContentType,
        limit_choices_to=CONTENT_TYPE_PAYMENT_CHOICES,
        default=None,
        on_delete=models.SET_DEFAULT,
        null=True,
        blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    user_set = models.ManyToManyField(User, null=True)
    expires = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)

    def activate(self, user):
        if self.expires and self.expires < datetime.now(timezone.utc):
            return False
        if self.user_set.filter(id=user.id).exists():
            return True
        if self.usage_limit and self.usage_limit <= self.usage_count:
            return False
        else:
            self.user_set.add(user)
            self.usage_count += 1
            self.save()
            return True

    def is_active(self):
        expired = self.expires and self.expires < datetime.now(timezone.utc)
        limit_exceeded = self.usage_limit and self.usage_limit <= self.usage_count
        return not (expired or limit_exceeded)

    def __str__(self):
        return '{}: {}'.format(self.slug, str(self.content_object))


class Payment(models.Model):
    CANCELED = 0
    PENDING = 1
    SUCCEEDED = 2
    STATUS_CHOICES = (
        (CANCELED, 'canceled'),
        (PENDING, 'pending'),
        (SUCCEEDED, 'succeeded'),
    )

    TYPE_CHOICES = (
        ('tinkoff', 'tinkoff'),
        ('cloudpayments', 'cloudpayments'),
    )

    content_type = models.ForeignKey(
        ContentType,
        limit_choices_to=CONTENT_TYPE_PAYMENT_CHOICES,
        default=None,
        on_delete=models.SET_DEFAULT,
        null=True,
        blank=True)

    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    creation_time = models.DateTimeField(auto_now_add=True, blank=True)

    sum = models.PositiveIntegerField()
    return_url = models.CharField(max_length=200)
    description = models.CharField(max_length=200, null=True, blank=True)
    user = models.ForeignKey('simulators.SimulatorUser', on_delete=models.CASCADE)

    confirmation_url = models.CharField(max_length=200, null=True, blank=True)
    payment_id = models.CharField(max_length=200, null=True, blank=True)

    status = models.IntegerField(default=1, choices=STATUS_CHOICES)
    backend = models.CharField(max_length=30, choices=TYPE_CHOICES)

    promo_code = models.ForeignKey(PromoCode, null=True, blank=True, on_delete=models.SET_NULL)

    @staticmethod
    def _get_tinkoff_token(jsn, simulator):
        b = deepcopy(jsn)
        b['Password'] = simulator.pay_password
        b.pop('Receipt', None)
        b.pop('DATA', None)
        b_items = sorted(list(b.items()), key=lambda p: p[0])
        b_values = [str(val) for key, val in b_items]
        b_str = ''.join(b_values)
        return sha256(b_str.encode('utf-8')).hexdigest()

    def _signed(self, jsn, simulator):
        b = deepcopy(jsn)
        b['Token'] = self._get_tinkoff_token(jsn, simulator)
        return b

    def get_vat(self, simulator):
        vat = simulator.vat
        if not vat:
            return "none"
        return f"vat{vat}"

    def _pay_tinkoff(self, simulator):
        response = requests.post(
            'https://securepay.tinkoff.ru/v2/Init',
            json=self._signed({
                "TerminalKey": simulator.pay_TerminalKey,
                "Amount": self.sum * 100,
                "OrderId": self.id,
                "Description": simulator.simulator.name,
                "DATA": {
                    "Email": self.user.user.email
                },
                "Receipt": {
                    "Email": self.user.user.email,
                    "EmailCompany": simulator.pay_EmailCompany,
                    "Taxation": "usn_income",
                    "Items": [
                        {
                            "Name": simulator.simulator.name,
                            "Price": self.sum * 100,
                            "Quantity": 1,
                            "Amount": self.sum * 100,
                            "PaymentMethod": "full_prepayment",
                            "PaymentObject": "service",
                            "Tax": self.getVat(simulator),
                        }
                    ]
                }
            }, simulator)
        )
        jsn = json.loads(response.text)
        assert jsn['ErrorCode'] == '0'
        self.confirmation_url = jsn['PaymentURL']
        self.payment_id = jsn['PaymentId']
        self.save()

    def _cloudpayments_pay(self):
        self.payment_id = self.id
        self.confirmation_url = HOST_URL + "/api/pay_cloudpayments/" + str(self.payment_id)
        self.save()

    def init_bank_transaction(self, simulator):
        if self.payment_id:
            return

        if self.backend == 'tinkoff':
           self._pay_tinkoff(simulator)
        elif self.backend == 'cloudpayments':
            self._cloudpayments_pay()

    def check_bank_transaction_status(self, simulator=None, status=None):
        if not self.payment_id:
            return None

        elif self.status != 1:
            return self.status

        elif self.backend == 'tinkoff':
            response = requests.post(
                'https://securepay.tinkoff.ru/v2/GetState',
                json=self._signed({
                    "TerminalKey": simulator.pay_TerminalKey,
                    "PaymentId": self.payment_id,
                }, simulator)
            )

            try:
                assert response.status_code == 200
            except:
                return self.status

            try:
                jsn = json.loads(response.text)
                assert jsn['Message'] == 'OK'
            except:
                return self.status

            if jsn['Status'] in ('REJECTED', 'REFUNDED'):
                self.status = 0
                # self.content_object.send_email(2, self.user.user)
            elif jsn['Status'] == 'CONFIRMED':
                self.status = 2
                if self.content_object == self.user.simulator:
                    self.user.simulator_paid = True
                    self.user.save()

                if self.user.simulator.notifications_url:
                    data = {
                        "user_id": self.user.id,
                        "user_email": self.user.email,
                        "simulator_id": self.user.simulator.id,
                        "price": self.sum,
                        "promocode": self.promo_code if self.promo_code else ""
                    }

                    requests.post(self.user.simulator.notifications_url, data)
            self.save()
            return self.status

        elif self.backend == 'cloudpayments':
            if not status:
                return status

            if status in ('Authorized', 'Completed'):
                self.status = 2
                if self.content_object == self.user.simulator:
                    self.user.simulator_paid = True
                    self.user.save()

                if self.user.simulator.notifications_url:
                    data = {
                        "user_id": self.user.id,
                        "user_email": self.user.email,
                        "simulator_id": self.user.simulator.id,
                        "price": self.sum,
                        "promocode": self.promo_code if self.promo_code else ""
                    }

                    requests.post(self.user.simulator.notifications_url, data)
            else:
                self.status = 0
                # self.content_object.send_email(2, self.user.user)
            self.save()
            return self.status

    def __str__(self):
        return "({id}) {user}: {content_object} - {status}".format(id=self.id,
                                                                   user=self.user,
                                                                   content_object=self.content_object,
                                                                   status=dict(self.STATUS_CHOICES).get(self.status))

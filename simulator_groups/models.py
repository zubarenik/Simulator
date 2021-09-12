from django.db import models
from django.contrib.auth import get_user_model

from emails.models import Email

User = get_user_model()


class SimulatorGroup(models.Model):
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_simulator_group_set')
    name = models.CharField(max_length=200, default="Основная группа")

    email_sender = models.CharField(max_length=30, blank=True, null=True)

    auth_facebook_key = models.CharField(max_length=255, blank=True, null=True)
    auth_facebook_secret = models.CharField(max_length=255, blank=True, null=True)
    auth_vk_key = models.CharField(max_length=255, blank=True, null=True)
    auth_vk_secret = models.CharField(max_length=255, blank=True, null=True)

    def send_email(self, type, user):
        email = Email.objects.filter(group=self, email_type=type).first()
        if email:
            email.send_email(user=user, email_sender=self.email_sender)

    def __str__(self):
        return '({}) {}'.format(self.id, self.name)
from string import Template
from django.db import models
from .emails import send_email


class Email(models.Model):
    simulator = models.ForeignKey('simulators.Simulator', on_delete=models.CASCADE, blank=True, null=True)
    group = models.ForeignKey('simulator_groups.SimulatorGroup', on_delete=models.CASCADE, blank=True, null=True)
    TYPES = (
        (0, 'Регистрация'),
        (1, 'Покупка'),
        (2, 'Покупка отклонена'),
        (3, 'Автоматическая регистрация'),
    )
    email_type = models.PositiveIntegerField(choices=TYPES, default=0)
    template = models.TextField()
    theme = models.CharField(max_length=255)

    def send_email(self, user, email_sender, password=None):
        if not user.subscribe:
            return

        template = self.template
        if self.email_type == 3:
            template = Template(template).safe_substitute(password=password,
                                                          email=user.email,
                                                          first_name=user.first_name,
                                                          last_name=user.last_name)

        send_email(user.email, template, self.theme, email_sender)

    def __str__(self):
        return '({}) {} - {}'.format(self.id, self.email_type, self.simulator)

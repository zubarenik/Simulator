from django.db import models
from django.contrib.auth.models import AbstractUser

STATES = {
    'Регистрация': -2,
    'Создание персонажа': -1,
    'Онбординг': 0,
    'Прохождение урока': 1,
}
STATES_CHOICES = [(value, key) for key, value in STATES.items()]


class User(AbstractUser):
    creation_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    male = models.BooleanField(null=True, blank=True)
    vip = models.BooleanField(default=False)
    is_admin_user = models.BooleanField(default=False)
    avatar = models.ImageField(upload_to='user_avatars', blank=True, null=True)
    email_confirmed = models.BooleanField(default=False)
    email_confirmation_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    balance = models.IntegerField(default=0)
    curr_simulator = models.IntegerField(default=0)
    send_notifications = models.BooleanField(default=True)
    last_notification = models.DateTimeField(null=True, blank=True)
    api_key = models.CharField(max_length=200, null=True, blank=True)
    utm = models.TextField(null=True, blank=True)

    last_action = models.IntegerField(choices=STATES_CHOICES, default=-2)
    last_action_time = models.DateTimeField(blank=True, null=True)
    last_lesson = models.ForeignKey('lessons.Lesson', on_delete=models.CASCADE, blank=True, null=True)

    subscribe = models.BooleanField(default=True)

    temporary_code = models.CharField(max_length=8, null=True, blank=True, unique=True)

    facebook_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    vk_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    def __str__(self):
        return '{}'.format(self.username)


class AuthAttempt(models.Model):
    key = models.CharField(max_length=500, null=True, blank=True)
    TYPES = (
        (0, 'Начало авторизации'),
        (1, 'Ошибка авторизации'),
        (2, 'Отказ от авторизации'),
        (3, 'Успех авторизации'),
    )
    status = models.IntegerField(default=0, choices=TYPES)
    code = models.CharField(max_length=255, blank=True, null=True, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    creation_time = models.DateTimeField(auto_now_add=True, blank=True)
    simulator = models.ForeignKey('simulators.Simulator', on_delete=models.CASCADE, null=True, blank=True)

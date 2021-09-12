from django.contrib import admin
from .models import Lesson, UserLessonProgress

admin.site.register(Lesson)
admin.site.register(UserLessonProgress)

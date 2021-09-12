from django.contrib import admin
from .models import Payment, PromoCode

admin.site.register(PromoCode)
admin.site.register(Payment)

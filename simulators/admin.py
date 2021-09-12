from django.contrib import admin

# Register your models here.
from .models import Simulator, SimulatorUser

admin.site.register(Simulator)
admin.site.register(SimulatorUser)
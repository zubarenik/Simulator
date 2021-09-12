from django.db.models import query
from django.shortcuts import render
from backend.application_viewset import AdminApplicationViewset
from .serializers import SimulatorGroupSerializer
from .models import SimulatorGroup
# Create your views here.


class AdminSimulatorGroupViewSet(AdminApplicationViewset):
    pagination_class = None
    serializer_class = SimulatorGroupSerializer
    
    def get_queryset(self):
        return SimulatorGroup.objects.filter(owner=self.request.user)


from .permissions import TheoryChapterPermissions
from backend.application_viewset import AdminApplicationViewset
from .serializers import TheoryChapterSerializer
from .models import TheoryChapter
import logging

logger = logging.getLogger("django.server")
# Create your views here.


class AdminTheoryChapterViewSet(AdminApplicationViewset):
    pagination_class = None
    serializer_class = TheoryChapterSerializer
    permission_classes = [TheoryChapterPermissions]

    def get_queryset(self):
        
        if "simulator" in self.params:
            queryset = TheoryChapter.objects.filter(simulator__id=self.params.get('simulator'))
        else:
            queryset = TheoryChapter.objects.all()
        
        return queryset
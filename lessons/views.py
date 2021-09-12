from lessons.permissions import LessonPermissions
from backend.application_viewset import AdminApplicationViewset, ApplicationReadOnlyViewSet
from .serializers import LessonSerializer, AdminLessonSerializer
from .permissions import LessonPermissions
from .models import Lesson
from backend.helpers import SAFE_ACTIONS
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import logging
logger = logging.getLogger("django.server")

# Create your views here.


class AdminLessonViewSet(AdminApplicationViewset):
    pagination_class = None
    serializer_class = AdminLessonSerializer
    permission_classes = [LessonPermissions]
    
    @action(detail=False, methods=["post"])
    def reorder(self, request, *args, **kwargs):
        if "ids" in request.data:
            if "simulator" in request.data:
                if not Lesson.objects.filter(simulator__id=request.data['simulator']).count() == len(request.data['ids']):
                    return  Response({'lessons': "Неверное количество уроков"}, status=status.HTTP_400_BAD_REQUEST)
            for idx, id in enumerate(request.data['ids']):
                try:
                    lesson = Lesson.objects.get(id=id)
                    if not lesson.is_user_owner(request.user):
                        return Response({'lesson': f"У вас нет права изменять урок с id = {id}"}, status=status.HTTP_400_BAD_REQUEST)
                    lesson.sequence_no = idx+1
                    lesson.save()
                except:
                    return  Response({'lesson': f"Урока с id {id} не существует"}, status=status.HTTP_400_BAD_REQUEST)
        return Response()

    def get_queryset(self):
        queryset = []
        if self.params.get('simulator') and not self.action in SAFE_ACTIONS:
            queryset = Lesson.objects.filter(simulator__id=self.params.get('simulator'))
        else:
            queryset = Lesson.objects.all()
        queryset = queryset.order_by("sequence_no")
        return queryset


class LessonViewSet(ApplicationReadOnlyViewSet):
    pagination_class = None

    def get_serializer_class(self):
        if (self.action == 'list'):
            return LessonSerializer
        return LessonSerializer

    def get_queryset(self):
        if (self.request.simulator):
            queryset = Lesson.objects.filter(simulator=self.request.simulator)
            return queryset.order_by("sequence_no")
        return []

    @action(detail=True, methods=["post"])
    def start(self, request, *args, **kwargs):
        is_started = self.get_object().start(request.user)
        if is_started:
            return Response()
        return Response({"page": "У урока нет начальной страницы"}, status.HTTP_400_BAD_REQUEST)
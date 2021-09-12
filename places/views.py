import logging
from simulators.models import SimulatorUser
from django.shortcuts import render
from rest_framework import permissions
from backend.application_viewset import AdminApplicationViewset, ApplicationReadOnlyViewSet
from .serializers import PlaceSerializer, PlaceUserInfoSerializer
from .models import Place
from pages.models import UserPageProgress
from backend.helpers import SAFE_ACTIONS
from .permissions import PlacePermissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
logger = logging.getLogger("django.server")
# Create your views here.

class AdminPlaceViewSet(AdminApplicationViewset):
    pagination_class = None
    serializer_class = PlaceSerializer
    permission_classes = [PlacePermissions]

    def perform_destroy(self, instance):
        instance.page.delete_place(instance.id)
        instance.delete()

    def get_queryset(self):
        queryset = []
        if self.params.get('page') and not self.action in SAFE_ACTIONS:
            queryset = Place.objects.filter(page__id=self.params.get('lesson'))
        else:
            queryset = Place.objects.all()
        return queryset

# добавить сериалайзер для пользовательского плейса
class PlaceViewSet(ApplicationReadOnlyViewSet):
    pagination_class = None
    serializer_class = PlaceSerializer
    queryset = Place.objects.all()

    @action(detail=True, methods=["post"])
    def complete(self, request, *args, **kwargs):
        place = self.get_object()
        next_place_data = None
        next_page_data = None
        next_lesson_data = None
        page_user = UserPageProgress.objects.get(page=place.page, user=request.user)
        try:
            place_action = getattr(Place, f"{place.type}_action")
        except AttributeError:
            raise NotImplementedError("Class `{}` does not implement `{}`".format(Place.__class__.__name__, place.type))
        if place.type == 'question' or place.type == 'questionuserchoice':
            place_action(place, request.user, page_user, answers=request.data['answers'])
        elif place.type == 'openquestion' or place.type == 'openquestionexpert' or place.type == 'questionanswercheck':
            place_action(place, request.user, page_user, user_answer=request.data['user_answer'])
        else:
            place_action(place, request.user, page_user)

        next_place = place.get_next_place(request.user, page_user)
        if next_place:
            next_place_data = PlaceUserInfoSerializer(next_place).data
            page_user.places.append(next_place_data)
            page_user.save()
        else:
            page_user.completed = True
            if page_user.page.is_onboarding_for:
                sim_user = SimulatorUser.objects.get(simulator=request.simulator, user=request.user)
                sim_user.onboarding_complete = True
                sim_user.save()
            next_page_data = page_user.page.get_next_page(page_user, request.user)
            page_user.save()
            if not next_page_data:
                if page_user.page.lesson:
                    next_lesson_data = page_user.page.lesson.get_next_lesson(request.user)
                    if not next_lesson_data:
                        page_user.page.lesson.simulator.complete(request.user)
                
        return Response({"place": next_place_data, "page": next_page_data, "lesson": next_lesson_data})
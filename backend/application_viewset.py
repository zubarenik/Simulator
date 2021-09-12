from rest_framework.permissions import IsAuthenticated
from rest_framework import mixins, permissions
from rest_framework import viewsets
from django.utils import timezone
from datetime import datetime

from utils.audit.views import LoggingMixin, ModelLoggingMixin


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.is_superuser or request.method in permissions.SAFE_METHODS)


class AuthorizedViewset(LoggingMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @property
    def params(self):
        return self.request.query_params

    def parsed_int(self, str):
        try:
            return int(str)
        except:
            return None

    def parsed_date(self, str):
        try:
            return timezone.make_aware(datetime.strptime(str, '%d.%m.%Y %H:%M:%S'))
        except:
            try:
                return timezone.make_aware(datetime.strptime(str, '%d.%m.%Y %H:%M'))
            except:
                try:
                    return timezone.make_aware(datetime.strptime(str, '%d.%m.%Y'))
                except:
                    return None


class AdminAuthorizedViewset(AuthorizedViewset):
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]


class ReadOnlyViewset(viewsets.ReadOnlyModelViewSet, AuthorizedViewset):
    pass


class ApplicationReadOnlyViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, AuthorizedViewset):
    pass


class ApplicationViewset(ModelLoggingMixin, viewsets.ModelViewSet, AuthorizedViewset):
    pass


class AdminApplicationViewset(ModelLoggingMixin, viewsets.ModelViewSet, AdminAuthorizedViewset):
    pass

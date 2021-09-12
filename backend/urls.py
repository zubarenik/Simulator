"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from theories.views import AdminTheoryChapterViewSet
from characters.views import AdminCharacterViewSet
from django.conf.urls.static import static
from django.conf import settings
from utils.veiws import UploadImage

from places.views import AdminPlaceViewSet, PlaceViewSet
from pages.views import AdminPageViewSet, PageViewSet
from lessons.views import AdminLessonViewSet, LessonViewSet
from django.contrib import admin
from django.urls import path
from django.urls.conf import include
from backend.auth_token import AuthToken
from rest_framework_nested import routers
from simulator_groups.views import AdminSimulatorGroupViewSet
from simulators.views import AdminSimulatorViewSet, SimulatorViewSet
from user_profile.views import AdminsViewSet, UsersViewSet, AuthAttemptViewSet
from payments.views import AdminPromoCodeViewSet, PaymentViewSet
from emails.views import AdminEmailViewSet

router_admin = routers.DefaultRouter()
router_admin.register(r'simulator_groups', AdminSimulatorGroupViewSet, "SimulatorGroup")
router_admin.register(r'simulators', AdminSimulatorViewSet, "Simulator")
router_admin.register(r'lessons', AdminLessonViewSet, "Lessons")
router_admin.register(r'pages', AdminPageViewSet, "Pages")
router_admin.register(r'places', AdminPlaceViewSet, "Places")
router_admin.register(r'admins', AdminsViewSet, "Admins")
router_admin.register(r'characters', AdminCharacterViewSet, "Characters")
router_admin.register(r'theory_chapters', AdminTheoryChapterViewSet, "TheoryChapters")
router_admin.register(r'promo_codes', AdminPromoCodeViewSet, "PromoCodes")
router_admin.register(r'emails', AdminEmailViewSet, "Emails")

router_user = routers.DefaultRouter()
router_user.register(r'users', UsersViewSet, "Users")
router_user.register(r'auth/v2', AuthAttemptViewSet, "Auth")
router_user.register(r'simulators', SimulatorViewSet, "Simulators")
router_user.register(r'lessons', LessonViewSet, "Lessons")
router_user.register(r'pages', PageViewSet, "Pages")
router_user.register(r'places', PlaceViewSet, "Places")
router_user.register(r'payments', PaymentViewSet, "Payments")

urlpatterns = [
    path("api_admin/", include(router_admin.urls)),
    path("api/", include(router_user.urls)),
    path('admin/', admin.site.urls),
    path('api/auth/', AuthToken.as_view()),
    path('api_admin/auth/', AuthToken.as_view()),
    path('api_admin/upload_image/', UploadImage.as_view()),
    path('api/upload_image/', UploadImage.as_view())
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) \
  + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

import json
import requests
import uuid

from knox.models import AuthToken

from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.db.models import Q

from rest_framework import mixins, viewsets, status, serializers
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.renderers import StaticHTMLRenderer

from simulators.models import Simulator, SimulatorUser
from .serializers import AdminUserSerializer, UserCreateSerializer, UserInfoSerializer, AuthAttemptSerializer
from .models import AuthAttempt
from backend.settings import HOST_URL

User = get_user_model()


def auth(content,
         is_login=False,
         check_login=False,
         need_temporary_code=False,
         need_password=False,
         send_password=False,
         backend="standard"):
    # Получение данных
    if 'token' in content:
        simulator = Simulator.objects.get(token=content['token'])
    else:
        simulator = Simulator.objects.get(id=content['simulator'])

    if 'password' in content:
        password = content['password']
    else:
        password = uuid.uuid4().hex[:16]

    email = None
    if 'email' in content:
        email = content['email']

        try:
            serializers.EmailField().run_validators(email)
        except serializers.ValidationError:
            raise ValueError('Почта указана некорректно')

    # Социальный ID
    user_id = None
    if 'user_id' in content:
        user_id = str(content['user_id'])

    postfix = ''
    if simulator.group:
        postfix = '+{}'.format(simulator.group.id)

    # Формирование фильтра и username
    if backend == "standard":
        filter = Q(username=email + postfix)
        username = email + postfix
    elif backend == "facebook":
        filter = Q(facebook_id=user_id + postfix)
        username = "facebook+" + user_id + postfix
    elif backend == "vk":
        filter = Q(vk_id=user_id + postfix)
        username = "vk+" + user_id + postfix

    is_exists = User.objects.filter(filter).exists() or \
            email and SimulatorUser.objects.filter(user__email=email, simulator=simulator).exists()

    # Получение пользователя
    if is_exists:
        if User.objects.filter(filter).exists():
            user = User.objects.get(filter)
        else:
            user = SimulatorUser.objects.get(user__email=email, simulator=simulator).user

    # Авторизация
    if is_login:
        if not is_exists:
            raise ValueError('Такой учетной записи не существует')

        if not user.check_password(password):
            raise ValueError('Неверный пароль')
    # Регистрация
    elif is_exists:
        if not check_login:
            raise ValueError('Этот пользователь уже зарегистрирован')

        # Авторизация (check_login запросил проверку, и она пройдена - пользователь уже зарегистрирован)
        is_login = True
    else:
        user = User(password=password, username=username)
        user.set_password(password)
        user.save()

    # Сохранение данных
    if email:
        user.email = email
    if user_id:
        if backend == "facebook":
            user.facebook_id = user_id + postfix
        elif backend == "vk":
            user.vk_id = user_id + postfix
    if 'first_name' in content:
        user.first_name = content['first_name']
    if 'last_name' in content:
        user.last_name = content['last_name']
    if need_temporary_code:
        user.temporary_code = uuid.uuid4().hex[:8]
    user.is_active = True
    user.save()

    if is_login:
        return user

    # Регистрация во всех симуляторах группы
    if simulator.group:
        simulators = Simulator.objects.filter(group=simulator.group)
        for item in simulators:
            simulator_user = SimulatorUser(user=user, simulator=item)
            simulator_user.current_page = item.onboarding
            simulator_user.save()

    # Отправка письма
    if email:
        # Если need_password = True, то, чисто логически, send_password = True
        if need_password:
            simulator.send_email(3, user, password)
            return user, password

        if send_password:
            simulator.send_email(0, user, password)
        else:
            simulator.send_email(0, user)

    return user


class AdminsViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin):
    serializer_class = AdminUserSerializer
    
    def get_queryset(self):
        return User.objects.filter(id_admin_user=True)


class UsersViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.UpdateModelMixin):
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserInfoSerializer
    
    def get_queryset(self):
        return User.objects.filter(id_admin_user=False)
        
    def get_object(self):
        return self.request.user

    @action(detail=False, methods=['GET'])
    def details(self, request, *args, **kwargs):
        if request.user.is_anonymous:
            return Response({"details": "Учетные данные не предоставлены"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=['PUT', "PATCH"])
    def edit(self, request, *args, **kwargs):
        return super(UsersViewSet, self).update(request, *args, **kwargs)


class AuthAttemptViewSet(viewsets.ModelViewSet):
    queryset = AuthAttempt.objects.all()
    serializer_class = AuthAttemptSerializer

    @action(detail=False, methods=['post'], url_path='get_token')
    def get_token(self, request):
        code = request.data['code']

        user = User.objects.get(temporary_code=code)
        user.temporary_code = None
        user.save()

        attempt_auth = AuthAttempt.objects.get(code=code)
        attempt_auth.code = None
        attempt_auth.save()

        instance, token = AuthToken.objects.create(user=user, expiry=None)
        return Response({
            'token': token,
            'email': user.email,
            'full_name': f"{user.first_name} {user.last_name}",
            'admin': user.is_superuser
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='oauth/init')
    def social_init(self, request):
        provider = request.GET.get('provider')
        simulator = request.simulator
        redirect_uri = HOST_URL + "/api/auth/v2/oauth/login/"

        auth_attempt = AuthAttempt(simulator=simulator)
        auth_attempt.save()

        if provider == "facebook":
            url = ("https://www.facebook.com/v11.0/dialog/oauth?"
                   f"client_id={simulator.group.auth_facebook_key}"
                   f"&redirect_uri={redirect_uri + 'facebook/'}"
                   f"&state={auth_attempt.id}"
                   # "&scope=email"
                   )
        elif provider == "vk":
            url = ("https://oauth.vk.com/authorize?"
                   f"client_id={simulator.group.auth_vk_key}"
                   f"&redirect_uri={redirect_uri + 'vk/'}"
                   f"&state={auth_attempt.id}"
                   f"&scope=email"
                   "&response_type=code")
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'url': url,
            'attemptID': auth_attempt.id
        })

    @action(detail=False, methods=['get'], url_path='oauth/login/facebook', renderer_classes=[StaticHTMLRenderer])
    def social_login_facebook(self, request):
        state = request.GET.get("state")
        auth_attempt = AuthAttempt.objects.get(id=int(state))
        simulator = auth_attempt.simulator

        client_error_url = HOST_URL + "/api/auth/v2/oauth/init/?provider=facebook&simulator={}".format(simulator.id)
        redirect_uri = HOST_URL + "/api/auth/v2/oauth/login/facebook/"

        if "error" in request.GET:
            auth_attempt.status = 2
            auth_attempt.save()
            return Response('<html><body>Отмена авторизации...</body></html>')

        code = request.GET.get("code")

        # Обмен кода на маркер доступа клиента
        url = ("https://graph.facebook.com/v11.0/oauth/access_token?"
               f"client_id={simulator.group.auth_facebook_key}"
               f"&client_secret={simulator.group.auth_facebook_secret}"
               f"&redirect_uri={redirect_uri}"
               f"&code={code}")
        response = requests.get(url)

        if not response.status_code == 200:
            return HttpResponseRedirect(client_error_url)

        input_token = json.loads(response.text)['access_token']

        # Генерирование маркера доступа приложения
        url = ("https://graph.facebook.com/oauth/access_token?"
               f"client_id={simulator.group.auth_facebook_key}"
               f"&client_secret={simulator.group.auth_facebook_secret}"
               "&grant_type=client_credentials")
        response = requests.get(url)

        if not response.status_code == 200:
            auth_attempt.status = 1
            auth_attempt.save()
            return Response('<html><body>Ошибка авторизации!</body></html>')

        access_token = json.loads(response.text)['access_token']

        # Проверка маркера доступа клиента
        url = ("https://graph.facebook.com/debug_token?"
               f"input_token={input_token}"
               f"&access_token={access_token}")
        response = requests.get(url)

        if not response.status_code == 200:
            return HttpResponseRedirect(client_error_url)

        user_id = json.loads(response.text)['data']['user_id']

        # Получение данных клиента
        url = (f"https://graph.facebook.com/{user_id}?"
               f"access_token={input_token}")
        response = requests.get(url)

        if not response.status_code == 200:
            return HttpResponseRedirect(client_error_url)

        content = json.loads(response.text)
        print(content)  # TODO get email
        content['user_id'] = content['id']
        content['simulator'] = simulator.id

        try:
            authorized_user = auth(content=content, check_login=True, backend="facebook", need_temporary_code=True)
        except:
            auth_attempt.status = 1
            auth_attempt.save()
            return Response('<html><body>Ошибка авторизации!</body></html>')

        auth_attempt.status = 3
        auth_attempt.code = authorized_user.temporary_code
        auth_attempt.user = authorized_user
        auth_attempt.save()
        return Response('<html><body>Выполняем авторизацию...</body></html>')

    @action(detail=False, methods=['get'], url_path='oauth/login/vk', renderer_classes=[StaticHTMLRenderer])
    def social_login_vk(self, request):
        state = request.GET.get("state")
        auth_attempt = AuthAttempt.objects.get(id=int(state))
        simulator = auth_attempt.simulator

        client_error_url = HOST_URL + "/api/auth/v2/oauth/init/?provider=vk&simulator={}".format(simulator.id)
        redirect_uri = HOST_URL + "/api/auth/v2/oauth/login/vk/"

        if "error" in request.GET:
            auth_attempt.status = 2
            auth_attempt.save()
            return Response('<html><body>Отмена авторизации...</body></html>')

        code = request.GET.get("code")

        # Обмен кода на токен пользователя
        url = ("https://oauth.vk.com/access_token?"
               f"client_id={simulator.group.auth_vk_key}"
               f"&client_secret={simulator.group.auth_vk_secret}"
               f"&redirect_uri={redirect_uri}"
               f"&code={code}")

        response = requests.get(url)

        if not response.status_code == 200:
            return HttpResponseRedirect(client_error_url)

        content = json.loads(response.text)
        content['simulator'] = simulator.id

        try:
            authorized_user = auth(content=content, check_login=True, backend="vk", need_temporary_code=True)
        except:
            auth_attempt.status = 1
            auth_attempt.save()
            return Response('<html><body>Ошибка авторизации!</body></html>')

        auth_attempt.status = 3
        auth_attempt.code = authorized_user.temporary_code
        auth_attempt.user = authorized_user
        auth_attempt.save()
        return Response('<html><body>Выполняем авторизацию...</body></html>')

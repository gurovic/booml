from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from ..forms.authorization import RegisterForm, LoginForm
from django.http import HttpResponse
from django.middleware.csrf import get_token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('runner:login')
    else:
        form = RegisterForm()
    return render(request, 'runner/authorization/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            return redirect('runner:main_page')
    else:
        form = LoginForm()

    return render(request, 'runner/authorization/login.html', {'form': form})


def home_view(reqeust):
    return HttpResponse(f'Dear, {reqeust.user.username}, the home page is currently under development')


def logout_view(request):
    """Terminate user session and redirect to login page."""
    if request.user.is_authenticated:
        logout(request)
    return redirect('runner:main_page')


def get_user_role(user):
    if user.is_staff:
        return 'teacher'
    return 'student'


@api_view(['POST'])
def backend_register(request):
    form = RegisterForm(request.data)

    if form.is_valid():
        user = form.save()

        refresh = RefreshToken.for_user(user)

        login(request, user)

        return Response({
            'success': True,
            'message': 'Регистрация успешна',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': get_user_role(user),
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

    errors = {}
    for field, error_list in form.errors.items():
        errors[field] = error_list

    return Response({
        'success': False,
        'errors': errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def backend_login(request):
    form = LoginForm(request.data)

    if form.is_valid():
        user = form.cleaned_data['user']

        refresh = RefreshToken.for_user(user)

        login(request, user)

        return Response({
            'success': True,
            'message': 'Вход выполнен успешно',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': get_user_role(user),
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

    errors = {}
    for field, error_list in form.errors.items():
        errors[field] = error_list

    return Response({
        'success': False,
        'errors': errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backend_logout(request):
    logout(request)

    return Response({
        'success': True,
        'message': 'Выход выполнен успешно'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def backend_current_user(request):
    refresh = RefreshToken.for_user(request.user)

    return Response({
        'is_authenticated': True,
        'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'role': get_user_role(request.user),
            },
        'tokens': {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    })


@api_view(['GET'])
def backend_check_auth(request):

    if request.user.is_authenticated:
        refresh = RefreshToken.for_user(request.user)

        return Response({
            'is_authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'role': get_user_role(request.user),
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })
    else:
        return Response({
            'is_authenticated': False,
            'user': None
        })


@api_view(['GET'])
def get_csrf_token(request):
    return Response({'csrfToken': get_token(request)})

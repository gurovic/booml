from ..api.serializers import ProfileSerializer, ProfileDetailSerializer, SubmissionReadSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from ..models import Profile

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    serializer = ProfileDetailSerializer(profile, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_by_id(request, user_id):
    try:
        user = User.objects.get(pk=user_id)
        profile = getattr(user, 'profile', None)

        if not profile:
            return Response(
                {'detail': 'Профиль не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProfileDetailSerializer(profile, context={'request': request})
        return Response(serializer.data)

    except User.DoesNotExist:
        return Response(
            {'detail': 'Пользователь не найден'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_avatar(request):
    profile = getattr(request.user, 'profile', None)

    if not profile:
        return Response(
            {'detail': 'Профиль не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    avatar = request.FILES.get('avatar')
    if not avatar:
        return Response(
            {'detail': 'Файл аватара не предоставлен'},
            status=status.HTTP_400_BAD_REQUEST
        )

    max_size = 5 * 1024 * 1024  # 5MB
    if avatar.size > max_size:
        return Response(
            {'detail': 'Файл слишком большой. Максимальный размер 5MB'},
            status=status.HTTP_400_BAD_REQUEST
        )

    allowed_types = ['image/jpeg', 'image/png', 'image/gif']
    if avatar.content_type not in allowed_types:
        return Response(
            {'detail': 'Допустимы только JPEG, PNG и GIF'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if profile.avatar:
        profile.avatar.delete(save=False)

    profile.avatar = avatar
    profile.save()

    serializer = ProfileSerializer(profile, context={'request': request})
    return Response(serializer.data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_avatar(request):
    profile = getattr(request.user, 'profile', None)

    if not profile:
        return Response(
            {'detail': 'Профиль не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    if profile.avatar:
        profile.avatar.delete(save=False)
        profile.avatar = None
        profile.save()

    serializer = ProfileSerializer(profile, context={'request': request})
    return Response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile_info(request):
    profile = getattr(request.user, 'profile', None)

    if not profile:
        return Response(
            {'detail': 'Профиль не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    user = request.user
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')

    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name

    user.save()

    serializer = ProfileSerializer(profile, context={'request': request})
    return Response(serializer.data)

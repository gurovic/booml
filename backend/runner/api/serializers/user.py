from rest_framework import serializers
from django.contrib.auth import get_user_model

from ...models.profile import Profile
from .submissions import SubmissionReadSerializer


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'full_name', 'role')

    def get_full_name(self, obj):
        return f"{obj.last_name} {obj.first_name}".strip() or obj.username

    def get_role(self, obj):
        if obj.is_staff:
            return 'teacher'
        return 'student'


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('user', 'username', 'email', 'first_name', 'last_name',
                  'full_name', 'role', 'avatar', 'avatar_url')

    def get_full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}".strip() or obj.user.username

    def get_role(self, obj):
        if obj.user.is_staff:
            return 'teacher'
        return 'student'

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class ProfileDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    recent_submissions = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ('user', 'username', 'email', 'first_name', 'last_name',
                  'full_name', 'role', 'avatar', 'avatar_url', 'recent_submissions')

    def get_full_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}".strip() or obj.user.username

    def get_role(self, obj):
        if obj.user.is_staff:
            return 'teacher'
        return 'student'

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    def get_recent_submissions(self, obj):
        submissions = obj.user.submissions.all().order_by('-submitted_at')[:4]
        return SubmissionReadSerializer(submissions, many=True, context=self.context).data
from typing import Iterable

from django.contrib.auth import get_user_model
from rest_framework import serializers

from ...models import Course, CourseParticipant
from ...services import CourseCreateInput, create_course

User = get_user_model()


def _resolve_users(user_ids: Iterable[int], field_name: str) -> list[User]:
    users: list[User] = []
    for user_id in user_ids:
        try:
            users.append(User.objects.get(pk=user_id))
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({field_name: f"User {user_id} not found"}) from exc
    return users


class CourseReadSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(source="parent.id", allow_null=True, read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "is_open",
            "parent_id",
            "owner",
            "owner_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "owner_username", "created_at", "updated_at"]


class CourseCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    is_open = serializers.BooleanField(default=False)
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    teacher_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        default=list,
    )
    student_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        default=list,
    )

    def validate_parent_id(self, value: int | None) -> Course | None:
        if value is None:
            return None
        try:
            return Course.objects.get(pk=value)
        except Course.DoesNotExist as exc:
            raise serializers.ValidationError("Parent course not found") from exc

    def validate(self, data):
        data["parent"] = data.pop("parent_id", None)
        data["teacher_objs"] = _resolve_users(data.get("teacher_ids") or [], "teacher_ids")
        data["student_objs"] = _resolve_users(data.get("student_ids") or [], "student_ids")
        return data

    def create(self, validated_data):
        owner = self.context["request"].user
        payload = CourseCreateInput(
            title=validated_data["title"],
            description=validated_data.get("description", ""),
            is_open=validated_data.get("is_open", False),
            owner=owner,
            parent=validated_data.get("parent"),
            teachers=validated_data.get("teacher_objs"),
            students=validated_data.get("student_objs"),
        )
        return create_course(payload)


class CourseParticipantsUpdateSerializer(serializers.Serializer):
    teacher_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        default=list,
    )
    student_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        default=list,
    )
    allow_role_update = serializers.BooleanField(default=True)

    def validate(self, data):
        data["teacher_objs"] = _resolve_users(data.get("teacher_ids") or [], "teacher_ids")
        data["student_objs"] = _resolve_users(data.get("student_ids") or [], "student_ids")
        return data


class CourseParticipantSummarySerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")

    class Meta:
        model = CourseParticipant
        fields = ["user_id", "username", "role", "is_owner", "added_at"]

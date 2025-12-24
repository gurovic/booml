from typing import Iterable

from django.contrib.auth import get_user_model
from rest_framework import serializers

from ...models import Course, CourseParticipant, Section
from ...services import (
    CourseCreateInput,
    SectionCreateInput,
    create_course,
    create_section,
    is_root_section,
)
from ...services.section_service import ROOT_SECTION_TITLES

User = get_user_model()


def _resolve_users(user_ids: Iterable[int], field_name: str) -> list[User]:
    ids = list(user_ids)
    if not ids:
        return []

    users = list(User.objects.filter(pk__in=ids))
    if len(users) != len(ids):
        found = {user.pk for user in users}
        missing = sorted(set(ids) - found)
        raise serializers.ValidationError(
            {field_name: f"Users not found: {missing}"}
        )

    user_map = {user.pk: user for user in users}
    return [user_map[pk] for pk in ids]


class CourseReadSerializer(serializers.ModelSerializer):
    section_id = serializers.IntegerField(source="section.id", read_only=True)
    section_title = serializers.CharField(source="section.title", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "is_open",
            "section_id",
            "section_title",
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
    section_id = serializers.IntegerField(required=True)
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

    def validate_section_id(self, value: int) -> Section:
        try:
            return Section.objects.get(pk=value)
        except Section.DoesNotExist as exc:
            raise serializers.ValidationError("Section not found") from exc

    def validate(self, data):
        section = data.pop("section_id")
        data["section"] = section
        owner = self.context["request"].user
        if not is_root_section(section) and section.owner_id != owner.id:
            raise serializers.ValidationError(
                {"section_id": "Only section owner can create courses in this section"}
            )
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
            section=validated_data.get("section"),
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


class SectionReadSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(source="parent.id", allow_null=True, read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = Section
        fields = [
            "id",
            "title",
            "description",
            "parent_id",
            "owner",
            "owner_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "owner_username", "created_at", "updated_at"]


class SectionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_parent_id(self, value: int | None) -> Section | None:
        if value is None:
            return None
        try:
            return Section.objects.get(pk=value)
        except Section.DoesNotExist as exc:
            raise serializers.ValidationError("Parent section not found") from exc

    def validate(self, data):
        parent = data.pop("parent_id", None)
        data["parent"] = parent
        owner = self.context["request"].user
        if parent is None and data.get("title") not in ROOT_SECTION_TITLES:
            raise serializers.ValidationError(
                {"title": f"Root section title must be one of {ROOT_SECTION_TITLES}"}
            )
        if parent is None and Section.objects.filter(parent__isnull=True, title=data.get("title")).exists():
            raise serializers.ValidationError(
                {"title": "Root section with this title already exists"}
            )
        if parent is not None and not is_root_section(parent) and parent.owner_id != owner.id:
            raise serializers.ValidationError(
                {"parent_id": "Only section owner can create nested sections"}
            )
        return data

    def create(self, validated_data):
        owner = self.context["request"].user
        payload = SectionCreateInput(
            title=validated_data["title"],
            description=validated_data.get("description", ""),
            owner=owner,
            parent=validated_data.get("parent"),
        )
        return create_section(payload)

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from ...models import Section, Course


class SectionReadSerializer(serializers.ModelSerializer):
    """Serializer for reading section data."""

    class Meta:
        model = Section
        fields = [
            "id",
            "title",
            "description",
            "parent",
            "courses",
            "owner",
            "order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SectionCreateSerializer(serializers.Serializer):
    """Serializer for creating a new section."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    parent_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    course_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text="List of course IDs to add to this section.",
    )
    order = serializers.IntegerField(required=False, default=0)

    def validate_parent_id(self, value):
        if value is not None:
            if not Section.objects.filter(pk=value).exists():
                raise serializers.ValidationError("Parent section does not exist.")
        return value

    def validate_course_ids(self, value):
        if value:
            existing_ids = set(
                Course.objects.filter(pk__in=value).values_list("pk", flat=True)
            )
            missing = set(value) - existing_ids
            if missing:
                raise serializers.ValidationError(
                    f"Courses with IDs {list(missing)} do not exist."
                )
        return value

    def validate(self, attrs):
        parent_id = attrs.get("parent_id")
        course_ids = attrs.get("course_ids", [])

        if parent_id is not None:
            parent = Section.objects.get(pk=parent_id)
            # If parent has courses, we cannot add a child section to it
            if parent.has_courses():
                raise serializers.ValidationError(
                    "Cannot create child section under a section that contains courses."
                )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        parent_id = validated_data.pop("parent_id", None)
        course_ids = validated_data.pop("course_ids", [])

        parent = None
        if parent_id is not None:
            parent = Section.objects.get(pk=parent_id)

        section = Section(
            title=validated_data["title"],
            description=validated_data.get("description", ""),
            parent=parent,
            owner=request.user,
            order=validated_data.get("order", 0),
        )

        try:
            section.full_clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))

        section.save()

        # Add courses if provided (and section has no child sections)
        if course_ids:
            if section.has_child_sections():
                raise serializers.ValidationError(
                    "Cannot add courses to a section that contains child sections."
                )
            courses = Course.objects.filter(pk__in=course_ids)
            section.courses.set(courses)

        return section


class SectionUpdateSerializer(serializers.Serializer):
    """Serializer for updating a section."""

    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    order = serializers.IntegerField(required=False)
    add_course_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text="Course IDs to add to this section.",
    )
    remove_course_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text="Course IDs to remove from this section.",
    )

    def validate(self, attrs):
        add_course_ids = attrs.get("add_course_ids", [])
        section = self.instance

        if add_course_ids and section and section.has_child_sections():
            raise serializers.ValidationError(
                "Cannot add courses to a section that contains child sections."
            )

        return attrs

    def update(self, instance, validated_data):
        if "title" in validated_data:
            instance.title = validated_data["title"]
        if "description" in validated_data:
            instance.description = validated_data["description"]
        if "order" in validated_data:
            instance.order = validated_data["order"]

        instance.save()

        add_course_ids = validated_data.get("add_course_ids", [])
        remove_course_ids = validated_data.get("remove_course_ids", [])

        if add_course_ids:
            courses_to_add = Course.objects.filter(pk__in=add_course_ids)
            instance.courses.add(*courses_to_add)

        if remove_course_ids:
            courses_to_remove = Course.objects.filter(pk__in=remove_course_ids)
            instance.courses.remove(*courses_to_remove)

        return instance

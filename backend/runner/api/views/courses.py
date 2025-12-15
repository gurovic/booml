from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import Course, CourseParticipant, Section
from ...services import add_users_to_course
from ...services.section_service import build_section_tree, ensure_root_sections
from ..serializers import (
    CourseCreateSerializer,
    CourseParticipantSummarySerializer,
    CourseParticipantsUpdateSerializer,
    CourseReadSerializer,
    SectionCreateSerializer,
)


def _assert_section_owner(user, section: Section | None) -> None:
    if section is None:
        raise PermissionDenied("Курс или раздел должны принадлежать разделу.")
    if section.owner_id != getattr(user, "id", None):
        raise PermissionDenied("Только создатель раздела может управлять его содержимым.")


class CourseCreateView(generics.CreateAPIView):
    serializer_class = CourseCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    """
    Create a course with the authenticated user as owner and optional participants.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _assert_section_owner(request.user, serializer.validated_data.get("section"))
        course = serializer.save()
        data = CourseReadSerializer(course, context={"request": request}).data
        return Response(data, status=201)


class CourseParticipantsUpdateView(generics.GenericAPIView):
    serializer_class = CourseParticipantsUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "course_id"

    def post(self, request, *args, **kwargs):
        course = self.get_course()
        _assert_section_owner(request.user, course.section)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = add_users_to_course(
            course=course,
            teachers=serializer.validated_data.get("teacher_objs"),
            students=serializer.validated_data.get("student_objs"),
            allow_role_update=serializer.validated_data.get("allow_role_update", True),
        )

        created = CourseParticipantSummarySerializer(
            result["created"], many=True
        ).data
        updated = CourseParticipantSummarySerializer(
            result["updated"], many=True
        ).data

        return Response(
            {"course_id": course.id, "created": created, "updated": updated},
            status=200,
        )

    def get_course(self) -> Course:
        course_id = self.kwargs.get(self.lookup_url_kwarg)
        return get_object_or_404(Course, pk=course_id)


class SectionCreateView(generics.CreateAPIView):
    serializer_class = SectionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    """
    Создать дочерний раздел внутри уже существующего раздела.
    Корневые разделы создаются автоматически и не создаются через API.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent: Section | None = serializer.validated_data.get("parent")
        ensure_root_sections(request.user)

        if parent is None:
            raise PermissionDenied("Корневые разделы создаются автоматически и неизменяемы.")

        _assert_section_owner(request.user, parent)

        section = serializer.save()
        data = SectionCreateSerializer(section).data
        return Response(data, status=201)

class CourseTreeView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        ensure_root_sections(request.user if request.user.is_authenticated else None)
        tree = build_section_tree()
        return Response(tree)


class CourseSelfEnrollView(generics.GenericAPIView):
    """
    Allow authenticated users to self-enroll in open courses.
    Returns 400 if user already enrolled and 403 if the course is closed.
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "course_id"

    def post(self, request, *args, **kwargs):
        course = self.get_course()
        if not course.is_open:
            raise PermissionDenied("Only open courses allow self-enrollment.")

        if CourseParticipant.objects.filter(course=course, user=request.user).exists():
            return Response({"detail": "User already enrolled."}, status=400)

        result = add_users_to_course(
            course=course,
            students=[request.user],
            allow_role_update=False,
        )

        created = CourseParticipantSummarySerializer(
            result["created"], many=True
        ).data

        return Response(
            {"course_id": course.id, "enrolled": created},
            status=200,
        )

    def get_course(self) -> Course:
        course_id = self.kwargs.get(self.lookup_url_kwarg)
        return get_object_or_404(Course, pk=course_id)

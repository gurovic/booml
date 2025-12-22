from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import Course, CourseParticipant, Section
from ...services import add_users_to_course
from ...services.section_service import ROOT_SECTION_TITLES
from ..serializers import (
    CourseCreateSerializer,
    CourseParticipantSummarySerializer,
    CourseParticipantsUpdateSerializer,
    CourseReadSerializer,
    SectionCreateSerializer,
    SectionReadSerializer,
)


def _build_section_tree(sections, courses):
    sections_by_parent = {}
    for section in sections:
        sections_by_parent.setdefault(section.parent_id, []).append(section)

    courses_by_section = {}
    for course in courses:
        courses_by_section.setdefault(course.section_id, []).append(course)

    def sort_sections(items):
        return sorted(items, key=lambda item: item.title.lower())

    def sort_courses(items):
        return sorted(items, key=lambda item: item.title.lower())

    def build(section):
        child_nodes = []
        for child in sort_sections(sections_by_parent.get(section.id, [])):
            child_nodes.append(build(child))
        for course in sort_courses(courses_by_section.get(section.id, [])):
            child_nodes.append(
                {
                    "id": course.id,
                    "title": course.title,
                    "description": course.description,
                    "children": [],
                    "type": "course",
                }
            )
        return {
            "id": section.id,
            "title": section.title,
            "description": section.description,
            "children": child_nodes,
            "type": "section",
        }

    root_sections = sections_by_parent.get(None, [])
    root_map = {section.title: section for section in root_sections}
    ordered_roots = []
    for title in ROOT_SECTION_TITLES:
        section = root_map.get(title)
        if section:
            ordered_roots.append(section)
    for section in sort_sections([s for s in root_sections if s.title not in ROOT_SECTION_TITLES]):
        ordered_roots.append(section)

    return [build(section) for section in ordered_roots]


class CourseCreateView(generics.CreateAPIView):
    serializer_class = CourseCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    """
    Create a course inside a section with the authenticated user as owner.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        data = CourseReadSerializer(course, context={"request": request}).data
        return Response(data, status=201)


class CourseParticipantsUpdateView(generics.GenericAPIView):
    serializer_class = CourseParticipantsUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "course_id"

    """
    Allow course owner to add or update participants.
    """

    def post(self, request, *args, **kwargs):
        course = self.get_course()
        self._ensure_owner(request.user, course)

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

    def _ensure_owner(self, user, course: Course) -> None:
        if course.section.owner_id != user.id:
            raise PermissionDenied("Only section owner can manage course participants")


class CourseTreeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sections = list(Section.objects.select_related("parent").all())
        courses_qs = Course.objects.select_related("section").all()
        is_admin = request.user.is_staff or request.user.is_superuser
        if not is_admin:
            courses_qs = courses_qs.filter(
                Q(is_open=True)
                | Q(section__owner=request.user)
                | Q(participants__user=request.user)
            ).distinct()
        courses = list(courses_qs)

        if not is_admin:
            section_parent = {section.id: section.parent_id for section in sections}
            allowed_section_ids = {section.id for section in sections if section.parent_id is None}
            for section in sections:
                if section.owner_id != request.user.id:
                    continue
                current_id = section.id
                while current_id:
                    if current_id in allowed_section_ids:
                        break
                    allowed_section_ids.add(current_id)
                    current_id = section_parent.get(current_id)
            for course in courses:
                current_id = course.section_id
                while current_id:
                    if current_id in allowed_section_ids:
                        break
                    allowed_section_ids.add(current_id)
                    current_id = section_parent.get(current_id)
            sections = [section for section in sections if section.id in allowed_section_ids]

        tree = _build_section_tree(sections, courses)
        return Response(tree)


class SectionCreateView(generics.CreateAPIView):
    serializer_class = SectionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = serializer.save()
        data = SectionReadSerializer(section, context={"request": request}).data
        return Response(data, status=201)


class CourseSelfEnrollView(generics.GenericAPIView):
    """
    Allow course owner to ensure they are enrolled.
    Returns 400 if user already enrolled.
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "course_id"

    def post(self, request, *args, **kwargs):
        course = self.get_course()
        if course.section.owner_id != request.user.id:
            raise PermissionDenied("Only section owner can add participants.")

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

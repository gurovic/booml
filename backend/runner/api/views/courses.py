from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from collections import deque
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import Course, CourseParticipant, FavoriteCourse, Section
from ...services import add_users_to_course
from ...services.section_service import ROOT_SECTION_TITLES, is_root_section, root_section_order_key
from ..serializers import (
    CourseCreateSerializer,
    CourseParticipantSummarySerializer,
    CourseParticipantsUpdateSerializer,
    CourseReadSerializer,
    SectionCreateSerializer,
    SectionReadSerializer,
)


def _build_section_tree(sections, courses, favorite_positions=None, *, user=None, section_teacher_ids=None):
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

    section_teacher_ids = section_teacher_ids or set()
    is_admin = bool(user and getattr(user, "is_authenticated", False) and (user.is_staff or user.is_superuser))

    def build(section):
        child_nodes = []
        for child in sort_sections(sections_by_parent.get(section.id, [])):
            child_nodes.append(build(child))
        for course in sort_courses(courses_by_section.get(section.id, [])):
            fav_pos = None
            if favorite_positions is not None:
                fav_pos = favorite_positions.get(course.id)
            child_nodes.append(
                {
                    "id": course.id,
                    "title": course.title,
                    "description": course.description,
                    "is_open": course.is_open,
                    "owner_id": course.owner_id,
                    "owner_username": course.owner.username if course.owner_id else None,
                    "is_favorite": fav_pos is not None,
                    "favorite_position": fav_pos,
                    "children": [],
                    "type": "course",
                }
            )
        is_root = bool(is_root_section(section))
        can_manage = False
        can_manage_teachers = False
        if user and getattr(user, "is_authenticated", False):
            if is_admin:
                can_manage = True
                can_manage_teachers = True
            elif is_root and user.is_staff:
                can_manage = True
            elif section.owner_id == user.id:
                can_manage = True
                can_manage_teachers = True
            elif section.id in section_teacher_ids:
                can_manage = True
        return {
            "id": section.id,
            "title": section.title,
            "description": section.description,
            "parent_id": section.parent_id,
            "owner_id": section.owner_id,
            "owner_username": section.owner.username if section.owner_id else None,
            "is_root": bool(is_root),
            "can_manage": bool(can_manage),
            "can_manage_teachers": bool(can_manage_teachers),
            "children": child_nodes,
            "type": "section",
        }

    root_sections = sections_by_parent.get(None, [])
    ordered_roots = sorted(root_sections, key=root_section_order_key)
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
        if course.owner_id != user.id:
            raise PermissionDenied("Only course owner can manage course participants")


class CourseTreeView(APIView):
    """
    Return a tree representation of sections and their courses.
    Unauthenticated users receive an empty tree.
    Authenticated users see courses they have access to.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Return empty tree for unauthenticated users
        if not request.user.is_authenticated:
            return Response([])

        sections = list(Section.objects.select_related("parent", "owner").all())
        courses_qs = Course.objects.select_related("section", "owner").all()
        is_admin = request.user.is_staff or request.user.is_superuser

        section_teacher_ids = set()
        if request.user.is_authenticated and not is_admin:
            from ...models import SectionTeacher
            section_teacher_ids = set(
                SectionTeacher.objects.filter(user=request.user).values_list("section_id", flat=True)
            )

        if not is_admin:
            courses_qs = courses_qs.filter(
                Q(is_open=True)
                | Q(owner=request.user)
                | Q(section__owner=request.user)
                | Q(section__section_teachers__user=request.user)
                | Q(participants__user=request.user)
            ).distinct()
        courses = list(courses_qs)

        favorite_positions = {}
        if request.user.is_authenticated:
            favorite_positions = dict(
                FavoriteCourse.objects.filter(
                    user=request.user, course_id__in=[course.id for course in courses]
                ).values_list("course_id", "position")
            )

        if not is_admin:
            section_parent = {section.id: section.parent_id for section in sections}
            allowed_section_ids = {section.id for section in sections if section.parent_id is None}
            for section in sections:
                if section.owner_id != request.user.id and section.id not in section_teacher_ids:
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

        tree = _build_section_tree(
            sections,
            courses,
            favorite_positions=favorite_positions,
            user=request.user,
            section_teacher_ids=section_teacher_ids,
        )
        return Response(tree)


class CourseBrowseView(APIView):
    """
    Paginated course lists for the dedicated "Courses" page.

    Tabs:
    - tab=mine: for students/teachers: open courses where the user has at least one submission
      in a contest problem of that course, plus private courses where the user is a participant.
    - tab=admin: for teachers: courses where the user is owner or a teacher participant.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tab = str(request.query_params.get("tab") or "mine").strip().lower()
        q = str(request.query_params.get("q") or "").strip()

        try:
            page = int(request.query_params.get("page") or 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size") or 10)
        except (TypeError, ValueError):
            page_size = 10

        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)

        user = request.user
        is_admin = bool(user.is_staff or user.is_superuser)

        # Favorite flag for star UI.
        fav_exists = Exists(
            FavoriteCourse.objects.filter(user=user, course_id=OuterRef("pk"))
        )

        qs = Course.objects.select_related("section", "owner").annotate(
            is_favorite=fav_exists
        )

        if tab == "admin":
            if is_admin:
                pass
            else:
                qs = qs.filter(
                    Q(owner=user)
                    | Q(
                        participants__user=user,
                        participants__role=CourseParticipant.Role.TEACHER,
                    )
                ).distinct()
        else:
            # mine
            open_participated = Q(
                is_open=True,
                contests__problems__submissions__user=user,
            )
            private_invited = Q(
                is_open=False,
                participants__user=user,
            )
            qs = qs.filter(open_participated | private_invited | Q(owner=user)).distinct()

        if q:
            qs = qs.filter(title__icontains=q)

        qs = qs.order_by("title", "id")

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)

        items = []
        if tab == "admin":
            teacher_ids = set()
            if not is_admin:
                teacher_ids = set(
                    CourseParticipant.objects.filter(
                        user=user, role=CourseParticipant.Role.TEACHER
                    ).values_list("course_id", flat=True)
                )
            for course in page_obj.object_list:
                can_admin = bool(
                    is_admin or course.owner_id == user.id or course.id in teacher_ids
                )
                items.append(self._serialize_course(course, user=user, can_admin=can_admin))
        else:
            for course in page_obj.object_list:
                items.append(self._serialize_course(course, user=user, can_admin=False))

        return Response(
            {
                "items": items,
                "page": page_obj.number,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "total": paginator.count,
            },
            status=200,
        )

    def _serialize_course(self, course: Course, *, user, can_admin: bool) -> dict:
        # Find current user's role if they are a participant (optional, for UI).
        role = None
        if course.owner_id == user.id:
            role = "owner"
        else:
            participant = None
            # Avoid prefetch; list sizes are small (page <= 50).
            try:
                participant = CourseParticipant.objects.filter(
                    course=course, user=user
                ).only("role", "is_owner").first()
            except Exception:
                participant = None
            if participant:
                role = participant.role

        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "is_open": course.is_open,
            "section_id": course.section_id,
            "section_title": course.section.title if course.section_id else None,
            "owner_id": course.owner_id,
            "owner_username": course.owner.username if course.owner_id else None,
            "is_favorite": bool(getattr(course, "is_favorite", False)),
            "role": role,
            "can_admin": bool(can_admin),
        }


class SectionCreateView(generics.CreateAPIView):
    serializer_class = SectionCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = serializer.save()
        data = SectionReadSerializer(section, context={"request": request}).data
        return Response(data, status=201)


class SectionDeleteView(generics.GenericAPIView):
    """
    Delete a section subtree (non-root only). Allowed only for the section owner.

    Deletes:
    - the section
    - all nested child sections
    - all courses inside those sections (and everything cascading from courses: contests, etc.)
    """

    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "section_id"

    def post(self, request, *args, **kwargs):
        section_id = self.kwargs.get(self.lookup_url_kwarg)
        section = get_object_or_404(Section.objects.select_related("parent", "owner"), pk=section_id)

        if is_root_section(section):
            raise PermissionDenied("Root sections cannot be deleted")
        if section.owner_id != request.user.id:
            raise PermissionDenied("Only section owner can delete section")

        from django.db import transaction

        # Collect subtree ids (BFS) without N+1 queries.
        # Fetch once and build parent -> children map in memory.
        parent_rows = list(Section.objects.values_list("id", "parent_id"))
        children_by_parent = {}
        for sid, pid in parent_rows:
            children_by_parent.setdefault(pid, []).append(sid)

        to_delete_ids = []
        queue = deque([section.id])
        seen = set()
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            to_delete_ids.append(current)
            queue.extend(children_by_parent.get(current, []))

        deleted_id = section.id
        with transaction.atomic():
            # Courses depend on Section via PROTECT, delete them first.
            Course.objects.filter(section_id__in=to_delete_ids).delete()
            # Delete sections bottom-up to satisfy on_delete=PROTECT on Section.parent.
            nodes = list(
                Section.objects.filter(id__in=to_delete_ids).values_list("id", "parent_id")
            )
            parent_by_id = {sid: pid for sid, pid in nodes}
            child_count = {sid: 0 for sid, _ in nodes}
            for sid, pid in nodes:
                if pid in child_count:
                    child_count[pid] += 1

            remaining = set(child_count.keys())
            while remaining:
                leaves = [sid for sid in remaining if child_count.get(sid, 0) == 0]
                if not leaves:
                    # Defensive: shouldn't happen unless there is a cycle.
                    raise RuntimeError("Section delete: cannot resolve leaf nodes (cycle?)")
                Section.objects.filter(id__in=leaves).delete()
                for sid in leaves:
                    remaining.remove(sid)
                    pid = parent_by_id.get(sid)
                    if pid in remaining:
                        child_count[pid] -= 1

        return Response(
            {"success": True, "deleted_id": deleted_id, "deleted_section_ids": to_delete_ids},
            status=200,
        )


class CourseSelfEnrollView(generics.GenericAPIView):
    """
    Allow course owner to ensure they are enrolled.
    Returns 400 if user already enrolled.
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "course_id"

    def post(self, request, *args, **kwargs):
        course = self.get_course()
        if course.owner_id != request.user.id:
            raise PermissionDenied("Only course owner can add participants.")

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

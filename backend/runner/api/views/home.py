from django.db import transaction
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import Course, FavoriteCourse, SiteUpdate, Submission


def _course_is_visible_to_user(course: Course, user) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    if course.is_open:
        return True
    if course.owner_id == user.id:
        return True
    if getattr(course, "section_id", None) and getattr(course, "section", None) is not None:
        if course.section.owner_id == user.id:
            return True
    return course.participants.filter(user=user).exists()


def _serialize_favorites(qs):
    return [
        {
            "course_id": fav.course_id,
            "title": fav.course.title if fav.course_id else None,
            "position": fav.position,
        }
        for fav in qs
    ]


class HomeSidebarView(APIView):
    """
    Aggregated data for the HomePage right sidebar:
    - favorite courses (max 5)
    - recent problems (based on recent submissions)
    - site updates ("what's new")

    Unauthenticated users get an empty payload (HomePage shows login prompt).
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"favorites": [], "recent_problems": [], "updates": []}, status=200
            )

        favorites_qs = (
            FavoriteCourse.objects.filter(user=request.user)
            .select_related("course")
            .order_by("position", "id")
        )
        favorites = _serialize_favorites(favorites_qs)

        # Recent problems for the current user, based on recent submissions.
        recent = (
            Submission.objects.filter(user_id=request.user.id, problem__isnull=False)
            .values("problem_id", "problem__title")
            .annotate(last_submitted_at=Max("submitted_at"))
            .order_by("-last_submitted_at")[:5]
        )
        recent_problems = [
            {
                "problem_id": row["problem_id"],
                "title": row["problem__title"],
                "last_submitted_at": row["last_submitted_at"].isoformat()
                if row["last_submitted_at"]
                else None,
            }
            for row in recent
        ]

        updates_qs = (
            SiteUpdate.objects.filter(is_published=True).order_by("-created_at")[:5]
        )
        updates = [
            {
                "id": item.id,
                "title": item.title,
                "body": item.body,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in updates_qs
        ]

        return Response(
            {
                "favorites": favorites,
                "recent_problems": recent_problems,
                "updates": updates,
            },
            status=200,
        )


class FavoriteCoursesListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = (
            FavoriteCourse.objects.filter(user=request.user)
            .select_related("course")
            .order_by("position", "id")
        )
        return Response({"items": _serialize_favorites(qs)}, status=200)


class FavoriteCoursesAddView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        course_id = request.data.get("course_id")
        try:
            course_id = int(course_id)
        except (TypeError, ValueError):
            return Response({"detail": "course_id must be an integer"}, status=400)

        course = get_object_or_404(Course.objects.select_related("section"), pk=course_id)
        if not _course_is_visible_to_user(course, request.user):
            return Response({"detail": "Forbidden"}, status=403)

        qs = FavoriteCourse.objects.select_for_update().filter(user=request.user)
        if qs.count() >= 5 and not qs.filter(course_id=course_id).exists():
            return Response({"detail": "Favorites limit reached (max 5)"}, status=400)

        existing = qs.filter(course_id=course_id).first()
        if existing:
            items = _serialize_favorites(
                FavoriteCourse.objects.filter(user=request.user)
                .select_related("course")
                .order_by("position", "id")
            )
            return Response({"items": items, "added": False}, status=200)

        max_pos = (
            qs.aggregate(Max("position")).get("position__max")
        )
        next_pos = (max_pos + 1) if max_pos is not None else 0
        FavoriteCourse.objects.create(
            user=request.user, course=course, position=next_pos
        )

        items = _serialize_favorites(
            FavoriteCourse.objects.filter(user=request.user)
            .select_related("course")
            .order_by("position", "id")
        )
        return Response({"items": items, "added": True}, status=201)


class FavoriteCoursesRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        course_id = request.data.get("course_id")
        try:
            course_id = int(course_id)
        except (TypeError, ValueError):
            return Response({"detail": "course_id must be an integer"}, status=400)

        qs = FavoriteCourse.objects.select_for_update().filter(user=request.user).order_by(
            "position", "id"
        )
        deleted, _ = qs.filter(course_id=course_id).delete()

        # Re-pack positions after deletion.
        remaining = list(
            FavoriteCourse.objects.select_for_update()
            .filter(user=request.user)
            .select_related("course")
            .order_by("position", "id")
        )
        for idx, fav in enumerate(remaining):
            fav.position = idx
        if remaining:
            FavoriteCourse.objects.bulk_update(remaining, ["position"])

        return Response(
            {"items": _serialize_favorites(remaining), "removed": bool(deleted)},
            status=200,
        )


class FavoriteCoursesReorderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        course_ids = request.data.get("course_ids")
        if not isinstance(course_ids, list) or not course_ids:
            return Response({"detail": "course_ids must be a non-empty list"}, status=400)
        try:
            requested = [int(x) for x in course_ids]
        except (TypeError, ValueError):
            return Response({"detail": "course_ids must contain integers"}, status=400)

        favs = list(
            FavoriteCourse.objects.select_for_update()
            .filter(user=request.user)
            .select_related("course")
            .order_by("position", "id")
        )
        by_id = {f.course_id: f for f in favs}
        existing_order = [f.course_id for f in favs]

        requested = [cid for cid in requested if cid in by_id]
        if not requested:
            return Response({"detail": "No provided course_ids are in favorites"}, status=400)

        remaining = [cid for cid in existing_order if cid not in set(requested)]
        new_order = requested + remaining
        for idx, cid in enumerate(new_order):
            by_id[cid].position = idx
        FavoriteCourse.objects.bulk_update([by_id[cid] for cid in new_order], ["position"])

        updated = list(
            FavoriteCourse.objects.filter(user=request.user)
            .select_related("course")
            .order_by("position", "id")
        )
        return Response({"items": _serialize_favorites(updated)}, status=200)


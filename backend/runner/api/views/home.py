from django.db import transaction
from django.db.models import Exists, Max, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import (
    Contest,
    ContestProblem,
    Course,
    CourseParticipant,
    FavoriteCourse,
    ProblemDescriptor,
    SiteUpdate,
    Submission,
)

from ...views.submissions import _primary_metric  # keep scoring logic consistent across views
from ...services.problem_scoring import (
    default_curve_p,
    extract_raw_metric,
    extract_score_100,
    resolve_score_spec,
    score_from_raw,
)


def _score_from_metrics(metrics, descriptor):
    score_100 = extract_score_100(metrics)
    if score_100 is not None:
        return float(score_100)

    metric_name = "metric"
    if descriptor is not None:
        descriptor_metric = getattr(descriptor, "metric", "")
        descriptor_metric_name = getattr(descriptor, "metric_name", "")
        if isinstance(descriptor_metric, str) and descriptor_metric.strip():
            metric_name = descriptor_metric.strip()
        elif isinstance(descriptor_metric_name, str) and descriptor_metric_name.strip():
            metric_name = descriptor_metric_name.strip()
    if isinstance(metrics, dict):
        raw_metric_name = metrics.get("raw_metric_name")
        if isinstance(raw_metric_name, str) and raw_metric_name.strip():
            metric_name = raw_metric_name.strip()

    raw_metric = extract_raw_metric(metrics, metric_name=metric_name)
    if raw_metric is None:
        return _primary_metric(metrics)

    score_spec = resolve_score_spec(
        metric_name,
        descriptor_direction=getattr(descriptor, "score_direction", "") if descriptor else "",
        descriptor_ideal=getattr(descriptor, "score_ideal_metric", None) if descriptor else None,
    )
    reference_metric = getattr(descriptor, "score_reference_metric", None) if descriptor else None
    curve_p = getattr(descriptor, "score_curve_p", None) if descriptor else None
    nonlinear_reference = (
        float(reference_metric)
        if isinstance(reference_metric, (int, float))
        and abs(float(reference_metric) - float(score_spec.ideal)) > 1e-12
        else None
    )
    nonlinear_curve = (
        float(curve_p)
        if isinstance(curve_p, (int, float))
        else default_curve_p(score_spec.direction)
    )
    score_100, _ = score_from_raw(
        float(raw_metric),
        metric_name=metric_name,
        direction=score_spec.direction,
        ideal=float(score_spec.ideal),
        reference=nonlinear_reference,
        curve_p=nonlinear_curve,
    )
    return float(score_100)


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

        is_admin = request.user.is_staff or request.user.is_superuser

        favorites_qs = (
            FavoriteCourse.objects.filter(user=request.user)
            .select_related("course")
            .order_by("position", "id")
        )
        favorites = _serialize_favorites(favorites_qs)

        # Recent problems for the current user, based on recent submissions.
        latest_sub = (
            Submission.objects.filter(
                user_id=request.user.id,
                problem_id=OuterRef("problem_id"),
            )
            .order_by("-submitted_at", "-id")
        )
        recent = (
            Submission.objects.filter(user_id=request.user.id, problem__isnull=False)
            .values("problem_id", "problem__title")
            .annotate(
                last_submitted_at=Max("submitted_at"),
                last_metrics=Subquery(latest_sub.values("metrics")[:1]),
            )
            .order_by("-last_submitted_at")[:5]
        )

        # Best-effort: infer a contest/course context for each recent problem.
        # Submissions are not linked to contests, so we pick a visible contest that contains the problem.
        problem_ids = [row["problem_id"] for row in recent if row.get("problem_id")]
        context_by_problem_id = {}
        descriptor_by_problem_id = {}
        if problem_ids:
            descriptor_by_problem_id = {
                descriptor.problem_id: descriptor
                for descriptor in ProblemDescriptor.objects.filter(problem_id__in=problem_ids)
            }
            links = list(
                ContestProblem.objects.filter(problem_id__in=problem_ids).values(
                    "problem_id", "contest_id"
                )
            )
            contest_ids = sorted({x["contest_id"] for x in links if x.get("contest_id")})
            if contest_ids:
                teacher_exists = Exists(
                    CourseParticipant.objects.filter(
                        course_id=OuterRef("course_id"),
                        user_id=request.user.id,
                        role=CourseParticipant.Role.TEACHER,
                    )
                )
                member_exists = Exists(
                    CourseParticipant.objects.filter(
                        course_id=OuterRef("course_id"), user_id=request.user.id
                    )
                )
                allowed_exists = Exists(
                    Contest.allowed_participants.through.objects.filter(
                        contest_id=OuterRef("pk"), user_id=request.user.id
                    )
                )

                contests = list(
                    Contest.objects.filter(id__in=contest_ids)
                    .select_related("course", "course__section")
                    .annotate(
                        is_course_teacher=teacher_exists,
                        is_course_member=member_exists,
                        is_allowed=allowed_exists,
                    )
                )
                contest_by_id = {c.id: c for c in contests}

                def is_visible(contest):
                    if is_admin:
                        return True
                    if contest.course and contest.course.owner_id == request.user.id:
                        return True
                    if getattr(contest, "is_course_teacher", False):
                        return True
                    if not contest.is_published:
                        return False
                    if contest.access_type == Contest.AccessType.PRIVATE:
                        return bool(getattr(contest, "is_allowed", False))
                    if contest.access_type == Contest.AccessType.LINK:
                        return bool(getattr(contest, "is_allowed", False))
                    if contest.access_type == Contest.AccessType.PUBLIC and contest.course.is_open:
                        return True
                    return bool(getattr(contest, "is_course_member", False)) or (
                        contest.course and contest.course.owner_id == request.user.id
                    )

                def rank(contest):
                    if is_admin:
                        return 100
                    if contest.course and contest.course.owner_id == request.user.id:
                        return 95
                    if getattr(contest, "is_course_teacher", False):
                        return 90
                    if getattr(contest, "is_course_member", False):
                        return 80
                    if bool(getattr(contest, "is_allowed", False)):
                        return 60
                    if contest.access_type == Contest.AccessType.PUBLIC and contest.course.is_open:
                        return 50
                    return 0

                by_problem = {}
                for row in links:
                    pid = row.get("problem_id")
                    cid = row.get("contest_id")
                    if pid and cid:
                        by_problem.setdefault(pid, []).append(cid)

                for pid, cids in by_problem.items():
                    best = None
                    best_key = None
                    for cid in cids:
                        c = contest_by_id.get(cid)
                        if not c or not c.course:
                            continue
                        if not is_visible(c):
                            continue
                        key = (rank(c), c.created_at.timestamp() if c.created_at else 0, c.id)
                        if best_key is None or key > best_key:
                            best_key = key
                            best = c
                    if best:
                        context_by_problem_id[pid] = {
                            "contest_id": best.id,
                            "contest_title": best.title,
                            "course_id": best.course_id,
                            "course_title": best.course.title if best.course_id else None,
                        }

        recent_problems = []
        for row in recent:
            pid = row["problem_id"]
            ctx = context_by_problem_id.get(pid) or {}
            descriptor = descriptor_by_problem_id.get(pid)
            recent_problems.append(
                {
                    "problem_id": pid,
                    "title": row["problem__title"],
                    "last_submitted_at": row["last_submitted_at"].isoformat()
                    if row["last_submitted_at"]
                    else None,
                    "last_score": _score_from_metrics(row.get("last_metrics"), descriptor),
                    "contest_id": ctx.get("contest_id"),
                    "contest_title": ctx.get("contest_title"),
                    "course_id": ctx.get("course_id"),
                    "course_title": ctx.get("course_title"),
                }
            )

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

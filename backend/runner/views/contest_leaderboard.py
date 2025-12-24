from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import Contest, CourseParticipant, ProblemDescriptor, Submission
from .submissions import _primary_metric


_VALID_STATUSES = {Submission.STATUS_ACCEPTED, Submission.STATUS_VALIDATED}
_LOWER_IS_BETTER_HINTS = (
    "mse",
    "rmse",
    "mae",
    "mape",
    "smape",
    "msle",
    "rmsle",
    "logloss",
    "log_loss",
    "loss",
    "error",
)


def _metric_is_lower_better(metric_name: str | None) -> bool:
    name = (metric_name or "").strip().lower()
    if not name:
        return False
    return any(hint in name for hint in _LOWER_IS_BETTER_HINTS)


def _coerce_metric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_metric_value(metrics: Any, preferred_key: str | None) -> float | None:
    if metrics is None:
        return None
    if isinstance(metrics, dict) and preferred_key:
        value = metrics.get(preferred_key)
        metric = _coerce_metric(value)
        if metric is not None:
            return metric
    return _coerce_metric(_primary_metric(metrics))


def _is_better(
    candidate: float,
    candidate_at: datetime | None,
    current: float,
    current_at: datetime | None,
    lower_is_better: bool,
) -> bool:
    if lower_is_better:
        if candidate < current:
            return True
        if candidate == current and candidate_at and current_at:
            return candidate_at < current_at
        return False
    if candidate > current:
        return True
    if candidate == current and candidate_at and current_at:
        return candidate_at < current_at
    return False


def _collect_contest_participants(contest: Contest) -> List[Dict[str, Any]]:
    if contest.access_type == Contest.AccessType.PRIVATE:
        return [
            {
                "id": user.id,
                "username": user.username,
                "role": None,
                "is_owner": False,
            }
            for user in contest.allowed_participants.all()
        ]

    participants: Dict[int, Dict[str, Any]] = {
        participant.user_id: {
            "id": participant.user_id,
            "username": participant.user.username,
            "role": participant.role,
            "is_owner": participant.is_owner,
        }
        for participant in CourseParticipant.objects.filter(course=contest.course).select_related("user")
    }
    for user in contest.allowed_participants.all():
        if user.id not in participants:
            participants[user.id] = {
                "id": user.id,
                "username": user.username,
                "role": None,
                "is_owner": False,
            }
    return list(participants.values())


def build_contest_problem_leaderboards(contest: Contest) -> List[Dict[str, Any]]:
    problems = list(contest.problems.all())
    if not problems:
        return []

    participants = _collect_contest_participants(contest)
    participant_ids = [participant["id"] for participant in participants]

    problem_ids = [problem.id for problem in problems]
    descriptors = {
        descriptor.problem_id: descriptor
        for descriptor in ProblemDescriptor.objects.filter(problem_id__in=problem_ids)
    }
    problem_settings: Dict[int, Dict[str, Any]] = {}
    for problem in problems:
        descriptor = descriptors.get(problem.id)
        metric_name = ""
        if descriptor is not None:
            metric_name = (descriptor.metric or descriptor.metric_name or "").strip()
        if not metric_name:
            metric_name = "metric"
        problem_settings[problem.id] = {
            "metric": metric_name,
            "lower_is_better": _metric_is_lower_better(metric_name),
        }

    attempts: Dict[Tuple[int, int], int] = defaultdict(int)
    best_results: Dict[Tuple[int, int], Dict[str, Any]] = {}
    if participant_ids:
        submissions = Submission.objects.filter(
            problem_id__in=problem_ids,
            user_id__in=participant_ids,
        ).values(
            "id",
            "problem_id",
            "user_id",
            "metrics",
            "status",
            "submitted_at",
        )
        for row in submissions:
            key = (row["problem_id"], row["user_id"])
            attempts[key] += 1
            if row["status"] not in _VALID_STATUSES:
                continue
            settings = problem_settings.get(row["problem_id"])
            if settings is None:
                continue
            metric = _extract_metric_value(row["metrics"], settings["metric"])
            if metric is None:
                continue
            current = best_results.get(key)
            if current is None or _is_better(
                metric,
                row["submitted_at"],
                current["metric"],
                current["submitted_at"],
                settings["lower_is_better"],
            ):
                best_results[key] = {
                    "metric": metric,
                    "submission_id": row["id"],
                    "submitted_at": row["submitted_at"],
                }

    leaderboards: List[Dict[str, Any]] = []
    for problem in problems:
        settings = problem_settings.get(problem.id, {"metric": "metric", "lower_is_better": False})
        entries: List[Dict[str, Any]] = []
        for participant in participants:
            key = (problem.id, participant["id"])
            best = best_results.get(key)
            entries.append(
                {
                    "user_id": participant["id"],
                    "username": participant["username"],
                    "role": participant.get("role"),
                    "is_owner": participant.get("is_owner", False),
                    "attempts": attempts.get(key, 0),
                    "best_metric": best["metric"] if best else None,
                    "best_submission_id": best["submission_id"] if best else None,
                    "best_submitted_at": best["submitted_at"] if best else None,
                }
            )

        lower_is_better = settings["lower_is_better"]
        fallback_time = timezone.now()

        def _sort_key(entry: Dict[str, Any]) -> Tuple[int, float, datetime, int]:
            metric = entry["best_metric"]
            if metric is None:
                return (1, 0.0, fallback_time, entry["user_id"])
            metric_value = metric if lower_is_better else -metric
            return (
                0,
                metric_value,
                entry["best_submitted_at"] or fallback_time,
                entry["user_id"],
            )

        entries.sort(key=_sort_key)

        rank = 0
        last_metric = None
        for entry in entries:
            metric = entry["best_metric"]
            if metric is None:
                entry["rank"] = None
            else:
                if last_metric is None or metric != last_metric:
                    rank += 1
                    last_metric = metric
                entry["rank"] = rank
            if entry["best_submitted_at"] is not None:
                entry["best_submitted_at"] = entry["best_submitted_at"].isoformat()

        leaderboards.append(
            {
                "problem_id": problem.id,
                "problem_title": problem.title,
                "metric": settings["metric"],
                "lower_is_better": lower_is_better,
                "entries": entries,
            }
        )

    return leaderboards


@login_required
def contest_problem_leaderboard(request, contest_id: int):
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    contest = get_object_or_404(
        Contest.objects.select_related("course__section").prefetch_related(
            "problems",
            "allowed_participants",
        ),
        pk=contest_id,
    )
    if not contest.is_visible_to(request.user):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    leaderboards = build_contest_problem_leaderboards(contest)
    return JsonResponse(
        {
            "contest_id": contest.id,
            "leaderboards": leaderboards,
        },
        status=200,
    )

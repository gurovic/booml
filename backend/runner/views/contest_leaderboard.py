from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import Contest, CourseParticipant, ProblemDescriptor, Submission
from ..services.problem_scoring import (
    default_curve_p,
    extract_raw_metric,
    extract_score_100,
    resolve_score_spec,
    score_from_raw,
)


_VALID_STATUSES = {Submission.STATUS_ACCEPTED, Submission.STATUS_VALIDATED}
def _coerce_metric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_score_value(metrics: Any, settings: Dict[str, Any]) -> float | None:
    stored_score = extract_score_100(metrics)
    if stored_score is not None:
        return stored_score

    metric_name = settings.get("metric") or "metric"
    raw_metric = extract_raw_metric(metrics, metric_name=metric_name)
    if raw_metric is None:
        return None

    score_spec = settings["score_spec"]
    reference_metric = settings.get("reference_metric")
    curve_p = settings.get("curve_p")
    score_100, _ = score_from_raw(
        raw_metric,
        metric_name=metric_name,
        direction=score_spec.direction,
        ideal=score_spec.ideal,
        reference=reference_metric,
        curve_p=curve_p,
    )
    return _coerce_metric(score_100)


def _is_better(
    candidate: float,
    candidate_at: datetime | None,
    current: float,
    current_at: datetime | None,
) -> bool:
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


def _build_contest_leaderboard_data(contest: Contest) -> Dict[str, Any]:
    problems = list(contest.problems.filter(is_published=True))
    participants = _collect_contest_participants(contest) if problems else []
    problem_settings: Dict[int, Dict[str, Any]] = {}

    if problems:
        problem_ids = [problem.id for problem in problems]
        descriptors = {
            descriptor.problem_id: descriptor
            for descriptor in ProblemDescriptor.objects.filter(problem_id__in=problem_ids)
        }
        for problem in problems:
            descriptor = descriptors.get(problem.id)
            metric_name = ""
            if descriptor is not None:
                metric_name = (descriptor.metric or descriptor.metric_name or "").strip()
            if not metric_name:
                metric_name = "metric"
            score_spec = resolve_score_spec(
                metric_name,
                descriptor_direction=getattr(descriptor, "score_direction", "") if descriptor else "",
                descriptor_ideal=getattr(descriptor, "score_ideal_metric", None) if descriptor else None,
            )
            reference_metric = None
            curve_p = None
            if descriptor is not None:
                cached_reference = getattr(descriptor, "score_reference_metric", None)
                if isinstance(cached_reference, (int, float)):
                    reference_metric = float(cached_reference)
                    stored_p = getattr(descriptor, "score_curve_p", None)
                    if isinstance(stored_p, (int, float)):
                        curve_p = float(stored_p)
                    else:
                        curve_p = default_curve_p(score_spec.direction)
            problem_settings[problem.id] = {
                "metric": metric_name,
                "score_spec": score_spec,
                "reference_metric": reference_metric,
                "curve_p": curve_p,
            }

    attempts: Dict[Tuple[int, int], int] = defaultdict(int)
    best_results: Dict[Tuple[int, int], Dict[str, Any]] = {}
    first_valid: Dict[Tuple[int, int], Dict[str, Any]] = {}
    wrong_attempts_before: Dict[Tuple[int, int], int] = defaultdict(int)
    earliest_submission_at = None

    participant_ids = [participant["id"] for participant in participants]
    if problems and participant_ids:
        problem_ids = [problem.id for problem in problems]
        submissions = (
            Submission.objects.filter(
                problem_id__in=problem_ids,
                user_id__in=participant_ids,
            )
            .values(
                "id",
                "problem_id",
                "user_id",
                "metrics",
                "status",
                "submitted_at",
            )
            .order_by("submitted_at", "id")
        )
        for row in submissions.iterator(chunk_size=1000):
            key = (row["problem_id"], row["user_id"])
            attempts[key] += 1
            submitted_at = row["submitted_at"]
            if submitted_at is not None and (
                earliest_submission_at is None or submitted_at < earliest_submission_at
            ):
                earliest_submission_at = submitted_at

            is_valid = row["status"] in _VALID_STATUSES
            if not is_valid:
                if key not in first_valid:
                    wrong_attempts_before[key] += 1
                continue

            if key not in first_valid:
                first_valid[key] = {
                    "submission_id": row["id"],
                    "submitted_at": submitted_at,
                }

            settings = problem_settings.get(row["problem_id"])
            if settings is None:
                continue
            score_100 = _extract_score_value(row["metrics"], settings)
            if score_100 is None:
                continue
            current = best_results.get(key)
            if current is None or _is_better(
                score_100,
                submitted_at,
                current["score_100"],
                current["submitted_at"],
            ):
                best_results[key] = {
                    "score_100": score_100,
                    "submission_id": row["id"],
                    "submitted_at": submitted_at,
                }

    return {
        "problems": problems,
        "participants": participants,
        "problem_settings": problem_settings,
        "attempts": attempts,
        "best_results": best_results,
        "first_valid": first_valid,
        "wrong_attempts_before": wrong_attempts_before,
        "earliest_submission_at": earliest_submission_at,
    }


def build_contest_problem_leaderboards(
    contest: Contest,
    data: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    data = data or _build_contest_leaderboard_data(contest)
    problems = data["problems"]
    if not problems:
        return []

    participants = data["participants"]
    problem_settings = data["problem_settings"]
    attempts = data["attempts"]
    best_results = data["best_results"]

    leaderboards: List[Dict[str, Any]] = []
    for problem in problems:
        settings = problem_settings.get(
            problem.id,
            {
                "metric": "metric",
                "score_spec": resolve_score_spec("metric"),
                "reference_metric": None,
                "curve_p": None,
            },
        )
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
                    "best_score": best["score_100"] if best else None,
                    "best_metric": best["score_100"] if best else None,
                    "best_submission_id": best["submission_id"] if best else None,
                    "best_submitted_at": best["submitted_at"] if best else None,
                }
            )

        now = timezone.now()
        fallback_time = datetime.max.replace(tzinfo=now.tzinfo) if timezone.is_aware(now) else datetime.max

        def _sort_key(entry: Dict[str, Any]) -> Tuple[int, float, datetime, int]:
            best_score = entry["best_score"]
            if best_score is None:
                return (1, 0.0, fallback_time, entry["user_id"])
            return (
                0,
                -best_score,
                entry["best_submitted_at"] or fallback_time,
                entry["user_id"],
            )

        entries.sort(key=_sort_key)

        rank = 0
        last_score = None
        for entry in entries:
            best_score = entry["best_score"]
            if best_score is None:
                entry["rank"] = None
            else:
                if last_score is None or best_score != last_score:
                    rank += 1
                    last_score = best_score
                entry["rank"] = rank
            if entry["best_submitted_at"] is not None:
                entry["best_submitted_at"] = entry["best_submitted_at"].isoformat()

        leaderboards.append(
            {
                "problem_id": problem.id,
                "problem_title": problem.title,
                "metric": "points",
                "lower_is_better": False,
                "entries": entries,
            }
        )

    return leaderboards


def build_contest_overall_leaderboard(
    contest: Contest,
    data: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Build the overall leaderboard for a contest.
    
    Scoring modes:
    - IOI: Sums individual problem scores (0-100 each). With N problems,
           total scores range from 0 to N×100 points.
    - PARTIAL: Averages problem scores to maintain 0-100 scale.
    - ICPC: Counts solved problems with time penalties.
    
    Note: Individual problem scores are always on a 0-100 scale, but IOI
    scoring allows totals to exceed 100 as it sums across all problems.
    """
    data = data or _build_contest_leaderboard_data(contest)
    problems = data["problems"]
    if not problems:
        return {"scoring": contest.scoring, "problems_count": 0, "entries": []}

    participants = data["participants"]
    problem_settings = data["problem_settings"]
    best_results = data["best_results"]
    first_valid = data["first_valid"]
    wrong_attempts_before = data["wrong_attempts_before"]

    start_reference = contest.start_time or data["earliest_submission_at"]
    now = timezone.now()
    fallback_time = datetime.max.replace(tzinfo=now.tzinfo) if timezone.is_aware(now) else datetime.max

    entries: List[Dict[str, Any]] = []
    for participant in participants:
        user_id = participant["id"]
        solved_count = 0
        total_score = 0.0
        penalty_minutes = 0
        last_time = None

        if contest.scoring == Contest.Scoring.ICPC:
            for problem in problems:
                key = (problem.id, user_id)
                solved = first_valid.get(key)
                if solved is None:
                    continue
                solved_count += 1
                if start_reference is not None and solved["submitted_at"] is not None:
                    delta = solved["submitted_at"] - start_reference
                    delta_minutes = max(int(delta.total_seconds() // 60), 0)
                else:
                    delta_minutes = 0
                penalty_minutes += delta_minutes + wrong_attempts_before.get(key, 0) * 20
                if solved["submitted_at"] is not None:
                    last_time = solved["submitted_at"] if last_time is None else max(last_time, solved["submitted_at"])
            total_score_value = float(solved_count) if solved_count else None
            entry = {
                "user_id": user_id,
                "username": participant["username"],
                "role": participant.get("role"),
                "is_owner": participant.get("is_owner", False),
                "solved_count": solved_count,
                "penalty_minutes": penalty_minutes if solved_count else None,
                "total_score": total_score_value,
                "_sort_time": last_time or fallback_time,
            }
        else:
            # IOI or PARTIAL scoring: sum individual problem scores (0-100 each)
            for problem in problems:
                key = (problem.id, user_id)
                best = best_results.get(key)
                if best is None:
                    continue
                solved_count += 1
                total_score += float(best["score_100"])
                if best["submitted_at"] is not None:
                    last_time = best["submitted_at"] if last_time is None else max(last_time, best["submitted_at"])
            if contest.scoring == Contest.Scoring.PARTIAL and problems:
                # PARTIAL mode: average to maintain 0-100 scale
                total_score = total_score / len(problems)
            # IOI mode: sum is kept as-is, allowing totals > 100
            total_score_value = total_score if solved_count else None
            entry = {
                "user_id": user_id,
                "username": participant["username"],
                "role": participant.get("role"),
                "is_owner": participant.get("is_owner", False),
                "solved_count": solved_count,
                "penalty_minutes": None,
                "total_score": total_score_value,
                "_sort_time": last_time or fallback_time,
            }

        entries.append(entry)

    if contest.scoring == Contest.Scoring.ICPC:
        def _sort_key(entry: Dict[str, Any]) -> Tuple[int, int, int, datetime, int]:
            if entry["solved_count"] == 0:
                return (1, 0, 0, fallback_time, entry["user_id"])
            return (
                0,
                -entry["solved_count"],
                entry["penalty_minutes"] or 0,
                entry["_sort_time"],
                entry["user_id"],
            )

        entries.sort(key=_sort_key)
        rank = 0
        last_score = None
        for entry in entries:
            if entry["solved_count"] == 0:
                entry["rank"] = None
                entry.pop("_sort_time", None)
                continue
            score_key = (entry["solved_count"], entry["penalty_minutes"])
            if last_score is None or score_key != last_score:
                rank += 1
                last_score = score_key
            entry["rank"] = rank
            entry.pop("_sort_time", None)
    else:
        def _sort_key(entry: Dict[str, Any]) -> Tuple[int, float, datetime, int]:
            total = entry["total_score"]
            if total is None:
                return (1, 0.0, fallback_time, entry["user_id"])
            return (0, -total, entry["_sort_time"], entry["user_id"])

        entries.sort(key=_sort_key)
        rank = 0
        last_score = None
        for entry in entries:
            total = entry["total_score"]
            if total is None:
                entry["rank"] = None
                entry.pop("_sort_time", None)
                continue
            if last_score is None or total != last_score:
                rank += 1
                last_score = total
            entry["rank"] = rank
            entry.pop("_sort_time", None)

    return {
        "scoring": contest.scoring,
        "problems_count": len(problems),
        "entries": entries,
    }


def build_contest_leaderboards(contest: Contest) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    data = _build_contest_leaderboard_data(contest)
    return (
        build_contest_problem_leaderboards(contest, data=data),
        build_contest_overall_leaderboard(contest, data=data),
    )


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

    leaderboards, overall_leaderboard = build_contest_leaderboards(contest)
    return JsonResponse(
        {
            "contest_id": contest.id,
            "leaderboards": leaderboards,
            "overall_leaderboard": overall_leaderboard,
        },
        status=200,
    )


def build_course_leaderboard(course) -> Dict[str, Any]:
    from ..models import Course

    contests = list(course.contests.filter(is_published=True, approval_status=Contest.ApprovalStatus.APPROVED))

    participants = {
        participant.user_id: {
            "user_id": participant.user_id,
            "username": participant.user.username,
            "role": participant.role,
            "is_owner": participant.is_owner,
        }
        for participant in CourseParticipant.objects.filter(course=course).select_related("user")
    }

    student_ids = [pid for pid, p in participants.items() if p.get("role") == CourseParticipant.Role.STUDENT]
    if not student_ids:
        return {"course_id": course.id, "contests": [], "entries": []}

    problem_descriptors = {}
    contest_problems = {}
    for contest in contests:
        problems = list(contest.problems.all())
        contest_problems[contest.id] = problems
        for problem in problems:
            if problem.id not in problem_descriptors:
                descriptor = ProblemDescriptor.objects.filter(problem=problem).first()
                if descriptor:
                    metric_name = (descriptor.metric or descriptor.metric_name or "").strip()
                else:
                    metric_name = "metric"
                problem_descriptors[problem.id] = {
                    "metric": metric_name or "metric",
                    "lower_is_better": _metric_is_lower_better(metric_name),
                }

    user_results: Dict[int, Dict[str, Any]] = {uid: {
        "user_id": uid,
        "username": participants[uid]["username"],
        "total_score": 0.0,
        "contests_completed": 0,
        "problems_solved": 0,
        "contest_details": [],
    } for uid in student_ids}

    for contest in contests:
        problems = contest_problems.get(contest.id, [])
        if not problems:
            continue

        problem_ids = [p.id for p in problems]
        contest_score_lower_is_better = contest.scoring == Contest.Scoring.ICPC

        for user_id in student_ids:
            user_results[user_id]["contest_details"].append({
                "contest_id": contest.id,
                "contest_title": contest.title,
                "score": None,
                "problems_solved": 0,
                "problems_total": len(problems),
            })

        last_contest_idx = {uid: len(user_results[uid]["contest_details"]) - 1 for uid in student_ids}

        submissions = Submission.objects.filter(
            problem_id__in=problem_ids,
            user_id__in=student_ids,
            status__in=_VALID_STATUSES,
        ).values("id", "problem_id", "user_id", "metrics", "submitted_at")

        contest_best: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for row in submissions.iterator(chunk_size=1000):
            key = (row["problem_id"], row["user_id"])
            descriptor = problem_descriptors.get(row["problem_id"])
            if descriptor is None:
                continue
            metric = _extract_metric_value(row["metrics"], descriptor["metric"])
            if metric is None:
                continue
            current = contest_best.get(key)
            if current is None or _is_better(
                metric, row["submitted_at"],
                current["metric"], current["submitted_at"],
                descriptor["lower_is_better"]
            ):
                contest_best[key] = {
                    "metric": metric,
                    "submitted_at": row["submitted_at"],
                }

        for problem in problems:
            descriptor = problem_descriptors.get(problem.id, {"metric": "metric", "lower_is_better": False})
            lower_is_better = descriptor["lower_is_better"]
            for user_id in student_ids:
                key = (problem.id, user_id)
                best = contest_best.get(key)
                if best:
                    score = best["metric"]
                    if lower_is_better:
                        score = -score
                    contest_entry = user_results[user_id]["contest_details"][last_contest_idx[user_id]]
                    contest_entry["score"] = contest_entry["score"] or 0 + abs(best["metric"])
                    contest_entry["problems_solved"] += 1
                    user_results[user_id]["problems_solved"] += 1

        for user_id in student_ids:
            contest_entry = user_results[user_id]["contest_details"][last_contest_idx[user_id]]
            if contest_entry["problems_solved"] > 0:
                user_results[user_id]["contests_completed"] += 1
                user_results[user_id]["total_score"] += contest_entry["score"] or 0

    entries = list(user_results.values())
    entries.sort(key=lambda x: (-x["total_score"], x.get("problems_solved", 0), x.get("contests_completed", 0)), reverse=True)

    rank = 0
    last_score = None
    for entry in entries:
        if entry["total_score"] != last_score:
            rank += 1
            last_score = entry["total_score"]
        entry["rank"] = rank
        for detail in entry["contest_details"]:
            if detail.get("best_submitted_at") and isinstance(detail["best_submitted_at"], datetime):
                detail["best_submitted_at"] = detail["best_submitted_at"].isoformat()

    return {
        "course_id": course.id,
        "course_title": course.title,
        "contests": [
            {"id": c.id, "title": c.title}
            for c in contests
        ],
        "entries": entries,
    }


@login_required
def course_leaderboard(request, course_id: int):
    from ..models import Course

    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    course = get_object_or_404(
        Course.objects.prefetch_related("contests", "participants"),
        pk=course_id,
    )

    is_teacher = CourseParticipant.objects.filter(
        course=course,
        user=request.user,
        role=CourseParticipant.Role.TEACHER,
    ).exists()

    is_owner = course.owner_id == request.user.id

    if not (is_teacher or is_owner or course.is_open):
        return JsonResponse({"detail": "Forbidden"}, status=403)

    leaderboard = build_course_leaderboard(course)
    return JsonResponse(leaderboard, status=200)

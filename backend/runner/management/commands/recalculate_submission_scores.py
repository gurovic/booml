from __future__ import annotations

from typing import Iterable, Optional

from django.core.management.base import BaseCommand

from runner.models import Problem, Submission
from runner.services.checker import SubmissionChecker
from runner.services.problem_scoring import (
    default_curve_p,
    extract_raw_metric,
    infer_curve_p,
    resolve_score_spec,
    score_from_raw,
)


VALID_STATUSES = (Submission.STATUS_ACCEPTED, Submission.STATUS_VALIDATED)


def _resolve_metric_name(submissions: Iterable[Submission], descriptor) -> str:
    descriptor_metric_name = (getattr(descriptor, "metric_name", "") or "").strip()
    descriptor_legacy_metric = (getattr(descriptor, "metric", "") or "").strip()
    if descriptor_metric_name and descriptor_metric_name != "rmse":
        return descriptor_metric_name
    if descriptor_legacy_metric:
        return descriptor_legacy_metric
    if descriptor_metric_name:
        return descriptor_metric_name

    for submission in submissions:
        metrics = submission.metrics
        if not isinstance(metrics, dict):
            continue
        raw_name = metrics.get("raw_metric_name")
        if isinstance(raw_name, str) and raw_name.strip():
            return raw_name.strip()
        for key in ("accuracy", "f1", "auc", "rmse", "mse", "mae", "r2"):
            if isinstance(metrics.get(key), (int, float)):
                return key
    return "metric"


class Command(BaseCommand):
    help = "Recalculate submission score_100 for accepted/validated submissions and refresh contest tables."

    def add_arguments(self, parser):
        parser.add_argument("--problem-id", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        problem_id: Optional[int] = options.get("problem_id")
        dry_run: bool = bool(options.get("dry_run"))

        checker = SubmissionChecker()
        problems = Problem.objects.filter(submissions__status__in=VALID_STATUSES).distinct().select_related(
            "descriptor",
            "data",
        )
        if problem_id:
            problems = problems.filter(id=problem_id)

        updated_submissions = 0
        updated_problems = 0
        skipped_submissions = 0

        for problem in problems.iterator(chunk_size=100):
            submissions = list(
                Submission.objects.filter(problem=problem, status__in=VALID_STATUSES).order_by("id")
            )
            if not submissions:
                continue

            descriptor = getattr(problem, "descriptor", None)
            problem_data = getattr(problem, "data", None)
            metric_name = _resolve_metric_name(submissions, descriptor)
            metric_code = (getattr(descriptor, "metric_code", "") or "").strip() if descriptor else ""

            score_spec = resolve_score_spec(
                metric_name,
                descriptor_direction=getattr(descriptor, "score_direction", "") if descriptor else "",
                descriptor_ideal=getattr(descriptor, "score_ideal_metric", None) if descriptor else None,
            )

            reference_metric = None
            ground_truth_df = None
            if problem_data is not None:
                ground_truth_file = checker._select_ground_truth_file(problem_data)
                ground_truth_df = checker._load_ground_truth(ground_truth_file)
                if ground_truth_df is not None and descriptor is not None:
                    reference_metric = checker.compute_sample_reference_metric(
                        problem_data=problem_data,
                        descriptor=descriptor,
                        metric_name=metric_name,
                        metric_code=metric_code,
                        ground_truth_df=ground_truth_df,
                    )

            raw_values = []
            for submission in submissions:
                raw_metric = extract_raw_metric(submission.metrics, metric_name=metric_name)
                if raw_metric is not None:
                    raw_values.append(float(raw_metric))

            curve_p = None
            if (
                reference_metric is not None
                and abs(float(reference_metric) - float(score_spec.ideal)) > 1e-12
            ):
                stored_p = getattr(descriptor, "score_curve_p", None) if descriptor else None
                if isinstance(stored_p, (int, float)):
                    curve_p = float(stored_p)
                else:
                    curve_p = infer_curve_p(
                        raw_values,
                        ideal=float(score_spec.ideal),
                        reference=float(reference_metric),
                        direction=score_spec.direction,
                        default_p=default_curve_p(score_spec.direction),
                    )

            descriptor_changed = False
            if descriptor is not None:
                if reference_metric is not None and descriptor.score_reference_metric != reference_metric:
                    descriptor.score_reference_metric = float(reference_metric)
                    descriptor_changed = True
                if curve_p is not None and descriptor.score_curve_p != curve_p:
                    descriptor.score_curve_p = float(curve_p)
                    descriptor_changed = True
                if descriptor_changed and not dry_run:
                    update_fields = []
                    if reference_metric is not None:
                        update_fields.append("score_reference_metric")
                    if curve_p is not None:
                        update_fields.append("score_curve_p")
                    descriptor.save(update_fields=update_fields)

            to_update = []
            for submission in submissions:
                raw_metric = extract_raw_metric(submission.metrics, metric_name=metric_name)
                if raw_metric is None:
                    skipped_submissions += 1
                    continue

                score_100, mode = score_from_raw(
                    float(raw_metric),
                    metric_name=metric_name,
                    direction=score_spec.direction,
                    ideal=float(score_spec.ideal),
                    reference=float(reference_metric) if reference_metric is not None and curve_p is not None else None,
                    curve_p=curve_p,
                )

                metrics_payload = dict(submission.metrics or {}) if isinstance(submission.metrics, dict) else {}
                metrics_payload[metric_name] = float(raw_metric)
                metrics_payload["raw_metric"] = float(raw_metric)
                metrics_payload["raw_metric_name"] = metric_name
                metrics_payload["score_100"] = float(score_100)
                metrics_payload["metric_score"] = float(score_100)
                metrics_payload["score"] = float(score_100)
                metrics_payload["metric"] = float(score_100)
                metrics_payload["score_mode"] = mode
                if curve_p is not None:
                    metrics_payload["curve_p"] = float(curve_p)
                if reference_metric is not None:
                    metrics_payload["reference_metric"] = float(reference_metric)

                submission.metrics = metrics_payload
                to_update.append(submission)

            if to_update and not dry_run:
                Submission.objects.bulk_update(to_update, ["metrics"])

            if to_update:
                updated_submissions += len(to_update)
                updated_problems += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Score recalculation finished. problems={updated_problems}, "
                f"updated_submissions={updated_submissions}, skipped_submissions={skipped_submissions}, "
                f"dry_run={dry_run}"
            )
        )

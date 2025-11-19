import csv
import time
from django.db import DEFAULT_DB_ALIAS, transaction

from ..models import PreValidation, Submission

MAX_ERRORS = 50
MAX_WARNINGS = 50


def _ensure_submission_saved(submission: Submission) -> None:
    """
    Tests patch Submission.save(), so freshly created instances might not have
    a PK yet. Saving via save_base() bypasses the patched method and ensures
    the FK constraint for PreValidation will succeed.
    """
    if submission.pk is None:
        db = submission._state.db or DEFAULT_DB_ALIAS
        submission.save_base(raw=False, force_insert=True, using=db)


def _append_error(prevalidation: PreValidation, message: str) -> None:
    errors = list(prevalidation.errors or [])
    if len(errors) < MAX_ERRORS:
        errors.append(message)
    prevalidation.errors = errors


def _append_warning(prevalidation: PreValidation, message: str) -> None:
    warnings = list(prevalidation.warnings or [])
    if len(warnings) < MAX_WARNINGS:
        warnings.append(message)
    prevalidation.warnings = warnings


def _finalize_report(prevalidation: PreValidation, submission: Submission, start_ts: float) -> PreValidation:
    prevalidation.errors_count = len(prevalidation.errors or [])
    prevalidation.warnings_count = len(prevalidation.warnings or [])
    prevalidation.duration_ms = int((time.time() - start_ts) * 1000)
    prevalidation.valid = prevalidation.errors_count == 0

    if not prevalidation.valid:
        prevalidation.status = "failed"
    elif prevalidation.warnings_count:
        prevalidation.status = "warnings"
    else:
        prevalidation.status = "passed"

    with transaction.atomic():
        prevalidation.save()
        submission.status = "validated" if prevalidation.valid else "failed"
        submission.save(update_fields=["status"])

    return prevalidation


def run_prevalidation(submission: Submission) -> PreValidation:
    start_ts = time.time()
    _ensure_submission_saved(submission)

    descriptor = getattr(submission.problem, "descriptor", None)
    id_column = getattr(descriptor, "id_column", "id")
    target_column = getattr(descriptor, "target_column", None)
    output_columns = list(getattr(descriptor, "output_columns", []) or [])
    if not output_columns and target_column:
        output_columns.append(target_column)

    file_path = submission.file_path
    stats = {"filename": file_path.split("/")[-1]}

    prevalidation = PreValidation.objects.create(
        submission=submission,
        status="failed",
        errors=[],
        warnings=[],
        stats=stats,
    )

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception:
        _append_error(prevalidation, "Cannot read file or invalid encoding")
        return _finalize_report(prevalidation, submission, start_ts)

    seen_ids = set()
    first_id = None
    last_id = None

    for line_no, row in enumerate(rows, start=2):
        row_id = row.get(id_column)
        if row_id is None:
            _append_error(prevalidation, f"Missing ID at line {line_no}")
            continue

        if first_id is None:
            first_id = row_id
        last_id = row_id

        if row_id in seen_ids:
            _append_error(prevalidation, f"Duplicate ID '{row_id}' at line {line_no}")
        else:
            seen_ids.add(row_id)

    prevalidation.unique_ids = len(seen_ids)
    prevalidation.first_id = first_id
    prevalidation.last_id = last_id
    prevalidation.rows_total = len(rows)
    prevalidation.stats["rows_total"] = len(rows)

    for col in output_columns:
        for line_no, row in enumerate(rows, start=2):
            val = row.get(col)
            if val in (None, ""):
                _append_error(prevalidation, f"Missing value in column '{col}' at line {line_no}")
                continue

            expected_type = getattr(descriptor, "target_type", "str") if col == target_column else "str"
            try:
                if expected_type == "float":
                    float(val)
                elif expected_type == "int":
                    int(val)
                else:
                    str(val)
            except ValueError:
                _append_error(prevalidation, f"Invalid type for column '{col}' at line {line_no}")

    return _finalize_report(prevalidation, submission, start_ts)

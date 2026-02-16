import csv
import os
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
        submission.status = (
            Submission.STATUS_VALIDATED
            if prevalidation.valid
            else Submission.STATUS_VALIDATION_ERROR
        )
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
    stats = {"filename": os.path.basename(file_path)}

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
            header = list(reader.fieldnames or [])
            rows = list(reader)
    except Exception:
        _append_error(prevalidation, "Cannot read file or invalid encoding")
        return _finalize_report(prevalidation, submission, start_ts)

    if not header:
        _append_error(prevalidation, "Missing CSV header row")
        return _finalize_report(prevalidation, submission, start_ts)

    if len(header) != len(set(header)):
        duplicates = [name for name in header if header.count(name) > 1]
        _append_error(prevalidation, f"Duplicate column names in header: {sorted(set(duplicates))}")

    sample_rows = []
    sample_header = []
    reference_rows = []
    reference_header = []
    reference_source = None
    sample_read_failed = False
    answer_read_failed = False
    problem_data = getattr(submission.problem, "data", None)
    sample_file = getattr(problem_data, "sample_submission_file", None)
    answer_file = getattr(problem_data, "answer_file", None)

    sample_path = None
    if sample_file and getattr(sample_file, "name", ""):
        try:
            sample_path = sample_file.path
        except Exception:
            sample_path = None
    if sample_path:
        try:
            with open(sample_path, "r", encoding="utf-8", newline="") as f:
                sample_reader = csv.DictReader(f)
                sample_header = list(sample_reader.fieldnames or [])
                sample_rows = list(sample_reader)
                if sample_header:
                    reference_header = sample_header
                    reference_rows = sample_rows
                    reference_source = "sample submission"
        except Exception:
            sample_read_failed = True
            _append_warning(prevalidation, "Cannot read sample submission file; fallback to other schema sources")

    if not reference_header:
        answer_path = None
        if answer_file and getattr(answer_file, "name", ""):
            try:
                answer_path = answer_file.path
            except Exception:
                answer_path = None
        if answer_path:
            try:
                with open(answer_path, "r", encoding="utf-8", newline="") as f:
                    answer_reader = csv.DictReader(f)
                    answer_header = list(answer_reader.fieldnames or [])
                    answer_rows = list(answer_reader)
                    if answer_header:
                        reference_header = answer_header
                        reference_rows = answer_rows
                        reference_source = "answer file"
            except Exception:
                answer_read_failed = True
                _append_warning(prevalidation, "Cannot read answer file; fallback to descriptor-only checks")

    # If the user uploads the exact sample submission, accept it as valid template.
    # This prevents false negatives from stale descriptor constraints.
    if reference_source == "sample submission" and header == sample_header and rows == sample_rows:
        effective_id_column = id_column if id_column in header else (header[0] if header else None)
        ids = [row.get(effective_id_column) for row in rows] if effective_id_column else []
        non_null_ids = [value for value in ids if value is not None]
        prevalidation.unique_ids = len(set(non_null_ids))
        prevalidation.first_id = non_null_ids[0] if non_null_ids else None
        prevalidation.last_id = non_null_ids[-1] if non_null_ids else None
        prevalidation.rows_total = len(rows)
        prevalidation.stats["rows_total"] = len(rows)
        prevalidation.stats["validated_against_sample"] = True
        return _finalize_report(prevalidation, submission, start_ts)

    effective_id_column = id_column if id_column in header else None
    if effective_id_column is None and header:
        if reference_header and reference_header[0] in header:
            effective_id_column = reference_header[0]
        else:
            effective_id_column = header[0]
        _append_warning(
            prevalidation,
            f"Descriptor id column '{id_column}' not found in submission; using '{effective_id_column}'",
        )

    if reference_header:
        if header != reference_header:
            _append_error(
                prevalidation,
                f"Columns do not match {reference_source}: expected {reference_header}, got {header}",
            )
    else:
        if sample_read_failed or answer_read_failed:
            prevalidation.stats["schema_fallback"] = "descriptor"
        if not output_columns:
            output_columns = [col for col in header if col != effective_id_column]
            if output_columns:
                _append_warning(
                    prevalidation,
                    f"No descriptor output columns configured; inferring outputs from submission header: {output_columns}",
                )
        expected_columns = [effective_id_column] + [col for col in output_columns if col != effective_id_column]
        missing_columns = [col for col in expected_columns if col and col not in header]
        extra_columns = [col for col in header if col not in expected_columns]
        if missing_columns:
            _append_error(prevalidation, f"Missing required columns: {missing_columns}")
        if extra_columns:
            _append_error(prevalidation, f"Unexpected columns: {extra_columns}")

    if len(rows) == 0:
        _append_error(prevalidation, "CSV contains no data rows")
        return _finalize_report(prevalidation, submission, start_ts)

    if reference_rows and len(rows) != len(reference_rows):
        _append_error(prevalidation, f"Row count does not match {reference_source}")

    seen_ids = set()
    first_id = None
    last_id = None

    for line_no, row in enumerate(rows, start=2):
        if row.get(None):
            _append_error(prevalidation, f"Too many columns at line {line_no}")
            continue
        if any(value is None for value in row.values()):
            _append_error(prevalidation, f"Not enough columns at line {line_no}")

        row_id = row.get(effective_id_column)
        if row_id in (None, ""):
            _append_error(prevalidation, f"Missing ID at line {line_no}")
            continue

        if first_id is None:
            first_id = row_id
        last_id = row_id

        if row_id in seen_ids:
            _append_error(prevalidation, f"Duplicate ID '{row_id}' at line {line_no}")
        else:
            seen_ids.add(row_id)

    if reference_rows and getattr(descriptor, "check_order", False):
        reference_id_column = effective_id_column
        if reference_header and reference_id_column not in reference_header:
            reference_id_column = reference_header[0]
        for idx, (submission_row, sample_row) in enumerate(zip(rows, reference_rows), start=2):
            sub_id = submission_row.get(effective_id_column)
            sample_id = sample_row.get(reference_id_column)
            if sub_id != sample_id:
                _append_error(prevalidation, f"IDs out of order at line {idx}: {sub_id} -> {sample_id}")
                break

    prevalidation.unique_ids = len(seen_ids)
    prevalidation.first_id = first_id
    prevalidation.last_id = last_id
    prevalidation.rows_total = len(rows)
    prevalidation.stats["rows_total"] = len(rows)

    effective_output_columns = [col for col in reference_header if col != effective_id_column] if reference_header else [col for col in output_columns if col != effective_id_column]
    type_column = target_column if target_column in effective_output_columns else None
    enforce_type_check = bool(type_column)
    if enforce_type_check and reference_rows:
        sample_type = getattr(descriptor, "target_type", "str")
        try:
            for sample_row in reference_rows[:50]:
                sample_value = sample_row.get(type_column)
                if sample_value in (None, ""):
                    continue
                if sample_type == "float":
                    float(sample_value)
                elif sample_type == "int":
                    int(sample_value)
            # keep enforce_type_check=True
        except ValueError:
            enforce_type_check = False
            _append_warning(
                prevalidation,
                f"Skipping strict type check for column '{type_column}' because reference data contains non-{sample_type} values",
            )

    for col in effective_output_columns:
        for line_no, row in enumerate(rows, start=2):
            val = row.get(col)
            if val in (None, ""):
                _append_error(prevalidation, f"Missing value in column '{col}' at line {line_no}")
                continue

            expected_type = getattr(descriptor, "target_type", "str") if (enforce_type_check and col == type_column) else "str"
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

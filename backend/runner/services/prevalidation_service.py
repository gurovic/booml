import csv
import time
from django.db import transaction
from ..models import PreValidation, Submission

MAX_ERRORS = 50
MAX_WARNINGS = 50   

def run_prevalidation(submission: Submission) -> PreValidation:
    start_ts = time.time()
    descriptor = submission.problem.descriptor

    prevalidation = PreValidation(
        submission=submission,
        status="failed",
        errors=[],
        warnings=[],
        stats={}
    )

    file_path = submission.file_path
    prevalidation.stats["filename"] = file_path.split("/")[-1]

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception:
        prevalidation.errors.append("Cannot read file or invalid encoding")
        prevalidation.status = "failed"
        prevalidation.duration_ms = int((time.time() - start_ts) * 1000)
        prevalidation.save()
        submission.status = "failed"
        submission.save(update_fields=["status"])
        return prevalidation

    try:
        with open(submission.problem.data.sample_submission_file, "r", encoding="utf-8", newline="") as f:
            sample_submission_reader = csv.DictReader(f)
            sample_submission_rows = list(sample_submission_reader)
    except Exception:
        prevalidation.errors.append("Cannot read sample submission file")
        sample_submission_rows = []

    if sample_submission_rows and len(rows) != len(sample_submission_rows):
        prevalidation.errors.append("Row count does not match sample submission")

    seen_ids = set()
    first_id = None
    last_id = None
    for i, row in enumerate(rows, start=2):
        row_id = row.get(descriptor.id_column)
        if row_id is None:
            if len(prevalidation.errors) < MAX_ERRORS:
                prevalidation.errors.append(f"Missing ID at line {i}")
            continue
        if first_id is None:
            first_id = row_id
        last_id = row_id
        if row_id in seen_ids:
            if len(prevalidation.errors) < MAX_ERRORS:
                prevalidation.errors.append(f"Duplicate ID '{row_id}' at line {i}")
        else:
            seen_ids.add(row_id)

        if submission.problem.descriptor.check_order:
            for i, row in enumerate(rows):
                submission_id = row[descriptor.id_column]
                sample_id = sample_submission_rows[i][descriptor.id_column]
                if submission_id != sample_id:
                    if len(prevalidation.errors) < MAX_ERRORS:
                        prevalidation.errors.append(f"IDs out of order at line {i}: {submission_id} -> {sample_id}")


    prevalidation.unique_ids = len(seen_ids)
    prevalidation.first_id = first_id
    prevalidation.last_id = last_id

    for col in descriptor.output_columns:
        for i, row in enumerate(rows, start=2):
            val = row.get(col)
            if val is None or val == "":
                if len(prevalidation.errors) < MAX_ERRORS:
                    prevalidation.errors.append(f"Missing value in column '{col}' at line {i}")
            else:
                expected_type = descriptor.target_type if col == descriptor.target_column else "str"
                try:
                    if expected_type == "float":
                        float(val)
                    elif expected_type == "int":
                        int(val)
                    elif expected_type == "str":
                        str(val)
                except ValueError:
                    if len(prevalidation.errors) < MAX_ERRORS:
                        prevalidation.errors.append(f"Invalid type for column '{col}' at line {i}")

    if prevalidation.errors:
        prevalidation.status = "failed"
    elif prevalidation.warnings:
        prevalidation.status = "warnings"
    else:
        prevalidation.status = "passed"

    prevalidation.errors_count = len(prevalidation.errors)
    prevalidation.warnings_count = len(prevalidation.warnings)
    prevalidation.duration_ms = int((time.time() - start_ts) * 1000)

    with transaction.atomic():
        prevalidation.save()
        submission.status = "validated" if prevalidation.status != "failed" else "failed"
        submission.save(update_fields=["status"])

    return prevalidation

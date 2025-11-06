import csv
import time
import logging
from typing import Dict, Any, Optional

from django.db import transaction

from runner.models import Submission, PreValidation

logger = logging.getLogger(__name__)

# How many error / warning messages we will keep in the report JSON fields.
# This prevents creating huge DB blobs for very noisy files.
MAX_COLLECTED_ERRORS = 50
MAX_COLLECTED_WARNINGS = 50

# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------
def run_pre_validation(submission: Submission, descriptor: Optional[Dict[str, Any]] = None, *,
                       id_column: int = 0, check_order: bool = False) -> PreValidation:
    """
    Main entry point for pre-validation.

    Parameters
    ----------
    submission:
        A saved Submission model instance. The model is expected to contain `file_path`.
    descriptor:
        Optional competition descriptor snapshot (e.g. output_schema). Used by schema check.
    id_column:
        Zero-based index of the column that contains the ID (default 0).
    check_order:
        If True, enforce that IDs are in non-decreasing order.

    Returns
    -------
    PreValidation:
        A filled validation report instance (saved to DB inside this function).
    """
    start_ts = time.time()

    # Create a new in-memory validation record. We'll populate fields and save at the end.
    validation = PreValidation(
        submission=submission,
        valid=False,
        status="failed",
        file_info={},
        descriptor=descriptor or {},
        stats={},
        errors=[],
        warnings=[]
    )

    # Basic file metadata to include in the report
    file_path = submission.file_path
    validation.file_info.update({
        "filename": file_path.split("/")[-1],
        "path": file_path,
    })

    try:
        # 1) Schema/header check
        # returns a small stats dict (e.g. headers_ok, expected_headers, found_headers)
        schema_stats = _validate_schema(file_path, descriptor)
        validation.add_stats(schema_stats)

        # 2) ID checks: uniqueness, ordering, counts, duplicates
        id_stats = _validate_ids(file_path, id_column=id_column, check_order=check_order,
                                 validation=validation)

        target_stats = _validate_target_column(file_path, descriptor, validation)
        validation.add_stats(target_stats)
        
        # propagate key numeric/string results to dedicated fields on the model
        validation.rows_total = id_stats.get("rows_total")
        validation.unique_ids = id_stats.get("unique_ids")
        validation.first_id = id_stats.get("first_id")
        validation.last_id = id_stats.get("last_id")
        validation.add_stats(id_stats)

        # Decide final state depending on collected errors/warnings
        # - if there are no errors and no warnings => passed
        # - if there are no errors but there are warnings => warnings
        # - if there are errors => failed
        if not (validation.errors or []):
            if validation.warnings:
                validation.finalize(valid=True, status="warnings", duration_ms=int((time.time() - start_ts) * 1000))
            else:
                validation.finalize(valid=True, status="passed", duration_ms=int((time.time() - start_ts) * 1000))
        else:
            validation.finalize(valid=False, status="failed", duration_ms=int((time.time() - start_ts) * 1000))

    except Exception as exc:
        # Unexpected error — log full traceback and add a short message to the report.
        # We avoid leaking internal stack traces to end users; the report keeps a concise message.
        logger.exception("Unexpected error during pre-validation for submission %s", submission.pk)
        validation.append_error(f"Internal validation error: {str(exc)}", max_errors=MAX_COLLECTED_ERRORS)
        validation.finalize(valid=False, status="failed", duration_ms=int((time.time() - start_ts) * 1000))

    # Save report and update submission status atomically.
    # Doing this in a transaction keeps DB in a consistent state (report + submission.status).
    with transaction.atomic():
        validation.save()
        submission.status = "validated" if validation.valid else "failed"
        submission.save(update_fields=["status"])

    return validation


# ---------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------
def _validate_schema(file_path: str, descriptor: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Basic header / encoding check.

    Behavior:
    - Attempts to open the file as UTF-8 (raises ValueError if not UTF-8).
    - Reads the first row as headers and compares to descriptor['output_schema'] if provided.
    - Returns a small stats dictionary describing header match and found headers.

    Note: This is intentionally simple. If you need robust encoding detection,
    consider using chardet / charset-normalizer, but that will add latency and dependencies.
    """
    stats = {"headers_ok": False, "expected_headers": None, "found_headers": None}
    expected_headers = None
    if descriptor:
        expected_headers = descriptor.get("output_schema")

    try:
        # Enforce UTF-8 as required by your spec
        with open(file_path, "r", encoding="utf-8", newline='') as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                # Empty file or missing header row
                stats.setdefault("errors", []).append("Empty file or missing header")
                return stats

            stats["found_headers"] = headers
            stats["expected_headers"] = expected_headers

            if expected_headers:
                # Exact header equality is enforced here. If you want to allow column order
                # variance, compare as sets or implement a mapping.
                if headers != expected_headers:
                    stats.setdefault("errors", []).append("Headers do not match expected output_schema")
                    stats["headers_ok"] = False
                else:
                    stats["headers_ok"] = True
            else:
                # No schema provided — consider headers acceptable
                stats["headers_ok"] = True
    except UnicodeDecodeError:
        # Signal upstream that encoding is invalid — the caller will record the error.
        raise ValueError("File encoding is not UTF-8")

    return stats


# ---------------------------------------------------------------------
# ID validation (streaming)
# ---------------------------------------------------------------------
def _validate_ids(file_path: str, *, id_column: int = 0, check_order: bool = False,
                  validation: Optional[PreValidation] = None) -> Dict[str, Any]:
    """
    Stream through CSV rows and validate IDs.

    This function:
    - Enforces UTF-8 when opening the file.
    - Skips header row and iterates rows one-by-one (streaming).
    - Tracks seen IDs in a Python set (memory usage grows with unique IDs).
    - Counts duplicates and records the first/last ID seen.
    - Optionally enforces ordering (string comparison by default).

    Returns a dict with keys: rows_total, unique_ids, first_id, last_id, duplicates.

    Important memory note:
    - `seen` is a Python set and must fit in memory. For extremely large submissions
      consider alternative approaches: Bloom filter, Redis temporary set, or external sort.
    """
    seen = set()
    prev_id = None
    total = 0
    duplicates = 0
    first_id = None
    last_id = None

    try:
        # Open the file in strict utf-8 mode; UnicodeDecodeError will be handled below
        with open(file_path, "r", encoding="utf-8", newline='') as f:
            reader = csv.reader(f)
            # Skip header row
            try:
                headers = next(reader)
            except StopIteration:
                # No data rows
                if validation:
                    validation.append_error("CSV contains no data rows", max_errors=MAX_COLLECTED_ERRORS)
                return {"rows_total": 0, "unique_ids": 0, "duplicates": 0}

            # Iterate rows in streaming fashion to avoid loading entire file into memory
            for i, row in enumerate(reader, start=2):
                total += 1

                # Row length guard: if the expected id column doesn't exist on this line
                if id_column >= len(row):
                    if validation:
                        validation.append_error(f"Missing id at line {i}", max_errors=MAX_COLLECTED_ERRORS)
                    # Continue processing other rows to gather fuller statistics
                    continue

                row_id = row[id_column]

                if first_id is None:
                    first_id = row_id

                # Duplicate detection using a set
                if row_id in seen:
                    duplicates += 1
                    if validation:
                        validation.append_error(f"Duplicate id '{row_id}' at line {i}", max_errors=MAX_COLLECTED_ERRORS)
                else:
                    seen.add(row_id)

                # Order check (string comparison). If IDs are numeric, convert to int
                # and handle ValueError where appropriate.
                if check_order and prev_id is not None:
                    # If IDs should be compared numerically, cast here.
                    if row_id < prev_id:
                        if validation:
                            validation.append_error(f"IDs out of order at line {i}: {prev_id} -> {row_id}", max_errors=MAX_COLLECTED_ERRORS)

                prev_id = row_id
                last_id = row_id

                # If we've collected too many errors, stop collecting more errors to avoid huge reports.
                # We still break the loop to avoid excessive processing on a corrupt file.
                if validation and validation.errors_count >= MAX_COLLECTED_ERRORS:
                    validation.append_warning(f"Too many errors, truncating error collection after line {i}", max_warnings=MAX_COLLECTED_WARNINGS)
                    break

    except UnicodeDecodeError:
        # Encoding problem: record the error and return partial stats collected so far.
        if validation:
            validation.append_error("File encoding is not UTF-8", max_errors=MAX_COLLECTED_ERRORS)
        return {"rows_total": total, "unique_ids": len(seen), "duplicates": duplicates}

    return {
        "rows_total": total,
        "unique_ids": len(seen),
        "first_id": first_id,
        "last_id": last_id,
        "duplicates": duplicates,
    }


# ---------------------------------------------------------------------
# Target validation
# ---------------------------------------------------------------------
def _validate_target_column(file_path: str, descriptor: dict, validation: PreValidation) -> dict:
    """
    Checks that target column values match expected type (float, int, str).
    """
    stats = {"target_type_ok": True, "type_errors": 0}

    if not descriptor:
        return stats

    target_col = descriptor.get("target_column")
    target_type = descriptor.get("target_type")

    if not target_col or not target_type:
        return stats  # nothing to check

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if target_col not in reader.fieldnames:
                validation.append_error(f"Missing target column '{target_col}'")
                stats["target_type_ok"] = False
                return stats

            for i, row in enumerate(reader, start=2):
                value = row.get(target_col)
                if value is None or value == "":
                    continue

                try:
                    if target_type == "float":
                        float(value)
                    elif target_type == "int":
                        int(value)
                    elif target_type == "str":
                        str(value)
                    else:
                        validation.append_warning(f"Unknown target type '{target_type}', skipping check.")
                        break
                except ValueError:
                    validation.append_error(f"Invalid value '{value}' in target column at line {i}")
                    stats["type_errors"] += 1

                if stats["type_errors"] >= 50:
                    validation.append_warning("Too many target type errors, stopping check.")
                    break

    except Exception as e:
        validation.append_error(f"Error reading file for target check: {e}")
        stats["target_type_ok"] = False

    return stats


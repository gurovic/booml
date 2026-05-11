from __future__ import annotations

import argparse
import io
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any, Callable

import requests


FINAL_SUBMISSION_STATUSES = {"accepted", "failed", "validation_error"}


@dataclass
class RequestResult:
    name: str
    index: int
    status_code: int | None
    ok: bool
    latency_ms: float
    started_at: float
    error: str = ""
    submission_id: int | None = None
    problem_id: int | None = None
    user_index: int | None = None


@dataclass
class AuthenticatedUser:
    index: int
    username: str
    client: "BoomlClient"
    lock: Lock


class BoomlClient:
    def __init__(self, base_url: str, *, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.csrf_token = ""

    def url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + path

    def refresh_csrf(self) -> str:
        response = self.session.get(self.url("/backend/csrf-token/"), timeout=self.timeout)
        response.raise_for_status()
        try:
            self.csrf_token = response.json().get("csrfToken") or ""
        except ValueError:
            self.csrf_token = ""
        if not self.csrf_token:
            self.csrf_token = self.session.cookies.get("csrftoken", "")
        return self.csrf_token

    def login(self, username: str, password: str) -> None:
        token = self.refresh_csrf()
        headers = {"X-CSRFToken": token} if token else {}
        response = self.session.post(
            self.url("/backend/login/"),
            json={"username": username, "password": password},
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        self.csrf_token = self.session.cookies.get("csrftoken", self.csrf_token)
        self.refresh_csrf()

    def csrf_headers(self) -> dict[str, str]:
        token = self.csrf_token or self.session.cookies.get("csrftoken", "")
        return {"X-CSRFToken": token} if token else {}

    def get_json(self, path: str) -> requests.Response:
        return self.session.get(self.url(path), timeout=self.timeout)

    def post_json(self, path: str, payload: dict[str, Any]) -> requests.Response:
        return self.session.post(
            self.url(path),
            json=payload,
            headers=self.csrf_headers(),
            timeout=self.timeout,
        )

    def put_json(self, path: str, payload: dict[str, Any]) -> requests.Response:
        return self.session.put(
            self.url(path),
            json=payload,
            headers=self.csrf_headers(),
            timeout=self.timeout,
        )

    def post_multipart(
        self,
        path: str,
        *,
        data: dict[str, Any],
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> requests.Response:
        request_files = None
        if files:
            request_files = {
                key: (filename, io.BytesIO(content), content_type)
                for key, (filename, content, content_type) in files.items()
            }
        return self.session.post(
            self.url(path),
            data=data,
            files=request_files,
            headers=self.csrf_headers(),
            timeout=self.timeout,
        )


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return ordered[index]


def summarize_results(results: list[RequestResult], *, started_at: float | None = None) -> dict[str, Any]:
    latencies = [item.latency_ms for item in results if item.latency_ms >= 0]
    status_counts: dict[str, int] = {}
    for item in results:
        key = str(item.status_code) if item.status_code is not None else "exception"
        status_counts[key] = status_counts.get(key, 0) + 1

    wall_start = started_at if started_at is not None else min((r.started_at for r in results), default=time.time())
    wall_end = max((r.started_at + r.latency_ms / 1000.0 for r in results), default=wall_start)
    duration = max(wall_end - wall_start, 0.001)
    errors = [item for item in results if not item.ok]

    return {
        "requests": len(results),
        "successes": len(results) - len(errors),
        "failures": len(errors),
        "status_counts": status_counts,
        "throughput_rps": len(results) / duration,
        "latency_ms": {
            "min": min(latencies) if latencies else None,
            "mean": statistics.fmean(latencies) if latencies else None,
            "p50": percentile(latencies, 50),
            "p95": percentile(latencies, 95),
            "p99": percentile(latencies, 99),
            "max": max(latencies) if latencies else None,
        },
        "errors_sample": [asdict(item) for item in errors[:10]],
    }


def summarize_by_minute(results: list[RequestResult], started_at: float) -> list[dict[str, Any]]:
    buckets: dict[int, list[RequestResult]] = {}
    for item in results:
        bucket = max(0, int((item.started_at - started_at) // 60))
        buckets.setdefault(bucket, []).append(item)
    return [
        {"minute": minute, **summarize_results(items, started_at=started_at + minute * 60)}
        for minute, items in sorted(buckets.items())
    ]


def print_summary(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def make_csv(rows: int, *, column: str = "prediction") -> bytes:
    lines = [f"id,{column}\n"]
    for idx in range(1, rows + 1):
        value = (idx % 1000) / 1000
        lines.append(f"{idx},{value:.6f}\n")
    return "".join(lines).encode("utf-8")


def make_sized_csv(size_mb: float, *, column: str = "prediction") -> bytes:
    target = max(int(size_mb * 1024 * 1024), 32)
    buffer = bytearray(f"id,{column}\n".encode("utf-8"))
    idx = 1
    while len(buffer) < target:
        value = (idx % 1000) / 1000
        buffer.extend(f"{idx},{value:.6f}\n".encode("utf-8"))
        idx += 1
    return bytes(buffer)


def make_sized_csv_with_rows(size_mb: float, rows: int, *, column: str = "prediction") -> bytes:
    target = max(int(size_mb * 1024 * 1024), 32)
    rows = max(int(rows), 1)
    header = f"id,{column}\n"
    base_line_size = len(f"{rows},0.100000\n".encode("utf-8"))
    base_size = len(header.encode("utf-8")) + rows * base_line_size
    extra_per_row = max((target - base_size) // rows, 0)
    remainder = max((target - base_size) - extra_per_row * rows, 0)

    lines = [header]
    for idx in range(1, rows + 1):
        pad = extra_per_row + (remainder if idx == rows else 0)
        if pad > 0:
            value = "0." + ("1" * max(1, pad))
        else:
            value = f"{(idx % 1000) / 1000:.6f}"
        lines.append(f"{idx},{value}\n")
    return "".join(lines).encode("utf-8")


def invalid_csv_cases() -> list[tuple[str, bytes]]:
    return [
        ("duplicate_ids.csv", b"id,prediction\n1,0.1\n1,0.2\n"),
        ("wrong_columns.csv", b"row_id,value\n1,0.1\n2,0.2\n"),
        ("empty_rows.csv", b"id,prediction\n"),
        ("bad_encoding.csv", b"id,prediction\n1,\xff\xfe\xfa\n"),
    ]


def user_name(run_id: str, index: int) -> str:
    return f"loadtest_{run_id}_student_{index}"


def teacher_name(run_id: str) -> str:
    return f"loadtest_{run_id}_teacher"


def login_users(args: argparse.Namespace, count: int, *, teacher: bool = False) -> list[AuthenticatedUser]:
    users = []
    for idx in range(count):
        username = teacher_name(args.run_id) if teacher else user_name(args.run_id, idx)
        client = BoomlClient(args.base_url, timeout=args.request_timeout)
        client.login(username, args.password)
        users.append(AuthenticatedUser(index=idx, username=username, client=client, lock=Lock()))
    return users


def run_parallel(
    total: int,
    concurrency: int,
    worker: Callable[[int], RequestResult],
) -> list[RequestResult]:
    results: list[RequestResult] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = [executor.submit(worker, idx) for idx in range(total)]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: item.index)


def result_from_response(
    *,
    name: str,
    index: int,
    started: float,
    response: requests.Response,
    ok_statuses: set[int],
    user_index: int | None = None,
) -> RequestResult:
    latency_ms = (time.time() - started) * 1000
    error = ""
    submission_id = None
    problem_id = None
    ok = response.status_code in ok_statuses
    try:
        data = response.json()
    except ValueError:
        data = None
    if isinstance(data, dict):
        raw_submission_id = data.get("id") or (data.get("submission") or {}).get("id")
        raw_problem_id = data.get("id") if name.startswith("polygon") else data.get("problem_id")
        if raw_submission_id is not None:
            try:
                submission_id = int(raw_submission_id)
            except (TypeError, ValueError):
                pass
        if raw_problem_id is not None:
            try:
                problem_id = int(raw_problem_id)
            except (TypeError, ValueError):
                pass
    if not ok:
        error = response.text[:500]
    return RequestResult(
        name=name,
        index=index,
        status_code=response.status_code,
        ok=ok,
        latency_ms=latency_ms,
        started_at=started,
        error=error,
        submission_id=submission_id,
        problem_id=problem_id,
        user_index=user_index,
    )


def submit_solution(
    auth_user: AuthenticatedUser,
    *,
    index: int,
    problem_id: int,
    csv_bytes: bytes,
    contest_id: int | None = None,
    expected_statuses: set[int] | None = None,
) -> RequestResult:
    started = time.time()
    data: dict[str, Any] = {"problem_id": str(problem_id)}
    if contest_id:
        data["contest_id"] = str(contest_id)
    try:
        with auth_user.lock:
            response = auth_user.client.post_multipart(
                "/api/submissions/",
                data=data,
                files={
                    "file": (
                        f"submission_{index}.csv",
                        csv_bytes,
                        "text/csv",
                    )
                },
            )
        return result_from_response(
            name="submission",
            index=index,
            started=started,
            response=response,
            ok_statuses=expected_statuses or {201},
            user_index=auth_user.index,
        )
    except Exception as exc:
        return RequestResult(
            name="submission",
            index=index,
            status_code=None,
            ok=False,
            latency_ms=(time.time() - started) * 1000,
            started_at=started,
            error=str(exc),
            user_index=auth_user.index,
        )


def poll_submissions(
    users: list[AuthenticatedUser],
    submissions: list[RequestResult],
    *,
    timeout: float,
    interval: float,
) -> dict[str, Any]:
    pending = {
        item.submission_id: item
        for item in submissions
        if item.submission_id is not None and item.user_index is not None
    }
    final: dict[int, dict[str, Any]] = {}
    deadline = time.time() + timeout

    while pending and time.time() < deadline:
        for submission_id, item in list(pending.items()):
            auth_user = users[item.user_index or 0]
            try:
                with auth_user.lock:
                    response = auth_user.client.get_json(f"/api/submissions/{submission_id}/")
                if response.status_code != 200:
                    continue
                payload = response.json()
                status = payload.get("status")
            except Exception:
                continue
            if status in FINAL_SUBMISSION_STATUSES:
                final[submission_id] = {
                    "status": status,
                    "elapsed_sec": time.time() - item.started_at,
                    "metrics": payload.get("metrics"),
                }
                pending.pop(submission_id, None)
        if pending:
            time.sleep(interval)

    status_counts: dict[str, int] = {}
    for row in final.values():
        status = str(row.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "tracked": len(final) + len(pending),
        "completed": len(final),
        "pending": len(pending),
        "status_counts": status_counts,
        "pending_ids_sample": list(pending.keys())[:50],
        "completion_seconds": {
            "p50": percentile([row["elapsed_sec"] for row in final.values()], 50),
            "p95": percentile([row["elapsed_sec"] for row in final.values()], 95),
            "p99": percentile([row["elapsed_sec"] for row in final.values()], 99),
            "max": max([row["elapsed_sec"] for row in final.values()], default=None),
        },
    }


def scenario_submissions_burst(args: argparse.Namespace) -> int:
    users = login_users(args, args.users)
    csv_payload = (
        make_sized_csv_with_rows(args.csv_size_mb, args.csv_rows)
        if args.csv_size_mb
        else make_csv(args.csv_rows)
    )

    def worker(index: int) -> RequestResult:
        return submit_solution(
            users[index % len(users)],
            index=index,
            problem_id=args.problem_id,
            contest_id=args.contest_id,
            csv_bytes=csv_payload,
        )

    started = time.time()
    results = run_parallel(args.submissions, args.concurrency, worker)
    successful_submissions = [item for item in results if item.ok and item.submission_id is not None]
    poll = poll_submissions(
        users,
        successful_submissions,
        timeout=args.drain_timeout,
        interval=args.poll_interval,
    )
    summary = {
        "scenario": "submissions-burst",
        "http": summarize_results(results, started_at=started),
        "queue_drain": poll,
        "acceptance": {
            "no_5xx": not any((item.status_code or 0) >= 500 for item in results),
            "all_created_completed": poll["pending"] == 0,
            "all_fast_accepted": (
                True
                if args.csv_size_mb
                else poll["status_counts"].get("accepted", 0) == len(successful_submissions)
            ),
        },
    }
    print_summary(summary)
    return 0 if all(summary["acceptance"].values()) else 1


def scenario_submissions_sustained(args: argparse.Namespace) -> int:
    users = login_users(args, args.users)
    csv_payload = make_csv(args.csv_rows)
    interval = 1.0 / max(args.rps, 0.001)
    total = max(1, int(args.duration * args.rps))
    results: list[RequestResult] = []
    started = time.time()

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = []
        for index in range(total):
            target_time = started + index * interval
            sleep_for = target_time - time.time()
            if sleep_for > 0:
                time.sleep(sleep_for)
            futures.append(
                executor.submit(
                    submit_solution,
                    users[index % len(users)],
                    index=index,
                    problem_id=args.problem_id,
                    contest_id=args.contest_id,
                    csv_bytes=csv_payload,
                )
            )
        for future in as_completed(futures):
            results.append(future.result())

    successful_submissions = [item for item in results if item.ok and item.submission_id is not None]
    poll = poll_submissions(
        users,
        successful_submissions,
        timeout=args.drain_timeout,
        interval=args.poll_interval,
    )
    summary = {
        "scenario": "submissions-sustained",
        "http": summarize_results(results, started_at=started),
        "minute_buckets": summarize_by_minute(results, started),
        "queue_drain": poll,
        "acceptance": {
            "no_5xx": not any((item.status_code or 0) >= 500 for item in results),
            "all_created_completed": poll["pending"] == 0,
        },
    }
    print_summary(summary)
    return 0 if all(summary["acceptance"].values()) else 1


def scenario_heavy_csv(args: argparse.Namespace) -> int:
    users = login_users(args, 1)
    user = users[0]
    results: list[RequestResult] = []
    index = 0
    started = time.time()

    for raw_size in args.sizes_mb.split(","):
        size_mb = float(raw_size.strip())
        payload = make_sized_csv_with_rows(size_mb, args.csv_rows)
        results.append(
            submit_solution(
                user,
                index=index,
                problem_id=args.problem_id,
                csv_bytes=payload,
                expected_statuses={201},
            )
        )
        index += 1

    for filename, payload in invalid_csv_cases():
        item = submit_solution(
            user,
            index=index,
            problem_id=args.problem_id,
            csv_bytes=payload,
            expected_statuses={400},
        )
        item.error = item.error or filename
        results.append(item)
        index += 1

    valid_results = [item for item in results if item.status_code == 201 and item.submission_id is not None]
    poll = poll_submissions(users, valid_results, timeout=args.drain_timeout, interval=args.poll_interval)
    summary = {
        "scenario": "heavy-csv-prevalidation",
        "http": summarize_results(results, started_at=started),
        "valid_queue_drain": poll,
        "acceptance": {
            "no_5xx": not any((item.status_code or 0) >= 500 for item in results),
            "invalid_cases_rejected": len([item for item in results if item.status_code == 400]) >= 4,
        },
    }
    print_summary(summary)
    return 0 if all(summary["acceptance"].values()) else 1


def create_polygon_problem(auth_user: AuthenticatedUser, *, index: int, title: str, rating: int) -> RequestResult:
    started = time.time()
    try:
        with auth_user.lock:
            response = auth_user.client.post_json(
                "/backend/polygon/problems/create",
                {"title": title, "rating": rating},
            )
        return result_from_response(
            name="polygon-create",
            index=index,
            started=started,
            response=response,
            ok_statuses={201},
            user_index=auth_user.index,
        )
    except Exception as exc:
        return RequestResult(
            name="polygon-create",
            index=index,
            status_code=None,
            ok=False,
            latency_ms=(time.time() - started) * 1000,
            started_at=started,
            error=str(exc),
            user_index=auth_user.index,
        )


def scenario_polygon_drafts(args: argparse.Namespace) -> int:
    teachers = login_users(args, max(1, min(args.concurrency, args.problems)), teacher=True)

    def worker(index: int) -> RequestResult:
        teacher = teachers[index % len(teachers)]
        return create_polygon_problem(
            teacher,
            index=index,
            title=f"loadtest_{args.run_id}_draft_{index}",
            rating=800 + index % 1000,
        )

    started = time.time()
    results = run_parallel(args.problems, args.concurrency, worker)
    teacher = teachers[0]
    with teacher.lock:
        list_response = teacher.client.get_json(
            f"/backend/polygon/problems?q=loadtest_{args.run_id}_draft&page=1&page_size=100"
        )
    list_ok = list_response.status_code == 200
    summary = {
        "scenario": "polygon-drafts",
        "http": summarize_results(results, started_at=started),
        "verification": {
            "list_status_code": list_response.status_code,
            "list_ok": list_ok,
        },
        "acceptance": {
            "no_5xx": not any((item.status_code or 0) >= 500 for item in results),
            "all_created": all(item.ok for item in results),
            "list_ok": list_ok,
        },
    }
    print_summary(summary)
    return 0 if all(summary["acceptance"].values()) else 1


def update_polygon_problem(
    auth_user: AuthenticatedUser,
    problem_id: int,
    index: int,
    *,
    run_id: str,
) -> RequestResult:
    started = time.time()
    payload = {
        "title": f"loadtest_{run_id}_lifecycle_problem_{index}",
        "rating": 1000,
        "statement": "Load-test polygon lifecycle statement.",
        "descriptor": {
            "id_column": "id",
            "target_column": "prediction",
            "id_type": "int",
            "target_type": "float",
            "check_order": False,
            "metric_name": "csv_match",
            "metric_code": "",
        },
    }
    try:
        with auth_user.lock:
            response = auth_user.client.put_json(f"/backend/polygon/problems/{problem_id}/update", payload)
        return result_from_response(
            name="polygon-update",
            index=index,
            started=started,
            response=response,
            ok_statuses={200},
            user_index=auth_user.index,
        )
    except Exception as exc:
        return RequestResult("polygon-update", index, None, False, (time.time() - started) * 1000, started, str(exc))


def upload_polygon_files(
    auth_user: AuthenticatedUser,
    problem_id: int,
    index: int,
    *,
    file_bytes: bytes,
    fields: list[str],
) -> RequestResult:
    started = time.time()
    files = {
        field: (f"{field}_{index}.csv", file_bytes, "text/csv")
        for field in fields
    }
    try:
        with auth_user.lock:
            response = auth_user.client.post_multipart(
                f"/backend/polygon/problems/{problem_id}/upload",
                data={},
                files=files,
            )
        return result_from_response(
            name="polygon-upload",
            index=index,
            started=started,
            response=response,
            ok_statuses={200},
            user_index=auth_user.index,
        )
    except Exception as exc:
        return RequestResult("polygon-upload", index, None, False, (time.time() - started) * 1000, started, str(exc))


def publish_polygon_problem(auth_user: AuthenticatedUser, problem_id: int, index: int) -> RequestResult:
    started = time.time()
    try:
        with auth_user.lock:
            response = auth_user.client.post_json(f"/backend/polygon/problems/{problem_id}/publish", {})
        return result_from_response(
            name="polygon-publish",
            index=index,
            started=started,
            response=response,
            ok_statuses={200},
            user_index=auth_user.index,
        )
    except Exception as exc:
        return RequestResult("polygon-publish", index, None, False, (time.time() - started) * 1000, started, str(exc))


def scenario_polygon_lifecycle(args: argparse.Namespace) -> int:
    teachers = login_users(args, max(1, min(args.concurrency, args.problems)), teacher=True)
    file_payload = make_csv(args.csv_rows)
    all_results: list[RequestResult] = []

    def worker(index: int) -> list[RequestResult]:
        teacher = teachers[index % len(teachers)]
        title = f"loadtest_{args.run_id}_lifecycle_{index}"
        create_result = create_polygon_problem(teacher, index=index, title=title, rating=1000)
        results = [create_result]
        if not create_result.ok or create_result.problem_id is None:
            return results
        problem_id = create_result.problem_id
        results.append(update_polygon_problem(teacher, problem_id, index, run_id=args.run_id))
        results.append(
            upload_polygon_files(
                teacher,
                problem_id,
                index,
                file_bytes=file_payload,
                fields=["train_file", "test_file", "sample_submission_file", "answer_file"],
            )
        )
        results.append(publish_polygon_problem(teacher, problem_id, index))
        return results

    started = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = [executor.submit(worker, idx) for idx in range(args.problems)]
        for future in as_completed(futures):
            all_results.extend(future.result())

    summary = {
        "scenario": "polygon-lifecycle",
        "http": summarize_results(all_results, started_at=started),
        "acceptance": {
            "no_5xx": not any((item.status_code or 0) >= 500 for item in all_results),
            "all_steps_ok": all(item.ok for item in all_results),
        },
    }
    print_summary(summary)
    return 0 if all(summary["acceptance"].values()) else 1


def scenario_polygon_large_uploads(args: argparse.Namespace) -> int:
    teachers = login_users(args, max(1, min(args.upload_concurrency, args.problems)), teacher=True)
    fields = [field.strip() for field in args.fields.split(",") if field.strip()]
    file_payload = make_sized_csv(args.polygon_file_size_mb)
    all_results: list[RequestResult] = []

    def worker(index: int) -> list[RequestResult]:
        teacher = teachers[index % len(teachers)]
        title = f"loadtest_{args.run_id}_large_upload_{index}"
        create_result = create_polygon_problem(teacher, index=index, title=title, rating=1000)
        results = [create_result]
        if not create_result.ok or create_result.problem_id is None:
            return results
        problem_id = create_result.problem_id
        results.append(update_polygon_problem(teacher, problem_id, index, run_id=args.run_id))
        results.append(
            upload_polygon_files(
                teacher,
                problem_id,
                index,
                file_bytes=file_payload,
                fields=fields,
            )
        )
        if "answer_file" in fields:
            results.append(publish_polygon_problem(teacher, problem_id, index))
        with teacher.lock:
            detail_started = time.time()
            try:
                detail_response = teacher.client.get_json(f"/backend/polygon/problems/{problem_id}")
                results.append(
                    result_from_response(
                        name="polygon-detail",
                        index=index,
                        started=detail_started,
                        response=detail_response,
                        ok_statuses={200},
                        user_index=teacher.index,
                    )
                )
            except Exception as exc:
                results.append(
                    RequestResult(
                        "polygon-detail",
                        index,
                        None,
                        False,
                        (time.time() - detail_started) * 1000,
                        detail_started,
                        str(exc),
                    )
                )
        return results

    started = time.time()
    with ThreadPoolExecutor(max_workers=max(1, args.upload_concurrency)) as executor:
        futures = [executor.submit(worker, idx) for idx in range(args.problems)]
        for future in as_completed(futures):
            all_results.extend(future.result())

    summary = {
        "scenario": "polygon-large-uploads",
        "fields": fields,
        "file_size_mb": args.polygon_file_size_mb,
        "http": summarize_results(all_results, started_at=started),
        "acceptance": {
            "no_5xx": not any((item.status_code or 0) >= 500 for item in all_results),
            "all_steps_ok": all(item.ok for item in all_results),
        },
    }
    print_summary(summary)
    return 0 if all(summary["acceptance"].values()) else 1


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=os.getenv("BOOML_BASE_URL", "http://localhost:8100"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--password", default=os.getenv("BOOML_LOAD_PASSWORD", "LoadTestPass123!"))
    parser.add_argument("--request-timeout", type=float, default=120.0)


def add_submission_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--problem-id", type=int, required=True)
    parser.add_argument("--contest-id", type=int, default=None)
    parser.add_argument("--users", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--csv-rows", type=int, default=1000)
    parser.add_argument("--drain-timeout", type=float, default=300.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone BOOML load-test runner.")
    subparsers = parser.add_subparsers(dest="scenario", required=True)

    burst = subparsers.add_parser("submissions-burst")
    add_common_args(burst)
    add_submission_args(burst)
    burst.add_argument("--submissions", type=int, default=100)
    burst.add_argument("--csv-size-mb", type=float, default=0.0)
    burst.set_defaults(func=scenario_submissions_burst)

    sustained = subparsers.add_parser("submissions-sustained")
    add_common_args(sustained)
    add_submission_args(sustained)
    sustained.add_argument("--duration", type=float, default=600.0)
    sustained.add_argument("--rps", type=float, default=1.0)
    sustained.set_defaults(func=scenario_submissions_sustained)

    heavy = subparsers.add_parser("heavy-csv")
    add_common_args(heavy)
    add_submission_args(heavy)
    heavy.add_argument("--sizes-mb", default="1,10,50")
    heavy.set_defaults(func=scenario_heavy_csv)

    drafts = subparsers.add_parser("polygon-drafts")
    add_common_args(drafts)
    drafts.add_argument("--problems", type=int, default=100)
    drafts.add_argument("--concurrency", type=int, default=10)
    drafts.set_defaults(func=scenario_polygon_drafts)

    lifecycle = subparsers.add_parser("polygon-lifecycle")
    add_common_args(lifecycle)
    lifecycle.add_argument("--problems", type=int, default=10)
    lifecycle.add_argument("--concurrency", type=int, default=5)
    lifecycle.add_argument("--csv-rows", type=int, default=1000)
    lifecycle.set_defaults(func=scenario_polygon_lifecycle)

    uploads = subparsers.add_parser("polygon-large-uploads")
    add_common_args(uploads)
    uploads.add_argument("--problems", type=int, default=1)
    uploads.add_argument("--upload-concurrency", type=int, default=1)
    uploads.add_argument("--polygon-file-size-mb", type=float, default=50.0)
    uploads.add_argument(
        "--fields",
        default="train_file,test_file,sample_submission_file,answer_file",
        help="Comma-separated upload fields.",
    )
    uploads.set_defaults(func=scenario_polygon_large_uploads)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

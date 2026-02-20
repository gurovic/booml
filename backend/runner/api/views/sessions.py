from __future__ import annotations

import base64
import csv
import io
import logging
import math
import shutil
from pathlib import Path
from typing import Any, Optional

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models.notebook import Notebook
from ...models.problem import Problem
from ...models.problem_data import ProblemData
from ...services.runtime import (
    RuntimeSession,
    SessionNotFoundError,
    create_session,
    get_session,
    reset_session,
    stop_session,
)
from ...services.streaming_runs import cancel_streaming_runs
from ..serializers import (
    NotebookCreateSerializer,
    NotebookSessionCreateSerializer,
    SessionResetSerializer,
    SessionFilesQuerySerializer,
    SessionFileDownloadSerializer,
    SessionFileUploadSerializer,
    SessionFilePreviewSerializer,
    SessionFileChartSerializer,
)

NOTEBOOK_SESSION_PREFIX = "notebook:"
DEFAULT_PREVIEW_ROWS = 50
DEFAULT_PREVIEW_COLS = 50
MAX_PREVIEW_ROWS = 500
MAX_PREVIEW_COLS = 200
MAX_PREVIEW_CELL_CHARS = 2000
SUPPORTED_PREVIEW_EXTENSIONS = {".csv", ".parquet", ".parq"}
DEFAULT_CHART_ROWS = 5000
MAX_CHART_ROWS = 50000
DEFAULT_CHART_POINTS = 1000
MAX_CHART_POINTS = 5000
DEFAULT_CHART_BINS = 20
DEFAULT_BAR_TOP_N = 30
MAX_BAR_TOP_N = 200


def build_notebook_session_id(notebook_id: int) -> str:
    return f"{NOTEBOOK_SESSION_PREFIX}{notebook_id}"


def extract_notebook_id(session_id: str) -> Optional[int]:
    if session_id.startswith(NOTEBOOK_SESSION_PREFIX):
        suffix = session_id[len(NOTEBOOK_SESSION_PREFIX):]
        if suffix.isdigit():
            return int(suffix)
    return None


def ensure_notebook_access(user, notebook: Notebook) -> None:
    if user is None or not getattr(user, "is_authenticated", False):
        return
    owner_id = notebook.owner_id
    if owner_id not in (None, user.id) and not user.is_staff:
        raise PermissionDenied("Недостаточно прав для работы с этим блокнотом")


def copy_problem_files_to_session(problem: Problem, session: RuntimeSession) -> None:
    """
    Copy problem data files (train, test, sample_submission) to the notebook session workdir.
    """
    try:
        problem_data = ProblemData.objects.filter(problem=problem).first()
        if not problem_data:
            return
        workdir = session.workdir
        workdir.mkdir(parents=True, exist_ok=True)

        files_to_copy = [
            (problem_data.train_file, "train.csv"),
            (problem_data.test_file, "test.csv"),
            (problem_data.sample_submission_file, "sample_submission.csv"),
        ]
        for file_field, target_name in files_to_copy:
            if file_field and file_field.name:
                try:
                    source_path = Path(file_field.path)
                    if source_path.exists():
                        target_path = workdir / target_name
                        shutil.copy2(source_path, target_path)
                except Exception as exc:
                    logger = logging.getLogger(__name__)
                    logger.warning("Failed to copy %s: %s", target_name, exc)
    except Exception as exc:
        logger = logging.getLogger(__name__)
        logger.warning("Failed to copy problem files: %s", exc)


class CreateNotebookView(APIView):
    """
    POST /api/notebooks/ - Create a notebook for the authenticated user.

    If ``problem_id`` is provided in the request body, a notebook linked to that
    problem is created. If a notebook for the given ``problem_id`` already exists
    for the current user, the existing notebook is returned instead of creating
    a new one.

    Request body (JSON):
      - title (str, optional): Custom notebook title. If omitted, a default
        title is used. When ``problem_id`` is provided, the title is derived
        from the problem title.
      - problem_id (int, optional): ID of the problem to link the notebook to.

    Responses:
      - 200 OK: Existing notebook for the (user, problem) pair already exists
        and is returned.
      - 201 Created: New notebook successfully created.

    Response body (JSON):
      - id (int): Notebook ID.
      - title (str): Notebook title.
      - problem_id (int|null): Linked problem ID, if any.
      - created_at (str): Notebook creation timestamp.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NotebookCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        problem_id = serializer.validated_data.get("problem_id")
        title = serializer.validated_data.get("title") or "Новый блокнот"
        
        # If problem_id is provided, set title based on problem
        if problem_id:
            problem = serializer.problem
            if problem is None:
                problem = get_object_or_404(Problem, pk=problem_id)
            title = f"Блокнот для задачи: {problem.title}"
            
            # Check if notebook for this problem already exists for this user
            existing_notebook = Notebook.objects.filter(
                owner=request.user,
                problem=problem
            ).first()
            
            if existing_notebook:
                return Response(
                    {
                        "id": existing_notebook.id,
                        "title": existing_notebook.title,
                        "problem_id": existing_notebook.problem_id,
                        "created_at": existing_notebook.created_at,
                        "message": "Notebook already exists for this problem"
                    },
                    status=status.HTTP_200_OK
                )
            
            notebook = Notebook.objects.create(
                owner=request.user,
                problem=problem,
                title=title
            )
        else:
            notebook = Notebook.objects.create(
                owner=request.user,
                title=title
            )

        return Response(
            {
                "id": notebook.id,
                "title": notebook.title,
                "problem_id": notebook.problem_id,
                "created_at": notebook.created_at,
            },
            status=status.HTTP_201_CREATED
        )


class CreateNotebookSessionView(APIView):
    """
    POST /api/sessions/notebook/ - Create a runtime session for a notebook.
    
    If the notebook is linked to a problem, the problem's data files (train.csv,
    test.csv, sample_submission.csv) are automatically copied to the session
    workdir for immediate use.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = NotebookSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notebook = getattr(serializer, "notebook", None)
        if notebook is None:
            notebook_id = serializer.validated_data["notebook_id"]
            notebook = get_object_or_404(Notebook, pk=notebook_id)

        ensure_notebook_access(request.user, notebook)

        session_id = build_notebook_session_id(notebook.id)
        overrides = {
            "gpu": notebook.compute_device == Notebook.ComputeDevice.GPU,
        }
        session = create_session(session_id, overrides=overrides)

        if notebook.problem:
            copy_problem_files_to_session(notebook.problem, session)

        payload = _build_session_payload(session_id, session, status_label="created")
        return Response(payload, status=status.HTTP_201_CREATED)


class ResetSessionView(APIView):
    """
    POST /api/sessions/reset/ - Reset a runtime session.
    
    If the session belongs to a notebook linked to a problem, the problem's data
    files are re-copied to the session workdir.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SessionResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["session_id"]
        cancel_streaming_runs(session_id, reason="Сессия перезапущена")
        notebook_id = extract_notebook_id(session_id)
        notebook = None
        if notebook_id is not None:
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            ensure_notebook_access(request.user, notebook)

        overrides = None
        if notebook_id is not None:
            overrides = {
                "gpu": notebook.compute_device == Notebook.ComputeDevice.GPU,
            }
        try:
            session = reset_session(session_id, overrides=overrides)
        except SessionNotFoundError:
            raise Http404("Session not found")
        if notebook and notebook.problem:
            copy_problem_files_to_session(notebook.problem, session)
        payload = _build_session_payload(session_id, session, status_label="reset")
        return Response(payload, status=status.HTTP_200_OK)


class StopSessionView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SessionResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]
        cancel_streaming_runs(session_id, reason="Сессия остановлена")
        notebook_id = extract_notebook_id(session_id)
        if notebook_id is not None:
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            ensure_notebook_access(request.user, notebook)

        removed = stop_session(session_id)
        if not removed:
            raise Http404("Session not found")
        payload = {"session_id": session_id, "status": "stopped"}
        return Response(payload, status=status.HTTP_200_OK)


class SessionFilesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = SessionFilesQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]

        session = get_session(session_id, touch=False)
        if session is None:
            raise Http404("Session not found")

        files: list[dict[str, str | int]] = []
        for path in sorted(session.workdir.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(session.workdir)
            if ".streams" in rel.parts:
                continue
            stat = path.stat()
            files.append({
                "path": rel.as_posix(),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })

        body = {"session_id": session_id, "files": files}
        vm_payload = _serialize_vm_payload(session)
        if vm_payload:
            body["vm"] = vm_payload
        return Response(body, status=status.HTTP_200_OK)


class SessionFileUploadView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SessionFileUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]
        upload = serializer.validated_data["file"]
        relative_override = serializer.validated_data.get("path")

        session = get_session(session_id, touch=False)
        if session is None:
            raise Http404("Session not found")

        notebook_id = extract_notebook_id(session_id)
        if notebook_id is not None:
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            if notebook.owner_id is not None and not getattr(request.user, "is_authenticated", False):
                raise PermissionDenied("Недостаточно прав для работы с этим блокнотом")
            ensure_notebook_access(request.user, notebook)

        filename = Path(getattr(upload, "name", "") or "uploaded.file").name
        raw_path = (relative_override or "").strip()
        relative_path = Path(raw_path) if raw_path else Path(filename)
        if raw_path.endswith(("/", "\\")) or relative_path.name in ("", "."):
            relative_path = relative_path / filename
        if relative_path.is_absolute():
            return Response(
                {"detail": "Path must be relative to the session"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_dir = session.workdir.resolve()
        target_path = (base_dir / relative_path).resolve()
        try:
            target_path.relative_to(base_dir)
        except ValueError:
            raise Http404("File outside sandbox")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with target_path.open("wb") as destination:
            for chunk in upload.chunks():
                destination.write(chunk)

        stat = target_path.stat()
        return Response(
            {
                "session_id": session_id,
                "path": target_path.relative_to(base_dir).as_posix(),
                "size": stat.st_size,
            },
            status=status.HTTP_201_CREATED,
        )


class SessionFileDownloadView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = SessionFileDownloadSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]
        relative_path = serializer.validated_data["path"]

        session = get_session(session_id, touch=False)
        if session is None:
            raise Http404("Session not found")

        notebook_id = extract_notebook_id(session_id)
        if notebook_id is not None:
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            ensure_notebook_access(request.user, notebook)

        candidate = (session.workdir / relative_path).resolve()
        try:
            candidate.relative_to(session.workdir.resolve())
        except ValueError:
            raise Http404("File outside sandbox")

        if not candidate.exists() or not candidate.is_file():
            raise Http404("File not found")

        return FileResponse(candidate.open("rb"), as_attachment=True, filename=candidate.name)


class SessionFilePreviewView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = SessionFilePreviewSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]
        relative_path = serializer.validated_data["path"]
        max_rows, max_cols = _normalize_preview_limits(serializer)
        delimiter = _normalize_delimiter(serializer.validated_data.get("delimiter"))

        session = get_session(session_id, touch=False)
        if session is None:
            raise Http404("Session not found")

        notebook_id = extract_notebook_id(session_id)
        if notebook_id is not None:
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            ensure_notebook_access(request.user, notebook)

        candidate = (session.workdir / relative_path).resolve()
        try:
            candidate.relative_to(session.workdir.resolve())
        except ValueError:
            raise Http404("File outside sandbox")

        if not candidate.exists() or not candidate.is_file():
            raise Http404("File not found")

        ext = candidate.suffix.lower()
        if ext not in SUPPORTED_PREVIEW_EXTENSIONS:
            return Response(
                {"detail": "Unsupported file type for preview"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if ext == ".csv":
                preview = _preview_csv(candidate, max_rows=max_rows, max_cols=max_cols, delimiter=delimiter)
            else:
                preview = _preview_parquet(candidate, max_rows=max_rows, max_cols=max_cols)
        except PreviewError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            "session_id": session_id,
            "path": relative_path,
            "format": "csv" if ext == ".csv" else "parquet",
            **preview,
        }
        return Response(payload, status=status.HTTP_200_OK)


class SessionFileChartView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SessionFileChartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]
        relative_path = serializer.validated_data["path"]
        chart_type = serializer.validated_data.get("chart_type")
        x_column = _normalize_optional_column(serializer.validated_data.get("x"))
        y_columns = _normalize_y_columns(serializer.validated_data.get("y"))
        aggregation = (serializer.validated_data.get("agg") or "mean").lower()
        delimiter = _normalize_delimiter(serializer.validated_data.get("delimiter"))
        render_image = bool(serializer.validated_data.get("render_image", True))
        row_limit = _normalize_chart_row_limit(serializer)
        max_points = _normalize_chart_max_points(serializer)
        bins = serializer.validated_data.get("bins") or DEFAULT_CHART_BINS
        top_n = _normalize_chart_top_n(serializer)

        session = get_session(session_id, touch=False)
        if session is None:
            raise Http404("Session not found")

        notebook_id = extract_notebook_id(session_id)
        if notebook_id is not None:
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            ensure_notebook_access(request.user, notebook)

        candidate = (session.workdir / relative_path).resolve()
        try:
            candidate.relative_to(session.workdir.resolve())
        except ValueError:
            raise Http404("File outside sandbox")

        if not candidate.exists() or not candidate.is_file():
            raise Http404("File not found")

        ext = candidate.suffix.lower()
        if ext not in SUPPORTED_PREVIEW_EXTENSIONS:
            return Response(
                {"detail": "Unsupported file type for chart"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            frame = _load_chart_dataframe(candidate, delimiter=delimiter, row_limit=row_limit)
            schema = _build_chart_schema(frame)
            recommended = _recommend_chart(frame)
            if not chart_type:
                return Response(
                    {
                        "session_id": session_id,
                        "path": relative_path,
                        "format": "csv" if ext == ".csv" else "parquet",
                        "schema": schema,
                        "recommended": recommended,
                    },
                    status=status.HTTP_200_OK,
                )

            chart = _build_chart_payload(
                frame,
                chart_type=chart_type,
                x_column=x_column,
                y_columns=y_columns,
                aggregation=aggregation,
                bins=bins,
                max_points=max_points,
                top_n=top_n,
            )
            chart_image = _render_chart_image(chart) if render_image else None
        except ChartError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            "session_id": session_id,
            "path": relative_path,
            "format": "csv" if ext == ".csv" else "parquet",
            "schema": schema,
            "recommended": recommended,
            "chart": chart,
        }
        if chart_image:
            payload["chart_image"] = chart_image
        return Response(payload, status=status.HTTP_200_OK)


def _build_session_payload(
    session_id: str,
    session: RuntimeSession | None,
    *,
    status_label: str,
) -> dict:
    payload = {"session_id": session_id, "status": status_label}
    vm_payload = _serialize_vm_payload(session)
    if vm_payload:
        payload["vm"] = vm_payload
    return payload


def _serialize_vm_payload(session: RuntimeSession | None) -> dict | None:
    vm = getattr(session, "vm", None)
    if vm is None:
        return None
    return {
        "id": vm.id,
        "state": vm.state.value,
        "image": vm.spec.image,
        "resources": {
            "cpu": vm.spec.resources.cpu,
            "ram_mb": vm.spec.resources.ram_mb,
            "disk_gb": vm.spec.resources.disk_gb,
            "gpu": vm.spec.gpu,
        },
        "network": {
            "outbound": vm.spec.network.outbound,
            "allowlist": list(vm.spec.network.allowlist),
        },
        "workspace_path": vm.workspace_path.as_posix(),
        "created_at": vm.created_at.isoformat(),
        "updated_at": vm.updated_at.isoformat(),
    }


class PreviewError(ValueError):
    pass


class ChartError(ValueError):
    pass


def _normalize_preview_limits(serializer: SessionFilePreviewSerializer) -> tuple[int, int]:
    max_rows = serializer.validated_data.get("max_rows") or DEFAULT_PREVIEW_ROWS
    max_cols = serializer.validated_data.get("max_cols") or DEFAULT_PREVIEW_COLS
    max_rows = min(int(max_rows), MAX_PREVIEW_ROWS)
    max_cols = min(int(max_cols), MAX_PREVIEW_COLS)
    return max_rows, max_cols


def _normalize_chart_row_limit(serializer: SessionFileChartSerializer) -> int:
    raw = serializer.validated_data.get("row_limit") or DEFAULT_CHART_ROWS
    return min(int(raw), MAX_CHART_ROWS)


def _normalize_chart_max_points(serializer: SessionFileChartSerializer) -> int:
    raw = serializer.validated_data.get("max_points") or DEFAULT_CHART_POINTS
    return min(int(raw), MAX_CHART_POINTS)


def _normalize_chart_top_n(serializer: SessionFileChartSerializer) -> int:
    raw = serializer.validated_data.get("top_n") or DEFAULT_BAR_TOP_N
    return min(int(raw), MAX_BAR_TOP_N)


def _normalize_delimiter(raw: object) -> str | None:
    if raw is None:
        return None
    text = str(raw)
    if not text:
        return None
    lowered = text.strip().lower()
    if lowered in {"\\t", "tab"}:
        return "\t"
    if len(text) == 1:
        return text
    return None


def _detect_csv_delimiter(sample: str) -> str:
    if not sample:
        return ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        return dialect.delimiter
    except Exception:
        return _guess_csv_delimiter(sample)


def _guess_csv_delimiter(sample: str) -> str:
    lines = [line for line in sample.splitlines() if line.strip()]
    if not lines:
        return ","
    line = lines[0]
    candidates = [",", ";", "\t", "|"]
    best = ","
    best_count = -1
    for delim in candidates:
        count = line.count(delim)
        if count > best_count:
            best = delim
            best_count = count
    return best


def _normalize_columns(header: list[str], display_cols: int) -> list[str]:
    columns: list[str] = []
    for idx in range(display_cols):
        raw = header[idx] if idx < len(header) else ""
        text = str(raw).strip() if raw is not None else ""
        if not text:
            text = f"col{idx + 1}"
        columns.append(_truncate_preview_value(text))
    return columns


def _normalize_row(row: list[object], display_cols: int) -> list[str]:
    normalized: list[str] = []
    for idx in range(display_cols):
        value = row[idx] if idx < len(row) else ""
        normalized.append(_truncate_preview_value(value))
    return normalized


def _truncate_preview_value(value: object) -> str:
    text = "" if value is None else str(value)
    if len(text) > MAX_PREVIEW_CELL_CHARS:
        return text[:MAX_PREVIEW_CELL_CHARS] + "…"
    return text


def _read_csv_sample(handle) -> str:
    sample = handle.read(65536)
    max_sample_size = 1024 * 1024
    while sample and ("\n" not in sample and "\r" not in sample) and len(sample) < max_sample_size:
        chunk = handle.read(65536)
        if not chunk:
            break
        sample += chunk
    return sample


def _preview_csv(path: Path, *, max_rows: int, max_cols: int, delimiter: str | None) -> dict:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        sample = _read_csv_sample(handle)
        handle.seek(0)
        delim = delimiter or _detect_csv_delimiter(sample)
        try:
            reader = csv.reader(handle, delimiter=delim)
            header = next(reader, None)
            if header is None:
                return {
                    "columns": [],
                    "rows": [],
                    "dtypes": {},
                    "truncated": {"rows": False, "cols": False},
                    "delimiter": delim,
                }

            rows: list[list[str]] = []
            max_seen_cols = len(header)
            truncated_rows = False
            for row in reader:
                max_seen_cols = max(max_seen_cols, len(row))
                if len(rows) < max_rows:
                    rows.append(row)
                else:
                    truncated_rows = True
                    break
        except Exception as exc:
            raise PreviewError("Не удалось прочитать CSV-файл: проверьте формат и кодировку.") from exc

    truncated_cols = max_seen_cols > max_cols
    display_cols = min(max_seen_cols, max_cols)
    columns = _normalize_columns([str(item) for item in header], display_cols)
    normalized_rows = [_normalize_row(row, display_cols) for row in rows]
    return {
        "columns": columns,
        "rows": normalized_rows,
        "dtypes": {},
        "truncated": {"rows": truncated_rows, "cols": truncated_cols},
        "delimiter": delim,
    }


def _preview_parquet(path: Path, *, max_rows: int, max_cols: int) -> dict:
    try:
        import pyarrow.parquet as pq
    except Exception as exc:  # pragma: no cover - optional dependency
        raise PreviewError("Для предпросмотра Parquet установите pyarrow.") from exc

    try:
        parquet_file = pq.ParquetFile(path)
        schema = parquet_file.schema
        all_columns = list(schema.names)
        if not all_columns:
            return {
                "columns": [],
                "rows": [],
                "dtypes": {},
                "truncated": {"rows": False, "cols": False},
            }

        display_columns = all_columns[:max_cols]
        batch_iter = parquet_file.iter_batches(batch_size=max_rows, columns=display_columns)
        batch = next(batch_iter, None)
        rows: list[list[str]] = []
        if batch is not None and batch.num_rows:
            data = batch.to_pydict()
            for index in range(batch.num_rows):
                row = []
                for col in display_columns:
                    value = data.get(col, [None] * batch.num_rows)[index]
                    row.append(_truncate_preview_value(value))
                rows.append(row)

        total_rows = getattr(parquet_file.metadata, "num_rows", None)
        if total_rows is None:
            total_rows = len(rows)
        truncated_rows = total_rows > len(rows)
        truncated_cols = len(all_columns) > max_cols
        dtypes = {name: str(schema.field(name).type) for name in display_columns}
        return {
            "columns": display_columns,
            "rows": rows,
            "dtypes": dtypes,
            "truncated": {"rows": truncated_rows, "cols": truncated_cols},
        }
    except Exception as exc:
        raise PreviewError(
            "Не удалось прочитать Parquet-файл: возможно, он поврежден или имеет неподдерживаемый формат."
        ) from exc


def _normalize_optional_column(raw: object) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def _normalize_y_columns(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [item.strip() for item in raw.split(",")]
    elif isinstance(raw, (list, tuple)):
        parts = [str(item).strip() for item in raw]
    else:
        return []
    columns: list[str] = []
    for name in parts:
        if name and name not in columns:
            columns.append(name)
    return columns


def _load_chart_dataframe(path: Path, *, delimiter: str | None, row_limit: int):
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ChartError("Для построения графиков установите pandas.") from exc

    ext = path.suffix.lower()
    if ext == ".csv":
        resolved_delimiter = delimiter
        if resolved_delimiter is None:
            with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                sample = _read_csv_sample(handle)
            resolved_delimiter = _detect_csv_delimiter(sample)
        try:
            frame = pd.read_csv(
                path,
                sep=resolved_delimiter,
                engine="python",
                nrows=row_limit,
            )
        except Exception as exc:
            raise ChartError("Не удалось прочитать CSV для построения графика.") from exc
        return frame

    if ext in {".parquet", ".parq"}:
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            raise ChartError("Не удалось прочитать Parquet для построения графика.") from exc
        if len(frame.index) > row_limit:
            frame = frame.head(row_limit)
        return frame

    raise ChartError("Unsupported file type for chart")


def _build_chart_schema(frame) -> dict[str, object]:
    columns: list[dict[str, object]] = []
    numeric: list[str] = []
    categorical: list[str] = []
    datetimes: list[str] = []
    for name in frame.columns:
        series = frame[name]
        kind = _column_kind(series)
        if kind == "numeric":
            numeric.append(str(name))
        elif kind == "datetime":
            datetimes.append(str(name))
        elif kind in {"categorical", "bool"}:
            categorical.append(str(name))
        columns.append(
            {
                "name": str(name),
                "dtype": str(series.dtype),
                "kind": kind,
                "non_null": int(series.notna().sum()),
            }
        )
    return {
        "rows": int(len(frame.index)),
        "columns": columns,
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "datetime_columns": datetimes,
    }


def _recommend_chart(frame) -> dict[str, object] | None:
    numeric = _select_numeric_columns(frame)
    datetimes = [str(name) for name in frame.columns if _column_kind(frame[name]) == "datetime"]
    categorical = [
        str(name)
        for name in frame.columns
        if _column_kind(frame[name]) in {"categorical", "bool"}
    ]

    if datetimes and numeric:
        return {"chart_type": "line", "x": datetimes[0], "y": [numeric[0]]}
    if len(numeric) >= 2:
        return {"chart_type": "scatter", "x": numeric[0], "y": [numeric[1]]}
    if categorical and numeric:
        return {"chart_type": "bar", "x": categorical[0], "y": [numeric[0]], "agg": "mean"}
    if numeric:
        return {"chart_type": "hist", "y": [numeric[0]], "bins": DEFAULT_CHART_BINS}
    if categorical:
        return {"chart_type": "bar", "x": categorical[0], "agg": "count"}
    return None


def _build_chart_payload(
    frame,
    *,
    chart_type: str,
    x_column: str | None,
    y_columns: list[str],
    aggregation: str,
    bins: int,
    max_points: int,
    top_n: int,
) -> dict[str, object]:
    if frame.empty:
        raise ChartError("Набор данных пуст: график строить не из чего.")

    if chart_type == "line":
        return _build_line_chart(frame, x_column=x_column, y_columns=y_columns, max_points=max_points)
    if chart_type == "bar":
        return _build_bar_chart(
            frame,
            x_column=x_column,
            y_columns=y_columns,
            aggregation=aggregation,
            top_n=top_n,
        )
    if chart_type == "scatter":
        return _build_scatter_chart(frame, x_column=x_column, y_columns=y_columns, max_points=max_points)
    if chart_type == "hist":
        return _build_hist_chart(frame, y_columns=y_columns, bins=bins)
    if chart_type == "box":
        return _build_box_chart(frame, y_columns=y_columns)
    raise ChartError("Unsupported chart type")


def _build_line_chart(frame, *, x_column: str | None, y_columns: list[str], max_points: int) -> dict[str, object]:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ChartError("Для построения графиков установите pandas.") from exc

    if x_column and x_column not in frame.columns:
        raise ChartError(f"Колонка '{x_column}' не найдена.")

    numeric_columns = _select_numeric_columns(frame)
    if not y_columns:
        y_columns = [col for col in numeric_columns if col != x_column][:3]
    if not y_columns:
        raise ChartError("Для line-графика нужна хотя бы одна числовая колонка y.")

    for name in y_columns:
        if name not in frame.columns:
            raise ChartError(f"Колонка '{name}' не найдена.")
        if name not in numeric_columns:
            raise ChartError(f"Колонка '{name}' должна быть числовой для line-графика.")

    x_name = x_column or "__index__"
    x_values = frame.index if x_column is None else frame[x_column]
    payload_series: list[dict[str, object]] = []
    for name in y_columns:
        numeric_y = pd.to_numeric(frame[name], errors="coerce")
        points: list[dict[str, object]] = []
        for x_val, y_val in zip(x_values, numeric_y):
            if _is_missing(y_val):
                continue
            points.append({"x": _to_json_scalar(x_val), "y": _to_json_scalar(y_val)})
        total_points = len(points)
        points, truncated = _downsample_points(points, max_points=max_points)
        payload_series.append(
            {
                "name": name,
                "points": points,
                "total_points": total_points,
                "truncated": truncated,
            }
        )

    return {
        "type": "line",
        "x": x_name,
        "y": y_columns,
        "series": payload_series,
    }


def _build_scatter_chart(
    frame,
    *,
    x_column: str | None,
    y_columns: list[str],
    max_points: int,
) -> dict[str, object]:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ChartError("Для построения графиков установите pandas.") from exc

    numeric_columns = _select_numeric_columns(frame)
    if not numeric_columns:
        raise ChartError("Для scatter-графика нужны как минимум две числовые колонки.")

    if not x_column:
        x_column = numeric_columns[0]
    if x_column not in frame.columns:
        raise ChartError(f"Колонка '{x_column}' не найдена.")
    if x_column not in numeric_columns:
        raise ChartError(f"Колонка '{x_column}' должна быть числовой для scatter-графика.")

    if y_columns:
        y_column = y_columns[0]
    else:
        y_candidates = [name for name in numeric_columns if name != x_column]
        y_column = y_candidates[0] if y_candidates else None
    if not y_column:
        raise ChartError("Для scatter-графика нужна вторая числовая колонка.")
    if y_column not in frame.columns:
        raise ChartError(f"Колонка '{y_column}' не найдена.")
    if y_column not in numeric_columns:
        raise ChartError(f"Колонка '{y_column}' должна быть числовой для scatter-графика.")

    x_series = pd.to_numeric(frame[x_column], errors="coerce")
    y_series = pd.to_numeric(frame[y_column], errors="coerce")
    points: list[dict[str, object]] = []
    for x_val, y_val in zip(x_series, y_series):
        if _is_missing(x_val) or _is_missing(y_val):
            continue
        points.append({"x": _to_json_scalar(x_val), "y": _to_json_scalar(y_val)})
    total_points = len(points)
    points, truncated = _downsample_points(points, max_points=max_points)
    return {
        "type": "scatter",
        "x": x_column,
        "y": [y_column],
        "series": [
            {
                "name": f"{y_column} vs {x_column}",
                "points": points,
                "total_points": total_points,
                "truncated": truncated,
            }
        ],
    }


def _build_bar_chart(
    frame,
    *,
    x_column: str | None,
    y_columns: list[str],
    aggregation: str,
    top_n: int,
) -> dict[str, object]:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ChartError("Для построения графиков установите pandas.") from exc

    if not x_column:
        raise ChartError("Для bar-графика укажите колонку x.")
    if x_column not in frame.columns:
        raise ChartError(f"Колонка '{x_column}' не найдена.")

    if not y_columns:
        counts = frame[x_column].astype("string").fillna("<null>").value_counts(dropna=False).head(top_n)
        points = [{"x": _to_json_scalar(idx), "y": int(value)} for idx, value in counts.items()]
        return {
            "type": "bar",
            "x": x_column,
            "y": ["count"],
            "agg": "count",
            "series": [{"name": "count", "points": points}],
        }

    for name in y_columns:
        if name not in frame.columns:
            raise ChartError(f"Колонка '{name}' не найдена.")

    numeric_columns = set(_select_numeric_columns(frame))
    if aggregation != "count":
        for name in y_columns:
            if name not in numeric_columns:
                raise ChartError(
                    f"Колонка '{name}' должна быть числовой для agg='{aggregation}' в bar-графике."
                )

    working = frame[[x_column, *y_columns]].copy()
    if aggregation != "count":
        for name in y_columns:
            working[name] = pd.to_numeric(working[name], errors="coerce")
    grouped = working.groupby(x_column, dropna=False)[y_columns]
    if aggregation == "count":
        aggregated = grouped.count()
    elif aggregation == "mean":
        aggregated = grouped.mean()
    elif aggregation == "sum":
        aggregated = grouped.sum()
    elif aggregation == "median":
        aggregated = grouped.median()
    elif aggregation == "min":
        aggregated = grouped.min()
    elif aggregation == "max":
        aggregated = grouped.max()
    else:
        raise ChartError(f"Неподдерживаемая агрегация '{aggregation}'.")

    if aggregated.empty:
        raise ChartError("Не удалось построить bar-график: нет данных после агрегации.")

    aggregated = aggregated.reset_index()
    sort_column = y_columns[0]
    if sort_column in aggregated.columns:
        aggregated = aggregated.sort_values(by=sort_column, ascending=False, kind="stable")
    aggregated = aggregated.head(top_n)

    x_values = aggregated[x_column].tolist()
    series_payload: list[dict[str, object]] = []
    for name in y_columns:
        points = []
        for x_val, y_val in zip(x_values, aggregated[name]):
            if _is_missing(y_val):
                continue
            points.append({"x": _to_json_scalar(x_val), "y": _to_json_scalar(y_val)})
        series_payload.append({"name": name, "points": points})

    return {
        "type": "bar",
        "x": x_column,
        "y": y_columns,
        "agg": aggregation,
        "series": series_payload,
    }


def _build_hist_chart(frame, *, y_columns: list[str], bins: int) -> dict[str, object]:
    try:
        import numpy as np
        import pandas as pd
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ChartError("Для построения графиков установите numpy/pandas.") from exc

    numeric_columns = _select_numeric_columns(frame)
    if y_columns:
        target = y_columns[0]
    else:
        target = numeric_columns[0] if numeric_columns else None
    if not target:
        raise ChartError("Для hist-графика укажите числовую колонку y.")
    if target not in frame.columns:
        raise ChartError(f"Колонка '{target}' не найдена.")
    if target not in numeric_columns:
        raise ChartError(f"Колонка '{target}' должна быть числовой для hist-графика.")

    values = pd.to_numeric(frame[target], errors="coerce").dropna()
    if values.empty:
        raise ChartError(f"В колонке '{target}' нет числовых значений для hist-графика.")

    counts, edges = np.histogram(values.to_numpy(dtype=float), bins=int(bins))
    buckets = []
    for idx, count in enumerate(counts):
        buckets.append(
            {
                "start": _to_json_scalar(edges[idx]),
                "end": _to_json_scalar(edges[idx + 1]),
                "count": int(count),
            }
        )
    return {"type": "hist", "x": target, "y": ["count"], "bins": int(bins), "series": [{"name": target, "bins": buckets}]}


def _build_box_chart(frame, *, y_columns: list[str]) -> dict[str, object]:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ChartError("Для построения графиков установите pandas.") from exc

    numeric_columns = _select_numeric_columns(frame)
    if not y_columns:
        y_columns = numeric_columns[:5]
    if not y_columns:
        raise ChartError("Для box-графика нужна хотя бы одна числовая колонка y.")

    stats: list[dict[str, object]] = []
    for name in y_columns:
        if name not in frame.columns:
            raise ChartError(f"Колонка '{name}' не найдена.")
        if name not in numeric_columns:
            raise ChartError(f"Колонка '{name}' должна быть числовой для box-графика.")
        values = pd.to_numeric(frame[name], errors="coerce").dropna()
        if values.empty:
            continue
        quantiles = values.quantile([0.25, 0.5, 0.75])
        stats.append(
            {
                "name": name,
                "count": int(values.count()),
                "min": _to_json_scalar(values.min()),
                "q1": _to_json_scalar(quantiles.loc[0.25]),
                "median": _to_json_scalar(quantiles.loc[0.5]),
                "q3": _to_json_scalar(quantiles.loc[0.75]),
                "max": _to_json_scalar(values.max()),
                "mean": _to_json_scalar(values.mean()),
            }
        )

    if not stats:
        raise ChartError("Для box-графика не найдено подходящих числовых данных.")
    return {"type": "box", "x": None, "y": y_columns, "series": stats}


def _select_numeric_columns(frame) -> list[str]:
    columns: list[str] = []
    for name in frame.columns:
        if _column_kind(frame[name]) == "numeric":
            columns.append(str(name))
    return columns


def _column_kind(series) -> str:
    kind = getattr(series.dtype, "kind", None)
    dtype_text = str(series.dtype).lower()
    if kind in {"i", "u", "f", "c"}:
        return "numeric"
    if kind in {"M", "m"} or dtype_text.startswith("datetime"):
        return "datetime"
    if dtype_text in {"bool", "boolean"}:
        return "bool"
    if dtype_text in {"object", "string", "category"}:
        return "categorical"
    return "other"


def _downsample_points(points: list[dict[str, object]], *, max_points: int) -> tuple[list[dict[str, object]], bool]:
    if len(points) <= max_points:
        return points, False
    step = max(1, math.ceil(len(points) / max_points))
    reduced = points[::step]
    if reduced and reduced[-1] != points[-1]:
        reduced.append(points[-1])
    if len(reduced) > max_points:
        reduced = reduced[:max_points]
    return reduced, True


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        import pandas as pd
    except Exception:
        pd = None
    if pd is not None:
        try:
            return bool(pd.isna(value))
        except Exception:
            pass
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    try:
        return bool(value != value)
    except Exception:
        return False


def _to_json_scalar(value: Any) -> Any:
    if _is_missing(value):
        return None

    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, (bool, int, str)):
        return value

    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        try:
            return isoformat()
        except Exception:
            pass

    return str(value)


def _render_chart_image(chart: dict[str, object]) -> str:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - optional dependency
        raise ChartError("Для рендера графиков установите matplotlib.") from exc

    fig, axis = plt.subplots(figsize=(8, 4.8))
    try:
        chart_type = str(chart.get("type") or "").strip().lower()
        if chart_type == "line":
            _render_line_chart_image(axis, chart)
        elif chart_type == "scatter":
            _render_scatter_chart_image(axis, chart)
        elif chart_type == "bar":
            _render_bar_chart_image(axis, chart)
        elif chart_type == "hist":
            _render_hist_chart_image(axis, chart)
        elif chart_type == "box":
            _render_box_chart_image(axis, chart)
        else:
            raise ChartError("Неподдерживаемый тип графика для рендера.")

        axis.grid(True, alpha=0.25)
        fig.tight_layout()
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=130)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except ChartError:
        raise
    except Exception as exc:
        raise ChartError("Не удалось построить изображение графика.") from exc
    finally:
        plt.close(fig)


def _render_line_chart_image(axis, chart: dict[str, object]) -> None:
    series = chart.get("series") or []
    if not isinstance(series, list) or not series:
        raise ChartError("Недостаточно данных для line-графика.")

    for item in series:
        if not isinstance(item, dict):
            continue
        points = item.get("points") or []
        if not isinstance(points, list):
            continue
        xs = []
        ys = []
        for point in points:
            if not isinstance(point, dict):
                continue
            y_value = _safe_float(point.get("y"))
            if y_value is None:
                continue
            xs.append(_coerce_axis_value(point.get("x")))
            ys.append(y_value)
        if not ys:
            continue
        label = str(item.get("name") or "")
        axis.plot(xs, ys, marker="o", linewidth=1.7, markersize=3.5, label=label or None)

    axis.set_title("Line chart")
    axis.set_xlabel(str(chart.get("x") or "x"))
    axis.set_ylabel(", ".join(chart.get("y") or []) or "value")
    if len(series) > 1:
        axis.legend(loc="best")


def _render_scatter_chart_image(axis, chart: dict[str, object]) -> None:
    series = chart.get("series") or []
    if not isinstance(series, list) or not series:
        raise ChartError("Недостаточно данных для scatter-графика.")

    for item in series:
        if not isinstance(item, dict):
            continue
        points = item.get("points") or []
        if not isinstance(points, list):
            continue
        xs = []
        ys = []
        for point in points:
            if not isinstance(point, dict):
                continue
            x_value = _safe_float(point.get("x"))
            y_value = _safe_float(point.get("y"))
            if x_value is None or y_value is None:
                continue
            xs.append(x_value)
            ys.append(y_value)
        if not xs:
            continue
        label = str(item.get("name") or "")
        axis.scatter(xs, ys, s=18, alpha=0.85, label=label or None)

    axis.set_title("Scatter chart")
    axis.set_xlabel(str(chart.get("x") or "x"))
    y_labels = chart.get("y") or []
    axis.set_ylabel(str(y_labels[0]) if isinstance(y_labels, list) and y_labels else "y")
    if len(series) > 1:
        axis.legend(loc="best")


def _render_bar_chart_image(axis, chart: dict[str, object]) -> None:
    series = chart.get("series") or []
    if not isinstance(series, list) or not series:
        raise ChartError("Недостаточно данных для bar-графика.")

    labels: list[str] = []
    for item in series:
        if not isinstance(item, dict):
            continue
        points = item.get("points") or []
        if not isinstance(points, list):
            continue
        for point in points:
            if not isinstance(point, dict):
                continue
            x_value = str(point.get("x"))
            if x_value not in labels:
                labels.append(x_value)
    if not labels:
        raise ChartError("Недостаточно данных для bar-графика.")

    positions = list(range(len(labels)))
    width = 0.8 / max(1, len(series))
    for idx, item in enumerate(series):
        if not isinstance(item, dict):
            continue
        points = item.get("points") or []
        point_map: dict[str, float] = {}
        if isinstance(points, list):
            for point in points:
                if not isinstance(point, dict):
                    continue
                y_value = _safe_float(point.get("y"))
                if y_value is None:
                    continue
                point_map[str(point.get("x"))] = y_value
        values = [point_map.get(label, 0.0) for label in labels]
        offset = (idx - (len(series) - 1) / 2.0) * width
        shifted = [pos + offset for pos in positions]
        label = str(item.get("name") or "")
        axis.bar(shifted, values, width=width, label=label or None)

    axis.set_title("Bar chart")
    axis.set_xlabel(str(chart.get("x") or "x"))
    axis.set_ylabel(", ".join(chart.get("y") or []) or "value")
    axis.set_xticks(positions)
    axis.set_xticklabels(labels, rotation=30, ha="right")
    if len(series) > 1:
        axis.legend(loc="best")


def _render_hist_chart_image(axis, chart: dict[str, object]) -> None:
    series = chart.get("series") or []
    if not isinstance(series, list) or not series:
        raise ChartError("Недостаточно данных для hist-графика.")
    first = series[0] if isinstance(series[0], dict) else {}
    buckets = first.get("bins") or []
    if not isinstance(buckets, list) or not buckets:
        raise ChartError("Недостаточно данных для hist-графика.")

    starts = []
    widths = []
    counts = []
    for bucket in buckets:
        if not isinstance(bucket, dict):
            continue
        start = _safe_float(bucket.get("start"))
        end = _safe_float(bucket.get("end"))
        count = _safe_float(bucket.get("count"))
        if start is None or end is None or count is None:
            continue
        starts.append(start)
        widths.append(max(end - start, 1e-9))
        counts.append(count)
    if not starts:
        raise ChartError("Недостаточно данных для hist-графика.")

    axis.bar(starts, counts, width=widths, align="edge", edgecolor="#ffffff", linewidth=0.8, alpha=0.85)
    axis.set_title("Histogram")
    axis.set_xlabel(str(chart.get("x") or "value"))
    axis.set_ylabel("count")


def _render_box_chart_image(axis, chart: dict[str, object]) -> None:
    series = chart.get("series") or []
    if not isinstance(series, list) or not series:
        raise ChartError("Недостаточно данных для box-графика.")

    bxp_stats = []
    for item in series:
        if not isinstance(item, dict):
            continue
        q1 = _safe_float(item.get("q1"))
        q3 = _safe_float(item.get("q3"))
        med = _safe_float(item.get("median"))
        whislo = _safe_float(item.get("min"))
        whishi = _safe_float(item.get("max"))
        mean = _safe_float(item.get("mean"))
        if None in (q1, q3, med, whislo, whishi):
            continue
        bxp_stats.append(
            {
                "label": str(item.get("name") or ""),
                "q1": q1,
                "q3": q3,
                "med": med,
                "whislo": whislo,
                "whishi": whishi,
                "mean": mean if mean is not None else med,
            }
        )
    if not bxp_stats:
        raise ChartError("Недостаточно данных для box-графика.")

    axis.bxp(bxp_stats, showmeans=True)
    axis.set_title("Box plot")
    axis.set_ylabel("value")


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _coerce_axis_value(value: object) -> object:
    numeric = _safe_float(value)
    if numeric is not None:
        return numeric
    if value is None:
        return ""
    return str(value)

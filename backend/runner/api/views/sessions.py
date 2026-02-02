from __future__ import annotations

import shutil
from pathlib import Path

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from typing import Optional

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
from ..serializers import (
    NotebookCreateSerializer,
    NotebookSessionCreateSerializer,
    SessionResetSerializer,
    SessionFilesQuerySerializer,
    SessionFileDownloadSerializer,
    SessionFileUploadSerializer,
)

NOTEBOOK_SESSION_PREFIX = "notebook:"


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
        
        # Copy each file if it exists
        files_to_copy = [
            (problem_data.train_file, 'train.csv'),
            (problem_data.test_file, 'test.csv'),
            (problem_data.sample_submission_file, 'sample_submission.csv'),
        ]
        
        for file_field, target_name in files_to_copy:
            if file_field and file_field.name:
                try:
                    source_path = Path(file_field.path)
                    if source_path.exists():
                        target_path = workdir / target_name
                        shutil.copy2(source_path, target_path)
                except Exception as e:
                    # Log error but don't fail notebook creation
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to copy {target_name}: {e}")
    except Exception as e:
        # Don't fail notebook creation if file copying fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to copy problem files: {e}")


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
        session = create_session(session_id)
        
        # Copy problem files if notebook is linked to a problem
        if notebook.problem:
            try:
                copy_problem_files_to_session(notebook.problem, session)
            except Exception as e:
                # Log error but don't fail session creation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to copy problem files to session: {e}")
        
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
        notebook_id = extract_notebook_id(session_id)
        notebook = None
        if notebook_id is not None:
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            ensure_notebook_access(request.user, notebook)

        try:
            session = reset_session(session_id)
        except SessionNotFoundError:
            raise Http404("Session not found")
        
        # Copy problem files if notebook is linked to a problem
        if notebook and notebook.problem:
            try:
                copy_problem_files_to_session(notebook.problem, session)
            except Exception as e:
                # Log error but don't fail session reset
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to copy problem files to reset session: {e}")
        
        payload = _build_session_payload(session_id, session, status_label="reset")
        return Response(payload, status=status.HTTP_200_OK)


class StopSessionView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SessionResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]
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

        candidate = (session.workdir / relative_path).resolve()
        try:
            candidate.relative_to(session.workdir.resolve())
        except ValueError:
            raise Http404("File outside sandbox")

        if not candidate.exists() or not candidate.is_file():
            raise Http404("File not found")

        return FileResponse(candidate.open("rb"), as_attachment=True, filename=candidate.name)


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
        },
        "network": {
            "outbound": vm.spec.network.outbound,
            "allowlist": list(vm.spec.network.allowlist),
        },
        "workspace_path": vm.workspace_path.as_posix(),
        "created_at": vm.created_at.isoformat(),
        "updated_at": vm.updated_at.isoformat(),
    }

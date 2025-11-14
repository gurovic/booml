from __future__ import annotations

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models.notebook import Notebook
from ...services.runtime import (
    RuntimeSession,
    SessionNotFoundError,
    create_session,
    get_session,
    reset_session,
    stop_session,
)
from ..serializers import (
    NotebookSessionCreateSerializer,
    SessionResetSerializer,
    SessionFilesQuerySerializer,
    SessionFileDownloadSerializer,
)

NOTEBOOK_SESSION_PREFIX = "notebook:"


def build_notebook_session_id(notebook_id: int) -> str:
    return f"{NOTEBOOK_SESSION_PREFIX}{notebook_id}"


def extract_notebook_id(session_id: str) -> int | None:
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


class CreateNotebookSessionView(APIView):
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
        payload = _build_session_payload(session_id, session, status_label="created")
        return Response(payload, status=status.HTTP_201_CREATED)


class ResetSessionView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SessionResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session_id = serializer.validated_data["session_id"]
        notebook_id = extract_notebook_id(session_id)
        if notebook_id is not None:
            notebook = get_object_or_404(Notebook, pk=notebook_id)
            ensure_notebook_access(request.user, notebook)

        try:
            session = reset_session(session_id)
        except SessionNotFoundError:
            raise Http404("Session not found")
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
                "path": str(rel),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })

        body = {"session_id": session_id, "files": files}
        vm_payload = _serialize_vm_payload(session)
        if vm_payload:
            body["vm"] = vm_payload
        return Response(body, status=status.HTTP_200_OK)


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
        "workspace_path": str(vm.workspace_path),
        "created_at": vm.created_at.isoformat(),
        "updated_at": vm.updated_at.isoformat(),
    }

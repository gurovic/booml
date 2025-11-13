from __future__ import annotations

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models.notebook import Notebook
from ...services.runtime import create_session, reset_session, get_session
from ..serializers import (
    NotebookSessionCreateSerializer,
    SessionResetSerializer,
    SessionFilesQuerySerializer,
    SessionFileDownloadSerializer,
)
from pathlib import Path
import re

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
        create_session(session_id)
        return Response({"session_id": session_id, "status": "created"}, status=status.HTTP_201_CREATED)


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

        reset_session(session_id)
        return Response({"session_id": session_id, "status": "reset"}, status=status.HTTP_200_OK)


class SessionFilesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = SessionFilesQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data["session_id"]

        session = get_session(session_id, touch=False)
        if session is None:
            session = create_session(session_id)

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

        return Response({"session_id": session_id, "files": files}, status=status.HTTP_200_OK)


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

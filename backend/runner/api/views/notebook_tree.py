from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models.notebook import Notebook
from ...models.notebook_folder import NotebookFolder


def _folder_has_ancestor(folder: NotebookFolder, ancestor_id: int) -> bool:
    current = folder
    visited: set[int] = set()
    while current is not None:
        if current.id in visited:
            return False
        visited.add(current.id)
        if current.id == ancestor_id:
            return True
        if current.parent_id is None:
            return False
        current = (
            NotebookFolder.objects
            .filter(id=current.parent_id, owner_id=folder.owner_id)
            .only("id", "owner_id", "parent_id", "kind")
            .first()
        )
    return False


def _resolve_parent_folder(user, parent_id):
    if parent_id in (None, ""):
        return None

    parent = NotebookFolder.objects.filter(
        id=parent_id,
        owner=user,
    ).first()
    if parent is None:
        raise ValidationError({"parent_id": "Родительская папка не найдена"})
    return parent


def _collect_folder_subtree_ids(owner, root_folder_id: int) -> list[int]:
    folder_rows = (
        NotebookFolder.objects
        .filter(owner=owner)
        .values_list("id", "parent_id")
    )
    children_by_parent: dict[int | None, list[int]] = {}
    for folder_id, parent_id in folder_rows:
        children_by_parent.setdefault(parent_id, []).append(folder_id)

    to_visit = [root_folder_id]
    visited: set[int] = set()
    result: list[int] = []
    while to_visit:
        current_id = to_visit.pop()
        if current_id in visited:
            continue
        visited.add(current_id)
        result.append(current_id)
        to_visit.extend(children_by_parent.get(current_id, []))
    return result


def _serialize_folder(folder: NotebookFolder, *, size_bytes: int = 0) -> dict:
    return {
        "id": folder.id,
        "title": folder.title,
        "parent_id": folder.parent_id,
        "kind": folder.kind,
        "is_system": folder.is_system,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
        "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
        "size_bytes": int(max(size_bytes, 0)),
    }


def _serialize_notebook(notebook: Notebook, *, size_bytes: int = 0) -> dict:
    return {
        "id": notebook.id,
        "title": notebook.title,
        "folder_id": notebook.folder_id,
        "problem_id": notebook.problem_id,
        "problem_title": notebook.problem.title if notebook.problem else None,
        "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
        "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
        "size_bytes": int(max(size_bytes, 0)),
    }


def _estimate_notebook_size_bytes(notebook: Notebook) -> int:
    # Simple size estimate based on notebook text payload currently stored in DB.
    total = len((notebook.title or "").encode("utf-8"))
    total += len((notebook.compute_device or "").encode("utf-8"))
    for cell in notebook.cells.all():
        if cell.content:
            total += len(cell.content.encode("utf-8"))
        if cell.output:
            total += len(cell.output.encode("utf-8"))
    return max(total, 0)


def _build_folder_size_map(folders, notebooks, notebook_size_map: dict[int, int]) -> dict[int, int]:
    children_by_parent: dict[int | None, list[int]] = {}
    for folder in folders:
        children_by_parent.setdefault(folder.parent_id, []).append(folder.id)

    direct_size: dict[int, int] = {folder.id: 0 for folder in folders}
    for notebook in notebooks:
        if notebook.folder_id in direct_size:
            direct_size[notebook.folder_id] += notebook_size_map.get(notebook.id, 0)

    cache: dict[int, int] = {}

    def _sum_subtree(folder_id: int) -> int:
        if folder_id in cache:
            return cache[folder_id]
        total = direct_size.get(folder_id, 0)
        for child_id in children_by_parent.get(folder_id, []):
            total += _sum_subtree(child_id)
        cache[folder_id] = total
        return total

    for folder in folders:
        _sum_subtree(folder.id)
    return cache


def _validate_folder_title(raw_title) -> str:
    title = (raw_title or "").strip()
    if not title:
        raise ValidationError({"title": "Название папки не может быть пустым"})
    if len(title) > 200:
        raise ValidationError({"title": "Название папки слишком длинное"})
    return title


class NotebookTreeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(request.user)
        (
            Notebook.objects
            .filter(owner=request.user, problem_id__isnull=False)
            .exclude(folder_id=tasks_folder.id)
            .update(folder=tasks_folder)
        )

        folders = (
            NotebookFolder.objects
            .filter(owner=request.user)
            .order_by(
                Case(
                    When(kind=NotebookFolder.Kind.TASKS, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                ),
                "parent_id",
                "title",
                "id",
            )
        )
        notebooks = (
            Notebook.objects
            .filter(owner=request.user)
            .select_related("problem")
            .prefetch_related("cells")
            .order_by("-updated_at", "-id")
        )
        notebook_size_map = {
            notebook.id: _estimate_notebook_size_bytes(notebook)
            for notebook in notebooks
        }
        folder_size_map = _build_folder_size_map(folders, notebooks, notebook_size_map)

        return Response(
            {
                "folders": [
                    _serialize_folder(
                        folder,
                        size_bytes=folder_size_map.get(folder.id, 0),
                    )
                    for folder in folders
                ],
                "notebooks": [
                    _serialize_notebook(
                        notebook,
                        size_bytes=notebook_size_map.get(notebook.id, 0),
                    )
                    for notebook in notebooks
                ],
                "tasks_folder_id": tasks_folder.id,
            },
            status=status.HTTP_200_OK,
        )


class NotebookFolderCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        title = _validate_folder_title(request.data.get("title"))
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(request.user)
        parent = _resolve_parent_folder(request.user, request.data.get("parent_id"))
        if parent is not None and _folder_has_ancestor(parent, tasks_folder.id):
            raise ValidationError({"parent_id": "В папке «Блокноты для задач» нельзя создавать папки"})

        folder = NotebookFolder.objects.create(
            owner=request.user,
            parent=parent,
            title=title,
            kind=NotebookFolder.Kind.CUSTOM,
        )
        return Response(_serialize_folder(folder), status=status.HTTP_201_CREATED)


class NotebookFolderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, folder_id: int):
        folder = get_object_or_404(NotebookFolder, id=folder_id, owner=request.user)
        if folder.is_system:
            raise ValidationError({"detail": "Системную папку нельзя переименовать"})

        folder.title = _validate_folder_title(request.data.get("title"))
        folder.save(update_fields=["title", "updated_at"])
        return Response(_serialize_folder(folder), status=status.HTTP_200_OK)

    def delete(self, request, folder_id: int):
        folder = get_object_or_404(NotebookFolder, id=folder_id, owner=request.user)
        if folder.is_system:
            raise ValidationError({"detail": "Системную папку нельзя удалить"})

        folder_ids_to_delete = _collect_folder_subtree_ids(request.user, folder.id)
        Notebook.objects.filter(owner=request.user, folder_id__in=folder_ids_to_delete).delete()
        NotebookFolder.objects.filter(owner=request.user, id__in=folder_ids_to_delete).delete()
        return Response({"status": "success", "folder_id": folder_id}, status=status.HTTP_200_OK)


class NotebookFolderMoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, folder_id: int):
        folder = get_object_or_404(NotebookFolder, id=folder_id, owner=request.user)
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(request.user)

        if folder.is_system:
            raise ValidationError({"detail": "Системную папку нельзя перетаскивать"})
        if _folder_has_ancestor(folder, tasks_folder.id):
            raise ValidationError({"detail": "Из папки «Блокноты для задач» нельзя ничего перетаскивать"})

        parent = _resolve_parent_folder(request.user, request.data.get("parent_id"))
        if parent is not None:
            if _folder_has_ancestor(parent, tasks_folder.id):
                raise ValidationError({"detail": "В папку «Блокноты для задач» нельзя ничего перетаскивать"})
            if parent.id == folder.id:
                raise ValidationError({"parent_id": "Нельзя переместить папку в саму себя"})
            if _folder_has_ancestor(parent, folder.id):
                raise ValidationError({"parent_id": "Нельзя переместить папку внутрь себя"})

        target_parent_id = parent.id if parent is not None else None
        if folder.parent_id == target_parent_id:
            return Response(_serialize_folder(folder), status=status.HTTP_200_OK)

        folder.parent = parent
        folder.save(update_fields=["parent", "updated_at"])
        return Response(_serialize_folder(folder), status=status.HTTP_200_OK)


class NotebookMoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, notebook_id: int):
        notebook = get_object_or_404(Notebook, id=notebook_id, owner=request.user)
        tasks_folder = NotebookFolder.get_or_create_tasks_folder(request.user)

        source_folder = notebook.folder
        if source_folder is not None and _folder_has_ancestor(source_folder, tasks_folder.id):
            raise ValidationError({"detail": "Из папки «Блокноты для задач» нельзя ничего перетаскивать"})

        target_folder = _resolve_parent_folder(request.user, request.data.get("folder_id"))
        if target_folder is not None and _folder_has_ancestor(target_folder, tasks_folder.id):
            raise ValidationError({"detail": "В папку «Блокноты для задач» нельзя ничего перетаскивать"})

        target_folder_id = target_folder.id if target_folder is not None else None
        if notebook.folder_id == target_folder_id:
            return Response(_serialize_notebook(notebook), status=status.HTTP_200_OK)

        notebook.folder = target_folder
        notebook.save(update_fields=["folder", "updated_at"])
        return Response(_serialize_notebook(notebook), status=status.HTTP_200_OK)

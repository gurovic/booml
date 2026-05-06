import json
import re
import zipfile
from io import BytesIO
from urllib.parse import quote

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from ..models import Cell, Notebook, NotebookFolder


def _sanitize_filename_part(raw_title, default="notebook"):
    title = (raw_title or "").strip()
    invalid_chars = r'[<>:"/\\|?*]'
    safe_title = re.sub(invalid_chars, "_", title)
    safe_title = re.sub(r"[\s_]+", "_", safe_title).strip("_")
    return safe_title or default


def _build_notebook_data(notebook):
    cells_data = []
    execution_count = 1

    for cell in notebook.cells.all().order_by("execution_order"):
        if cell.cell_type == Cell.CODE:
            outputs = []
            if cell.output:
                try:
                    output_data = json.loads(cell.output)
                    if isinstance(output_data, dict):
                        if output_data.get("error"):
                            outputs.append({
                                "output_type": "error",
                                "ename": "Error",
                                "evalue": output_data.get("error", ""),
                                "traceback": [],
                            })
                        else:
                            if output_data.get("stdout"):
                                outputs.append({
                                    "output_type": "stream",
                                    "name": "stdout",
                                    "text": output_data["stdout"],
                                })
                            if output_data.get("outputs"):
                                for output_item in output_data["outputs"]:
                                    outputs.append({
                                        "output_type": "execute_result",
                                        "data": output_item,
                                        "execution_count": execution_count,
                                        "metadata": {},
                                    })
                except (json.JSONDecodeError, AttributeError):
                    outputs.append({
                        "output_type": "stream",
                        "name": "stdout",
                        "text": cell.output,
                    })

            cells_data.append({
                "cell_type": "code",
                "execution_count": execution_count,
                "metadata": {},
                "outputs": outputs,
                "source": cell.content.split("\n") if cell.content else [],
            })
            execution_count += 1
            continue

        if cell.cell_type == Cell.TEXT:
            cells_data.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": cell.content.split("\n") if cell.content else [],
            })
            continue

        if cell.cell_type == Cell.LATEX:
            latex_content = cell.content or ""
            markdown_content = f"$$\n{latex_content}\n$$"
            cells_data.append({
                "cell_type": "markdown",
                "metadata": {
                    "original_type": "latex",
                },
                "source": markdown_content.split("\n"),
            })

    return {
        "cells": cells_data,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.8.0",
            },
            "booml_metadata": {
                "booml_notebook_id": notebook.id,
                "booml_title": notebook.title,
                "compute_device": notebook.compute_device,
                "created_at": notebook.created_at.isoformat() if notebook.created_at else None,
                "updated_at": notebook.updated_at.isoformat() if notebook.updated_at else None,
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _parse_id_list(raw_values):
    if not isinstance(raw_values, list):
        return []
    values = []
    for value in raw_values:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            values.append(parsed)
    return values


def _collect_folder_tree(owner, selected_folder_ids):
    selected_set = set(selected_folder_ids)
    folder_rows = list(
        NotebookFolder.objects
        .filter(owner=owner)
        .values("id", "parent_id", "title")
    )

    folder_map = {row["id"]: row for row in folder_rows}
    children_by_parent = {}
    for row in folder_rows:
        children_by_parent.setdefault(row["parent_id"], []).append(row["id"])

    descendants = set()
    stack = [folder_id for folder_id in selected_set if folder_id in folder_map]
    while stack:
        current = stack.pop()
        if current in descendants:
            continue
        descendants.add(current)
        stack.extend(children_by_parent.get(current, []))

    return descendants, folder_map


def _build_folder_path(folder_id, folder_map):
    if folder_id is None:
        return []

    path = []
    current_id = folder_id
    visited = set()
    while current_id is not None:
        if current_id in visited:
            break
        visited.add(current_id)
        folder = folder_map.get(current_id)
        if folder is None:
            break
        path.insert(0, folder.get("title") or "folder")
        current_id = folder.get("parent_id")
    return path


def _make_unique_zip_path(desired_path, used_paths):
    if desired_path not in used_paths:
        used_paths.add(desired_path)
        return desired_path

    if "." in desired_path:
        base, extension = desired_path.rsplit(".", 1)
        extension = f".{extension}"
    else:
        base = desired_path
        extension = ""

    suffix = 2
    while True:
        candidate = f"{base} ({suffix}){extension}"
        if candidate not in used_paths:
            used_paths.add(candidate)
            return candidate
        suffix += 1


@csrf_exempt
@require_http_methods(["GET", "POST"])
def export_notebook(request, notebook_id):
    notebook = get_object_or_404(Notebook, id=notebook_id)
    notebook_data = _build_notebook_data(notebook)
    json_content = json.dumps(notebook_data, ensure_ascii=False, indent=2)

    if request.method == 'GET':
        safe_title = _sanitize_filename_part(notebook.title, default='notebook')
        filename = f"{safe_title}.ipynb"

        response = HttpResponse(json_content, content_type='application/json; charset=utf-8')
        encoded_filename = quote(filename, safe='')
        response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'

        return response

    return JsonResponse({
        'status': 'success',
        'data': notebook_data,
        'filename': f"{notebook.title.replace(' ', '_')}_{notebook.id}.ipynb"
    })


@csrf_exempt
@require_http_methods(["POST"])
def export_notebooks_archive(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "status": "error",
            "message": "Требуется авторизация",
        }, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return JsonResponse({
            "status": "error",
            "message": f"Некорректный JSON: {exc}",
        }, status=400)

    notebook_ids = _parse_id_list(payload.get("notebook_ids"))
    folder_ids = _parse_id_list(payload.get("folder_ids"))
    if not notebook_ids and not folder_ids:
        return JsonResponse({
            "status": "error",
            "message": "Не переданы элементы для экспорта",
        }, status=400)

    owner = request.user
    direct_notebooks = list(
        Notebook.objects
        .filter(owner=owner, id__in=notebook_ids)
        .prefetch_related("cells")
    )
    direct_notebooks_by_id = {item.id: item for item in direct_notebooks}

    ordered_notebooks = []
    seen_notebook_ids = set()
    for notebook_id in notebook_ids:
        notebook = direct_notebooks_by_id.get(notebook_id)
        if notebook is None or notebook.id in seen_notebook_ids:
            continue
        seen_notebook_ids.add(notebook.id)
        ordered_notebooks.append(notebook)

    folder_descendants, folder_map = _collect_folder_tree(owner, folder_ids)
    if folder_descendants:
        folder_notebooks = list(
            Notebook.objects
            .filter(owner=owner, folder_id__in=folder_descendants)
            .prefetch_related("cells")
            .order_by("folder_id", "id")
        )
        for notebook in folder_notebooks:
            if notebook.id in seen_notebook_ids:
                continue
            seen_notebook_ids.add(notebook.id)
            ordered_notebooks.append(notebook)

    if not ordered_notebooks:
        return JsonResponse({
            "status": "error",
            "message": "Не найдено блокнотов для экспорта",
        }, status=400)

    archive_buffer = BytesIO()
    used_paths = set()
    with zipfile.ZipFile(archive_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for notebook in ordered_notebooks:
            notebook_data = _build_notebook_data(notebook)
            notebook_content = json.dumps(notebook_data, ensure_ascii=False, indent=2)
            notebook_name = f"{_sanitize_filename_part(notebook.title, default='notebook')}.ipynb"

            folder_parts = [
                _sanitize_filename_part(part, default="folder")
                for part in _build_folder_path(notebook.folder_id, folder_map)
            ]
            desired_path = "/".join(folder_parts + [notebook_name]) if folder_parts else notebook_name
            archive_path = _make_unique_zip_path(desired_path, used_paths)
            archive.writestr(archive_path, notebook_content)

    archive_name = "notebooks_export.zip"
    response = HttpResponse(archive_buffer.getvalue(), content_type="application/zip")
    encoded_archive_name = quote(archive_name, safe="")
    response["Content-Disposition"] = (
        f'attachment; filename="{archive_name}"; filename*=UTF-8\'\'{encoded_archive_name}'
    )
    return response

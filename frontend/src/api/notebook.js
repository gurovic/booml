import { toApiError } from './error'
import { apiDelete, apiGet, apiPatch, apiPost, ensureCsrfToken } from './http'

export function createNotebook(problemIdOrOptions = null) {
    const payload = {}

    if (typeof problemIdOrOptions === 'number') {
        payload.problem_id = problemIdOrOptions
    } else if (problemIdOrOptions && typeof problemIdOrOptions === 'object') {
        if (problemIdOrOptions.problemId != null) {
            payload.problem_id = problemIdOrOptions.problemId
        }
        if (problemIdOrOptions.title != null) {
            payload.title = problemIdOrOptions.title
        }
        if (problemIdOrOptions.folderId != null) {
            payload.folder_id = problemIdOrOptions.folderId
        }
    }

    return apiPost('/api/notebooks/', payload)
}

export function getNotebookTree() {
    return apiGet('/api/notebook-tree/')
}

export function createNotebookFolder(title, parentId = null) {
    const payload = { title }
    if (parentId != null) {
        payload.parent_id = parentId
    }
    return apiPost('/api/notebook-folders/', payload)
}

export function renameNotebookFolder(folderId, title) {
    return apiPatch(`/api/notebook-folders/${folderId}/`, { title })
}

export function deleteNotebookFolder(folderId) {
    return apiDelete(`/api/notebook-folders/${folderId}/`)
}

export function moveNotebookFolder(folderId, parentId = null) {
    const payload = { parent_id: parentId }
    return apiPatch(`/api/notebook-folders/${folderId}/move/`, payload)
}

export function moveNotebookToFolder(notebookId, folderId = null) {
    const payload = { folder_id: folderId }
    return apiPatch(`/api/notebooks/${notebookId}/move/`, payload)
}

export function importNotebookFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    return apiPost('/backend/notebook/import/', formData)
}

export function getNotebookExportUrl(notebookId) {
    return `/backend/notebook/${notebookId}/export/`
}

function parseFilenameFromDisposition(disposition, fallback = 'notebooks_export.zip') {
    if (!disposition) return fallback

    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
    if (utf8Match && utf8Match[1]) {
        try {
            return decodeURIComponent(utf8Match[1].replace(/["']/g, '').trim())
        } catch (_) {
            // fall through
        }
    }

    const simpleMatch = disposition.match(/filename="?([^";]+)"?/i)
    if (simpleMatch && simpleMatch[1]) {
        return simpleMatch[1].trim()
    }
    return fallback
}

export async function exportNotebooksArchive({ notebookIds = [], folderIds = [] } = {}) {
    const csrftoken = await ensureCsrfToken()
    const res = await fetch('/backend/notebooks/export/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(csrftoken ? { 'X-CSRFToken': csrftoken } : {}),
        },
        credentials: 'include',
        body: JSON.stringify({
            notebook_ids: Array.isArray(notebookIds) ? notebookIds : [],
            folder_ids: Array.isArray(folderIds) ? folderIds : [],
        }),
    })

    if (!res.ok) {
        const errorText = await res.text()
        throw toApiError(res.status, errorText)
    }

    const blob = await res.blob()
    const filename = parseFilenameFromDisposition(res.headers.get('Content-Disposition'))
    return { blob, filename }
}

export async function exportNotebookFile(notebookId) {
    const res = await fetch(`/backend/notebook/${notebookId}/export/`, {
        method: 'GET',
        credentials: 'include',
    })

    if (!res.ok) {
        const errorText = await res.text()
        throw toApiError(res.status, errorText)
    }

    const blob = await res.blob()
    const filename = parseFilenameFromDisposition(
        res.headers.get('Content-Disposition'),
        `notebook_${notebookId}.ipynb`,
    )
    return { blob, filename }
}

export function getNotebook(notebookId) {
    return apiGet(`backend/notebook/${notebookId}/`)
}

export function saveCodeCell(notebookId, cellId, code, output = '') {
    return apiPost(`/backend/notebook/${notebookId}/cell/${cellId}/save_output/`, {
        code,
        output,
    })
}

export function saveTextCell(notebookId, cellId, content) {
    return apiPost(`/backend/notebook/${notebookId}/cell/${cellId}/save_text/`, {
        content,
    })
}

export function createCell(notebookId, type = 'code') {
    return apiPost(`/backend/notebook/${notebookId}/cell/new/`, { type })
}

export function deleteCell(notebookId, cellId) {
    return apiDelete(`/backend/notebook/${notebookId}/cell/${cellId}/delete/`)
}

export function moveCell(notebookId, cellId, targetPosition) {
    return apiPatch(`/backend/notebook/${notebookId}/cell/${cellId}/move/`, {
        target_position: targetPosition,
    })
}

export function renameNotebook(notebookId, title) {
    return apiPost(`/backend/notebook/${notebookId}/rename/`, { title })
}

export function deleteNotebook(notebookId) {
    return apiPost(
        `/backend/notebook/${notebookId}/delete/`,
        {},
        { headers: { 'X-Requested-With': 'XMLHttpRequest' } },
    )
}

export function getNotebookSessionId(notebookId) {
    return `notebook:${notebookId}`
}

export function startNotebookSession(notebookId) {
    return apiPost('/api/sessions/notebook/', {
        notebook_id: notebookId,
    })
}

export function resetNotebookSession(sessionId) {
    return apiPost('/api/sessions/reset/', {
        session_id: sessionId,
    })
}

export function stopNotebookSession(sessionId) {
    return apiPost('/api/sessions/stop/', {
        session_id: sessionId,
    })
}

export function getNotebookSessionFiles(sessionId) {
    return apiGet('/api/sessions/files/', {
        session_id: sessionId,
    })
}

export function runNotebookCell(sessionId, cellId) {
    return apiPost('/api/cells/run/', {
        session_id: sessionId,
        cell_id: cellId,
    })
}

export function uploadNotebookSessionFile(sessionId, file, path = '') {
    const formData = new FormData()
    formData.append('session_id', sessionId)
    formData.append('file', file)
    if (path) {
        formData.append('path', path)
    }
    return apiPost('/api/sessions/files/upload/', formData)
}

export function deleteNotebookSessionFile(sessionId, path) {
    return apiDelete('/api/sessions/file/', {
        session_id: sessionId,
        path,
    })
}

export function getNotebookSessionFileDownloadUrl(sessionId, path) {
    const query = new URLSearchParams({
        session_id: sessionId,
        path,
    })
    return `/api/sessions/file/?${query.toString()}`
}

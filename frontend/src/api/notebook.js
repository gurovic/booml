import { apiDelete, apiGet, apiPatch, apiPost } from './http'

export function createNotebook(problemId) {
    return apiPost('/api/notebooks/', { problem_id: problemId })
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

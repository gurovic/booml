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

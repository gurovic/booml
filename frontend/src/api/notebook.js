import { apiGet, apiPost } from './http'

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

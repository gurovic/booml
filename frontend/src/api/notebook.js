import { apiGet, apiPost } from './http'

export function createNotebook(problemId) {
    return apiPost('/api/notebooks/', { problem_id: problemId })
}

export function getNotebook(notebookId) {
    return apiGet(`backend/notebook/${notebookId}/`)
}

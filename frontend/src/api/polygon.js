import { apiGet, apiPost, apiPut } from './http'

export function getPolygonProblems(params = {}) {
    return apiGet('backend/polygon/problems', params)
}

export function createPolygonProblem(data) {
    return apiPost('backend/polygon/problems/create', data)
}

export function getPolygonProblem(problemId) {
    return apiGet(`backend/polygon/problems/${problemId}`)
}

export function updatePolygonProblem(problemId, data) {
    return apiPut(`backend/polygon/problems/${problemId}/update`, data)
}

export function uploadPolygonProblemFiles(problemId, formData) {
    return apiPost(`backend/polygon/problems/${problemId}/upload`, formData, {
        headers: {
            'Content-Type': 'multipart/form-data'
        }
    })
}

export function publishPolygonProblem(problemId) {
    return apiPost(`backend/polygon/problems/${problemId}/publish`)
}

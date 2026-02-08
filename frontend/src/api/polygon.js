import { apiGet, apiPost } from './http'

export function getPolygonProblems() {
    return apiGet('backend/polygon/problems')
}

export function createPolygonProblem(data) {
    return apiPost('backend/polygon/problems/create', data)
}

import { apiGet, apiPost } from './http'

export function getPolygonProblems(params = {}) {
    return apiGet('backend/polygon/problems', params)
}

export function createPolygonProblem(data) {
    return apiPost('backend/polygon/problems/create', data)
}

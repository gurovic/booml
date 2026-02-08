import { apiGet, apiPost } from './http'

export function getPolygonProblems() {
    return apiGet('backend/polygon/problems')
}

export function createPolygonProblem(data) {
    return apiPost('backend/polygon/problems/create', data)
}

export async function getAllProblems() {
    try {
        return await apiGet('backend/polygon/problems')
    } catch (err) {
        console.error('Failed to load problems.', err)
        throw err
    }
}

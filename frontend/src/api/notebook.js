import { apiPost } from './http'

export function createNotebook(problemId) {
    return apiPost('api/notebooks/', { problem_id: problemId })
}

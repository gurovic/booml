import { apiGet } from './http'

export function getProblem(problemId) {
    return apiGet('backend/problem', {problem_id: problemId})
}

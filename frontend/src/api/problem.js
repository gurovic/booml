import { apiGet } from './http'

export function getProblem(problemId) {
    return apiGet('/problem', {problem_id: problemId})
}

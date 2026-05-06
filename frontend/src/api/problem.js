import { apiGet } from './http'

export function getProblem(problemId, options = {}) {
  const params = { problem_id: problemId }
  const contestId = options?.contestId
  if (contestId != null && contestId !== '') {
    params.contest_id = contestId
  }
  return apiGet('backend/problem', params)
}

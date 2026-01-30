import { apiGet, apiPost } from './http'

/**
 * Get list of problems created by current user
 * @returns {Promise<Array>} List of problems
 */
export async function getPolygonProblems() {
  return apiGet('api/polygon/problems/')
}

/**
 * Create a new problem
 * @param {Object} data - Problem data
 * @param {string} data.title - Problem title
 * @param {number} data.rating - Problem rating (optional, defaults to 800)
 * @returns {Promise<Object>} Created problem
 */
export async function createPolygonProblem(data) {
  return apiPost('/api/polygon/problems/create/', data)
}

import { apiGet } from '../http'

export async function getCourses() {
  const data = await apiGet('api/courses/tree/')
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  return []
}

export async function getCourse(courseId) {
  if (courseId == null || courseId === '') {
    return null
  }
  return await apiGet(`backend/course/${courseId}/`)
}

export async function getCourseLeaderboard(courseId) {
  if (courseId == null || courseId === '') {
    return null
  }
  return await apiGet(`course/${courseId}/leaderboard/`)
}

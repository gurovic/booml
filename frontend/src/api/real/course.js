import { apiGet, apiPost } from '../http'

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

export async function getMyCourses(params = {}) {
  return await apiGet('api/courses/my/', params)
}

export async function pinCourse(courseId, position) {
  const data = { course_id: courseId }
  if (position !== undefined) data.position = position
  return await apiPost('api/courses/pin/', data)
}

export async function unpinCourse(courseId) {
  return await apiPost('api/courses/unpin/', { course_id: courseId })
}

export async function reorderPins(courseIds) {
  return await apiPost('api/courses/pins/reorder/', { course_ids: courseIds })
}

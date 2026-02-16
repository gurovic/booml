import { apiGet, apiPost } from '../http'

export async function getHomeSidebar() {
  return await apiGet('api/home/sidebar/')
}

export async function addFavoriteCourse(courseId) {
  return await apiPost('api/favorites/courses/add/', { course_id: courseId })
}

export async function removeFavoriteCourse(courseId) {
  return await apiPost('api/favorites/courses/remove/', { course_id: courseId })
}

export async function reorderFavoriteCourses(courseIds = []) {
  return await apiPost('api/favorites/courses/reorder/', { course_ids: courseIds })
}


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

export async function createCourse({ title, section_id, description = '', is_open = false } = {}) {
  return await apiPost('api/courses/', {
    title,
    description,
    is_open,
    section_id,
    teacher_ids: [],
    student_ids: [],
  })
}

export async function createSection({ title, parent_id = null, description = '' } = {}) {
  return await apiPost('api/sections/', {
    title,
    description,
    parent_id,
  })
}

export async function updateCourse(courseId, data) {
  return await apiPost(`backend/course/${courseId}/update/`, data)
}

export async function deleteCourse(courseId) {
  return await apiPost(`backend/course/${courseId}/delete/`, {})
}

export async function updateCourseParticipants(courseId, { teacherUsernames = [], studentUsernames = [], allowRoleUpdate = true } = {}) {
  return await apiPost(`backend/course/${courseId}/participants/update/`, {
    teacher_usernames: teacherUsernames,
    student_usernames: studentUsernames,
    allow_role_update: allowRoleUpdate,
  })
}

export async function removeCourseParticipants(courseId, usernames = []) {
  return await apiPost(`backend/course/${courseId}/participants/remove/`, { usernames })
}

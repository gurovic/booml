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

export async function createCourse({ title, section_id, description = '', is_open = false, is_published = true } = {}) {
  return await apiPost('api/courses/', {
    title,
    description,
    is_open,
    is_published,
    section_id,
    teacher_ids: [],
    student_ids: [],
  })
}

export async function createSection({ title, parent_id = null, description = '', is_published = true } = {}) {
  return await apiPost('api/sections/', {
    title,
    description,
    is_published,
    parent_id,
  })
}

export async function updateSection(sectionId, data) {
  return await apiPost(`api/sections/${sectionId}/update/`, data)
}

export async function deleteSection(sectionId) {
  return await apiPost(`api/sections/${sectionId}/delete/`, {})
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

export async function reorderCourseContests(courseId, contestIds = []) {
  return await apiPost(`backend/course/${courseId}/contests/reorder/`, { contest_ids: contestIds })
}

export async function browseCourses({ tab = 'mine', q = '', page = 1, page_size = 10 } = {}) {
  const params = {
    tab,
    q,
    page,
    page_size,
  }
  return await apiGet('api/courses/browse/', params)
}

export async function getCourseLeaderboard(courseId) {
  return await apiGet(`backend/course/${courseId}/leaderboard/`)
}

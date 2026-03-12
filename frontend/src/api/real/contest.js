import { apiGet, apiPost } from '../http'

export async function getContestsByCourse(courseId) {
  const params = {}
  if (courseId != null) {
    params.course_id = courseId
  }

  const data = await apiGet('backend/contest/', params)
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  return []
}

export async function getContest(contestId) {
  if (contestId == null || contestId === '') {
    return null
  }
  try {
    return await apiGet(`backend/contest/${contestId}/`)
  } catch (err) {
    console.error('Failed to load contest.', err)
    throw err
  }
}

export async function getContestLeaderboard(contestId) {
  if (contestId == null || contestId === '') {
    return null
  }
  try {
    return await apiGet(`backend/contest/${contestId}/leaderboard/`)
  } catch (err) {
    console.error('Failed to load contest leaderboard.', err)
    throw err
  }
}

export async function createContest(courseId, contestData) {
  try {
    // Use /backend/* so Vue devServer proxy forwards to Django backend.
    return await apiPost(`backend/contest/${courseId}/new/`, contestData)
  } catch (err) {
    console.error('Failed to create contest.', err)
    throw err
  }
}

export async function getContestSubmissions(contestId, options = {}) {
  if (contestId == null || contestId === '') {
    return null
  }
  const {
    page = 1,
    pageSize = 20,
    ...filters
  } = options
  const params = {}
  if (page != null) params.page = page
  if (pageSize != null) params.page_size = pageSize
  const allowedFilterKeys = [
    'problem_id',
    'user_id',
    'status',
    'q',
    'submitted_from',
    'submitted_to',
    'has_file',
  ]
  for (const key of allowedFilterKeys) {
    const value = filters[key]
    if (value === null || value === undefined || value === '') continue
    params[key] = value
  }
  try {
    return await apiGet(`backend/contest/${contestId}/submissions/`, params)
  } catch (err) {
    console.error('Failed to load contest submissions.', err)
    throw err
  }
}

export async function addProblemToContest(contestId, problemId) {
  try {
    // Use /backend/* so Vue devServer proxy forwards to Django backend.
    return await apiPost(`backend/contest/${contestId}/problems/add/`, { problem_id: problemId })
  } catch (err) {
    console.error('Failed to add problem to contest.', err)
    throw err
  }
}

export async function bulkAddProblemsToContest(contestId, problemIds = []) {
  try {
    return await apiPost(`backend/contest/${contestId}/problems/bulk_add/`, { problem_ids: problemIds })
  } catch (err) {
    console.error('Failed to bulk add problems to contest.', err)
    throw err
  }
}

export async function reorderContestProblems(contestId, problemIds = []) {
  try {
    return await apiPost(`backend/contest/${contestId}/problems/reorder/`, { problem_ids: problemIds })
  } catch (err) {
    console.error('Failed to reorder contest problems.', err)
    throw err
  }
}

export async function removeProblemFromContest(contestId, problemId) {
  try {
    return await apiPost(`backend/contest/${contestId}/problems/remove/`, { problem_id: problemId })
  } catch (err) {
    console.error('Failed to remove problem from contest.', err)
    throw err
  }
}

export async function deleteContest(contestId) {
  try {
    return await apiPost(`backend/contest/${contestId}/delete/`, {})
  } catch (err) {
    console.error('Failed to delete contest.', err)
    throw err
  }
}

export async function updateContest(contestId, contestData) {
  try {
    return await apiPost(`backend/contest/${contestId}/update/`, contestData)
  } catch (err) {
    console.error('Failed to update contest.', err)
    throw err
  }
}

export async function updateContestQuestionSettings(contestId, payload = {}) {
  try {
    return await apiPost(`backend/contest/${contestId}/questions/`, payload)
  } catch (err) {
    console.error('Failed to update contest question settings.', err)
    throw err
  }
}

export async function getContestNotifications(contestId, options = {}) {
  if (contestId == null || contestId === '') {
    return {
      items: [],
      unread_count: 0,
      participants: [],
      can_manage: false,
      notifications_enabled: true,
      questions_enabled: true,
    }
  }
  const params = {}
  if (options.limit != null) params.limit = options.limit
  try {
    return await apiGet(`backend/contest/${contestId}/notifications/`, params)
  } catch (err) {
    console.error('Failed to load contest notifications.', err)
    throw err
  }
}

export async function sendContestNotification(contestId, payload = {}) {
  try {
    return await apiPost(`backend/contest/${contestId}/notifications/send/`, payload)
  } catch (err) {
    console.error('Failed to send contest notification.', err)
    throw err
  }
}

export async function askContestQuestion(contestId, payload = {}) {
  try {
    return await apiPost(`backend/contest/${contestId}/notifications/ask/`, payload)
  } catch (err) {
    console.error('Failed to ask contest question.', err)
    throw err
  }
}

export async function answerContestQuestion(contestId, questionId, payload = {}) {
  try {
    return await apiPost(`backend/contest/${contestId}/notifications/${questionId}/answer/`, payload)
  } catch (err) {
    console.error('Failed to answer contest question.', err)
    throw err
  }
}

export async function markContestNotificationsRead(contestId, notificationIds = null) {
  const payload = {}
  if (Array.isArray(notificationIds)) {
    payload.notification_ids = notificationIds
  }
  try {
    return await apiPost(`backend/contest/${contestId}/notifications/read/`, payload)
  } catch (err) {
    console.error('Failed to mark contest notifications as read.', err)
    throw err
  }
}

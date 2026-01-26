import { apiGet } from '../http'

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

const mockContests = {
  111: [
    { id: 1001, title: "Базовый контест по линейной регрессии", problems_count: 5, allow_notifications: true, allow_student_questions: true },
    { id: 1002, title: "Градиентный спуск на практике", problems_count: 4, allow_notifications: true, allow_student_questions: true },
  ],
  121: [
    { id: 1003, title: "Метрики классификации", problems_count: 6, allow_notifications: true, allow_student_questions: true },
    { id: 1004, title: "Оптимизация гиперпараметров", problems_count: 5, allow_notifications: true, allow_student_questions: true },
  ],
  21: [
    { id: 1005, title: "Основы статистики", problems_count: 5, allow_notifications: true, allow_student_questions: true },
  ],
}

const mockLeaderboards = {
  1001: {
    overall_leaderboard: {
      scoring: "ioi",
      problems_count: 5,
      entries: [
        { user_id: 1, username: "alice", rank: 1, solved_count: 5, total_score: 4.25 },
        { user_id: 2, username: "bob", rank: 2, solved_count: 4, total_score: 3.8 },
        { user_id: 3, username: "charlie", rank: 3, solved_count: 2, total_score: 1.5 },
        { user_id: 4, username: "diana", rank: null, solved_count: 0, total_score: null },
      ],
    },
    leaderboards: [
      {
        problem_id: 101,
        problem_title: "Linear Regression",
        metric: "rmse",
        entries: [
          { user_id: 1, username: "alice", best_metric: 0.21 },
          { user_id: 2, username: "bob", best_metric: 0.33 },
          { user_id: 3, username: "charlie", best_metric: 0.75 },
          { user_id: 4, username: "diana", best_metric: null },
        ],
      },
      {
        problem_id: 102,
        problem_title: "Gradient Descent",
        metric: "rmse",
        entries: [
          { user_id: 1, username: "alice", best_metric: 0.19 },
          { user_id: 2, username: "bob", best_metric: 0.28 },
          { user_id: 3, username: "charlie", best_metric: null },
          { user_id: 4, username: "diana", best_metric: null },
        ],
      },
      {
        problem_id: 103,
        problem_title: "Regularization",
        metric: "rmse",
        entries: [
          { user_id: 1, username: "alice", best_metric: 0.24 },
          { user_id: 2, username: "bob", best_metric: 0.3 },
          { user_id: 3, username: "charlie", best_metric: null },
          { user_id: 4, username: "diana", best_metric: null },
        ],
      },
    ],
  },
  1002: {
    overall_leaderboard: {
      scoring: "icpc",
      problems_count: 4,
      entries: [
        { user_id: 10, username: "eva", rank: 1, solved_count: 4, penalty_minutes: 90, total_score: 4 },
        { user_id: 11, username: "frank", rank: 2, solved_count: 3, penalty_minutes: 120, total_score: 3 },
        { user_id: 12, username: "gwen", rank: 3, solved_count: 1, penalty_minutes: 35, total_score: 1 },
        { user_id: 13, username: "hank", rank: null, solved_count: 0, penalty_minutes: null, total_score: null },
      ],
    },
    leaderboards: [
      {
        problem_id: 201,
        problem_title: "Warmup",
        metric: "accuracy",
        entries: [
          { user_id: 10, username: "eva", best_metric: 0.98 },
          { user_id: 11, username: "frank", best_metric: 0.92 },
          { user_id: 12, username: "gwen", best_metric: 0.75 },
          { user_id: 13, username: "hank", best_metric: null },
        ],
      },
      {
        problem_id: 202,
        problem_title: "Optimization",
        metric: "accuracy",
        entries: [
          { user_id: 10, username: "eva", best_metric: 0.96 },
          { user_id: 11, username: "frank", best_metric: 0.9 },
          { user_id: 12, username: "gwen", best_metric: null },
          { user_id: 13, username: "hank", best_metric: null },
        ],
      },
    ],
  },
}

const mockContestSubmissions = {
  1001: [
    {
      id: 501,
      user_id: 1,
      username: 'alice',
      problem_id: 101,
      problem_title: 'Linear Regression',
      problem_label: 'A',
      submitted_at: new Date().toISOString(),
      status: 'accepted',
      metrics: { score: 95.2 },
      score: 95.2,
      file_url: '/media/submissions/alice_501.csv',
      file_name: 'alice_501.csv',
      is_csv_file: true,
    },
    {
      id: 502,
      user_id: 2,
      username: 'bob',
      problem_id: 102,
      problem_title: 'Gradient Descent',
      problem_label: 'B',
      submitted_at: new Date(Date.now() - 3600 * 1000).toISOString(),
      status: 'failed',
      metrics: {},
      score: null,
      file_url: '/media/submissions/bob_502.csv',
      file_name: 'bob_502.csv',
      is_csv_file: true,
    },
  ],
}

const mockContestParticipants = {
  1001: [
    { id: 201, username: 'student_alpha' },
    { id: 202, username: 'student_beta' },
    { id: 203, username: 'student_gamma' },
  ],
}

const mockContestNotifications = {
  1001: [
    {
      id: 9001,
      kind: 'announcement',
      audience: 'all_participants',
      audience_label: 'Всем участникам',
      text: 'Добро пожаловать в контест! Удачи всем.',
      created_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
      author: { id: 1, username: 'teacher' },
      parent_id: null,
      parent_author_id: null,
      is_read: false,
      recipient_count: 3,
      recipient_ids: [201, 202, 203],
      recipient_usernames: ['student_alpha', 'student_beta', 'student_gamma'],
      answer_count: 0,
    },
  ],
}

let mockNotificationSeq = 10000

const nextNotificationId = () => {
  mockNotificationSeq += 1
  return mockNotificationSeq
}

const STATUS_OPTIONS = [
  { value: 'pending', label: '⏳ В очереди' },
  { value: 'running', label: '🏃 Выполняется' },
  { value: 'accepted', label: '✅ Протестировано' },
  { value: 'failed', label: '❌ Ошибка' },
  { value: 'validation_error', label: '⚠️ Ошибка валидации' },
  { value: 'validated', label: '✅ Валидировано' },
]

const buildProblems = (contest) => {
  const count = Number(contest?.problems_count ?? 0)
  if (!count) return []
  const baseId = Number(contest.id) * 100
  return Array.from({ length: count }, (_, index) => ({
    id: baseId + index + 1,
    title: `Problem ${index + 1}`,
  }))
}

export function getContestsByCourse(courseId) {
  const key = Number(courseId)
  return Promise.resolve(mockContests[key] ?? [])
}

const findMockContestById = (contestId) => {
  const numericId = Number(contestId)
  return Object.values(mockContests).flat().find(item => Number(item.id) === numericId) || null
}

const isNotificationsEnabled = (contestId) => {
  const contest = findMockContestById(contestId)
  if (!contest) return true
  return contest.allow_notifications !== false
}

const isStudentQuestionsEnabled = (contestId) => {
  const contest = findMockContestById(contestId)
  if (!contest) return true
  return contest.allow_notifications !== false && contest.allow_student_questions !== false
}

export function getContest(contestId) {
  const numericId = Number(contestId)
  const found = findMockContestById(numericId)
  if (!found) return Promise.resolve(null)
  const problems = Array.isArray(found.problems) ? found.problems : buildProblems(found)
  return Promise.resolve({
    ...found,
    allow_notifications: found.allow_notifications !== false,
    allow_student_questions: found.allow_student_questions !== false,
    problems,
    can_manage: true,
    can_edit: true,
  })
}

export function getContestLeaderboard(contestId) {
  const numericId = Number(contestId)
  const data = mockLeaderboards[numericId]
  if (!data) return Promise.resolve(null)
  return Promise.resolve({
    contest_id: numericId,
    leaderboards: data.leaderboards || [],
    overall_leaderboard: data.overall_leaderboard || null,
  })
}

export async function createContest(courseId, contestData) {
  // Mock contest creation
  const newContestId = Date.now()
  const newContest = {
    id: newContestId,
    title: contestData.title,
    description: contestData.description,
    course: courseId,
    has_time_limit: !!contestData.has_time_limit,
    start_time: contestData.start_time || null,
    end_time: contestData.end_time || null,
    allow_upsolving: !!contestData.allow_upsolving,
    allow_notifications: contestData.allow_notifications !== false,
    allow_student_questions:
      contestData.allow_notifications === false
        ? false
        : contestData.allow_student_questions !== false,
    time_state: contestData.has_time_limit ? 'not_started' : 'always_open',
    is_published: contestData.is_published || false,
    is_rated: contestData.is_rated || false,
    scoring: contestData.scoring || 'ioi',
    problems_count: 0,
    can_manage: true,
    can_edit: true,
  }
  
  // Add to mock data
  const key = Number(courseId)
  if (!mockContests[key]) {
    mockContests[key] = []
  }
  mockContests[key].push(newContest)
  
  return Promise.resolve(newContest)
}

export async function addProblemToContest(contestId, problemId) {
  // Mock adding problem to contest
  return Promise.resolve({
    contest: contestId,
    problem: {
      id: problemId,
      title: `Problem ${problemId}`,
    },
    added: true,
    problems_count: 1,
  })
}

export function getContestSubmissions(contestId, options = {}) {
  const {
    page = 1,
    pageSize = 20,
    problem_id = '',
    user_id = '',
    status = '',
    q = '',
    submitted_from = '',
    submitted_to = '',
    has_file = '',
  } = options
  const numericId = Number(contestId)
  const allRows = mockContestSubmissions[numericId] || []
  const problemOptions = Array.from(
    new Map(
      allRows
        .filter(row => row.problem_id != null)
        .map(row => [row.problem_id, {
          id: row.problem_id,
          title: row.problem_title || `Задача ${row.problem_id}`,
          label: row.problem_label || '',
        }])
    ).values()
  )
  const studentOptions = Array.from(
    new Map(
      allRows
        .filter(row => row.user_id != null)
        .map(row => [row.user_id, {
          id: row.user_id,
          username: row.username || `user_${row.user_id}`,
        }])
    ).values()
  )

  const searchNeedle = String(q || '').trim().toLowerCase()
  const parsedProblemId = Number(problem_id)
  const parsedUserId = Number(user_id)
  const fromTs = submitted_from ? new Date(submitted_from).getTime() : null
  const toTs = submitted_to ? new Date(submitted_to).getTime() : null
  const hasFileEnabled = String(has_file).toLowerCase() === 'true'

  const filteredRows = allRows.filter((row) => {
    if (problem_id !== '' && Number.isFinite(parsedProblemId) && row.problem_id !== parsedProblemId) {
      return false
    }
    if (user_id !== '' && Number.isFinite(parsedUserId) && row.user_id !== parsedUserId) {
      return false
    }
    if (status && row.status !== status) {
      return false
    }
    if (hasFileEnabled && !row.file_url) {
      return false
    }

    if (fromTs != null || toTs != null) {
      const submittedTs = row.submitted_at ? new Date(row.submitted_at).getTime() : null
      if (submittedTs == null || Number.isNaN(submittedTs)) {
        return false
      }
      if (fromTs != null && !Number.isNaN(fromTs) && submittedTs < fromTs) {
        return false
      }
      if (toTs != null && !Number.isNaN(toTs) && submittedTs > toTs) {
        return false
      }
    }

    if (searchNeedle) {
      const haystack = [
        String(row.id || ''),
        String(row.username || ''),
        String(row.problem_title || ''),
      ].join(' ').toLowerCase()
      if (!haystack.includes(searchNeedle)) {
        return false
      }
    }

    return true
  })

  const safePageSize = Math.max(1, Number(pageSize) || 20)
  const safePage = Math.max(1, Number(page) || 1)
  const offset = (safePage - 1) * safePageSize
  const slice = filteredRows.slice(offset, offset + safePageSize)
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / safePageSize))
  return Promise.resolve({
    count: filteredRows.length,
    page: safePage,
    page_size: safePageSize,
    total_pages: totalPages,
    next: safePage < totalPages ? safePage + 1 : null,
    previous: safePage > 1 ? safePage - 1 : null,
    results: slice,
    filters: {
      problems: problemOptions,
      students: studentOptions,
      statuses: STATUS_OPTIONS,
    },
  })
}

export async function bulkAddProblemsToContest(contestId, problemIds = []) {
  return Promise.resolve({
    contest: contestId,
    added_ids: problemIds || [],
    already_present_ids: [],
    problems_count: (problemIds || []).length,
  })
}

export async function reorderContestProblems(contestId, problemIds = []) {
  return Promise.resolve({
    contest: contestId,
    problem_ids: problemIds || [],
    problems_count: (problemIds || []).length,
  })
}

export async function removeProblemFromContest(contestId, problemId) {
  // Mock remove: no-op success.
  return Promise.resolve({
    contest: contestId,
    removed_ids: [Number(problemId)],
    problem_ids: [],
    problems_count: 0,
  })
}

export async function deleteContest(contestId) {
  const numericId = Number(contestId)
  let deleted = false

  for (const key of Object.keys(mockContests)) {
    const list = mockContests[key] || []
    const next = list.filter(item => Number(item.id) !== numericId)
    if (next.length !== list.length) {
      mockContests[key] = next
      deleted = true
    }
  }

  if (!deleted) {
    return Promise.reject(new Error('Contest not found'))
  }

  return Promise.resolve({ success: true, deleted_id: numericId })
}

export async function updateContest(contestId, contestData) {
  const numericId = Number(contestId)
  let updated = null

  for (const key of Object.keys(mockContests)) {
    const list = mockContests[key] || []
    const idx = list.findIndex(item => Number(item.id) === numericId)
    if (idx < 0) continue
    const next = { ...list[idx] }
    next.has_time_limit = !!contestData.has_time_limit
    next.start_time = contestData.start_time || null
    next.end_time = contestData.end_time || null
    next.allow_upsolving = !!contestData.allow_upsolving
    if (Object.prototype.hasOwnProperty.call(contestData, 'allow_notifications')) {
      next.allow_notifications = contestData.allow_notifications !== false
      if (!next.allow_notifications) {
        next.allow_student_questions = false
      }
    }
    if (Object.prototype.hasOwnProperty.call(contestData, 'allow_student_questions')) {
      next.allow_student_questions =
        next.allow_notifications === false
          ? false
          : contestData.allow_student_questions !== false
    }
    next.can_edit = true
    updated = next
    list[idx] = next
    break
  }

  if (!updated) {
    return Promise.reject(new Error('Contest not found'))
  }

  return Promise.resolve(updated)
}

export async function updateContestQuestionSettings(contestId, payload = {}) {
  const contest = findMockContestById(contestId)
  if (!contest) {
    return Promise.reject(new Error('Contest not found'))
  }
  if (Object.prototype.hasOwnProperty.call(payload, 'allow_notifications')) {
    contest.allow_notifications = payload.allow_notifications !== false
  }
  if (contest.allow_notifications === false) {
    contest.allow_student_questions = false
  } else if (Object.prototype.hasOwnProperty.call(payload, 'allow_student_questions')) {
    contest.allow_student_questions = payload.allow_student_questions !== false
  }
  return Promise.resolve({
    id: Number(contest.id),
    allow_notifications: contest.allow_notifications !== false,
    allow_student_questions:
      contest.allow_notifications !== false && contest.allow_student_questions !== false,
  })
}

export async function getContestNotifications(contestId) {
  const numericId = Number(contestId)
  const notificationsEnabled = isNotificationsEnabled(numericId)
  if (!notificationsEnabled) {
    return Promise.resolve({
      items: [],
      unread_count: 0,
      participants: [],
      can_manage: true,
      notifications_enabled: false,
      questions_enabled: false,
    })
  }
  const items = Array.isArray(mockContestNotifications[numericId])
    ? [...mockContestNotifications[numericId]]
    : []
  const questionsEnabled = isStudentQuestionsEnabled(numericId)
  const filteredItems = questionsEnabled
    ? items
    : items.filter(item => item.kind === 'announcement')
  filteredItems.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)))
  const unread_count = filteredItems.filter(item => item.is_read === false).length
  const participants = mockContestParticipants[numericId] || []
  return Promise.resolve({
    items: filteredItems,
    unread_count,
    participants,
    can_manage: true,
    notifications_enabled: notificationsEnabled,
    questions_enabled: questionsEnabled,
  })
}

export async function sendContestNotification(contestId, payload = {}) {
  const numericId = Number(contestId)
  if (!isNotificationsEnabled(numericId)) {
    return Promise.reject(new Error('Contest notifications are disabled'))
  }
  if (!mockContestNotifications[numericId]) {
    mockContestNotifications[numericId] = []
  }
  const participants = mockContestParticipants[numericId] || []
  const audience = payload.audience === 'selected' ? 'selected_participants' : 'all_participants'
  const recipient_ids = Array.isArray(payload.recipient_ids) && payload.recipient_ids.length
    ? payload.recipient_ids.map(Number).filter(Number.isFinite)
    : participants.map(row => row.id)

  const notification = {
    id: nextNotificationId(),
    kind: 'announcement',
    audience,
    audience_label: audience === 'selected_participants' ? 'Выбранным участникам' : 'Всем участникам',
    text: String(payload.text || '').trim(),
    created_at: new Date().toISOString(),
    author: { id: 1, username: 'teacher' },
    parent_id: null,
    parent_author_id: null,
    is_read: true,
    recipient_count: recipient_ids.length,
    recipient_ids,
    recipient_usernames: participants
      .filter(row => recipient_ids.includes(row.id))
      .map(row => row.username),
    answer_count: 0,
  }
  mockContestNotifications[numericId].unshift(notification)
  return Promise.resolve({ notification })
}

export async function askContestQuestion(contestId, payload = {}) {
  const numericId = Number(contestId)
  if (!isNotificationsEnabled(numericId)) {
    return Promise.reject(new Error('Contest notifications are disabled'))
  }
  if (!isStudentQuestionsEnabled(numericId)) {
    return Promise.reject(new Error('Student questions are disabled for this contest'))
  }
  if (!mockContestNotifications[numericId]) {
    mockContestNotifications[numericId] = []
  }
  const notification = {
    id: nextNotificationId(),
    kind: 'question',
    audience: 'teachers',
    audience_label: 'Преподавателям',
    text: String(payload.text || '').trim(),
    created_at: new Date().toISOString(),
    author: { id: 201, username: 'student_alpha' },
    parent_id: null,
    parent_author_id: null,
    is_read: true,
    recipient_count: 1,
    recipient_ids: [1],
    recipient_usernames: ['teacher'],
    answer_count: 0,
  }
  mockContestNotifications[numericId].unshift(notification)
  return Promise.resolve({ notification })
}

export async function answerContestQuestion(contestId, questionId, payload = {}) {
  const numericId = Number(contestId)
  if (!isNotificationsEnabled(numericId)) {
    return Promise.reject(new Error('Contest notifications are disabled'))
  }
  if (!isStudentQuestionsEnabled(numericId)) {
    return Promise.reject(new Error('Student questions are disabled for this contest'))
  }
  if (!mockContestNotifications[numericId]) {
    mockContestNotifications[numericId] = []
  }
  const question = (mockContestNotifications[numericId] || []).find(
    row => Number(row.id) === Number(questionId) && row.kind === 'question'
  )
  if (!question) {
    return Promise.reject(new Error('Question not found'))
  }

  const notification = {
    id: nextNotificationId(),
    kind: 'answer',
    audience: 'question_author',
    audience_label: 'Автору вопроса',
    text: String(payload.text || '').trim(),
    created_at: new Date().toISOString(),
    author: { id: 1, username: 'teacher' },
    parent_id: question.id,
    parent_author_id: question.author?.id ?? null,
    is_read: false,
    recipient_count: question.author?.id ? 1 : 0,
    recipient_ids: question.author?.id ? [question.author.id] : [],
    recipient_usernames: question.author?.username ? [question.author.username] : [],
    answer_count: 0,
  }
  question.answer_count = Number(question.answer_count || 0) + 1
  mockContestNotifications[numericId].unshift(notification)
  return Promise.resolve({ notification })
}

export async function markContestNotificationsRead(contestId, notificationIds = null) {
  const numericId = Number(contestId)
  const all = mockContestNotifications[numericId] || []
  const idSet = Array.isArray(notificationIds)
    ? new Set(notificationIds.map(Number).filter(Number.isFinite))
    : null

  let marked = 0
  for (const item of all) {
    if (item.is_read) continue
    if (idSet && !idSet.has(Number(item.id))) continue
    item.is_read = true
    marked += 1
  }
  const unread_count = all.filter(item => item.is_read === false).length
  return Promise.resolve({ marked, unread_count })
}

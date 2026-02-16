const mockContests = {
  111: [
    { id: 1001, title: "Базовый контест по линейной регрессии", problems_count: 5 },
    { id: 1002, title: "Градиентный спуск на практике", problems_count: 4 },
  ],
  121: [
    { id: 1003, title: "Метрики классификации", problems_count: 6 },
    { id: 1004, title: "Оптимизация гиперпараметров", problems_count: 5 },
  ],
  21: [
    { id: 1005, title: "Основы статистики", problems_count: 5 },
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

export function getContest(contestId) {
  const numericId = Number(contestId)
  const found = Object.values(mockContests).flat().find(item => item.id === numericId)
  if (!found) return Promise.resolve(null)
  const problems = Array.isArray(found.problems) ? found.problems : buildProblems(found)
  return Promise.resolve({ ...found, problems })
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
    is_published: contestData.is_published || false,
    is_rated: contestData.is_rated || false,
    scoring: contestData.scoring || 'ioi',
    problems_count: 0,
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

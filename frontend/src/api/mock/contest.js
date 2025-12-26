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

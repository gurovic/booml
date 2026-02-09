const mockFavorites = [
  { course_id: 111, title: 'Введение в нейросети', position: 0 },
  { course_id: 122, title: 'KNN', position: 1 },
]

const mockRecentProblems = [
  { problem_id: 1, title: 'A+B', last_submitted_at: new Date().toISOString(), last_score: 1.0 },
  { problem_id: 2, title: 'Linear Regression', last_submitted_at: new Date(Date.now() - 3600_000).toISOString(), last_score: 0.8732 },
]

const mockUpdates = [
  { id: 1, title: 'Обновление: Избранное', body: 'Добавили избранные курсы на главную страницу.', created_at: new Date().toISOString() },
]

export async function getHomeSidebar() {
  return Promise.resolve({
    favorites: mockFavorites,
    recent_problems: mockRecentProblems,
    updates: mockUpdates,
  })
}

export async function addFavoriteCourse(courseId) {
  const cid = Number(courseId)
  if (!Number.isFinite(cid)) return Promise.reject(new Error('Invalid course_id'))
  if (mockFavorites.some(x => Number(x.course_id) === cid)) {
    return Promise.resolve({ items: mockFavorites, added: false })
  }
  if (mockFavorites.length >= 5) {
    return Promise.reject(new Error('Favorites limit reached (max 5)'))
  }
  mockFavorites.push({ course_id: cid, title: `Course ${cid}`, position: mockFavorites.length })
  return Promise.resolve({ items: mockFavorites, added: true })
}

export async function removeFavoriteCourse(courseId) {
  const cid = Number(courseId)
  const next = mockFavorites.filter(x => Number(x.course_id) !== cid)
  next.forEach((x, idx) => { x.position = idx })
  mockFavorites.splice(0, mockFavorites.length, ...next)
  return Promise.resolve({ items: mockFavorites, removed: true })
}

export async function reorderFavoriteCourses(courseIds = []) {
  const wanted = (courseIds || []).map(Number).filter(Number.isFinite)
  const byId = new Map(mockFavorites.map(x => [Number(x.course_id), x]))
  const ordered = []
  for (const cid of wanted) {
    if (byId.has(cid)) ordered.push(byId.get(cid))
  }
  for (const x of mockFavorites) {
    if (!ordered.includes(x)) ordered.push(x)
  }
  ordered.forEach((x, idx) => { x.position = idx })
  mockFavorites.splice(0, mockFavorites.length, ...ordered)
  return Promise.resolve({ items: mockFavorites })
}

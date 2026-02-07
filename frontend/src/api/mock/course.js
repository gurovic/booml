const mockData = [
  {
    id: 1,
    title: "Тематическое",
    type: "section",
    children: [
      {
        id: 11,
        title: "NLP и текстовая классификация",
        type: "section",
        children: [
          { id: 111, title: "Aggressive Ducks", type: "course" },
          { id: 112, title: "Duck Debugging", type: "course" },
        ],
      },
      {
        id: 12,
        title: "Анализ кода и безопасность",
        type: "section",
        children: [
          { id: 121, title: "Infection", type: "course" },
          { id: 122, title: "Code Code Code", type: "course" },
        ],
      },
      {
        id: 13,
        title: "Аномалии и сети",
        type: "section",
        children: [
          { id: 131, title: "Ah Insiders", type: "course" },
        ],
      },
    ],
  },
  {
    id: 2,
    title: "Олимпиады",
    type: "section",
    children: [
      {
        id: 21,
        title: "НТО ИИ",
        type: "section",
        children: [
          { id: 211, title: "Подготовка к отбору", type: "course" },
          { id: 212, title: "Решение треков", type: "course" },
        ],
      },
      {
        id: 22,
        title: "ВСОШ",
        type: "section",
        children: [
          { id: 221, title: "Базовый трек", type: "course" },
          { id: 222, title: "Финальный тур", type: "course" },
        ],
      },
    ],
  },
  {
    id: 3,
    title: "Авторское",
    type: "section",
    children: [
      {
        id: 31,
        title: "В.М. Гуровиц",
        type: "section",
        children: [
          { id: 311, title: "Анализ данных от А до Я", type: "course" },
          { id: 312, title: "Практикум по моделям", type: "course" },
        ],
      },
    ],
  },
];

export function getCourses() {
  return new Promise(resolve => setTimeout(() => resolve(mockData), 200));
}

const flattenCourses = (nodes = []) => {
  const result = []
  nodes.forEach(node => {
    result.push(node)
    if (Array.isArray(node.children)) {
      result.push(...flattenCourses(node.children))
    }
  })
  return result
}

export function getCourse(courseId) {
  const numericId = Number(courseId)
  if (!Number.isFinite(numericId)) {
    return Promise.resolve(null)
  }
  const found = flattenCourses(mockData).find(item => item.id === numericId)
  if (!found) {
    return Promise.resolve(null)
  }
  return Promise.resolve({
    id: found.id,
    title: found.title,
    description: found.description || '',
  })
}

export function getMyCourses() {
  return Promise.resolve({ pinned: [], courses: { count: 0, results: [] } })
}

export function pinCourse() {
  return Promise.resolve({ detail: 'ok' })
}

export function unpinCourse() {
  return Promise.resolve({ detail: 'ok' })
}

export function reorderPins() {
  return Promise.resolve({ detail: 'ok' })
}

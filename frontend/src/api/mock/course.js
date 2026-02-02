const mockData = [
  {
    id: 1,
    title: "Тематические",
    children: [
      {
        id: 11,
        title: "Нейросети",
        children: [
          { id: 111, title: "Введение в нейросети" },
          { id: 112, title: "CNN на практике" },
          { id: 113, title: "RNN и последовательности" },
        ],
      },
      {
        id: 12,
        title: "Классический ML",
        children: [
          {
            id: 121,
            title: "Линейная регрессия",
            children: [
              { id: 1211, title: "Основы линейных моделей" },
              { id: 1212, title: "Градиентный спуск в регрессии" },
            ],
          },
          { id: 122, title: "KNN" },
          { id: 123, title: "Логистическая регрессия" },
        ],
      },
    ],
  },
  {
    id: 2,
    title: "Олимпиады",
    children: [
      {
        id: 21,
        title: "ВСОШ",
        children: [
          { id: 211, title: "Базовый трек" },
          { id: 212, title: "Финальный тур" },
        ],
      },
      {
        id: 22,
        title: "НТО ИИ",
        children: [
          { id: 221, title: "Подготовка к отбору" },
          { id: 222, title: "Решение треков" },
        ],
      },
      {
        id: 23,
        title: "Большие данные: ИИ",
        children: [
          { id: 231, title: "Data pipeline" },
          { id: 232, title: "ML на больших данных" },
        ],
      },
    ],
  },
  {
    id: 3,
    title: "Авторские",
    children: [
      {
        id: 31,
        title: "В.М. Гуровиц",
        children: [
          { id: 311, title: "Анализ данных от А до Я" },
          { id: 312, title: "Практикум по моделям" },
        ],
      },
      {
        id: 32,
        title: "Вадим",
        children: [
          { id: 321, title: "ML интенсив" },
          { id: 322, title: "Компьютерное зрение" },
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

export function getSection(sectionId) {
  const numericId = Number(sectionId)
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
    children: found.children || [],
    type: 'section',
  })
}

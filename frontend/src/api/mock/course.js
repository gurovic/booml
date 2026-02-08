const mockData = [
  {
    id: 1,
    title: "Тематические",
    type: "section",
    is_root: true,
    parent_id: null,
    owner_id: 1,
    owner_username: "owner",
    children: [
      {
        id: 11,
        title: "Нейросети",
        type: "section",
        is_root: false,
        parent_id: 1,
        owner_id: 1,
        owner_username: "owner",
        children: [
          { id: 111, title: "Введение в нейросети", type: "course" },
          { id: 112, title: "CNN на практике", type: "course" },
          { id: 113, title: "RNN и последовательности", type: "course" },
        ],
      },
      {
        id: 12,
        title: "Классический ML",
        type: "section",
        is_root: false,
        parent_id: 1,
        owner_id: 1,
        owner_username: "owner",
        children: [
          {
            id: 121,
            title: "Линейная регрессия",
            type: "section",
            is_root: false,
            parent_id: 12,
            owner_id: 1,
            owner_username: "owner",
            children: [
              { id: 1211, title: "Основы линейных моделей", type: "course" },
              { id: 1212, title: "Градиентный спуск в регрессии", type: "course" },
            ],
          },
          { id: 122, title: "KNN", type: "course" },
          { id: 123, title: "Логистическая регрессия", type: "course" },
        ],
      },
    ],
  },
  {
    id: 2,
    title: "Олимпиады",
    type: "section",
    is_root: true,
    parent_id: null,
    owner_id: 1,
    owner_username: "owner",
    children: [
      {
        id: 21,
        title: "ВСОШ",
        type: "section",
        is_root: false,
        parent_id: 2,
        owner_id: 1,
        owner_username: "owner",
        children: [
          { id: 211, title: "Базовый трек", type: "course" },
          { id: 212, title: "Финальный тур", type: "course" },
        ],
      },
      {
        id: 22,
        title: "НТО ИИ",
        type: "section",
        is_root: false,
        parent_id: 2,
        owner_id: 1,
        owner_username: "owner",
        children: [
          { id: 221, title: "Подготовка к отбору", type: "course" },
          { id: 222, title: "Решение треков", type: "course" },
        ],
      },
      {
        id: 23,
        title: "Большие данные: ИИ",
        type: "section",
        is_root: false,
        parent_id: 2,
        owner_id: 1,
        owner_username: "owner",
        children: [
          { id: 231, title: "Data pipeline", type: "course" },
          { id: 232, title: "ML на больших данных", type: "course" },
        ],
      },
    ],
  },
  {
    id: 3,
    title: "Авторские",
    type: "section",
    is_root: true,
    parent_id: null,
    owner_id: 1,
    owner_username: "owner",
    children: [
      {
        id: 31,
        title: "В.М. Гуровиц",
        type: "section",
        is_root: false,
        parent_id: 3,
        owner_id: 1,
        owner_username: "owner",
        children: [
          { id: 311, title: "Анализ данных от А до Я", type: "course" },
          { id: 312, title: "Практикум по моделям", type: "course" },
        ],
      },
      {
        id: 32,
        title: "Вадим",
        type: "section",
        is_root: false,
        parent_id: 3,
        owner_id: 1,
        owner_username: "owner",
        children: [
          { id: 321, title: "ML интенсив", type: "course" },
          { id: 322, title: "Компьютерное зрение", type: "course" },
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
    is_open: true,
    owner_id: 1,
    owner_username: 'owner',
    can_create_contest: true,
    can_manage_course: true,
    participants: [
      { id: 1, username: 'owner', role: 'teacher', is_owner: true },
      { id: 2, username: 'teacher2', role: 'teacher', is_owner: false },
      { id: 3, username: 'student', role: 'student', is_owner: false },
    ],
  })
}

export function createCourse(payload) {
  const id = Date.now()
  return Promise.resolve({ id, ...payload })
}

export function createSection(payload) {
  const id = Date.now()
  return Promise.resolve({ id, ...payload })
}

export function updateCourse(courseId, data) {
  return Promise.resolve({ id: Number(courseId), ...data })
}

export function deleteCourse(courseId) {
  return Promise.resolve({ success: true, deleted_id: Number(courseId) })
}

export function updateCourseParticipants(courseId, payload) {
  return Promise.resolve({ course_id: Number(courseId), ...payload, created: [], updated: [] })
}

export function removeCourseParticipants(courseId, usernames) {
  return Promise.resolve({ course_id: Number(courseId), removed: usernames || [] })
}

export function reorderCourseContests(courseId, contestIds) {
  return Promise.resolve({ course_id: Number(courseId), contest_ids: contestIds || [] })
}

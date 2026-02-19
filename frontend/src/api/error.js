const FIELD_LABELS = {
  title: 'Название',
  description: 'Описание',
  parent_id: 'Раздел',
  section_id: 'Раздел',
  course_id: 'Курс',
  course_ids: 'Курсы',
  teacher_ids: 'Преподаватели',
  student_ids: 'Студенты',
}

const KNOWN_MESSAGE_RULES = [
  {
    test: /Only section owner or assigned teacher can create nested sections/i,
    text: 'Создавать подразделы здесь может только владелец раздела или назначенный преподаватель.',
  },
  {
    test: /Only section owner or assigned teacher can create courses in this section/i,
    text: 'Создавать курсы здесь может только владелец раздела или назначенный преподаватель.',
  },
  {
    test: /Only teachers can create sections in root categories/i,
    text: 'Создавать подразделы в главных разделах могут только преподаватели.',
  },
  {
    test: /Only teachers can create courses in root sections/i,
    text: 'Создавать курсы в главных разделах могут только преподаватели.',
  },
  {
    test: /Only course owner can manage course participants/i,
    text: 'Управлять участниками курса может только владелец курса.',
  },
  {
    test: /Root section with this title already exists/i,
    text: 'Раздел с таким названием уже существует.',
  },
  {
    test: /Root section title must be one of/i,
    text: 'Для главного раздела выбрано недопустимое название.',
  },
  {
    test: /Favorites limit/i,
    text: 'Лимит избранного: максимум 5 курсов.',
  },
  {
    test: /Authentication credentials were not provided/i,
    text: 'Нужно войти в систему.',
  },
  {
    test: /You do not have permission to perform this action/i,
    text: 'Недостаточно прав для этого действия.',
  },
  {
    test: /^Not found\.?$/i,
    text: 'Запрошенные данные не найдены.',
  },
  {
    test: /This field is required/i,
    text: 'Заполните обязательное поле.',
  },
  {
    test: /This field may not be blank/i,
    text: 'Поле не может быть пустым.',
  },
  {
    test: /A valid integer is required/i,
    text: 'Укажите корректное число.',
  },
  {
    test: /must be an integer/i,
    text: 'Укажите корректное число.',
  },
  {
    test: /must contain integers/i,
    text: 'Список должен содержать только числа.',
  },
  {
    test: /must be a non-empty list/i,
    text: 'Список не может быть пустым.',
  },
]

function parseJsonMaybe(text) {
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch (_) {
    return null
  }
}

function normalizeText(text) {
  return String(text || '').replace(/\s+/g, ' ').trim()
}

function extractFirstMessage(value) {
  if (value == null) return ''
  if (typeof value === 'string') return normalizeText(value)
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)

  if (Array.isArray(value)) {
    for (const item of value) {
      const msg = extractFirstMessage(item)
      if (msg) return msg
    }
    return ''
  }

  if (typeof value === 'object') {
    const priorityKeys = ['detail', 'message', 'error', 'errors', 'non_field_errors']
    for (const key of priorityKeys) {
      if (!(key in value)) continue
      const msg = extractFirstMessage(value[key])
      if (msg) return msg
    }

    for (const key of Object.keys(value)) {
      const msg = extractFirstMessage(value[key])
      if (!msg) continue
      const fieldLabel = FIELD_LABELS[key]
      return fieldLabel ? `${fieldLabel}: ${msg}` : msg
    }
  }

  return ''
}

function mapKnownMessage(message) {
  const normalized = normalizeText(message)
  if (!normalized) return ''

  for (const rule of KNOWN_MESSAGE_RULES) {
    if (rule.test.test(normalized)) return rule.text
  }
  return normalized
}

function fallbackByStatus(status) {
  if (status === 400) return 'Проверьте корректность заполненных данных.'
  if (status === 401) return 'Нужно войти в систему.'
  if (status === 403) return 'Недостаточно прав для этого действия.'
  if (status === 404) return 'Запрошенные данные не найдены.'
  if (status === 409) return 'Конфликт данных. Обновите страницу и попробуйте снова.'
  if (status === 429) return 'Слишком много запросов. Попробуйте немного позже.'
  if (status >= 500) return 'На сервере произошла ошибка. Попробуйте позже.'
  return 'Не удалось выполнить запрос. Попробуйте снова.'
}

export function getApiErrorMessage(status, responseText = '') {
  const parsed = parseJsonMaybe(responseText)
  const rawMessage = parsed ? extractFirstMessage(parsed) : normalizeText(responseText)
  const cleaned = mapKnownMessage(rawMessage)

  if (!cleaned) return fallbackByStatus(status)

  if (/^\s*API Error\b/i.test(cleaned)) {
    return fallbackByStatus(status)
  }

  if (/^\s*[{[]/.test(cleaned)) {
    return fallbackByStatus(status)
  }

  return cleaned
}

export function toApiError(status, responseText = '') {
  const message = getApiErrorMessage(status, responseText)
  const error = new Error(message)
  error.status = status
  return error
}

<template>
  <UiHeader />
  <div class="container">
    <UiBreadcrumbs :problem="problem" :contest="breadcrumbsContest" />
  </div>
  <div class="problem">
    <div class="container">
      <div
        v-if="problem != null"
        class="problem__inner"
        :class="{ 'problem__inner--no-contest-nav': !contestIdFromQuery }"
      >
        <nav
          v-if="contestIdFromQuery"
          class="problem__selection-menu"
          aria-label="Навигация по задачам контеста"
        >
          <router-link
            v-for="item in contestProblemItems"
            :key="item.id"
            :to="item.route"
            class="problem__selection-item"
            :class="{ 'is-selected': item.isCurrent }"
            :aria-current="item.isCurrent ? 'page' : undefined"
            :title="item.title"
          >
            {{ item.label }}
          </router-link>
        </nav>
        <div class="problem__content">
          <h1 class="problem__name">
            <span v-if="contestProblemLabel" class="problem__contest-label">Problem {{ contestProblemLabel }}</span>
            <span class="problem__title-text">{{ problem.title }}</span>
            <UiIdPill v-if="problem?.id" class="problem__id" :id="problem.id" title="ID задачи" />
          </h1>
          <div class="problem__text" v-html="problem.rendered_statement"></div>
        </div>
        <ul class="problem__menu">
          <li v-if="contestContext && contestHasTimeLimit" class="problem__contest-time problem__menu-item">
            <h2 class="problem__item-title">Режим контеста</h2>
            <p class="problem__contest-state">{{ contestStateLabel }}</p>
            <div v-if="contestCountdown" class="problem__contest-timer">
              <p class="problem__contest-timer-label">{{ contestCountdown.label }}</p>
              <p class="problem__contest-timer-value">{{ contestCountdown.value }}</p>
            </div>
            <div class="problem__contest-meta">
              <p class="problem__contest-line">Начало: {{ contestStartLabel }}</p>
              <p class="problem__contest-line">Дедлайн: {{ contestEndLabel }}</p>
              <p class="problem__contest-line">Дорешка: {{ contestUpsolvingLabel }}</p>
              <p v-if="contestSubmitBlockedReason" class="problem__contest-warning">
                {{ contestSubmitBlockedReason }}
              </p>
            </div>
          </li>
          <li v-if="contestContext && contestNotificationsEnabled" class="problem__menu-item problem__notifications">
            <ContestNotificationsWidget
              :contest-id="contestContext.id"
              :can-manage="contestCanManage"
              :contest-title="contestContext.title"
              :questions-enabled="contestQuestionsEnabled"
            />
          </li>
          <li class="problem__files problem__menu-item" v-if="availableFiles.length > 0">
            <h2 class="problem__files-title problem__item-title">Файлы</h2>
            <ul class="problem__files-list">
              <li
                class="problem__file"
                v-for="file in availableFiles"
                :key="file.key"
              >
                <a
                  class="problem__file-href button button--secondary"
                  :href="file.url"
                  :download="file.downloadName"
                >{{ file.downloadName }}</a>
            </li>
            </ul>
          </li>
          <li class="problem__notebook problem__menu-item" v-if="isAuthorized">
            <div v-if="problem.notebook_id" class="problem__notebook-exists">
              <a :href="`/notebook/${problem.notebook_id}`" class="problem__notebook-button">
                Перейти в блокнот
              </a>
            </div>
            <div v-else class="problem__notebook-create">
              <button
                @click="handleCreateNotebook"
                :disabled="isCreatingNotebook"
                class="problem__notebook-button"
              >
                <span v-if="!isCreatingNotebook">Перейти в блокнот</span>
                <span v-else>Создание...</span>
              </button>
              <div v-if="notebookMessage" :class="['problem__notebook-feedback', `problem__notebook-feedback--${notebookMessage.type}`]">
                {{ notebookMessage.text }}
              </div>
            </div>
          </li>
          <li class="problem__notebook problem__menu-item" v-else>
            <GuestActionCard
              title="Тетрадь"
              description="После регистрации вы сможете открыть личную тетрадь для этой задачи и сохранять прогресс."
              @register="goToAuth('register', 'notebook')"
              @login="goToAuth('login', 'notebook')"
            />
          </li>
          <li class="problem__submit problem__menu-item" v-if="isAuthorized">
            <h2 class="problem__submit-title problem__item-title">Отправить решение</h2>
            <div class="problem__submit-form">
              <p class="problem__submit-hint">Выберите один способ: файл или вставка CSV-текста</p>
              <input 
                type="file" 
                :key="fileInputKey"
                accept=".csv"
                @change="handleFileChange"
                class="problem__file-input"
                id="file-input"
              />
              <label for="file-input" class="problem__file-label">
                <span v-if="!selectedFile">Выбрать файл</span>
                <span v-else>{{ selectedFile.name }}</span>
              </label>
              <textarea
                v-model="textSubmission"
                class="problem__text-input"
                placeholder="Или вставьте CSV прямо сюда, например:
id,pred
1,0.42
2,0.75"
              ></textarea>
              <button 
                @click="handleSubmit"
                :disabled="!canSubmit || isSubmitting"
                class="problem__submit-button button button--primary"
              >
                <span v-if="!isSubmitting">Отправить</span>
                <span v-else>Отправка...</span>
              </button>
              <div v-if="submitMessage" :class="['problem__submit-message', `problem__submit-message--${submitMessage.type}`]">
                {{ submitMessage.text }}
              </div>
              <div
                v-if="contestSubmitBlockedReason"
                class="problem__submit-message problem__submit-message--error"
              >
                {{ contestSubmitBlockedReason }}
              </div>
            </div>
          </li>
          <li class="problem__submit problem__menu-item" v-else>
            <GuestActionCard
              title="Сдача решения"
              description="Чтобы отправлять CSV-решения и получать результаты проверки, зарегистрируйтесь."
              @register="goToAuth('register', 'submit')"
              @login="goToAuth('login', 'submit')"
            />
          </li>
          <li class="problem__submissions problem__menu-item" v-if="isAuthorized">
            <h2 class="problem__submissions-title problem__item-title">Последние посылки</h2>
            <ul class="problem__submissions-list">
              <li class="problem__submission-head">
                <p class="problem__submission-col problem__submission-col--id">ID</p>
                <p class="problem__submission-col problem__submission-col--datetime">Дата и время</p>
                <p class="problem__submission-col problem__submission-col--status">Статус</p>
                <p class="problem__submission-col problem__submission-col--score">Баллы</p>
              </li>
              <li 
                class="problem__submission"
                v-for="submission in formattedSubmissions"
                :key="submission.id"
              >
                <router-link
                  :to="{ name: 'submission', params: { id: submission.id } }"
                  class="problem__submission-href"
                >
                  <p class="problem__submission-col problem__submission-col--id">{{ submission.id }}</p>
                  <div class="problem__submission-col problem__submission-col--datetime problem__submission-datetime">
                    <p class="problem__submission-date">{{ submission.formattedDateTime.date }}</p>
                    <p class="problem__submission-time">{{ submission.formattedDateTime.time }}</p>
                  </div>
                  <p
                    class="problem__submission-col problem__submission-col--status"
                    :title="getSubmissionStatusLabel(submission)"
                  >
                    {{ getSubmissionStatusLabel(submission) }}
                  </p>
                  <p class="problem__submission-col problem__submission-col--score">
                    {{ formatSubmissionMetric(submission) }}
                  </p>
                </router-link>
              </li>
            </ul>
            <router-link
              :to="{ name: 'problem-submissions', params: { id: problem.id } }"
              class="problem__all-submissions-button button button--primary"
            >
              Все посылки
            </router-link>
          </li>
          <li class="problem__submissions problem__menu-item" v-else>
            <GuestActionCard
              title="История посылок"
              description="После входа будет доступна история ваших отправок, статусы проверок и набранные баллы."
              @register="goToAuth('register', 'submissions')"
              @login="goToAuth('login', 'submissions')"
            />
          </li>
        </ul>
      </div>
      <div v-else-if="isLoadingProblem" class="problem__state">
        Загрузка задачи...
      </div>
      <div v-else>
        <h1 class="problem__state problem__state--error">Задача не найдена</h1>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { contestApi } from '@/api'
import { getProblem } from '@/api/problem'
import { submitSolution } from '@/api/submission'
import { createNotebook } from '@/api/notebook'
import { useUserStore } from '@/stores/UserStore'
import { renderProblemStatement } from '@/utils/problemMarkdown'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'
import UiIdPill from '@/components/ui/UiIdPill.vue'
import GuestActionCard from '@/components/ui/GuestActionCard.vue'
import ContestNotificationsWidget from '@/components/contest/ContestNotificationsWidget.vue'
import { normalizeContestProblemLabel, toContestProblemLabel } from '@/utils/contestProblemLabel'
import { formatCountdown, formatDateTimeMsk, toTimestamp } from '@/utils/datetime'
import { pushToAuthRoute } from '@/utils/authNavigation'
import { buildAuthRedirect } from '@/utils/redirect'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

let problem = ref(null)
let selectedFile = ref(null)
let textSubmission = ref('')
let isSubmitting = ref(false)
const isLoadingProblem = ref(false)
let submitMessage = ref(null)
let fileInputKey = ref(0)
let isCreatingNotebook = ref(false)
let notebookMessage = ref(null)
const contestProblemLabel = ref('')
const contestProblems = ref([])
const contestProblemsContestId = ref(null)
const contestDetails = ref(null)
const nowTs = ref(Date.now())
let clockTimer = null
let contestSyncTimer = null
const contestSyncInFlight = ref(false)
let problemLoadRequestId = 0

const renderStatement = (statement) => renderProblemStatement(statement)

const queryValue = (raw) => (Array.isArray(raw) ? raw[0] : raw)
const contestIdFromQuery = computed(() => {
  const parsed = Number(queryValue(route.query.contest))
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
})
const queryProblemLabel = computed(() => normalizeContestProblemLabel(queryValue(route.query.problem_label)))
const isAuthorized = computed(() => !!userStore.currentUser)
const isAuthRequiredError = (err) => {
  const status = Number(err?.status)
  return status === 401 || status === 403
}
const goToAuth = (mode = 'register', reason = 'generic') => {
  return pushToAuthRoute({
    router,
    route,
    mode,
    reason,
  })
}
const currentProblemId = computed(() => Number(route.params.id))
const breadcrumbsContest = computed(() => contestDetails.value)

const contestProblemItems = computed(() => {
  const contestId = contestIdFromQuery.value
  if (!contestId) return []

  const problems = Array.isArray(contestProblems.value) ? contestProblems.value : []
  return problems
    .filter(row => row?.id != null)
    .map((row, idx) => {
      const label = normalizeContestProblemLabel(row?.label) || toContestProblemLabel(idx)
      const title = String(row?.title || '').trim()
      return {
        id: row.id,
        label,
        title: title ? `${label}. ${title}` : `Задача ${label}`,
        isCurrent: Number(row.id) === currentProblemId.value,
        route: {
          name: 'problem',
          params: { id: row.id },
          query: { contest: contestId, problem_label: label },
        },
      }
    })
})

const resolveContestProblemLabelFromLoadedProblems = () => {
  const explicitLabel = queryProblemLabel.value
  contestProblemLabel.value = explicitLabel
  if (explicitLabel || !problem.value?.id) return

  const idx = contestProblems.value.findIndex((row) => Number(row?.id) === Number(problem.value.id))
  if (idx < 0) return
  contestProblemLabel.value = normalizeContestProblemLabel(contestProblems.value[idx]?.label) || toContestProblemLabel(idx)
}

const loadProblem = async () => {
  const requestId = ++problemLoadRequestId
  isLoadingProblem.value = true
  contestProblemLabel.value = queryProblemLabel.value
  const contestId = contestIdFromQuery.value
  if (!contestId) {
    contestProblems.value = []
    contestProblemsContestId.value = null
    contestDetails.value = null
  } else if (contestProblemsContestId.value !== contestId) {
    contestProblems.value = []
    contestProblemsContestId.value = contestId
    contestDetails.value = null
  }
  try {
    const [problemData, contestData] = await Promise.all([
      getProblem(route.params.id, { contestId }),
      contestId
        ? contestApi.getContest(contestId).catch((err) => {
          console.warn('Failed to load contest details for problem navigation:', err)
          return null
        })
        : Promise.resolve(null),
    ])
    if (requestId !== problemLoadRequestId) return

    if (contestId && contestData) {
      contestProblems.value = Array.isArray(contestData.problems) ? contestData.problems : []
      contestProblemsContestId.value = contestId
      contestDetails.value = contestData
    }
    problem.value = {
      ...problemData,
      rendered_statement: renderStatement(problemData?.statement || ''),
    }
    resolveContestProblemLabelFromLoadedProblems()
  } catch (err) {
    if (!isAuthorized.value && isAuthRequiredError(err)) {
      await router.replace({
        name: 'auth-required',
        query: buildAuthRedirect({
          redirect: route.fullPath,
          reason: 'generic',
        }),
      })
      return
    }
    if (requestId !== problemLoadRequestId) return
    console.log(err)
    problem.value = null
  } finally {
    if (requestId === problemLoadRequestId) {
      isLoadingProblem.value = false
    }
  }
}

onMounted(() => {
  if (clockTimer != null) return
  clockTimer = window.setInterval(() => {
    nowTs.value = Date.now()
  }, 1000)
})

const applyContestContextFromDetail = (contestData) => {
  if (!problem.value?.contest || !contestData) return
  const nextContest = {
    ...problem.value.contest,
    id: contestData.id,
    title: contestData.title,
    start_time: contestData.start_time,
    end_time: contestData.end_time,
    duration_minutes: contestData.duration_minutes,
    has_time_limit: contestData.has_time_limit,
    allow_upsolving: contestData.allow_upsolving,
    allow_notifications: contestData.allow_notifications !== false,
    allow_student_questions: contestData.allow_student_questions !== false,
    time_state: contestData.time_state,
    can_submit: contestData.can_submit,
    submit_block_reason: contestData.submit_block_reason,
    can_manage: contestData.can_manage,
  }
  if (contestData.can_view_problems === false) {
    nextContest.can_submit = false
    nextContest.submit_block_reason =
      contestData.problems_locked_reason || 'Задачи откроются после начала контеста.'
  }
  problem.value = {
    ...problem.value,
    contest: nextContest,
  }
}

const syncContestContextSilently = async () => {
  if (!problem.value || !contestContext.value) return
  if (!contestIdFromQuery.value) return
  if (!contestHasTimeLimit.value || contestCanManage.value) return
  if (isSubmitting.value || contestSyncInFlight.value) return

  contestSyncInFlight.value = true
  try {
    const contestData = await contestApi.getContest(contestIdFromQuery.value)
    applyContestContextFromDetail(contestData)
  } catch (err) {
    // Keep current state on transient sync errors.
  } finally {
    contestSyncInFlight.value = false
  }
}

onMounted(() => {
  if (contestSyncTimer != null) return
  contestSyncTimer = window.setInterval(() => {
    void syncContestContextSilently()
  }, 5000)
})

onBeforeUnmount(() => {
  if (clockTimer != null) {
    window.clearInterval(clockTimer)
    clockTimer = null
  }
  if (contestSyncTimer != null) {
    window.clearInterval(contestSyncTimer)
    contestSyncTimer = null
  }
})

watch(
  () => [route.params.id, contestIdFromQuery.value, queryProblemLabel.value],
  () => {
    loadProblem()
  },
  { immediate: true }
)

const availableFiles = computed(() => {
  if (!problem.value || !problem.value.files) return []
  return Object.entries(problem.value.files)
    .filter(([, url]) => url)
    .map(([key, url]) => {
      const k = String(key || '')
      const downloadName = k.toLowerCase().endsWith('.csv') ? k : `${k}.csv`
      return { key: k, url, downloadName }
    })
})

const contestContext = computed(() => problem.value?.contest || null)
const contestNotificationsEnabled = computed(() => contestContext.value?.allow_notifications !== false)
const contestQuestionsEnabled = computed(
  () => contestNotificationsEnabled.value && contestContext.value?.allow_student_questions !== false
)
const contestHasTimeLimit = computed(() => !!contestContext.value?.has_time_limit)
const contestCanManage = computed(() => !!contestContext.value?.can_manage)
const contestStartTs = computed(() => toTimestamp(contestContext.value?.start_time))
const contestEndTs = computed(() => toTimestamp(contestContext.value?.end_time))
const contestStartLabel = computed(() => formatDateTimeMsk(contestContext.value?.start_time))
const contestEndLabel = computed(() => formatDateTimeMsk(contestContext.value?.end_time))
const contestUpsolvingLabel = computed(() => {
  return contestContext.value?.allow_upsolving ? 'Да' : 'Нет'
})
const contestState = computed(() => {
  if (!contestHasTimeLimit.value) return 'always_open'
  const now = nowTs.value
  if (contestStartTs.value != null && now < contestStartTs.value) return 'not_started'
  if (contestEndTs.value != null && now >= contestEndTs.value) {
    return contestContext.value?.allow_upsolving ? 'upsolving' : 'finished'
  }
  return 'running'
})
const contestStateLabel = computed(() => {
  const state = contestState.value
  const labels = {
    not_started: 'Контест ещё не начался',
    running: 'Контест идёт',
    upsolving: 'Дорешка',
    finished: 'Контест завершён',
  }
  return labels[state] || 'Соревновательный режим'
})
const contestCountdown = computed(() => {
  if (!contestHasTimeLimit.value) return null
  const now = nowTs.value
  if (contestState.value === 'not_started' && contestStartTs.value != null) {
    const secondsLeft = Math.max(0, Math.ceil((contestStartTs.value - now) / 1000))
    return { label: 'До начала', value: formatCountdown(secondsLeft) }
  }
  if (contestState.value === 'running' && contestEndTs.value != null) {
    const secondsLeft = Math.max(0, Math.ceil((contestEndTs.value - now) / 1000))
    return { label: 'До конца', value: formatCountdown(secondsLeft) }
  }
  return null
})
const contestSubmitBlockedReason = computed(() => {
  if (!contestContext.value) return ''
  if (contestCanManage.value) return ''
  if (!contestHasTimeLimit.value) return ''
  if (contestState.value === 'not_started') return 'Контест ещё не начался.'
  if (contestState.value === 'finished') return 'Контест завершён, отправка недоступна.'
  if (contestContext.value.can_submit === false) {
    return contestContext.value.submit_block_reason || 'Отправка сейчас недоступна.'
  }
  return ''
})

const canSubmit = computed(() => {
  if (contestSubmitBlockedReason.value) return false
  const hasFile = selectedFile.value != null
  const hasText = textSubmission.value.trim().length > 0
  return hasFile || hasText
})

const formattedSubmissions = computed(() => {
  if (!problem.value || !problem.value.submissions) return []
  return problem.value.submissions.map(submission => ({
    ...submission,
    formattedDateTime: formatSubmissionDateTime(submission.submitted_at)
  }))
})

const toNumericScore = (value) => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }
  if (typeof value === 'string') {
    const normalized = value.replace(',', '.').trim()
    if (!normalized) return null
    const parsed = Number(normalized)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

const roundMetric = (value) => {
  const numeric = toNumericScore(value)
  if (numeric == null) return '-'
  return numeric.toFixed(2)
}

const extractMetricValue = (submission) => {
  if (!submission || typeof submission !== 'object') return null
  const submissionScore = toNumericScore(submission.score)
  if (submissionScore != null) return submissionScore
  const metrics = submission.metrics
  const metricAsNumber = toNumericScore(metrics)
  if (metricAsNumber != null) return metricAsNumber
  if (metrics && typeof metrics === 'object') {
    const keys = ['score_100', 'metric_score', 'metric', 'score', 'accuracy', 'f1', 'auc']
    for (const key of keys) {
      const metricValue = toNumericScore(metrics[key])
      if (metricValue != null) return metricValue
    }
    for (const value of Object.values(metrics)) {
      const metricValue = toNumericScore(value)
      if (metricValue != null) return metricValue
    }
  }
  return toNumericScore(submission.metric)
}

const formatSubmissionMetric = (submission) => {
  const metricValue = extractMetricValue(submission)
  return roundMetric(metricValue)
}

const getStatusLabel = (status) => {
  const statusMap = {
    'pending': '⏳ В очереди',
    'running': '🏃 Выполняется',
    'accepted': '✅ Протестировано',
    'failed': '❌ Ошибка',
    'validation_error': '⚠️ Ошибка валидации',
    'validated': '✅ Валидировано'
  }
  return statusMap[status] || status
}

const formatSubmissionDateTime = (dateTimeString) => {
  if (!dateTimeString) return { date: '-', time: '-' }
  
  try {
    const date = new Date(dateTimeString)
    
    // Check if date is valid
    if (Number.isNaN(date.getTime())) {
      console.error('Invalid date:', dateTimeString)
      return { date: '-', time: '-' }
    }
    
    // Use formatToParts for more reliable formatting in MSK timezone
    const parts = new Intl.DateTimeFormat('ru-RU', {
      timeZone: 'Europe/Moscow',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).formatToParts(date)
    
    const byType = Object.fromEntries(parts.map(p => [p.type, p.value]))
    const dateFormatted = `${byType.day}.${byType.month}.${byType.year}`
    const timeFormatted = `${byType.hour}:${byType.minute}`
    
    return { date: dateFormatted, time: timeFormatted }
  } catch (error) {
    console.error('Error formatting date:', error)
    return { date: '-', time: '-' }
  }
}

const getSubmissionStatusLabel = (submission) => {
  const base = getStatusLabel(submission?.status)
  if (submission?.is_after_deadline) {
    return `${base} (дорешка)`
  }
  return base
}

const handleFileChange = (event) => {
  const file = event.target.files[0]
  if (file) {
    // Note: Extension validation is done client-side for UX;
    // server-side validation provides actual security
    if (!file.name.toLowerCase().endsWith('.csv')) {
      submitMessage.value = { type: 'error', text: 'Пожалуйста, выберите CSV файл' }
      selectedFile.value = null
      clearFileInput()
      return
    }
    selectedFile.value = file
    submitMessage.value = null
  }
}

const clearFileInput = () => {
  selectedFile.value = null
  // Force re-render of file input to clear selection
  fileInputKey.value = (fileInputKey.value + 1) % 1000
}

const handleSubmit = async () => {
  if (contestSubmitBlockedReason.value) {
    submitMessage.value = { type: 'error', text: contestSubmitBlockedReason.value }
    return
  }

  const hasFile = selectedFile.value != null
  const hasText = textSubmission.value.trim().length > 0

  if (!hasFile && !hasText) {
    submitMessage.value = { type: 'error', text: 'Пожалуйста, выберите файл или вставьте CSV-текст' }
    return
  }

  if (hasFile && hasText) {
    submitMessage.value = { type: 'error', text: 'Используйте только один способ отправки: файл или текст' }
    return
  }

  isSubmitting.value = true
  submitMessage.value = null

  try {
    const payload = hasFile
      ? { file: selectedFile.value, contestId: contestIdFromQuery.value }
      : { rawText: textSubmission.value, contestId: contestIdFromQuery.value }
    await submitSolution(problem.value.id, payload)
    submitMessage.value = { type: 'success', text: 'Решение успешно отправлено на проверку!' }
    
    // Refresh problem data to show new submission
    try {
      const res = await getProblem(route.params.id, { contestId: contestIdFromQuery.value })
      problem.value = res
      if (problem.value != null) {
        problem.value.rendered_statement = renderStatement(problem.value.statement)
      }
    } catch (refreshError) {
      console.warn('Failed to refresh submissions after upload:', refreshError)
      submitMessage.value = {
        type: 'success',
        text: 'Решение отправлено. Не удалось обновить историю посылок, обновите страницу.'
      }
    }
    
    // Clear input for next submission
    clearFileInput()
    textSubmission.value = ''
  } catch (err) {
    console.error('Submission error:', err)
    submitMessage.value = { type: 'error', text: err.message || 'Ошибка при отправке решения' }
  } finally {
    isSubmitting.value = false
  }
}

const handleCreateNotebook = async () => {
  isCreatingNotebook.value = true
  notebookMessage.value = null

  try {
    const result = await createNotebook(problem.value.id)

    // Update problem with the new notebook_id
    problem.value.notebook_id = result.id

    notebookMessage.value = {
      type: 'success',
      text: 'Блокнот успешно создан!'
    }

    // Redirect immediately
    window.location.href = `/notebook/${result.id}`
  } catch (err) {
    console.error('Notebook creation error:', err)
    notebookMessage.value = {
      type: 'error',
      text: err.message || 'Ошибка при создании блокнота'
    }
  } finally {
    isCreatingNotebook.value = false
  }
}
</script>

<style scoped>
.problem {
  width: 100%;
  height: 100%;
  padding: 10px 0;
}

.problem__state {
  margin: 0;
  width: 100%;
  padding: 18px 20px;
  border-radius: 14px;
  border: 1px dashed var(--color-border-default);
  background: var(--color-bg-card);
  color: var(--color-text-muted);
  font-size: 16px;
  font-weight: 500;
}

.problem__state--error {
  border-color: var(--color-border-danger);
  color: var(--color-text-danger);
}

.problem__inner {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: flex-start;
  gap: 15px;
}

.problem__inner--no-contest-nav {
  padding-left: 0;
}

.problem__selection-menu {
  width: 40px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
  align-self: flex-start;
  position: sticky;
  top: 12px;
}

.problem__selection-item {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  border-radius: 10px;
  border: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
  color: var(--color-text-primary);
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
  transition:
    transform 0.12s ease,
    box-shadow 0.12s ease,
    background-color 0.12s ease,
    border-color 0.12s ease,
    color 0.12s ease;
}

.problem__selection-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
}

.problem__selection-item:active {
  transform: translateY(0);
}

.problem__selection-item.is-selected,
.problem__selection-item[aria-current='page'] {
  color: var(--color-primary);
  background: var(--color-button-secondary);
  border-color: var(--color-primary);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14);
}

.problem__selection-item:focus-visible {
  outline: 3px solid rgba(44, 62, 103, 0.28);
  outline-offset: 2px;
}

.problem__content {
  position: relative;
  z-index: 1;
  flex-grow: 1;
  min-width: 0;

  display: flex;
  flex-direction: column;

  padding: 32px 40px;

  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);

  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.problem__name {
  margin-bottom: 20px;

  font-size: 48px;
  font-weight: 400;
  line-height: 1.2;

  color: var(--color-title-text);

  padding-left: 16px;
  border-left: 6px solid var(--color-primary);
  overflow-wrap: anywhere;
}

.problem__id {
  margin-left: 12px;
  vertical-align: middle;
  white-space: nowrap;
}

.problem__title-text {
  display: inline;
}

.problem__contest-label {
  display: block;
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 8px;
}

.problem__text {
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
  font-family: var(--font-default);
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.problem__text :deep(img) {
  display: block;
  max-width: min(100%, 920px);
  height: auto;
  margin: 18px 0;
  border-radius: 12px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.problem__text :deep(a) {
  color: var(--color-primary);
  text-decoration: underline;
  overflow-wrap: anywhere;
}

.problem__text :deep(a:hover) {
  opacity: 0.85;
}

.problem__text :deep(table) {
  width: 100%;
  margin: 20px 0 24px;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid var(--color-border-default);
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(180deg, #ffffff 0%, #fcfbff 100%);
  box-shadow: 0 10px 24px rgba(39, 52, 106, 0.07);
}

.problem__text :deep(th),
.problem__text :deep(td) {
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-light);
}

.problem__text :deep(th + th),
.problem__text :deep(td + td) {
  border-left: 1px solid var(--color-border-light);
}

.problem__text :deep(thead th) {
  font-weight: 600;
  color: var(--color-title-text);
  background: linear-gradient(180deg, #f8f6ff 0%, #f0ecff 100%);
}

.problem__text :deep(tbody tr:nth-child(even)) {
  background-color: var(--color-bg-muted);
}

.problem__text :deep(tbody tr:hover) {
  background-color: var(--color-bg-primary);
}

.problem__text :deep(tbody tr:last-child td) {
  border-bottom: none;
}

@media (max-width: 720px) {
  .problem__text :deep(table) {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
}

@media (max-width: 1180px) {
  .problem__inner {
    flex-direction: column;
    gap: 12px;
  }

  .problem__inner--no-contest-nav {
    padding-left: 0;
  }

  .problem__content,
  .problem__menu {
    width: 100%;
    max-width: none;
    flex: 0 0 auto;
  }

  .problem__selection-menu {
    position: static;
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 6px;
  }

  .problem__selection-item {
    width: 34px;
    height: 34px;
    flex: 0 0 34px;
    border-radius: 9px;
    font-size: 13px;
  }
}

.problem__text :deep(p) {
  margin-bottom: 16px;
}

.problem__text :deep(ul),
.problem__text :deep(ol) {
  margin: 14px 0 18px 24px;
  padding-left: 10px;
}

.problem__text :deep(ul li) {
  list-style: disc;
}

.problem__text :deep(ol li) {
  list-style: decimal;
}

.problem__text :deep(li + li) {
  margin-top: 6px;
}

.problem__text :deep(pre) {
  margin: 16px 0 20px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid var(--color-border-default);
  background: #0f172a;
  color: #e2e8f0;
  overflow-x: auto;
}

.problem__text :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.problem__text :deep(p code),
.problem__text :deep(li code),
.problem__text :deep(td code) {
  padding: 0.1em 0.35em;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.08);
}

.problem__text :deep(blockquote) {
  margin: 16px 0;
  padding: 10px 14px;
  border-left: 4px solid var(--color-primary);
  background: var(--color-bg-muted);
  border-radius: 0 10px 10px 0;
}

.problem__text :deep(.statement-color) {
  font-weight: 700;
}

.problem__text :deep(.math-block) {
  margin: 16px 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.problem__text :deep(.math-block .katex-display) {
  margin: 0;
  text-align: center;
}

.problem__text :deep(.math-block .katex-display > .katex) {
  white-space: nowrap;
}

.problem__text :deep(h2) {
  font-size: 24px;
  font-weight: 500;
  margin: 32px 0 12px;
}

.problem__text :deep(h3) {
  font-size: 20px;
  font-weight: 500;
  margin: 24px 0 10px;
}

.problem__menu {
  width: 420px;
  max-width: 420px;
  flex: 0 0 420px;
  min-width: 0;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 25px;
}

.problem__menu-item {
  width: 100%;
  display: flex;
  flex-direction: column;

  padding: 24px;

  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);

  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.problem__item-title {
  margin-bottom: 10px;
}

.problem__contest-time {
  gap: 10px;
}

.problem__notifications {
  padding: 16px;
  background: var(--color-bg-card);
}

.problem__notifications :deep(.contest-notify__trigger) {
  width: 100%;
  justify-content: flex-start;
}

.problem__contest-state {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.problem__contest-meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.problem__contest-timer {
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  padding: 10px 12px;
}

.problem__contest-timer-label {
  margin: 0 0 4px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 700;
  color: #334155;
}

.problem__contest-timer-value {
  margin: 0;
  font-size: clamp(22px, 2.4vw, 28px);
  font-weight: 700;
  line-height: 1.1;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.problem__contest-line {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.problem__contest-warning {
  margin: 2px 0 0;
  color: var(--color-text-danger);
  font-size: 13px;
  line-height: 1.4;
}

.problem__files-list, .problem__submissions-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 10px;
}

.problem__file, .problem__submission {
  width: 100%;
}

.problem__file-href, .problem__submission-href {
  display: inline-block;
  width: 100%;
}

.problem__file-href {
  text-align: start;
  color: #9480C9;
}

.problem__submissions.problem__menu-item {
  padding: 16px;
}

.problem__submission-head,
.problem__submission-href {
  border-radius: 12px;
  padding: 10px 12px;
  width: 100%;
  display: grid;
  grid-template-columns: 52px 112px minmax(0, 1fr) 64px;
  align-items: center;
  column-gap: 8px;
  min-height: 64px;
  box-sizing: border-box;
}

.problem__submission-head {
  background-color: var(--color-button-primary);
  font-weight: 600;
}

.problem__submission-href {
  background-color: var(--color-button-secondary);
  text-decoration: none;
  transition: opacity 0.2s ease;
}

.problem__submission-href:hover {
  opacity: 0.85;
}

.problem__submission-col {
  margin: 0;
  min-width: 0;
  text-align: center;
}

.problem__submission-col--id,
.problem__submission-col--score {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.problem__submission-col--status {
  white-space: normal;
}

.problem__submission-href .problem__submission-col--status {
  white-space: normal;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-height: 1.2;
  font-size: 13px;
}

.problem__submission-head .problem__submission-col {
  color: var(--color-button-text-primary);
}

.problem__submission-href .problem__submission-col {
  color: #9480C9;
}

.problem__submission-datetime {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

.problem__submission-date {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.15;
}

.problem__submission-time {
  font-size: 11px;
  line-height: 1.15;
  opacity: 0.8;
}

@media (max-width: 1320px) and (min-width: 1181px) {
  .problem__menu {
    width: 390px;
    max-width: 390px;
    flex-basis: 390px;
  }

  .problem__submission-head,
  .problem__submission-href {
    grid-template-columns: 44px 104px minmax(0, 1fr) 58px;
    column-gap: 6px;
    padding: 9px 10px;
  }

  .problem__submission-href .problem__submission-col--status {
    font-size: 12px;
  }
}

.problem__submission {
  width: 100%;
}

.problem__submit-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.problem__submit-hint {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
}

.problem__file-input {
  display: none;
}

.problem__file-label {
  display: block;
  padding: 12px 20px;
  background-color: var(--color-button-secondary);
  color: var(--color-button-text-secondary);
  border-radius: 10px;
  text-align: center;
  cursor: pointer;
  transition: opacity 0.2s ease;
  font-weight: 500;
}

.problem__file-label:hover {
  opacity: 0.9;
}

.problem__text-input {
  min-height: 160px;
  resize: vertical;
  border-radius: 10px;
  border: 1px solid var(--color-border-default);
  padding: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 14px;
  line-height: 1.45;
  color: var(--color-text-primary);
  background-color: #fff;
}

.problem__text-input:focus {
  outline: 2px solid rgba(148, 128, 201, 0.25);
  border-color: #9480c9;
}

.problem__submit-button {
  width: 100%;
  padding: 12px 20px;
  border: none;
  font-weight: 500;
  transition: opacity 0.2s ease;
}

.problem__submit-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.problem__submit-message {
  padding: 10px 15px;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
}

.problem__submit-message--success {
  background-color: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-border);
}

.problem__submit-message--error {
  background-color: var(--color-error-bg);
  color: var(--color-error-text);
  border: 1px solid var(--color-error-border);
}

.problem__notebook-button {
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 100%;
  min-height: 52px;
  padding: 0 20px;
  background-color: #2c3e67;
  color: white;
  border: none;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-family: var(--font-default);
  font-weight: 500;
  font-size: 16px;
  line-height: 1.2;
  text-decoration: none;
  appearance: none;
  -webkit-appearance: none;
}

.problem__notebook-button:hover {
  background-color: #3d5180;
}

.problem__notebook-button:disabled {
  opacity: 0.6;
  cursor: progress;
}

.problem__notebook-exists,
.problem__notebook-create {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.problem__notebook-feedback {
  padding: 10px 15px;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
}

.problem__notebook-feedback--success {
  background-color: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-border);
}

.problem__notebook-feedback--error {
  background-color: var(--color-error-bg);
  color: var(--color-error-text);
  border: 1px solid var(--color-error-border);
}

.problem__all-submissions-button {
  width: 100%;
  margin-top: 15px;
  padding: 12px 20px;
  text-align: center;
  text-decoration: none;
  font-weight: 500;
  transition: opacity 0.2s ease;
  display: block;
}

.problem__all-submissions-button:hover {
  opacity: 0.9;
}
</style>

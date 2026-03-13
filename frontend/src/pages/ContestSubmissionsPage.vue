<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <UiBreadcrumbs :contest="contest" />
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Загрузка...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else>
          <div class="submissions-card">
            <div class="submissions-head">
              <div>
                <h2 class="submissions-title">{{ contestTitle }}</h2>
                <p class="submissions-meta">Все посылки учеников в контесте</p>
              </div>
              <router-link
                :to="contestRoute"
                class="button button--secondary submissions-link"
              >
                Назад
              </router-link>
            </div>

            <div class="filters-card">
              <div class="filters-card__top">
                <h3 class="filters-card__title">Фильтры</h3>
                <span v-if="activeFiltersCount > 0" class="filters-card__count">
                  Активно: {{ activeFiltersCount }}
                </span>
              </div>
              <form class="filters-form" @submit.prevent="applyFilters">
                <div class="filters-grid">
                  <label class="filter-field filter-field--wide">
                    <span class="filter-field__label">Поиск</span>
                    <input
                      v-model.trim="draftFilters.q"
                      type="text"
                      class="filter-field__control"
                      placeholder="ID посылки, ученик или задача"
                    />
                  </label>

                  <label class="filter-field">
                    <span class="filter-field__label">Задача</span>
                    <select v-model="draftFilters.problem_id" class="filter-field__control">
                      <option value="">Все задачи</option>
                      <option
                        v-for="problem in filterOptions.problems"
                        :key="problem.id"
                        :value="String(problem.id)"
                      >
                        {{ formatProblemOption(problem) }}
                      </option>
                    </select>
                  </label>

                  <label class="filter-field">
                    <span class="filter-field__label">Ученик</span>
                    <select v-model="draftFilters.user_id" class="filter-field__control">
                      <option value="">Все ученики</option>
                      <option
                        v-for="student in filterOptions.students"
                        :key="student.id"
                        :value="String(student.id)"
                      >
                        {{ student.username }}
                      </option>
                    </select>
                  </label>

                  <label class="filter-field">
                    <span class="filter-field__label">Статус</span>
                    <select v-model="draftFilters.status" class="filter-field__control">
                      <option value="">Все статусы</option>
                      <option
                        v-for="status in filterOptions.statuses"
                        :key="status.value"
                        :value="status.value"
                      >
                        {{ status.label }}
                      </option>
                    </select>
                  </label>

                  <label class="filter-field">
                    <span class="filter-field__label">От</span>
                    <input
                      v-model="draftFilters.submitted_from"
                      type="datetime-local"
                      class="filter-field__control"
                    />
                  </label>

                  <label class="filter-field">
                    <span class="filter-field__label">До</span>
                    <input
                      v-model="draftFilters.submitted_to"
                      type="datetime-local"
                      class="filter-field__control"
                    />
                  </label>

                  <label class="filter-field filter-field--checkbox">
                    <input
                      v-model="draftFilters.has_file"
                      type="checkbox"
                      class="filter-field__checkbox"
                    />
                    <span class="filter-field__label">Только с файлом</span>
                  </label>
                </div>

                <aside class="filters-actions">
                  <button
                    type="submit"
                    class="button button--primary filters-actions__button"
                    :disabled="isLoading"
                  >
                    Применить
                  </button>
                  <button
                    type="button"
                    class="button button--secondary filters-actions__button filters-actions__button--reset"
                    :disabled="isLoading || activeFiltersCount === 0"
                    @click="resetFilters"
                  >
                    Сбросить
                  </button>
                </aside>
              </form>
            </div>

            <p v-if="!submissions.length" class="note">По выбранным фильтрам посылок нет.</p>
            <div v-else class="submissions-table-wrap">
              <table class="submissions-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Ученик</th>
                    <th>Задача</th>
                    <th>Время</th>
                    <th>Статус</th>
                    <th>Баллы</th>
                    <th>Действия</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="submission in submissions" :key="submission.id">
                    <td>#{{ submission.id }}</td>
                    <td>{{ submission.username || '-' }}</td>
                    <td>
                      <router-link
                        v-if="submission.problem_id"
                        :to="problemRoute(submission)"
                        class="problem-link"
                      >
                        <span class="problem-cell">
                          <span v-if="submission.problem_label" class="problem-label">
                            {{ submission.problem_label }}
                          </span>
                          {{ submission.problem_title || `Задача ${submission.problem_id}` }}
                        </span>
                      </router-link>
                      <span v-else class="problem-cell">
                        <span v-if="submission.problem_label" class="problem-label">
                          {{ submission.problem_label }}
                        </span>
                        {{ submission.problem_title || '-' }}
                      </span>
                    </td>
                    <td>{{ formatDateTime(submission.submitted_at) }}</td>
                    <td>
                      <span class="status-chip" :class="statusChipClass(submission.status)">
                        {{ getStatusLabel(submission.status) }}
                      </span>
                    </td>
                    <td>{{ formatSubmissionScore(submission) }}</td>
                    <td>
                      <div class="submissions-actions">
                        <router-link
                          :to="submissionRoute(submission.id)"
                          class="button button--secondary action-btn"
                        >
                          Проверка
                        </router-link>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="totalPages > 1" class="pagination">
              <button
                class="button button--secondary pagination-btn"
                type="button"
                :disabled="currentPage <= 1 || isLoading"
                @click="goToPage(currentPage - 1)"
              >
                Назад
              </button>
              <span class="pagination-info">Страница {{ currentPage }} из {{ totalPages }}</span>
              <button
                class="button button--secondary pagination-btn"
                type="button"
                :disabled="currentPage >= totalPages || isLoading"
                @click="goToPage(currentPage + 1)"
              >
                Вперед
              </button>
            </div>
          </div>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contestApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'

const PAGE_SIZE = 20

const route = useRoute()
const contestId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(contestId.value) && contestId.value > 0)
const queryTitle = computed(() => {
  const title = route.query.title
  return Array.isArray(title) ? title[0] : title
})

const defaultFilters = () => ({
  q: '',
  problem_id: '',
  user_id: '',
  status: '',
  submitted_from: '',
  submitted_to: '',
  has_file: false,
})

const contest = ref(null)
const submissions = ref([])
const isLoading = ref(false)
const error = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const filterOptions = ref({
  problems: [],
  students: [],
  statuses: [],
})
const draftFilters = ref(defaultFilters())
const appliedFilters = ref(defaultFilters())

const contestTitle = computed(() => {
  if (contest.value?.title) return contest.value.title
  if (queryTitle.value) return queryTitle.value
  return hasValidId.value ? `Контест ${contestId.value}` : 'Контест'
})

const contestRoute = computed(() => {
  if (!hasValidId.value) return { name: 'home' }
  const title = contest.value?.title || queryTitle.value
  const query = title ? { title } : {}
  return { name: 'contest', params: { id: contestId.value }, query }
})

const activeFiltersCount = computed(() => {
  const filters = draftFilters.value
  let count = 0
  if (filters.q?.trim()) count += 1
  if (filters.problem_id) count += 1
  if (filters.user_id) count += 1
  if (filters.status) count += 1
  if (filters.submitted_from) count += 1
  if (filters.submitted_to) count += 1
  if (filters.has_file) count += 1
  return count
})

const submissionRoute = (submissionId) => {
  return {
    name: 'submission',
    params: { id: submissionId },
    query: { contest: contestId.value },
  }
}

const problemRoute = (submission) => {
  const query = { contest: contestId.value }
  if (submission?.problem_label) {
    query.problem_label = submission.problem_label
  }
  return {
    name: 'problem',
    params: { id: submission.problem_id },
    query,
  }
}

const formatProblemOption = (problem) => {
  if (!problem) return ''
  const label = problem.label ? `${problem.label} | ` : ''
  return `${label}${problem.title || `Задача ${problem.id}`}`
}

const toIsoDateTime = (localValue) => {
  if (!localValue) return ''
  const dt = new Date(localValue)
  if (Number.isNaN(dt.getTime())) return ''
  return dt.toISOString()
}

const normalizeFilterSelections = () => {
  const availableProblemIds = new Set(filterOptions.value.problems.map((row) => String(row.id)))
  const availableStudentIds = new Set(filterOptions.value.students.map((row) => String(row.id)))
  const availableStatuses = new Set(filterOptions.value.statuses.map((row) => String(row.value)))

  if (draftFilters.value.problem_id && !availableProblemIds.has(draftFilters.value.problem_id)) {
    draftFilters.value.problem_id = ''
    appliedFilters.value.problem_id = ''
  }
  if (draftFilters.value.user_id && !availableStudentIds.has(draftFilters.value.user_id)) {
    draftFilters.value.user_id = ''
    appliedFilters.value.user_id = ''
  }
  if (draftFilters.value.status && !availableStatuses.has(draftFilters.value.status)) {
    draftFilters.value.status = ''
    appliedFilters.value.status = ''
  }
}

const collectRequestFilters = () => {
  const filters = appliedFilters.value
  const params = {}
  const query = (filters.q || '').trim()
  if (query) params.q = query
  if (filters.problem_id) params.problem_id = Number(filters.problem_id)
  if (filters.user_id) params.user_id = Number(filters.user_id)
  if (filters.status) params.status = filters.status

  const submittedFrom = toIsoDateTime(filters.submitted_from)
  const submittedTo = toIsoDateTime(filters.submitted_to)
  if (submittedFrom) params.submitted_from = submittedFrom
  if (submittedTo) params.submitted_to = submittedTo
  if (filters.has_file) params.has_file = true
  return params
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return String(dateString)

  const parts = new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).formatToParts(date)

  const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${byType.day}.${byType.month}.${byType.year} ${byType.hour}:${byType.minute}`
}

const getStatusLabel = (status) => {
  const statusMap = {
    pending: '⏳ В очереди',
    running: '🏃 Выполняется',
    accepted: '✅ Протестировано',
    failed: '❌ Ошибка',
    validation_error: '⚠️ Ошибка валидации',
    validated: '✅ Валидировано',
  }
  return statusMap[status] || status
}

const statusChipClass = (status) => {
  if (status === 'accepted' || status === 'validated') return 'status-chip--success'
  if (status === 'failed' || status === 'validation_error') return 'status-chip--error'
  if (status === 'running') return 'status-chip--running'
  if (status === 'pending') return 'status-chip--pending'
  return ''
}

const formatMetric = (metrics) => {
  if (!metrics) return '-'
  if (typeof metrics === 'number') return metrics.toFixed(2)
  if (typeof metrics === 'object') {
    const keys = ['metric', 'metric_score', 'score_100', 'score', 'accuracy', 'f1', 'auc']
    for (const key of keys) {
      if (typeof metrics[key] === 'number') return metrics[key].toFixed(2)
    }
    for (const value of Object.values(metrics)) {
      if (typeof value === 'number') return value.toFixed(2)
    }
  }
  return '-'
}

const formatSubmissionScore = (submission) => {
  if (!submission || typeof submission !== 'object') return '-'
  if (typeof submission.score === 'number') return submission.score.toFixed(2)
  return formatMetric(submission.metrics)
}

const loadSubmissions = async (page = 1) => {
  if (!hasValidId.value) {
    contest.value = null
    submissions.value = []
    error.value = 'Некорректный id контеста.'
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    const contestData = await contestApi.getContest(contestId.value)
    contest.value = contestData
    if (!contestData?.can_manage) {
      submissions.value = []
      error.value = 'Раздел доступен только преподавателям контеста.'
      return
    }

    const data = await contestApi.getContestSubmissions(contestId.value, {
      page,
      pageSize: PAGE_SIZE,
      ...collectRequestFilters(),
    })
    submissions.value = Array.isArray(data?.results) ? data.results : []
    currentPage.value = Number(data?.page || page) || 1
    totalPages.value = Math.max(1, Number(data?.total_pages || 1) || 1)

    const responseFilters = data?.filters || {}
    filterOptions.value = {
      problems: Array.isArray(responseFilters.problems) ? responseFilters.problems : [],
      students: Array.isArray(responseFilters.students) ? responseFilters.students : [],
      statuses: Array.isArray(responseFilters.statuses) ? responseFilters.statuses : [],
    }
    normalizeFilterSelections()
  } catch (err) {
    console.error('Failed to load contest submissions.', err)
    error.value = err?.message || 'Не удалось загрузить посылки контеста.'
  } finally {
    isLoading.value = false
  }
}

const goToPage = (page) => {
  if (page < 1 || page > totalPages.value) return
  loadSubmissions(page)
}

const applyFilters = () => {
  appliedFilters.value = { ...draftFilters.value }
  loadSubmissions(1)
}

const resetFilters = () => {
  const next = defaultFilters()
  draftFilters.value = next
  appliedFilters.value = { ...next }
  loadSubmissions(1)
}

watch(contestId, () => {
  const next = defaultFilters()
  draftFilters.value = next
  appliedFilters.value = { ...next }
  loadSubmissions(1)
}, { immediate: true })
</script>

<style scoped>
.contest-page {
  min-height: 100vh;
  background: var(--color-bg-default);
  font-family: var(--font-default);
  color: var(--color-text-primary);
}

.contest-content {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 16px 40px;
}

.contest-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.submissions-card {
  background: var(--color-bg-card);
  border-radius: 16px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.submissions-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.submissions-title {
  margin: 0 0 6px;
  font-size: 24px;
}

.submissions-meta {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-primary);
}

.submissions-link {
  display: inline-flex;
  align-items: center;
  color: #1E264A;
  text-decoration: none;
}

.filters-card {
  border: 1px solid #dbe1f4;
  border-radius: 14px;
  background:
    linear-gradient(180deg, #ffffff 0%, #f7f9ff 100%);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.filters-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.filters-card__title {
  margin: 0;
  font-size: 17px;
  color: var(--color-title-text);
}

.filters-card__count {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 11px;
  border: 1px solid #ccd6fb;
  background: #ffffff;
  font-size: 12px;
  color: #2a3a79;
  font-weight: 500;
}

.filters-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 228px;
  gap: 12px;
  align-items: start;
}

.filters-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  align-content: start;
}

.filter-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-field--wide {
  grid-column: span 2;
}

.filter-field__label {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
  letter-spacing: 0.01em;
}

.filter-field__control {
  width: 100%;
  min-height: 40px;
  border: 1px solid #d5dcef;
  border-radius: 11px;
  padding: 9px 11px;
  background: #ffffff;
  color: var(--color-text-primary);
  font: inherit;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease;
}

.filter-field__control:focus {
  outline: none;
  border-color: #a8b5ea;
  box-shadow: 0 0 0 3px rgba(39, 52, 106, 0.11);
}

.filter-field--checkbox {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  padding-top: 26px;
}

.filter-field__checkbox {
  width: 17px;
  height: 17px;
}

.filters-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  border: 1px solid #d8deef;
  background: linear-gradient(180deg, #ffffff 0%, #f2f5ff 100%);
  border-radius: 12px;
  padding: 10px;
  align-self: start;
  width: 100%;
  max-width: 228px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.filters-actions__button {
  width: 100%;
  min-height: 42px;
  border: 1px solid transparent;
  font-size: 14px;
  font-weight: 600;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.filters-actions__button:hover:not(:disabled) {
  opacity: 1;
}

.filters-actions__button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(39, 52, 106, 0.14);
}

.filters-actions__button.button--primary {
  background-color: var(--color-button-primary);
  border-color: var(--color-button-primary);
  color: var(--color-button-text-primary);
}

.filters-actions__button.button--primary:hover:not(:disabled) {
  background-color: var(--color-button-primary-hover, #1A274D);
  border-color: var(--color-button-primary-hover, #1A274D);
}

.filters-actions__button--reset {
  background: #ffffff;
  border-color: #ccd5ef;
  color: var(--color-text-primary);
}

.filters-actions__button--reset:hover:not(:disabled) {
  background: #f4f7ff;
  border-color: #bbc8ea;
}

.filters-actions__button:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.submissions-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
}

.submissions-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 920px;
}

.submissions-table th,
.submissions-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-light);
  vertical-align: top;
}

.submissions-table th {
  background: var(--color-bg-default);
  font-size: 13px;
  letter-spacing: 0.01em;
  color: var(--color-text-primary);
}

.submissions-table tr:last-child td {
  border-bottom: none;
}

.problem-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.problem-link {
  color: var(--color-primary);
  text-decoration: none;
}

.problem-link:hover {
  text-decoration: underline;
}

.problem-label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--color-bg-default);
  border: 1px solid var(--color-border-light);
  font-size: 12px;
  font-weight: 600;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid var(--color-border-default);
  background: #f8f9fe;
}

.status-chip--success {
  background: #eafaf2;
  border-color: #c8eed9;
  color: #13643e;
}

.status-chip--error {
  background: #fff1f1;
  border-color: #ffd4d4;
  color: #9b1c1c;
}

.status-chip--running {
  background: #eef6ff;
  border-color: #cfe4ff;
  color: #205ea9;
}

.status-chip--pending {
  background: #fff9eb;
  border-color: #ffe7a8;
  color: #8a5b0a;
}

.submissions-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  font-size: 13px;
  padding: 6px 10px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.pagination-btn {
  min-width: 92px;
}

.pagination-info {
  font-size: 14px;
}

.state {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  padding: 14px;
}

.state--error {
  color: var(--color-error-text);
}

.note {
  margin: 0;
  color: var(--color-text-primary);
}

@media (max-width: 1024px) {
  .filters-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filters-form {
    grid-template-columns: 1fr;
  }

  .filters-actions {
    flex-direction: row;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: wrap;
    max-width: none;
    background: #f4f6ff;
  }

  .filters-actions__button {
    width: auto;
    min-width: 146px;
  }

}

@media (max-width: 640px) {
  .filters-grid {
    grid-template-columns: 1fr;
  }

  .filter-field--wide {
    grid-column: span 1;
  }

  .filters-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .filters-actions__button {
    width: 100%;
  }

  .submissions-table {
    min-width: 760px;
  }
}
</style>

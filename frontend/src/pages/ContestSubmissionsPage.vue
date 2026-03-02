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

            <p v-if="!submissions.length" class="note">Пока нет посылок учеников.</p>
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
                    <td>{{ getStatusLabel(submission.status) }}</td>
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
                :disabled="currentPage <= 1"
                @click="goToPage(currentPage - 1)"
              >
                Назад
              </button>
              <span class="pagination-info">Страница {{ currentPage }} из {{ totalPages }}</span>
              <button
                class="button button--secondary pagination-btn"
                type="button"
                :disabled="currentPage >= totalPages"
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

const contest = ref(null)
const submissions = ref([])
const isLoading = ref(false)
const error = ref('')
const currentPage = ref(1)
const totalPages = ref(1)

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
    })
    submissions.value = Array.isArray(data?.results) ? data.results : []
    currentPage.value = Number(data?.page || page) || 1
    totalPages.value = Math.max(1, Number(data?.total_pages || 1) || 1)
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

watch(contestId, () => {
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
  max-width: 1080px;
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

.submissions-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
}

.submissions-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 900px;
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
</style>

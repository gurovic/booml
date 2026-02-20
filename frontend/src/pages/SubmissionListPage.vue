<template>
  <UiHeader />
  <div class="submissions">
    <div class="container">
      <div class="submissions__inner">
        <div class="submissions__header">
          <h1 class="submissions__title">Все посылки</h1>
          <p v-if="problem" class="submissions__problem-title">{{ problem.title }}</p>
        </div>

        <div v-if="loading && submissions.length === 0" class="submissions__loading">
          Загрузка...
        </div>

        <div v-else-if="error" class="submissions__error">
          {{ error }}
        </div>

        <div v-else-if="submissions.length === 0" class="submissions__empty">
          Нет посылок по этой задаче
        </div>

        <div v-else class="submissions__content">
          <table class="submissions__table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Время</th>
                <th>Статус</th>
                <th>Баллы</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="submission in submissions" 
                :key="submission.id"
                @click="navigateToSubmission(submission.id)"
                class="submissions__table-row--clickable"
              >
                <td>{{ submission.id }}</td>
                <td>{{ formatDateTime(submission.submitted_at) }}</td>
                <td>
                  <span class="status">
                    {{ getStatusLabel(submission.status) }}
                  </span>
                </td>
                <td>{{ formatSubmissionScore(submission) }}</td>
              </tr>
            </tbody>
          </table>

          <div v-if="totalPages > 1" class="submissions__pagination">
            <button 
              @click="goToPage(currentPage - 1)"
              :disabled="currentPage === 1"
              class="pagination__button"
            >
              Предыдущая
            </button>
            <span class="pagination__info">
              Страница {{ currentPage }} из {{ totalPages }}
            </span>
            <button 
              @click="goToPage(currentPage + 1)"
              :disabled="currentPage === totalPages"
              class="pagination__button"
            >
              Следующая
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getProblemSubmissions } from '@/api/submission'
import { getProblem } from '@/api/problem'
import UiHeader from '@/components/ui/UiHeader.vue'

const route = useRoute()
const problemId = route.params.id

// Pagination configuration - must match backend SubmissionsPagination.page_size
const PAGE_SIZE = 10

const problem = ref(null)
const submissions = ref([])
const loading = ref(false)
const error = ref(null)
const currentPage = ref(1)
const totalPages = ref(1)
const totalCount = ref(0)

const fetchSubmissions = async (page = 1) => {
  loading.value = true
  error.value = null
  
  try {
    const response = await getProblemSubmissions(problemId, page)
    submissions.value = response.results || []
    totalCount.value = response.count || 0
    
    // Calculate total pages
    totalPages.value = Math.ceil(totalCount.value / PAGE_SIZE)
    currentPage.value = page
  } catch (err) {
    console.error('Failed to fetch submissions:', err)
    error.value = 'Не удалось загрузить список посылок'
  } finally {
    loading.value = false
  }
}

const goToPage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    fetchSubmissions(page)
  }
}

const navigateToSubmission = (submissionId) => {
  // Navigate to the submission detail page
  window.location.href = `/submission/${submissionId}/`
}

const formatDateTime = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return String(dateString)

  // Force MSK regardless of the user's local timezone.
  const parts = new Intl.DateTimeFormat('ru-RU', {
    timeZone: 'Europe/Moscow',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).formatToParts(date)

  const byType = Object.fromEntries(parts.map(p => [p.type, p.value]))
  return `${byType.day}.${byType.month}.${byType.year} ${byType.hour}:${byType.minute}`
}

const formatMetric = (metrics) => {
  if (!metrics) return '-'
  
  // If metrics is a number
  if (typeof metrics === 'number') {
    return metrics.toFixed(2)
  }
  
  // If metrics is an object, try to find the primary metric
  if (typeof metrics === 'object' && metrics !== null) {
    const keys = ['metric', 'metric_score', 'score', 'accuracy', 'f1', 'auc']
    for (const key of keys) {
      if (key in metrics && typeof metrics[key] === 'number') {
        return metrics[key].toFixed(2)
      }
    }
    
    // If no known key found, return the first numeric value
    for (const value of Object.values(metrics)) {
      if (typeof value === 'number') {
        return value.toFixed(2)
      }
    }
  }
  
  return '-'
}

const formatSubmissionScore = (submission) => {
  if (!submission || typeof submission !== 'object') return '-'
  if (typeof submission.score === 'number') return submission.score.toFixed(2)
  return formatMetric(submission.metrics)
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

onMounted(async () => {
  // Fetch problem details
  try {
    const res = await getProblem(problemId)
    problem.value = res
  } catch (err) {
    console.error('Failed to fetch problem:', err)
  }
  
  // Fetch submissions
  fetchSubmissions(1)
})
</script>

<style scoped>
.submissions {
  width: 100%;
  min-height: 100vh;
  padding: 20px 0;
  background: var(--color-bg);
}

.submissions__inner {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.submissions__header {
  padding: 32px 40px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.submissions__title {
  margin-bottom: 10px;
  font-size: 48px;
  font-weight: 400;
  line-height: 1.2;
  color: var(--color-title-text);
  padding-left: 16px;
  border-left: 6px solid var(--color-primary);
}

.submissions__problem-title {
  margin: 10px 0 0;
  padding-left: 22px;
  font-size: 18px;
  color: var(--color-text-secondary);
}

.submissions__content {
  padding: 32px 40px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.submissions__loading,
.submissions__error,
.submissions__empty {
  padding: 40px;
  text-align: center;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  font-size: 18px;
}

.submissions__error {
  color: var(--color-error-text);
}

.submissions__table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 16px;
}

.submissions__table thead tr {
  background-color: #9480C9;
}

.submissions__table th {
  padding: 15px 20px;
  text-align: left;
  font-weight: 500;
  color: #ffffff;
  border-radius: 0;
}

.submissions__table thead tr th:first-child {
  border-top-left-radius: 20px;
}

.submissions__table thead tr th:last-child {
  border-top-right-radius: 20px;
}

.submissions__table tbody tr {
  background-color: #E4DAFF;
  transition: opacity 0.2s ease;
}

.submissions__table tbody tr:nth-child(even) {
  background-color: #EDE6FF;
}

.submissions__table-row--clickable {
  cursor: pointer;
}

.submissions__table tbody tr:hover {
  opacity: 0.9;
}

.submissions__table tbody tr:last-child td:first-child {
  border-bottom-left-radius: 20px;
}

.submissions__table tbody tr:last-child td:last-child {
  border-bottom-right-radius: 20px;
}

.submissions__table tbody tr + tr {
  border-top: 2px solid var(--color-bg);
}

.submissions__table td {
  padding: 15px 20px;
  color: #333333;
}

.status {
  font-size: 14px;
  font-weight: 500;
  display: inline-block;
  color: #333333;
}

.submissions__pagination {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
}

.pagination__button {
  padding: 10px 20px;
  background-color: var(--color-button-primary);
  color: var(--color-button-text-primary);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: opacity 0.2s ease;
}

.pagination__button:hover:not(:disabled) {
  opacity: 0.9;
}

.pagination__button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination__info {
  font-size: 16px;
  color: var(--color-text-primary);
  font-weight: 500;
}
</style>


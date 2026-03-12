<template>
  <UiHeader />
  <div class="submission">
    <div class="container">
      <div v-if="submission != null" class="submission__inner">
        <div class="submission__content">
          <h1 class="submission__title">Посылка #{{ submission.id }}</h1>
          
          <div class="submission__info">
            <div class="submission__info-item">
              <span class="submission__info-label">Задача:</span>
              <router-link 
                :to="{ name: 'problem', params: { id: submission.problem_id } }"
                class="submission__problem-link"
              >
                {{ submission.problem_title }}
              </router-link>
            </div>
            
            <div class="submission__info-item">
              <span class="submission__info-label">Дата посылки:</span>
              <span class="submission__info-value">{{ formatDate(submission.submitted_at) }}</span>
            </div>
            
            <div class="submission__info-item">
              <span class="submission__info-label">Статус:</span>
              <span :class="['submission__status', `submission__status--${submission.status}`]">
                {{ getStatusLabel(submission.status) }}
              </span>
            </div>
            
            <div class="submission__info-item" v-if="submission.metrics || submission.score != null">
              <span class="submission__info-label">Баллы:</span>
              <span class="submission__info-value">{{ formatSubmissionScore(submission) }}</span>
            </div>
            
            <div class="submission__info-item" v-if="submission.code_size">
              <span class="submission__info-label">Размер файла:</span>
              <span class="submission__info-value">{{ formatFileSize(submission.code_size) }}</span>
            </div>
            
            <div class="submission__info-item" v-if="submission.file_url">
              <a :href="submission.file_url" class="submission__download-button button button--primary" download>
                Скачать файл посылки
              </a>
            </div>
          </div>
          
          <!-- PreValidation Report -->
          <div v-if="submission.prevalidation" class="submission__prevalidation">
            <h2 class="submission__section-title">Отчёт предварительной проверки</h2>
            
            <div class="prevalidation__summary">
              <div class="prevalidation__item">
                <span class="prevalidation__label">Валидность:</span>
                <span :class="['prevalidation__value', submission.prevalidation.valid ? 'prevalidation__value--success' : 'prevalidation__value--error']">
                  {{ submission.prevalidation.valid ? 'Валидно' : 'Невалидно' }}
                </span>
              </div>
              
              <div class="prevalidation__item">
                <span class="prevalidation__label">Статус:</span>
                <span class="prevalidation__value">{{ getPrevalidationStatus(submission.prevalidation.status) }}</span>
              </div>
              
              <div class="prevalidation__item" v-if="submission.prevalidation.rows_total != null">
                <span class="prevalidation__label">Всего строк:</span>
                <span class="prevalidation__value">{{ submission.prevalidation.rows_total }}</span>
              </div>
              
              <div class="prevalidation__item" v-if="submission.prevalidation.unique_ids != null">
                <span class="prevalidation__label">Уникальных ID:</span>
                <span class="prevalidation__value">{{ submission.prevalidation.unique_ids }}</span>
              </div>
              
              <div class="prevalidation__item" v-if="submission.prevalidation.duration_ms != null">
                <span class="prevalidation__label">Длительность:</span>
                <span class="prevalidation__value">{{ submission.prevalidation.duration_ms }} мс</span>
              </div>
            </div>
            
            <!-- Errors -->
            <div v-if="submission.prevalidation.errors && submission.prevalidation.errors.length > 0" class="prevalidation__errors">
              <h3 class="prevalidation__subtitle">
                Ошибки ({{ submission.prevalidation.errors_count }})
              </h3>
              <ul class="prevalidation__list">
                <li 
                  v-for="(error, index) in submission.prevalidation.errors" 
                  :key="index"
                  class="prevalidation__error-item"
                >
                  {{ error }}
                </li>
              </ul>
            </div>
            
            <!-- Warnings -->
            <div v-if="submission.prevalidation.warnings && submission.prevalidation.warnings.length > 0" class="prevalidation__warnings">
              <h3 class="prevalidation__subtitle">
                Предупреждения ({{ submission.prevalidation.warnings_count }})
              </h3>
              <ul class="prevalidation__list">
                <li 
                  v-for="(warning, index) in submission.prevalidation.warnings" 
                  :key="index"
                  class="prevalidation__warning-item"
                >
                  {{ warning }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="error" class="submission__error">
        <h1>Ошибка</h1>
        <p>{{ error }}</p>
      </div>
      <div v-else class="submission__loading">
        <h1>Загрузка...</h1>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getSubmission } from '@/api/submission'
import UiHeader from '@/components/ui/UiHeader.vue'

const route = useRoute()
const submission = ref(null)
const error = ref(null)

onMounted(async () => {
  try {
    const rawContestId = Array.isArray(route.query.contest)
      ? route.query.contest[0]
      : route.query.contest
    submission.value = await getSubmission(route.params.id, { contestId: rawContestId })
  } catch (err) {
    console.error('Failed to load submission:', err)
    error.value = err.message || 'Не удалось загрузить посылку'
  }
})

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('ru-RU', {
    timeZone: 'Europe/Moscow',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
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

const getPrevalidationStatus = (status) => {
  const statusMap = {
    'passed': 'Пройдено',
    'failed': 'Провалено',
    'warnings': 'С предупреждениями'
  }
  return statusMap[status] || status
}

const formatMetrics = (metrics) => {
  if (!metrics) return '-'
  if (typeof metrics === 'number') {
    return metrics.toFixed(2)
  }
  if (typeof metrics === 'object') {
    // Find primary metric
    const primaryKeys = ['metric', 'metric_score', 'score', 'accuracy', 'f1', 'auc']
    for (const key of primaryKeys) {
      if (key in metrics && typeof metrics[key] === 'number') {
        return metrics[key].toFixed(2)
      }
    }
    // Return first numeric value
    for (const [, value] of Object.entries(metrics)) {
      if (typeof value === 'number') {
        return value.toFixed(2)
      }
    }
    return JSON.stringify(metrics)
  }
  return String(metrics)
}

const formatSubmissionScore = (submission) => {
  if (!submission || typeof submission !== 'object') return '-'
  if (typeof submission.score === 'number') {
    return submission.score.toFixed(2)
  }
  return formatMetrics(submission.metrics)
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}
</script>

<style scoped>
.submission {
  width: 100%;
  min-height: 100vh;
  padding: 20px 0;
}

.submission__inner {
  width: 100%;
}

.submission__content {
  padding: 32px 40px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.submission__title {
  margin-bottom: 30px;
  font-size: 36px;
  font-weight: 400;
  line-height: 1.2;
  color: var(--color-title-text);
  padding-left: 16px;
  border-left: 6px solid var(--color-primary);
}

.submission__info {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

.submission__info-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--color-bg-light);
  border-radius: 10px;
}

.submission__info-label {
  font-weight: 600;
  color: var(--color-text-secondary);
  min-width: 150px;
}

.submission__info-value {
  color: var(--color-text-primary);
}

.submission__problem-link {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.submission__problem-link:hover {
  text-decoration: underline;
}

.submission__status {
  padding: 6px 12px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 14px;
}

.submission__status--pending {
  background: #fff3cd;
  color: #856404;
}

.submission__status--running {
  background: #d1ecf1;
  color: #0c5460;
}

.submission__status--accepted,
.submission__status--validated {
  background: #d4edda;
  color: #155724;
}

.submission__status--failed,
.submission__status--validation_error {
  background: #f8d7da;
  color: #721c24;
}

.submission__download-button {
  padding: 10px 20px;
  text-decoration: none;
  display: inline-block;
  border-radius: 10px;
  font-weight: 500;
  transition: opacity 0.2s ease;
}

.submission__download-button:hover {
  opacity: 0.9;
}

.submission__section-title {
  margin-top: 32px;
  margin-bottom: 20px;
  font-size: 24px;
  font-weight: 500;
  color: var(--color-title-text);
}

.submission__prevalidation {
  margin-top: 32px;
  padding-top: 32px;
  border-top: 2px solid var(--color-border-light);
}

.prevalidation__summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.prevalidation__item {
  padding: 12px 16px;
  background: var(--color-bg-light);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.prevalidation__label {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.prevalidation__value {
  color: var(--color-text-primary);
  font-size: 16px;
}

.prevalidation__value--success {
  color: #28a745;
  font-weight: 600;
}

.prevalidation__value--error {
  color: #dc3545;
  font-weight: 600;
}

.prevalidation__subtitle {
  margin-bottom: 12px;
  font-size: 18px;
  font-weight: 500;
  color: var(--color-title-text);
}

.prevalidation__errors,
.prevalidation__warnings {
  margin-top: 24px;
}

.prevalidation__list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.prevalidation__error-item,
.prevalidation__warning-item {
  padding: 10px 16px;
  margin-bottom: 8px;
  border-radius: 8px;
  font-size: 14px;
}

.prevalidation__error-item {
  background: #f8d7da;
  color: #721c24;
  border-left: 4px solid #dc3545;
}

.prevalidation__warning-item {
  background: #fff3cd;
  color: #856404;
  border-left: 4px solid #ffc107;
}

.submission__error,
.submission__loading {
  padding: 32px 40px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.submission__error h1 {
  color: #dc3545;
}
</style>


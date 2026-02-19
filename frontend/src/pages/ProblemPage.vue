<template>
  <UiHeader />
  <div class="container">
    <UiBreadcrumbs :problem="problem" />
  </div>
  <div class="problem">
    <div class="container">
      <div v-if="problem != null" class="problem__inner">
        <div class="problem__content">
          <h1 class="problem__name">
            <span class="problem__title-text">{{ problem.title }}</span>
            <UiIdPill v-if="problem?.id" class="problem__id" :id="problem.id" title="ID задачи" />
          </h1>
          <div class="problem__text" v-html="problem.rendered_statement"></div>
        </div>
        <ul class="problem__menu">
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
          <li class="problem__notebook problem__menu-item" v-if="userStore.isAuthenticated">
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
          <li class="problem__submit problem__menu-item" v-if="userStore.isAuthenticated">
            <h2 class="problem__submit-title problem__item-title">Отправить решение</h2>
            <div class="problem__submit-form">
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
              <button 
                @click="handleSubmit"
                :disabled="!selectedFile || isSubmitting"
                class="problem__submit-button button button--primary"
              >
                <span v-if="!isSubmitting">Отправить</span>
                <span v-else>Отправка...</span>
              </button>
              <div v-if="submitMessage" :class="['problem__submit-message', `problem__submit-message--${submitMessage.type}`]">
                {{ submitMessage.text }}
              </div>
            </div>
          </li>
          <li class="problem__submissions problem__menu-item">
            <h2 class="problem__submissions-title problem__item-title">Последние посылки</h2>
            <ul class="problem__submissions-list">
              <li class="problem__submission-head">
                <p>ID</p>
                <p>Дата и время</p>
                <p>Статус</p>
                <p>Метрика</p>
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
                  <p>{{ submission.id }}</p>
                  <div class="problem__submission-datetime">
                    <p class="problem__submission-date">{{ submission.formattedDateTime.date }}</p>
                    <p class="problem__submission-time">{{ submission.formattedDateTime.time }}</p>
                  </div>
                  <p>{{ getStatusLabel(submission.status) }}</p>
                  <p>{{ roundMetric(submission.metric) }}</p>
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
        </ul>
      </div>
      <div v-else>
        <h1>Задача не найдена</h1>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { getProblem } from '@/api/problem'
import { submitSolution } from '@/api/submission'
import { createNotebook } from '@/api/notebook'
import { useUserStore } from '@/stores/UserStore'
import MarkdownIt from 'markdown-it'
import mkKatex from 'markdown-it-katex'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'
import UiIdPill from '@/components/ui/UiIdPill.vue'

const md = new MarkdownIt({
  html: false,
  breaks: true,
}).use(mkKatex)

const route = useRoute()
const userStore = useUserStore()

let problem = ref(null)
let selectedFile = ref(null)
let isSubmitting = ref(false)
let submitMessage = ref(null)
let fileInputKey = ref(0)
let isCreatingNotebook = ref(false)
let notebookMessage = ref(null)

onMounted(async () => {
  try {
    const res = await getProblem(route.params.id)
    problem.value = res
  } catch (err) {
    console.log(err)
  } finally {
    if (problem.value != null) {
      problem.value.rendered_statement = md.render(problem.value.statement)
    }
  }
})

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

const formattedSubmissions = computed(() => {
  if (!problem.value || !problem.value.submissions) return []
  return problem.value.submissions.map(submission => ({
    ...submission,
    formattedDateTime: formatSubmissionDateTime(submission.submitted_at)
  }))
})

const roundMetric = (value) => {
  if (value == null) return '-'
  return value.toFixed(3)
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
  if (!selectedFile.value) {
    submitMessage.value = { type: 'error', text: 'Пожалуйста, выберите файл' }
    return
  }

  isSubmitting.value = true
  submitMessage.value = null

  try {
    await submitSolution(problem.value.id, selectedFile.value)
    submitMessage.value = { type: 'success', text: 'Файл успешно отправлен на проверку!' }
    
    // Refresh problem data to show new submission
    try {
      const res = await getProblem(route.params.id)
      problem.value = res
      if (problem.value != null) {
        problem.value.rendered_statement = md.render(problem.value.statement)
      }
    } catch (refreshError) {
      console.warn('Failed to refresh submissions after upload:', refreshError)
      submitMessage.value = {
        type: 'success',
        text: 'Файл отправлен. Не удалось обновить историю посылок — обновите страницу.'
      }
    }
    
    // Clear file input for next submission
    clearFileInput()
  } catch (err) {
    console.error('Submission error:', err)
    submitMessage.value = { type: 'error', text: err.message || 'Ошибка при отправке файла' }
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

.problem__inner {
  width: 100%;
  height: 100%;
  display: flex;
  gap: 15px;
}

.problem__content {
  position: relative;
  z-index: 1;
  flex-grow: 1;

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

.problem__text {
  font-family: var(--font-default);
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.problem__text :deep(p) {
  margin-bottom: 16px;
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
  max-width: 450px;
  width: 100%;
  flex-grow: 1;
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

.problem__files-list, .problem__submissions-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
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

.problem__submission-head,
.problem__submission-href {
  border-radius: 10px;
  padding: 10px 15px;
  width: 100%;
  display: grid;
  grid-template-columns: 55px 115px 1fr 85px;
  align-items: center;
  gap: 10px;
  height: 65px;
  overflow: hidden;
}

.problem__submission-head {
  background-color: var(--color-button-primary);
}

.problem__submission-href {
  background-color: var(--color-button-secondary);
  text-decoration: none;
  transition: opacity 0.2s ease;
}

.problem__submission-href:hover {
  opacity: 0.85;
}

.problem__submission-head p,
.problem__submission-href p {
  margin: 0;
  text-align: center;
}

.problem__submission-head > *,
.problem__submission-href > * {
  overflow: visible;
}

.problem__submission-head > :nth-child(1),
.problem__submission-href > :nth-child(1) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.problem__submission-head > :nth-child(3),
.problem__submission-href > :nth-child(3) {
  overflow-wrap: break-word;
  word-wrap: break-word;
  hyphens: auto;
  line-height: 1.2;
  font-size: 13px;
}


.problem__submission-head p {
  color: var(--color-button-text-primary);
}

.problem__submission-href p {
  color: #9480C9;
}

.problem__submission-datetime {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 100%;
}

.problem__submission-date {
  font-size: 14px;
  font-weight: 500;
}

.problem__submission-time {
  font-size: 12px;
  opacity: 0.8;
}

.problem__submission {
  width: 100%;
}

.problem__submit-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  display: block;
  width: 100%;
  padding: 16px 20px;
  background-color: #2c3e67;
  color: white;
  border: none;
  border-radius: 12px;
  text-align: center;
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-weight: 500;
  font-size: 16px;
  text-decoration: none;
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

<template>
  <UiHeader />
  <div class="container">
    <UiBreadcrumbs :problem="problem" />
  </div>
  <div class="problem">
    <div class="container">
      <div v-if="problem != null" class="problem__inner">
        <nav v-if="contestProblemItems.length > 0" class="problem__selection_menu" aria-label="Выбор задачи">
          <router-link
            v-for="item in contestProblemItems"
            :key="item.id"
            :to="item.route"
            class="problem__selection_item"
            :class="{ 'is-selected': item.isCurrent }"
            :aria-current="item.isCurrent ? 'page' : undefined"
          >
            {{ item.label }}
          </router-link>
        </nav>
        <div class="problem__content">
          <h1 class="problem__name">
            <span v-if="contestProblemLabel" class="problem__contest-label">Задача {{ contestProblemLabel }}</span>
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
                :key="`${file.kind}:${file.name}`"
              >
                <a
                  class="problem__file-href button button--secondary"
                  :href="file.url"
                  :download="file.name"
                >{{ file.name }}</a>
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
                <p>Время</p>
                <p>Статус</p>
                <p>Баллы</p>
              </li>
              <li 
                class="problem__submission"
                v-for="submission in problem.submissions"
                :key="submission.id"
              >
                <router-link
                  :to="{ name: 'submission', params: { id: submission.id } }"
                  class="problem__submission-href"
                >
                  <p>{{ submission.id }}</p>
                  <p>{{ submission.submitted_at }}</p>
                  <p>{{ getStatusLabel(submission.status) }}</p>
                  <p>{{ formatSubmissionMetric(submission) }}</p>
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
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contestApi } from '@/api'
import { getProblem } from '@/api/problem'
import { submitSolution } from '@/api/submission'
import { createNotebook } from '@/api/notebook'
import { useUserStore } from '@/stores/UserStore'
import MarkdownIt from 'markdown-it'
import markdownKatex from '@/utils/markdownKatex'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'
import UiIdPill from '@/components/ui/UiIdPill.vue'
import { normalizeContestProblemLabel, toContestProblemLabel } from '@/utils/contestProblemLabel'

const md = new MarkdownIt({
  html: false,
  breaks: false,
  linkify: true,
}).use(markdownKatex, { throwOnError: false })

const route = useRoute()
const userStore = useUserStore()

let problem = ref(null)
let selectedFile = ref(null)
let isSubmitting = ref(false)
let submitMessage = ref(null)
let fileInputKey = ref(0)
let isCreatingNotebook = ref(false)
let notebookMessage = ref(null)
const contestProblemLabel = ref('')
const contestProblems = ref([])

const stripLeadingH1 = (statement) => {
  if (typeof statement !== 'string' || !statement) return ''

  const lines = statement.replace(/\r\n?/g, '\n').split('\n')
  let firstContentLine = 0

  while (firstContentLine < lines.length && !lines[firstContentLine].trim()) {
    firstContentLine += 1
  }

  if (firstContentLine >= lines.length) return statement
  if (!/^#\s+/.test(lines[firstContentLine])) return statement

  lines.splice(firstContentLine, 1)
  while (firstContentLine < lines.length && !lines[firstContentLine].trim()) {
    lines.splice(firstContentLine, 1)
  }

  return lines.join('\n')
}

const renderStatement = (statement) => md.render(stripLeadingH1(statement))

const queryValue = (raw) => (Array.isArray(raw) ? raw[0] : raw)
const contestIdFromQuery = computed(() => {
  const parsed = Number(queryValue(route.query.contest))
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
})
const queryProblemLabel = computed(() => normalizeContestProblemLabel(queryValue(route.query.problem_label)))
const currentProblemId = computed(() => Number(route.params.id))

const contestProblemItems = computed(() => {
  const problems = Array.isArray(contestProblems.value) ? contestProblems.value : []
  const contestId = contestIdFromQuery.value

  return problems
    .filter(row => row?.id != null)
    .map((row, idx) => {
      const ordinal = Number.isInteger(row?.index) && row.index >= 0 ? row.index : idx
      const label = normalizeContestProblemLabel(row?.label) || toContestProblemLabel(ordinal)
      return {
        id: row.id,
        label,
        isCurrent: Number(row.id) === currentProblemId.value,
        route: {
          name: 'problem',
          params: { id: row.id },
          query: { contest: contestId, problem_label: label },
        },
      }
    })
})

const resolveContestProblemLabel = async () => {
  contestProblemLabel.value = queryProblemLabel.value
  contestProblems.value = []

  if (!problem.value?.id || !contestIdFromQuery.value) return

  try {
    const contestData = await contestApi.getContest(contestIdFromQuery.value)
    const problems = Array.isArray(contestData?.problems) ? contestData.problems : []
    contestProblems.value = problems
    if (contestProblemLabel.value) return

    const idx = problems.findIndex(row => Number(row?.id) === Number(problem.value.id))
    if (idx < 0) return

    contestProblemLabel.value =
      normalizeContestProblemLabel(problems[idx]?.label) || toContestProblemLabel(idx)
  } catch (err) {
    console.warn('Failed to resolve contest problem label:', err)
  }
}

const loadProblem = async () => {
  contestProblemLabel.value = ''
  try {
    const res = await getProblem(route.params.id)
    problem.value = res
  } catch (err) {
    console.log(err)
  } finally {
    if (problem.value != null) {
      problem.value.rendered_statement = renderStatement(problem.value.statement)
      await resolveContestProblemLabel()
    }
  }
}

onMounted(loadProblem)

watch(
  () => route.params.id,
  (nextId, prevId) => {
    if (nextId !== prevId) {
      loadProblem()
    }
  }
)

const availableFiles = computed(() => {
  if (!problem.value) return []

  if (Array.isArray(problem.value.file_list)) {
    return problem.value.file_list
      .filter(file => file && file.url && file.name && file.kind)
      .map(file => ({
        kind: String(file.kind),
        name: String(file.name),
        url: String(file.url),
      }))
  }

  const fallbackCanonicalNames = {
    train: 'train.csv',
    test: 'test.csv',
    sample_submission: 'sample_submission.csv',
  }

  if (!problem.value.files) return []
  return Object.entries(problem.value.files)
    .filter(([, url]) => url)
    .map(([key, url]) => ({
      kind: String(key || ''),
      name: String(fallbackCanonicalNames[key] || key || ''),
      url: String(url),
    }))
})

const roundMetric = (value) => {
  if (value == null) return '-'
  return value.toFixed(2)
}

const extractMetricValue = (submission) => {
  if (!submission || typeof submission !== 'object') return null
  if (typeof submission.score === 'number') return submission.score
  const metrics = submission.metrics
  if (typeof metrics === 'number') return metrics
  if (metrics && typeof metrics === 'object') {
    const keys = ['score_100', 'metric_score', 'metric', 'score', 'accuracy', 'f1', 'auc']
    for (const key of keys) {
      if (typeof metrics[key] === 'number') {
        return metrics[key]
      }
    }
    for (const value of Object.values(metrics)) {
      if (typeof value === 'number') {
        return value
      }
    }
  }
  if (typeof submission.metric === 'number') return submission.metric
  return null
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
        problem.value.rendered_statement = renderStatement(problem.value.statement)
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
  gap: 20px;
}

.problem__selection_menu {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.problem__selection_item {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  color: #111827;
  font-weight: 700;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  user-select: none;
  text-decoration: none;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  transition:
    background-color 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease,
    transform 0.05s ease,
    box-shadow 0.15s ease;
}

.problem__selection_item:hover {
  background: #f3f4f6;
}

.problem__selection_item:active {
  transform: translateY(1px);
}

.problem__selection_item.is-selected,
.problem__selection_item[aria-current='true'] {
  background: var(--color-button-secondary);
  border: #9480C9 1px solid;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
  color: var(--color-primary);
}

.problem__selection_item:focus {
  outline: 3px solid rgba(139, 92, 246, 0.35);
  outline-offset: 2px;
}

.problem__selection_item:focus-visible {
  outline: 3px solid rgba(139, 92, 246, 0.35);
  outline-offset: 2px;
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

.problem__contest-label {
  display: block;
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 8px;
}

.problem__text {
  font-family: var(--font-default);
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text-primary);
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

.problem__text :deep(p) {
  margin-bottom: 16px;
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
  max-width: 350px;
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
  padding: 10px 20px;
  width: 100%;
  display: grid;
  grid-template-columns: 0.5fr 1.5fr 1fr 1fr;
  align-items: center;
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


.problem__submission-head p {
  color: var(--color-button-text-primary);
}

.problem__submission-href p {
  color: #9480C9;
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

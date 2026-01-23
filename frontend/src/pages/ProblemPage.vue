<template>
  <UiHeader />
  <div class="problem">
    <div class="container">
      <div v-if="problem != null" class="problem__inner">
        <div class="problem__content">
          <h1 class="problem__name">{{ problem.title }}</h1>
          <div class="problem__text" v-html="problem.rendered_statement"></div>
        </div>
        <ul class="problem__menu">
          <li class="problem__submit problem__menu-item">
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
          <li class="problem__files problem__menu-item" v-if="availableFiles.length > 0">
            <h2 class="problem__files-title problem__item-title">Файлы</h2>
            <ul class="problem__files-list">
              <li
                class="problem__file"
                v-for="file in availableFiles"
                :key="file.name"
              >
                <a class="problem__file-href button button--secondary" :href="file.url" :download="file.name">{{ file.name }}</a>
            </li>
            </ul>
          </li>
          <li class="problem__submissions problem__menu-item">
            <h2 class="problem__submissions-title problem__item-title">Последние посылки</h2>
            <ul class="problem__submissions-list">
              <li class="problem__submission-head">
                <p>Время</p>
                <p>Статус</p>
                <p>Метрика</p>
              </li>
              <li 
                class="problem__submission"
                v-for="submission in problem.submissions"
                :key="submission.id"
              >
                <a class="problem__submission-href" href="#">
                  <p>{{ submission.submitted_at }}</p>
                  <p>{{ submission.status }}</p>
                  <p>{{ roundMetric(submission.metric.metric_score) }}</p>
                </a>
              </li>
            </ul>
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
import MarkdownIt from 'markdown-it'
import mkKatex from 'markdown-it-katex'
import UiHeader from '@/components/ui/UiHeader.vue'

const md = new MarkdownIt({
  html: false,
  breaks: true,
}).use(mkKatex)

const route = useRoute()

let problem = ref(null)
let selectedFile = ref(null)
let isSubmitting = ref(false)
let submitMessage = ref(null)
let fileInputKey = ref(0)

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
  if (!problem.value.files) return []
  return Object.entries(problem.value.files)
    .filter(([, url]) => url)
    .map(([name, url]) => ({ name, url }))
})

const roundMetric = (value) => {
  if (value == null) return '-'
  return Number(value).toFixed(3)
}

const handleFileChange = (event) => {
  const file = event.target.files[0]
  if (file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      submitMessage.value = { type: 'error', text: 'Пожалуйста, выберите CSV файл' }
      selectedFile.value = null
      return
    }
    selectedFile.value = file
    submitMessage.value = null
  }
}

const handleSubmit = async () => {
  if (!selectedFile.value) {
    submitMessage.value = { type: 'error', text: 'Пожалуйста, выберите файл' }
    return
  }

  isSubmitting.value = true
  submitMessage.value = null

  try {
    const result = await submitSolution(problem.value.id, selectedFile.value)
    submitMessage.value = { type: 'success', text: 'Файл успешно отправлен на проверку!' }
    
    // Refresh problem data to show new submission
    const res = await getProblem(route.params.id)
    problem.value = res
    if (problem.value != null) {
      problem.value.rendered_statement = md.render(problem.value.statement)
    }
    
    // Clear file input
    selectedFile.value = null
    fileInputKey.value++
  } catch (err) {
    console.error('Submission error:', err)
    submitMessage.value = { type: 'error', text: err.message || 'Ошибка при отправке файла' }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.problem {
  width: 100%;
  height: 100%;
  padding: 20px 0;
}

.problem__inner {
  width: 100%;
  height: 100%;
  display: flex;
  gap: 20px;
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
  grid-template-columns: 1fr 1fr 1fr;
  align-items: center;
}

.problem__submission-head {
  background-color: var(--color-button-primary);
}

.problem__submission-href {
  background-color: var(--color-button-secondary);
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
  background-color: #d1fae5;
  color: #065f46;
  border: 1px solid #a7f3d0;
}

.problem__submit-message--error {
  background-color: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

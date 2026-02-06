<template>
  <div class="polygon">
    <UiHeader />
    <div class="polygon__content">
      <div class="polygon__header">
        <h1 class="polygon__title">Мои задачи</h1>
        <button 
          class="button button--primary polygon__create-btn" 
          @click="showCreateDialog = true"
        >
          Создать задачу
        </button>
      </div>

      <div v-if="loading" class="polygon__loading">
        Загрузка...
      </div>

      <div v-else-if="error" class="polygon__error">
        {{ error }}
      </div>

      <div v-else-if="!problems.length" class="polygon__empty">
        <div class="empty-state">
          <h2 class="empty-state__title">Нет задач</h2>
          <p class="empty-state__text">
            Создайте свою первую задачу, чтобы начать работу
          </p>
          <button 
            class="button button--primary empty-state__button" 
            @click="showCreateDialog = true"
          >
            Создать задачу
          </button>
        </div>
      </div>

      <div v-else class="problems-table-container">
        <table class="problems-table">
          <thead>
            <tr>
              <th class="problems-table__header">Название</th>
              <th class="problems-table__header">Рейтинг</th>
              <th class="problems-table__header">Статус</th>
              <th class="problems-table__header">Дата создания</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="problem in problems" 
              :key="problem.id"
              class="problems-table__row"
              @click="goToEdit(problem.id)"
            >
              <td class="problems-table__cell">{{ problem.title }}</td>
              <td class="problems-table__cell">{{ problem.rating }}</td>
              <td class="problems-table__cell">
                <span 
                  class="status-badge" 
                  :class="problem.is_published ? 'status-badge--published' : 'status-badge--draft'"
                >
                  {{ problem.is_published ? 'Опубликована' : 'Не опубликована' }}
                </span>
              </td>
              <td class="problems-table__cell">{{ formatDate(problem.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click="closeCreateDialog">
      <div class="dialog" @click.stop>
        <div class="dialog__header">
          <h2 class="dialog__title">Создать задачу</h2>
          <button class="dialog__close" @click="closeCreateDialog">×</button>
        </div>
        <div class="dialog__body">
          <div class="form-group">
            <label for="problem-title" class="form-label">Название задачи</label>
            <input
              id="problem-title"
              v-model="newProblem.title"
              type="text"
              class="form-input"
              placeholder="Введите название задачи"
              @keyup.enter="createProblem"
            />
            <div v-if="createError" class="form-error">{{ createError }}</div>
          </div>
          <div class="form-group">
            <label for="problem-rating" class="form-label">Рейтинг (необязательно)</label>
            <input
              id="problem-rating"
              v-model.number="newProblem.rating"
              type="number"
              class="form-input"
              placeholder="800"
              min="800"
              max="3000"
              step="100"
            />
            <div v-if="ratingError" class="form-error">{{ ratingError }}</div>
          </div>
        </div>
        <div class="dialog__footer">
          <button 
            class="button button--secondary" 
            @click="closeCreateDialog"
            :disabled="creating"
          >
            Отмена
          </button>
          <button 
            class="button button--primary" 
            @click="createProblem"
            :disabled="creating || !newProblem.title.trim()"
          >
            {{ creating ? 'Создание...' : 'Создать' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPolygonProblems, createPolygonProblem } from '@/api/polygon'
import UiHeader from '@/components/ui/UiHeader.vue'

const router = useRouter()
const problems = ref([])
const loading = ref(true)
const error = ref(null)
const showCreateDialog = ref(false)
const creating = ref(false)
const createError = ref(null)
const ratingError = ref(null)
const newProblem = ref({
  title: '',
  rating: 800
})

const loadProblems = async () => {
  loading.value = true
  error.value = null
  try {
    const data = await getPolygonProblems()
    problems.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('Не удалось загрузить задачи', err)
    error.value = 'Не удалось загрузить задачи. Попробуйте позже.'
  } finally {
    loading.value = false
  }
}

const createProblem = async () => {
  createError.value = null
  ratingError.value = null

  if (!newProblem.value.title.trim()) {
    createError.value = 'Введите название задачи'
    return
  }

  // Validate that rating is within range
  if (newProblem.value.rating && (newProblem.value.rating < 800 || newProblem.value.rating > 3000)) {
    ratingError.value = 'Рейтинг должен быть от 800 до 3000'
    return
  }

  // Validate that rating is divisible by 100
  if (newProblem.value.rating && newProblem.value.rating % 100 !== 0) {
    ratingError.value = 'Рейтинг должен быть кратен 100'
    return
  }

  creating.value = true
  
  try {
    const data = {
      title: newProblem.value.title.trim(),
      rating: newProblem.value.rating || 800
    }
    const created = await createPolygonProblem(data)
    
    // Redirect to Vue edit page
    router.push({ name: 'polygon-problem-edit', params: { id: created.id } })
  } catch (err) {
    console.error('Не удалось создать задачу', err)
    createError.value = 'Не удалось создать задачу. Попробуйте еще раз.'
  } finally {
    creating.value = false
  }
}

const closeCreateDialog = () => {
  showCreateDialog.value = false
  newProblem.value = { title: '', rating: 800 }
  createError.value = null
  ratingError.value = null
}

const goToEdit = (problemId) => {
  // Redirect to Vue edit page
  router.push({ name: 'polygon-problem-edit', params: { id: problemId } })
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('ru-RU')
}

onMounted(loadProblems)
</script>

<style scoped>
.polygon {
  min-height: 100vh;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

.polygon__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 16px;
}

.polygon__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  gap: 16px;
  flex-wrap: wrap;
}

.polygon__title {
  font-family: var(--font-title);
  font-size: 36px;
  font-weight: 400;
  color: var(--color-title-text);
  margin: 0;
}

.polygon__create-btn {
  padding: 12px 24px;
  font-size: 16px;
  white-space: nowrap;
}

.polygon__loading,
.polygon__error {
  text-align: center;
  padding: 48px 16px;
  font-size: 18px;
}

.polygon__error {
  color: var(--color-error-text);
}

.polygon__empty {
  padding: 48px 16px;
}

.empty-state {
  background: var(--color-bg-card);
  border-radius: 12px;
  padding: 48px 32px;
  text-align: center;
  border: 1px solid var(--color-border-default);
}

.empty-state__title {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-title-text);
  margin: 0 0 16px;
}

.empty-state__text {
  font-size: 16px;
  color: var(--color-text-muted);
  margin: 0 0 24px;
}

.empty-state__button {
  padding: 12px 24px;
}

.problems-table-container {
  background: var(--color-bg-card);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border-default);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.problems-table {
  width: 100%;
  border-collapse: collapse;
}

.problems-table__header {
  background: var(--color-bg-muted);
  padding: 16px 20px;
  text-align: left;
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--color-border-default);
}

.problems-table__row {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.problems-table__row:hover {
  background: var(--color-bg-primary);
}

.problems-table__row:not(:last-child) {
  border-bottom: 1px solid var(--color-border-light);
}

.problems-table__cell {
  padding: 16px 20px;
  font-size: 16px;
}

.status-badge {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
}

.status-badge--published {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-border);
}

.status-badge--draft {
  background: var(--color-bg-muted);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border-default);
}

/* Dialog styles */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.dialog {
  background: var(--color-bg-card);
  border-radius: 12px;
  max-width: 500px;
  width: 100%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.dialog__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--color-border-default);
}

.dialog__title {
  font-size: 24px;
  font-weight: 600;
  color: var(--color-title-text);
  margin: 0;
}

.dialog__close {
  background: none;
  border: none;
  font-size: 32px;
  line-height: 1;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.dialog__close:hover {
  background: var(--color-bg-muted);
}

.dialog__body {
  padding: 24px;
}

.dialog__footer {
  padding: 16px 24px 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text-primary);
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  font-size: 16px;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-card);
  transition: border-color 0.2s ease;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-input::placeholder {
  color: var(--color-text-muted);
}

.form-error {
  margin-top: 8px;
  font-size: 14px;
  color: var(--color-error-text);
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .polygon__title {
    font-size: 28px;
  }

  .problems-table-container {
    overflow-x: auto;
  }

  .problems-table {
    min-width: 600px;
  }
}
</style>

<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Loading contests...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else>
          <div class="course-header">
            <h1 class="course-title">{{ courseTitle }}</h1>
            <button 
              v-if="canCreateContest" 
              class="button button--primary create-contest-btn"
              @click="showCreateDialog = true"
            >
              Создать контест
            </button>
          </div>
          
          <UiLinkList
            title="Контесты"
            :items="contestItems"
          />
          <p v-if="!contestItems.length" class="note">This course has no contests yet.</p>
        </template>
      </section>
    </main>

    <!-- Create Contest Dialog -->
    <div v-if="showCreateDialog" class="dialog-overlay" @click="closeCreateDialog">
      <div class="dialog" @click.stop>
        <div class="dialog__header">
          <h2 class="dialog__title">Создать контест</h2>
          <button class="dialog__close" @click="closeCreateDialog">×</button>
        </div>
        <div class="dialog__body">
          <div class="form-group">
            <label for="contest-title" class="form-label">Название контеста *</label>
            <input
              id="contest-title"
              v-model="newContest.title"
              type="text"
              class="form-input"
              placeholder="Введите название контеста"
              @keyup.enter="createContest"
            />
          </div>
          <div class="form-group">
            <label for="contest-description" class="form-label">Описание</label>
            <textarea
              id="contest-description"
              v-model="newContest.description"
              class="form-textarea"
              placeholder="Введите описание контеста"
              rows="4"
            ></textarea>
          </div>
          <div class="form-group">
            <label for="contest-scoring" class="form-label">Система оценки</label>
            <select id="contest-scoring" v-model="newContest.scoring" class="form-select">
              <option value="ioi">IOI (сумма баллов)</option>
              <option value="icpc">ICPC (штраф по времени)</option>
              <option value="partial">Частичная оценка</option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-checkbox">
                <input type="checkbox" v-model="newContest.is_published" />
                <span>Опубликовать контест</span>
              </label>
            </div>
            <div class="form-group">
              <label class="form-checkbox">
                <input type="checkbox" v-model="newContest.is_rated" />
                <span>Рейтинговый контест</span>
              </label>
            </div>
          </div>
          <div v-if="createError" class="form-error">{{ createError }}</div>
        </div>
        <div class="dialog__footer">
          <button class="button button--secondary" @click="closeCreateDialog">
            Отмена
          </button>
          <button 
            class="button button--primary" 
            @click="createContest"
            :disabled="isCreating || !newContest.title"
          >
            {{ isCreating ? 'Создание...' : 'Создать' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { contestApi, courseApi } from '@/api'
import { useUserStore } from '@/stores/UserStore'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiLinkList from '@/components/ui/UiLinkList.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const courseId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(courseId.value) && courseId.value > 0)
const queryTitle = computed(() => {
  const title = route.query.title
  return Array.isArray(title) ? title[0] : title
})

const course = ref(null)
const contests = ref([])
const isLoading = ref(false)
const error = ref('')
const showCreateDialog = ref(false)
const isCreating = ref(false)
const createError = ref('')

const newContest = ref({
  title: '',
  description: '',
  scoring: 'ioi',
  is_published: false,
  is_rated: false,
})

const courseTitle = computed(() => course.value?.title || queryTitle.value || 'Course')

const canCreateContest = computed(() => {
  if (!userStore.currentUser || !course.value) return false
  // User can create contest if they are the section owner
  return course.value.section_owner_id === userStore.currentUser.id
})

const contestItems = computed(() => {
  const list = Array.isArray(contests.value) ? contests.value : []
  return list
    .filter(contest => contest?.id != null)
    .map(contest => ({
      text: contest.title || `Contest ${contest.id}`,
      route: { name: 'contest', params: { id: contest.id }},
    }))
})

const loadContests = async () => {
  if (!hasValidId.value) {
    contests.value = []
    error.value = 'Invalid course id.'
    course.value = null
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    const [courseData, contestData] = await Promise.all([
      courseApi.getCourse(courseId.value),
      contestApi.getContestsByCourse(courseId.value),
    ])
    course.value = courseData
    contests.value = contestData
  } catch (err) {
    console.error('Failed to load contests.', err)
    error.value = err?.message || 'Failed to load contests.'
  } finally {
    isLoading.value = false
  }
}

const closeCreateDialog = () => {
  showCreateDialog.value = false
  createError.value = ''
  newContest.value = {
    title: '',
    description: '',
    scoring: 'ioi',
    is_published: false,
    is_rated: false,
  }
}

const createContest = async () => {
  if (!newContest.value.title.trim()) {
    createError.value = 'Название контеста обязательно'
    return
  }

  isCreating.value = true
  createError.value = ''
  
  try {
    const contestData = {
      title: newContest.value.title,
      description: newContest.value.description,
      scoring: newContest.value.scoring,
      is_published: newContest.value.is_published,
      is_rated: newContest.value.is_rated,
    }
    
    const result = await contestApi.createContest(courseId.value, contestData)
    
    // Reload contests
    await loadContests()
    
    // Close dialog
    closeCreateDialog()
    
    // Navigate to the new contest
    if (result && result.id) {
      router.push({ name: 'contest', params: { id: result.id } })
    }
  } catch (err) {
    console.error('Failed to create contest:', err)
    createError.value = err?.message || 'Не удалось создать контест'
  } finally {
    isCreating.value = false
  }
}

watch(courseId, () => {
  loadContests()
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
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px 40px;
}

.contest-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 16px;
}

.course-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}

.create-contest-btn {
  white-space: nowrap;
}

.state {
  padding: 14px 16px;
  background: var(--color-bg-card);
  border: 1px dashed var(--color-border-default);
  border-radius: 12px;
  color: var(--color-text-muted);
  font-size: 15px;
}

.state--error {
  border-color: var(--color-border-danger);
  color: var(--color-text-danger);
}

.note {
  margin: 0;
  padding: 10px 12px;
  background: var(--color-bg-muted);
  border-radius: 10px;
  border: 1px solid var(--color-border-light);
  font-size: 14px;
  color: var(--color-text-muted);
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
  background: var(--color-bg-card, #fff);
  border-radius: 16px;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.dialog__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-default, #e0e0e0);
}

.dialog__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary, #000);
}

.dialog__close {
  background: none;
  border: none;
  font-size: 32px;
  line-height: 1;
  color: var(--color-text-muted, #666);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: background 0.2s ease;
}

.dialog__close:hover {
  background: var(--color-bg-muted, #f5f5f5);
}

.dialog__body {
  padding: 24px;
}

.dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-default, #e0e0e0);
}

.form-group {
  margin-bottom: 16px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary, #000);
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border-default, #d0d0d0);
  border-radius: 8px;
  font-size: 15px;
  font-family: inherit;
  color: var(--color-text-primary, #000);
  background: var(--color-bg-default, #fff);
  transition: border-color 0.2s ease;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  outline: none;
  border-color: var(--color-primary, #3b82f6);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-text-primary, #000);
}

.form-checkbox input[type="checkbox"] {
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.form-error {
  margin-top: 12px;
  padding: 10px 12px;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c33;
  font-size: 14px;
}

@media (min-width: 900px) {
  .contest-content {
    padding: 28px 24px 48px;
  }
}
</style>

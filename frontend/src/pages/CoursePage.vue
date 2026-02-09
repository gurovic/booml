<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <UiBreadcrumbs :course="course" />
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Loading contests...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else>
          <div class="course-header">
            <div class="course-title-row">
              <h1 class="course-title">Курс "{{ courseTitle }}"</h1>
              <button
                v-if="isAuthorized"
                type="button"
                class="star-btn"
                :class="{ 'star-btn--on': isFavoriteCourse }"
                :title="isFavoriteCourse ? 'Убрать из избранного' : 'Добавить в избранное'"
                @click="toggleFavoriteCourse"
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27Z"
                    stroke="currentColor"
                    stroke-width="1.8"
                    stroke-linejoin="round"
                    :fill="isFavoriteCourse ? 'currentColor' : 'transparent'"
                  />
                </svg>
              </button>
            </div>
            <div class="course-header__actions">
              <button
                v-if="canCreateContest"
                class="button button--primary create-contest-btn"
                @click="showCreateDialog = true"
              >
                Создать контест
              </button>
              <button
                v-if="canManageCourse"
                class="button button--secondary"
                type="button"
                @click="showCourseSettings = !showCourseSettings"
              >
                Настройки курса
              </button>
            </div>
          </div>

          <section v-if="canManageCourse && showCourseSettings" class="course-settings">
            <div class="course-settings__row">
              <label class="form-checkbox">
                <input type="checkbox" v-model="courseIsOpen" @change="saveCourseSettings" />
                <span>Курс открыт для всех (open)</span>
              </label>
              <button class="button button--secondary" type="button" @click="deleteThisCourse">
                Удалить курс
              </button>
            </div>

            <div class="participants">
              <h3 class="participants__title">Участники</h3>
              <div v-if="!participants.length" class="note">Нет участников</div>
              <ul v-else class="participants__list">
                <li v-for="p in participants" :key="p.username" class="participants__item">
                  <div class="participants__meta">
                    <span class="participants__name">{{ p.username }}</span>
                    <span class="participants__role">
                      {{ p.is_owner ? 'owner' : p.role }}
                    </span>
                  </div>
                  <div class="participants__actions">
                    <button
                      v-if="!p.is_owner"
                      class="participants__btn"
                      type="button"
                      @click="toggleParticipantRole(p)"
                    >
                      {{ p.role === 'teacher' ? 'Сделать student' : 'Сделать teacher' }}
                    </button>
                    <button
                      v-if="!p.is_owner"
                      class="participants__btn participants__btn--danger"
                      type="button"
                      @click="removeParticipant(p)"
                    >
                      Удалить
                    </button>
                  </div>
                </li>
              </ul>

              <div class="participants__add">
                <input
                  v-model="newParticipantUsername"
                  type="text"
                  class="form-input"
                  placeholder="username пользователя"
                  @keyup.enter="addParticipant"
                />
                <select v-model="newParticipantRole" class="form-select">
                  <option value="student">student</option>
                  <option value="teacher">teacher</option>
                </select>
                <button class="button button--primary" type="button" @click="addParticipant" :disabled="!newParticipantUsername.trim()">
                  Добавить
                </button>
              </div>
            </div>
          </section>
          
          <UiLinkList
            title="Контесты"
            :items="contestItems"
          >
            <template #action="{ item }">
              <div v-if="canReorderContests" class="contest-order-actions">
                <button
                  class="contest-order-btn"
                  type="button"
                  title="Вверх"
                  :disabled="isFirstContest(item)"
                  @click.stop.prevent="moveContest(item, -1)"
                >
                  ↑
                </button>
                <button
                  class="contest-order-btn"
                  type="button"
                  title="Вниз"
                  :disabled="isLastContest(item)"
                  @click.stop.prevent="moveContest(item, 1)"
                >
                  ↓
                </button>
              </div>
              <button
                v-if="canDeleteContestItem(item)"
                class="contest-delete-btn"
                type="button"
                title="Удалить контест"
                @click.stop.prevent="deleteContest(item)"
              >
                Удалить
              </button>
            </template>
          </UiLinkList>
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
            :disabled="isCreating || !newContest.title.trim()"
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
import { contestApi, courseApi, homeApi } from '@/api'
import { useUserStore } from '@/stores/UserStore'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'
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
const showCourseSettings = ref(false)
const courseIsOpen = ref(false)
const newParticipantUsername = ref('')
const newParticipantRole = ref('student')
const favorites = ref([])

const newContest = ref({
  title: '',
  description: '',
  scoring: 'ioi',
  is_published: false,
  is_rated: false,
})

const courseTitle = computed(() => course.value?.title || queryTitle.value || '...')
const isAuthorized = computed(() => !!userStore.currentUser)

const isFavoriteCourse = computed(() => {
  const cid = Number(courseId.value)
  return favorites.value.some(x => Number(x.course_id) === cid)
})

const loadFavorites = async () => {
  if (!isAuthorized.value) {
    favorites.value = []
    return
  }
  try {
    const data = await homeApi.getHomeSidebar()
    favorites.value = Array.isArray(data?.favorites) ? data.favorites : []
  } catch (err) {
    console.error('Failed to load favorites', err)
  }
}

const toggleFavoriteCourse = async () => {
  if (!isAuthorized.value) return
  try {
    const cid = Number(courseId.value)
    const res = isFavoriteCourse.value
      ? await homeApi.removeFavoriteCourse(cid)
      : await homeApi.addFavoriteCourse(cid)
    if (Array.isArray(res?.items)) favorites.value = res.items
    else await loadFavorites()
  } catch (err) {
    console.error('Failed to toggle favorite', err)
    error.value = err?.message || 'Не удалось обновить избранное'
  }
}

const canCreateContest = computed(() => {
  if (!userStore.currentUser || !course.value) return false
  return !!course.value.can_create_contest
})

const canReorderContests = computed(() => {
  return canCreateContest.value && Array.isArray(contests.value) && contests.value.length > 1
})

const canManageCourse = computed(() => {
  if (!userStore.currentUser || !course.value) return false
  return !!course.value.can_manage_course
})

const participants = computed(() => {
  const list = Array.isArray(course.value?.participants) ? course.value.participants : []
  return list.map(p => ({
    id: p.id,
    username: p.username,
    role: p.role,
    is_owner: !!p.is_owner,
  }))
})

const contestItems = computed(() => {
  const list = Array.isArray(contests.value) ? contests.value : []
  return list
    .filter(contest => contest?.id != null)
    .map(contest => ({
      id: contest.id,
      text: contest.title || `Contest ${contest.id}`,
      route: { name: 'contest', params: { id: contest.id }},
      created_by_id: contest.created_by_id,
    }))
})

const loadContests = async () => {
  if (!hasValidId.value) {
    contests.value = []
    error.value = 'Invalid course id.'
    course.value = null
    favorites.value = []
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
    courseIsOpen.value = !!courseData?.is_open
    contests.value = contestData
    await loadFavorites()
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
  const title = newContest.value.title.trim()
  if (!title) {
    createError.value = 'Название контеста обязательно'
    return
  }

  isCreating.value = true
  createError.value = ''
  
  try {
    const contestData = {
      title,
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

const canDeleteContestItem = (item) => {
  const me = userStore.currentUser?.id
  if (!me) return false
  return Number(item?.created_by_id) === Number(me)
}

const _contestIndex = (contestId) => {
  const list = Array.isArray(contests.value) ? contests.value : []
  return list.findIndex(c => Number(c?.id) === Number(contestId))
}

const isFirstContest = (item) => _contestIndex(item?.id) <= 0
const isLastContest = (item) => {
  const list = Array.isArray(contests.value) ? contests.value : []
  const idx = _contestIndex(item?.id)
  return idx < 0 || idx >= list.length - 1
}

const moveContest = async (item, delta) => {
  const list = Array.isArray(contests.value) ? [...contests.value] : []
  const idx = list.findIndex(c => Number(c?.id) === Number(item?.id))
  const next = idx + delta
  if (idx < 0 || next < 0 || next >= list.length) return

  const tmp = list[idx]
  list[idx] = list[next]
  list[next] = tmp
  contests.value = list

  try {
    await courseApi.reorderCourseContests(courseId.value, list.map(c => c.id))
  } catch (err) {
    console.error('Failed to reorder contests:', err)
    error.value = err?.message || 'Не удалось поменять порядок контестов'
    await loadContests()
  }
}

const deleteContest = async (item) => {
  const contestId = item?.id
  if (!contestId) return
  const title = item?.text || `Contest ${contestId}`
  if (!confirm(`Удалить контест "${title}"? Это действие необратимо.`)) return

  try {
    await contestApi.deleteContest(contestId)
    await loadContests()
  } catch (err) {
    console.error('Failed to delete contest:', err)
    error.value = err?.message || 'Не удалось удалить контест'
  }
}

const saveCourseSettings = async () => {
  try {
    await courseApi.updateCourse(courseId.value, { is_open: courseIsOpen.value })
    await loadContests()
  } catch (err) {
    console.error('Failed to update course:', err)
    error.value = err?.message || 'Не удалось обновить курс'
  }
}

const addParticipant = async () => {
  const username = newParticipantUsername.value.trim()
  if (!username) return

  try {
    const payload =
      newParticipantRole.value === 'teacher'
        ? { teacherUsernames: [username], studentUsernames: [] }
        : { teacherUsernames: [], studentUsernames: [username] }

    await courseApi.updateCourseParticipants(courseId.value, payload)
    newParticipantUsername.value = ''
    await loadContests()
  } catch (err) {
    console.error('Failed to add participant:', err)
    error.value = err?.message || 'Не удалось добавить участника'
  }
}

const toggleParticipantRole = async (p) => {
  if (!p?.username || p.is_owner) return
  const nextRole = p.role === 'teacher' ? 'student' : 'teacher'
  try {
    const payload =
      nextRole === 'teacher'
        ? { teacherUsernames: [p.username], studentUsernames: [] }
        : { teacherUsernames: [], studentUsernames: [p.username] }
    await courseApi.updateCourseParticipants(courseId.value, payload)
    await loadContests()
  } catch (err) {
    console.error('Failed to update role:', err)
    error.value = err?.message || 'Не удалось обновить роль'
  }
}

const removeParticipant = async (p) => {
  if (!p?.username || p.is_owner) return
  if (!confirm(`Удалить пользователя ${p.username} из курса?`)) return
  try {
    await courseApi.removeCourseParticipants(courseId.value, [p.username])
    await loadContests()
  } catch (err) {
    console.error('Failed to remove participant:', err)
    error.value = err?.message || 'Не удалось удалить участника'
  }
}

const deleteThisCourse = async () => {
  if (!confirm('Удалить курс? Это удалит все контесты внутри курса.')) return
  try {
    await courseApi.deleteCourse(courseId.value)
    router.push({ name: 'home' })
  } catch (err) {
    console.error('Failed to delete course:', err)
    error.value = err?.message || 'Не удалось удалить курс'
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

.course-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.course-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary);
}

.star-btn {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid var(--color-border-default);
  background: #fff;
  color: #64748b;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.star-btn:hover {
  opacity: 0.9;
}

.star-btn--on {
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.45);
  background: rgba(251, 191, 36, 0.12);
}

.create-contest-btn {
  white-space: nowrap;
}

.course-header__actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.course-settings {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-default);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.course-settings__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.participants__title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
}

.participants__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0;
  margin: 0;
}

.participants__item {
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--color-bg-default);
  border: 1px solid var(--color-border-default);
  border-radius: 10px;
}

.participants__meta {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.participants__name {
  font-weight: 600;
}

.participants__role {
  font-size: 12px;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border-default);
  padding: 2px 8px;
  border-radius: 999px;
}

.participants__actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.participants__btn {
  border: 1px solid var(--color-border-default);
  background: #fff;
  padding: 6px 10px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
}

.participants__btn--danger {
  border-color: var(--color-border-danger);
  color: var(--color-text-danger);
}

.participants__add {
  display: grid;
  grid-template-columns: 1fr 150px auto;
  gap: 10px;
  align-items: center;
}

@media (max-width: 700px) {
  .participants__add {
    grid-template-columns: 1fr;
  }
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

.contest-delete-btn {
  border: 1px solid var(--color-border-danger);
  color: var(--color-text-danger);
  background: rgba(255, 255, 255, 0.65);
  padding: 6px 10px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  transition: filter 0.15s ease, background 0.15s ease;
}

.contest-order-actions {
  display: inline-flex;
  gap: 6px;
  margin-right: 8px;
}

.contest-order-btn {
  border: 1px solid var(--color-border-default);
  background: rgba(255, 255, 255, 0.65);
  padding: 6px 10px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
}

.contest-order-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.contest-delete-btn:hover {
  filter: brightness(0.98);
  background: rgba(255, 255, 255, 0.9);
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

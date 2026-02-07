<template>
  <div class="my-courses">
    <UiHeader />
    <div class="my-courses__content">
      <h1 class="my-courses__title">Мои курсы</h1>

      <div v-if="loading && !loaded" class="my-courses__loading">
        Загрузка...
      </div>

      <div v-else-if="error" class="my-courses__error">
        {{ error }}
      </div>

      <div v-else-if="!isAuthorized" class="section-card empty-state">
        <div class="empty-state__content">
          <h2 class="empty-state__title">Войдите в систему</h2>
          <p class="empty-state__text">
            Чтобы увидеть свои курсы, войдите в систему
          </p>
          <button
            class="button button--primary empty-state__button"
            @click="router.push('/login')"
          >
            Войти
          </button>
        </div>
      </div>

      <template v-else>
        <!-- Pinned courses -->
        <div v-if="pinned.length" class="section-card">
          <h2 class="section-card__title">📌 Закреплённые курсы</h2>
          <div class="course-grid">
            <div
              v-for="course in pinned"
              :key="'pin-' + course.id"
              class="course-card course-card--pinned"
            >
              <button
                type="button"
                class="course-card__body"
                @click="goToCourse(course.id)"
              >
                <span class="course-card__name">{{ course.title }}</span>
                <span v-if="course.role" class="course-card__role">{{ roleLabel(course.role) }}</span>
              </button>
              <button
                type="button"
                class="course-card__unpin"
                title="Открепить"
                @click.stop="handleUnpin(course.id)"
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        <!-- Teacher view: teaching courses -->
        <div v-if="teaching" class="section-card">
          <h2 class="section-card__title">Я преподаю</h2>
          <CourseList
            :courses="teaching.results"
            :pinned-ids="pinnedIds"
            @go="goToCourse"
            @pin="handlePin"
            @unpin="handleUnpin"
          />
          <Pagination
            v-if="teaching.count > pageSize"
            :current-page="teachingPage"
            :total-pages="Math.ceil(teaching.count / pageSize)"
            @change="p => loadTeaching(p)"
          />
        </div>

        <!-- Teacher view: studying courses -->
        <div v-if="studying" class="section-card">
          <h2 class="section-card__title">Я участник</h2>
          <CourseList
            :courses="studying.results"
            :pinned-ids="pinnedIds"
            @go="goToCourse"
            @pin="handlePin"
            @unpin="handleUnpin"
          />
          <Pagination
            v-if="studying.count > pageSize"
            :current-page="studyingPage"
            :total-pages="Math.ceil(studying.count / pageSize)"
            @change="p => loadStudying(p)"
          />
        </div>

        <!-- Student view: all courses -->
        <div v-if="courses" class="section-card">
          <h2 class="section-card__title">Недавние курсы</h2>
          <CourseList
            :courses="courses.results"
            :pinned-ids="pinnedIds"
            @go="goToCourse"
            @pin="handlePin"
            @unpin="handleUnpin"
          />
          <Pagination
            v-if="courses.count > pageSize"
            :current-page="coursesPage"
            :total-pages="Math.ceil(courses.count / pageSize)"
            @change="p => loadCourses(p)"
          />
        </div>

        <div v-if="!pinned.length && !teaching && !studying && (!courses || !courses.results.length)" class="section-card empty-state">
          <div class="empty-state__content">
            <h2 class="empty-state__title">Нет курсов</h2>
            <p class="empty-state__text">
              Вы ещё не участвуете ни в одном курсе
            </p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { courseApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import { useUserStore } from '@/stores/UserStore'

const router = useRouter()
const userStore = useUserStore()

const user = userStore.getCurrentUser()
const isAuthorized = computed(() => user.value != null)

const loading = ref(false)
const loaded = ref(false)
const error = ref(null)
const pageSize = 10

const pinned = ref([])
const teaching = ref(null)
const studying = ref(null)
const courses = ref(null)

const teachingPage = ref(1)
const studyingPage = ref(1)
const coursesPage = ref(1)

const pinnedIds = computed(() => new Set(pinned.value.map(c => c.id)))

const roleLabel = (role) => {
  return role === 'teacher' ? 'Преподаватель' : 'Ученик'
}

const goToCourse = (courseId) => {
  router.push({ name: 'course', params: { id: courseId } })
}

const loadAll = async () => {
  loading.value = true
  error.value = null
  try {
    const data = await courseApi.getMyCourses({ page: 1 })
    pinned.value = data.pinned || []
    if (data.teaching) {
      teaching.value = data.teaching
      studying.value = data.studying || { count: 0, results: [] }
      courses.value = null
    } else {
      courses.value = data.courses || { count: 0, results: [] }
      teaching.value = null
      studying.value = null
    }
    loaded.value = true
  } catch (err) {
    console.error('Failed to load my courses:', err)
    error.value = 'Не удалось загрузить курсы'
  } finally {
    loading.value = false
  }
}

const loadTeaching = async (page) => {
  try {
    const data = await courseApi.getMyCourses({ page, role: 'teacher' })
    teaching.value = data.courses || { count: 0, results: [] }
    teachingPage.value = page
  } catch (err) {
    console.error('Failed to load teaching courses:', err)
  }
}

const loadStudying = async (page) => {
  try {
    const data = await courseApi.getMyCourses({ page, role: 'student' })
    studying.value = data.courses || { count: 0, results: [] }
    studyingPage.value = page
  } catch (err) {
    console.error('Failed to load studying courses:', err)
  }
}

const loadCourses = async (page) => {
  try {
    const data = await courseApi.getMyCourses({ page })
    courses.value = data.courses || { count: 0, results: [] }
    coursesPage.value = page
  } catch (err) {
    console.error('Failed to load courses:', err)
  }
}

const handlePin = async (courseId) => {
  try {
    await courseApi.pinCourse(courseId)
    await loadAll()
  } catch (err) {
    console.error('Failed to pin course:', err)
  }
}

const handleUnpin = async (courseId) => {
  try {
    await courseApi.unpinCourse(courseId)
    await loadAll()
  } catch (err) {
    console.error('Failed to unpin course:', err)
  }
}

onMounted(() => {
  if (isAuthorized.value) {
    loadAll()
  }
})

/* Inline sub-components */

const CourseList = {
  props: {
    courses: { type: Array, default: () => [] },
    pinnedIds: { type: Set, default: () => new Set() },
  },
  emits: ['go', 'pin', 'unpin'],
  template: `
    <div v-if="courses.length === 0" class="course-list-empty">
      Нет курсов в этом разделе
    </div>
    <div v-else class="course-list">
      <div
        v-for="course in courses"
        :key="course.id"
        class="course-card"
      >
        <button
          type="button"
          class="course-card__body"
          @click="$emit('go', course.id)"
        >
          <span class="course-card__name">{{ course.title }}</span>
          <span v-if="course.role" class="course-card__role">
            {{ course.role === 'teacher' ? 'Преподаватель' : 'Ученик' }}
          </span>
        </button>
        <button
          v-if="pinnedIds.has(course.id)"
          type="button"
          class="course-card__pin-btn course-card__pin-btn--active"
          title="Открепить"
          @click.stop="$emit('unpin', course.id)"
        >
          📌
        </button>
        <button
          v-else
          type="button"
          class="course-card__pin-btn"
          title="Закрепить"
          @click.stop="$emit('pin', course.id)"
        >
          📌
        </button>
      </div>
    </div>
  `,
}

const Pagination = {
  props: {
    currentPage: { type: Number, required: true },
    totalPages: { type: Number, required: true },
  },
  emits: ['change'],
  template: `
    <div class="pagination">
      <button
        class="pagination__button"
        :disabled="currentPage === 1"
        @click="$emit('change', currentPage - 1)"
      >
        Предыдущая
      </button>
      <span class="pagination__info">
        Страница {{ currentPage }} из {{ totalPages }}
      </span>
      <button
        class="pagination__button"
        :disabled="currentPage === totalPages"
        @click="$emit('change', currentPage + 1)"
      >
        Следующая
      </button>
    </div>
  `,
}
</script>

<style scoped>
.my-courses {
  min-height: 100vh;
  padding: 0 0 24px;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

.my-courses__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.my-courses__title {
  font-size: 28px;
  font-weight: 600;
  color: var(--color-title-text);
  padding-left: 16px;
  border-left: 6px solid var(--color-primary);
}

.my-courses__loading,
.my-courses__error {
  padding: 40px;
  text-align: center;
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e5e9f1;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  font-size: 18px;
}

.my-courses__error {
  color: var(--color-error-text);
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 14px 16px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e9f1;
}

.section-card__title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-title-text);
  margin-bottom: 12px;
  padding: 6px 4px;
}

.course-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.course-card {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-button-secondary);
  border-radius: 8px;
  transition: filter 0.2s ease, transform 0.12s ease;
}

.course-card:hover {
  filter: brightness(0.98);
  transform: translateY(-1px);
}

.course-card--pinned {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-default);
}

.course-card__body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 9px 10px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  color: var(--color-text-primary);
  min-width: 0;
  flex: 1;
}

.course-card__name {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
}

.course-card__role {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.course-card__unpin,
.course-card__pin-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 8px;
  font-size: 14px;
  opacity: 0.4;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.course-card__unpin:hover,
.course-card__pin-btn:hover {
  opacity: 1;
}

.course-card__pin-btn--active {
  opacity: 0.8;
}

.course-card__pin-btn--active:hover {
  opacity: 1;
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.course-list-empty {
  padding: 16px;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 14px;
}

.pagination {
  margin-top: 16px;
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

.empty-state {
  text-align: center;
}

.empty-state__content {
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.empty-state__title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-title-text);
}

.empty-state__text {
  font-size: 16px;
  color: var(--color-text-primary);
  margin: 0;
}

.empty-state__button {
  margin-top: 8px;
  padding: 10px 24px;
}

@media (min-width: 900px) {
  .my-courses__content { padding: 28px 32px 0; }
}
</style>

<template>
  <div class="page">
    <UiHeader />
    <div class="page__content">
      <UiBreadcrumbs :section="section" />
      <div v-if="section" class="section-card">
        <div class="section-header-block">
          <h1 class="section-title">Раздел "{{ section.title }}"</h1>
          <p v-if="section.description" class="section-description">{{ section.description }}</p>
        </div>

        <div v-if="canCreateInSection || canDeleteSection" class="section-actions">
          <button
            v-if="canCreateInSection"
            class="button button--primary"
            type="button"
            @click="showCreateCourseDialog = true"
          >
            Создать курс
          </button>
          <button
            v-if="canCreateInSection"
            class="button button--secondary"
            type="button"
            @click="showCreateSectionDialog = true"
          >
            Создать раздел
          </button>
          <button
            v-if="canDeleteSection"
            class="button button--danger"
            type="button"
            @click="deleteThisSection"
          >
            Удалить раздел
          </button>
        </div>
        <div v-if="actionError" class="form-error">{{ actionError }}</div>

        <div v-if="hasChildren" class="section-content">
          <ul class="course-list">
            <li
              v-for="child in orderedChildren"
              :key="child.id"
              class="course-item"
            >
              <template v-if="hasChildrenItems(child)">
                <button
                  type="button"
                  class="section-header section-header--inline"
                  @click="toggleNested(child.id)"
                  :aria-expanded="isNestedOpen(child.id)"
                >
                  <span class="triangle triangle--nested" :class="{ 'triangle--open': isNestedOpen(child.id) }"></span>
                  <h2 class="course-title course-title--section">{{ child.title }}</h2>
                </button>
                <div v-if="isNestedOpen(child.id) && (child.children || []).length" class="badge-list">
                  <div v-for="grand in child.children" :key="grand.id" class="badge-row">
                    <button
                      type="button"
                      class="badge"
                      @click="navigateTo(grand)"
                    >
                      {{ grand.title }}
                    </button>
                    <button
                      v-if="isAuthorized && grand.type === 'course'"
                      type="button"
                      class="star-btn"
                      :class="{ 'star-btn--on': isFavoriteCourse(grand) }"
                      :title="isFavoriteCourse(grand) ? 'Убрать из избранного' : 'Добавить в избранное'"
                      @click.stop.prevent="toggleFavorite(grand)"
                    >
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path
                          d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27Z"
                          stroke="currentColor"
                          stroke-width="1.8"
                          stroke-linejoin="round"
                          :fill="isFavoriteCourse(grand) ? 'currentColor' : 'transparent'"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="course-row">
                  <button type="button" class="course-link" @click="navigateTo(child)">
                    {{ child.title }}
                  </button>
                  <button
                    v-if="isAuthorized && child.type === 'course'"
                    type="button"
                    class="star-btn"
                    :class="{ 'star-btn--on': isFavoriteCourse(child) }"
                    :title="isFavoriteCourse(child) ? 'Убрать из избранного' : 'Добавить в избранное'"
                    @click.stop.prevent="toggleFavorite(child)"
                  >
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path
                        d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27Z"
                        stroke="currentColor"
                        stroke-width="1.8"
                        stroke-linejoin="round"
                        :fill="isFavoriteCourse(child) ? 'currentColor' : 'transparent'"
                      />
                    </svg>
                  </button>
                </div>
              </template>
            </li>
          </ul>
        </div>
        <div v-else class="empty-state">
          <p class="empty-state__text">В этом разделе пока нет курсов или подразделов</p>
        </div>
      </div>
      <div v-else-if="loading" class="section-card">
        <p>Загрузка...</p>
      </div>
      <div v-else class="section-card empty-state">
        <p class="empty-state__text">Раздел не найден или доступ к нему запрещён</p>
      </div>

      <!-- Create Course Dialog -->
      <div v-if="showCreateCourseDialog" class="dialog-overlay" @click="closeDialogs">
        <div class="dialog" @click.stop>
          <div class="dialog__header">
            <h2 class="dialog__title">Создать курс</h2>
            <button class="dialog__close" @click="closeDialogs">×</button>
          </div>
          <div class="dialog__body">
            <div class="form-group">
              <label class="form-label">Название курса *</label>
              <input
                v-model="newCourse.title"
                type="text"
                class="form-input"
                placeholder="Введите название"
                @keyup.enter="createCourse"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Описание</label>
              <textarea
                v-model="newCourse.description"
                class="form-textarea"
                placeholder="Описание курса (необязательно)"
                rows="4"
              ></textarea>
            </div>
            <div class="form-group">
              <label class="form-checkbox">
                <input type="checkbox" v-model="newCourse.is_open" />
                <span>Открытый курс (виден всем)</span>
              </label>
            </div>
            <div v-if="createError" class="form-error">{{ createError }}</div>
          </div>
          <div class="dialog__footer">
            <button class="button button--secondary" @click="closeDialogs">Отмена</button>
            <button class="button button--primary" @click="createCourse" :disabled="isCreating || !newCourse.title.trim()">
              {{ isCreating ? 'Создание...' : 'Создать' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Create Section Dialog -->
      <div v-if="showCreateSectionDialog" class="dialog-overlay" @click="closeDialogs">
        <div class="dialog" @click.stop>
          <div class="dialog__header">
            <h2 class="dialog__title">Создать раздел</h2>
            <button class="dialog__close" @click="closeDialogs">×</button>
          </div>
          <div class="dialog__body">
            <div class="form-group">
              <label class="form-label">Название раздела *</label>
              <input
                v-model="newSection.title"
                type="text"
                class="form-input"
                placeholder="Введите название"
                @keyup.enter="createSubsection"
              />
            </div>
            <div class="form-group">
              <label class="form-label">Описание</label>
              <textarea
                v-model="newSection.description"
                class="form-textarea"
                placeholder="Описание раздела (необязательно)"
                rows="4"
              ></textarea>
            </div>
            <div v-if="createError" class="form-error">{{ createError }}</div>
          </div>
          <div class="dialog__footer">
            <button class="button button--secondary" @click="closeDialogs">Отмена</button>
            <button class="button button--primary" @click="createSubsection" :disabled="isCreating || !newSection.title.trim()">
              {{ isCreating ? 'Создание...' : 'Создать' }}
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="loading" class="section-card">
        <p>Загрузка...</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { courseApi, homeApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'
import { useUserStore } from '@/stores/UserStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const id = computed(() => route.params.id)

const courses = ref([])
const section = ref(null)
const loading = ref(true)
const openNested = ref({})

const showCreateCourseDialog = ref(false)
const showCreateSectionDialog = ref(false)
const isCreating = ref(false)
const createError = ref('')
const actionError = ref('')

const newCourse = ref({
  title: '',
  description: '',
  is_open: false,
})

const newSection = ref({
  title: '',
  description: '',
})

const hasChildrenItems = item => Array.isArray(item?.children) && item.children.length > 0

const hasChildren = computed(() => {
  return section.value && hasChildrenItems(section.value)
})

const orderedChildren = computed(() => {
  if (!section.value?.children) return []
  const list = section.value.children
  return [
    ...list.filter(item => hasChildrenItems(item)),
    ...list.filter(item => !hasChildrenItems(item)),
  ]
})

const isAuthorized = computed(() => !!userStore.currentUser)
const isTeacher = computed(() => String(userStore.currentUser?.role || '') === 'teacher')
const canDeleteSection = computed(() => {
  if (!isAuthorized.value || !section.value) return false
  if (section.value.is_root) return false
  return Number(section.value.owner_id) === Number(userStore.currentUser.id)
})

const canCreateInSection = computed(() => {
  if (!isAuthorized.value || !section.value) return false
  if (typeof section.value.can_manage === 'boolean') return section.value.can_manage
  if (section.value.is_root) return isTeacher.value
  return Number(section.value.owner_id) === Number(userStore.currentUser.id)
})

const isFavoriteCourse = (c) => {
  if (!c || c.type !== 'course') return false
  return !!c.is_favorite
}

const toggleFavorite = async (course) => {
  if (!isAuthorized.value || !course || course.type !== 'course') return
  try {
    const cid = Number(course.id)
    isFavoriteCourse(course)
      ? await homeApi.removeFavoriteCourse(cid)
      : await homeApi.addFavoriteCourse(cid)
    // Backend will reflect is_favorite in the tree; refresh to keep UI consistent.
    await load()
    actionError.value = ''
  } catch (err) {
    console.error('Failed to toggle favorite', err)
    actionError.value = err?.message || 'Не удалось обновить избранное'
  }
}

const isNestedOpen = nestedId => !!openNested.value[String(nestedId)]
const toggleNested = nestedId => {
  const key = String(nestedId)
  openNested.value = { ...openNested.value, [key]: !openNested.value[key] }
}

const navigateTo = (item) => {
  // Use the type field from API to determine route, fallback to section for non-course types
  const name = item.type === 'course' ? 'course' : 'section'
  router.push({ name, params: { id: item.id }, query: { title: item.title } })
}

const findSectionById = (items, targetId) => {
  // Convert targetId to number for comparison
  const numericId = Number(targetId)
  for (const item of items) {
    if (item.id === numericId && item.type === 'section') {
      return item
    }
    if (item.children) {
      const found = findSectionById(item.children, numericId)
      if (found) return found
    }
  }
  return null
}

const load = async () => {
  try {
    loading.value = true
    const data = await courseApi.getCourses()
    courses.value = Array.isArray(data) ? data : []
    section.value = findSectionById(courses.value, id.value)
  } catch (err) {
    console.error('Не удалось загрузить раздел', err)
  } finally {
    loading.value = false
  }
}

const closeDialogs = () => {
  showCreateCourseDialog.value = false
  showCreateSectionDialog.value = false
  createError.value = ''
  actionError.value = ''
  isCreating.value = false
  newCourse.value = { title: '', description: '', is_open: false }
  newSection.value = { title: '', description: '' }
}

const deleteThisSection = async () => {
  if (!canDeleteSection.value) return
  if (!confirm('Удалить раздел? Будут удалены все курсы и подразделы внутри.')) return
  try {
    await courseApi.deleteSection(Number(section.value.id))
    router.push({ name: 'home' })
  } catch (err) {
    console.error('Не удалось удалить раздел', err)
    actionError.value = err?.message || 'Не удалось удалить раздел'
  }
}

const createCourse = async () => {
  if (!canCreateInSection.value) return
  const title = newCourse.value.title.trim()
  if (!title) {
    createError.value = 'Название курса обязательно'
    return
  }

  isCreating.value = true
  createError.value = ''
  try {
    const res = await courseApi.createCourse({
      title,
      description: newCourse.value.description || '',
      is_open: !!newCourse.value.is_open,
      section_id: Number(section.value.id),
    })
    closeDialogs()
    if (res?.id) {
      router.push({ name: 'course', params: { id: res.id }, query: { title: res.title } })
    } else {
      await load()
    }
  } catch (err) {
    console.error('Не удалось создать курс', err)
    createError.value = err?.message || 'Не удалось создать курс'
  } finally {
    isCreating.value = false
  }
}

const createSubsection = async () => {
  if (!canCreateInSection.value) return
  const title = newSection.value.title.trim()
  if (!title) {
    createError.value = 'Название раздела обязательно'
    return
  }

  isCreating.value = true
  createError.value = ''
  try {
    await courseApi.createSection({
      title,
      description: newSection.value.description || '',
      parent_id: Number(section.value.id),
    })
    closeDialogs()
    await load()
  } catch (err) {
    console.error('Не удалось создать раздел', err)
    createError.value = err?.message || 'Не удалось создать раздел'
  } finally {
    isCreating.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 0 0 24px;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

.page__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 14px 16px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e9f1;
}

.section-header-block {
  padding: 6px 4px 16px;
  border-bottom: 1px solid #e5e9f1;
  margin-bottom: 16px;
}

.section-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding: 0 4px 16px;
}

.button--danger {
  background: #fff;
  border: 1px solid #e23b3b;
  color: #e23b3b;
}

.button--danger:hover {
  opacity: 0.9;
}

/* Dialog styles (mirrors CoursePage/ContestPage patterns) */
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
  max-width: 650px;
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

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  outline: none;
  border-color: var(--color-primary, #3b82f6);
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

.section-title {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-text-title);
  margin: 0 0 8px;
}

.section-description {
  font-size: 16px;
  line-height: 1.5;
  color: var(--color-text-primary);
  margin: 0;
}

.section-content {
  margin-top: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  background: none;
  padding: 6px 4px 10px;
  text-align: left;
  color: var(--color-text-title);
}

.section-header--inline {
  padding: 0;
  gap: 8px;
  color: var(--color-text-primary);
}

.course-title {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.4;
  color: var(--color-text-primary);
}

.course-title--section {
  font-weight: 500;
}

.triangle {
  width: 0;
  height: 0;
  border-left: 7px solid var(--color-text-primary);
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  transition: transform 0.2s ease;
}

.triangle--open { 
  transform: rotate(90deg); 
}

.triangle--nested { 
  border-left-width: 6px; 
  border-top-width: 4px; 
  border-bottom-width: 4px; 
}

.course-list {
  margin-left: 12px;
  padding-left: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.course-item {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: inherit;
}

.course-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.badge-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.badge-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding-left: 16px;
  width: 100%;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 9px 10px;
  background: var(--color-button-secondary);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
}

.course-link {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.4;
  color: var(--color-text-primary);
  background: none;
  padding: 6px 0;
  text-align: left;
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

.course-link:hover,
.badge:hover {
  opacity: 0.9;
}

.empty-state {
  padding: 16px 0;
}

.empty-state__text {
  font-size: 16px;
  color: var(--color-text-primary);
  margin: 0;
  text-align: center;
}

@media (min-width: 900px) {
  .page__content { 
    padding: 28px 32px 0; 
  }
}
</style>

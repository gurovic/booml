<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <UiBreadcrumbs :section="section" />

      <section class="contest-panel">
        <div v-if="loading" class="state">Загрузка...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>

        <template v-else-if="section">
          <div class="course-header">
            <div class="course-title-row">
              <h1 class="course-title">Раздел "{{ sectionTitle }}"</h1>
            </div>

            <div v-if="canCreateInSection || canDeleteSection" class="course-header__actions">
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
          </div>

          <div v-if="section.description" class="contest-description">
            {{ section.description }}
          </div>
          <div v-if="actionError" class="state state--error">{{ actionError }}</div>

          <div v-if="hasChildren" class="menu-list">
            <ul class="course-list course-list--tree">
              <CourseTreeNode
                v-for="child in orderedChildren"
                :key="child.id"
                :node="child"
                :level="0"
                :open-state="openNested"
                :show-favorite="isAuthorized"
                :is-favorite="isFavoriteCourse"
                @toggle-section="toggleNested"
                @navigate="navigateTo"
                @toggle-favorite="toggleFavorite"
              />
            </ul>
          </div>
          <p v-else class="note">В этом разделе пока нет курсов или подразделов</p>
        </template>

        <div v-else class="state state--error">Раздел не найден или доступ к нему запрещён</div>
      </section>

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
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { courseApi, homeApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'
import CourseTreeNode from '@/components/ui/CourseTreeNode.vue'
import { useUserStore } from '@/stores/UserStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const id = computed(() => Number(route.params.id))

const courses = ref([])
const section = ref(null)
const loading = ref(true)
const error = ref('')
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

const sectionTitle = computed(() => {
  if (section.value?.title) return section.value.title
  const q = String(route.query?.title || '').trim()
  if (q) return q
  return Number.isFinite(id.value) && id.value > 0 ? `Раздел ${id.value}` : 'Раздел'
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

const toggleNested = nestedId => {
  const key = String(nestedId)
  openNested.value = { ...openNested.value, [key]: !openNested.value[key] }
}

const navigateTo = (item) => {
  // Use the type field from API to determine route, fallback to section for non-course types
  const name = item.type === 'course' ? 'course' : 'section'
  router.push({ name, params: { id: Number(item.id) }, query: { title: item.title } })
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
    error.value = ''
    const data = await courseApi.getCourses()
    courses.value = Array.isArray(data) ? data : []
    section.value = findSectionById(courses.value, id.value)
  } catch (err) {
    console.error('Не удалось загрузить раздел', err)
    error.value = err?.message || 'Не удалось загрузить раздел'
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

watch(
  () => Number(route.params.id),
  async (next, prev) => {
    // Component instance is reused for /section/:id; reload on param changes.
    if (!Number.isFinite(next)) return
    if (prev == null) return
    if (next === prev) return
    openNested.value = {}
    await load()
  }
)

onMounted(load)
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
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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
  background: var(--color-bg-primary);
  border-radius: 10px;
  border: 1px solid var(--color-border-light);
  font-size: 14px;
  color: var(--color-text-muted);
}

.contest-description {
  padding: 12px 16px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border-default);
  color: var(--color-text-muted);
  font-size: 15px;
  line-height: 1.5;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
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

.course-header__actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.menu-list {
  width: 100%;
  border-radius: 12px;
  padding: 0 16px;
  color: var(--color-text-primary);
}

.menu-list h2 {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
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
  padding: 0;
  margin: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.course-list--tree {
  gap: 8px;
}

.course-item {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: inherit;
}

.nested-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-button-secondary);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.section-toggle {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border-default, #e5e9f1);
  background: #fff;
  border-radius: 10px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.section-toggle:disabled {
  opacity: 0.5;
  cursor: default;
}

.section-toggle--nested {
  width: 28px;
  height: 28px;
  border-radius: 8px;
}

.course-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-button-secondary);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.course-row--section {
  border-color: rgba(39, 52, 106, 0.30);
}

.course-row--course {
  border-color: rgba(224, 227, 240, 0.45);
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
  border: none;
  cursor: pointer;
}

.row-link {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--color-text-primary);
  background: none;
  border: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  flex: 1 1 auto;
  min-width: 0;
}

.row-link--section {
  font-weight: 700;
  color: rgba(22, 33, 89, 0.92);
}

.row-link--course {
  font-weight: 600;
  color: rgba(22, 33, 89, 0.92);
}

.row-icon {
  flex: 0 0 auto;
  color: rgba(22, 33, 89, 0.70);
}

.row-icon--section {
  color: rgba(37, 99, 235, 0.95);
}

.row-icon--course {
  color: rgba(22, 33, 89, 0.80);
}

.row-text {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

.row-link:hover,
.badge:hover {
  opacity: 0.9;
}

@media (min-width: 900px) {
  .contest-content { 
    padding: 28px 32px 40px; 
  }
}
</style>

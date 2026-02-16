<template>
  <div class="home">
    <UiHeader />
    <div class="home__content">
      <div class="home__layout">
        <div class="home__main">
          <div v-for="section in sections" :key="section.id" class="section-card">
            <div class="section-header-row">
              <button
                type="button"
                class="section-toggle"
                :disabled="!(section.children || []).length"
                @click="toggleSection(section.id)"
                :aria-expanded="isSectionOpen(section.id)"
                aria-label="Раскрыть/свернуть"
              >
                <span class="triangle" :class="{ 'triangle--open': isSectionOpen(section.id) }"></span>
              </button>
              <button type="button" class="section-title-btn" @click="goToCourse(section)">
                <h2 class="section-title">{{ section.title }}</h2>
              </button>
              <button
                v-if="canEditSection(section)"
                type="button"
                class="button button--primary"
                @click="goToCourse(section)"
                title="Редактировать раздел"
              >
                Редактировать
              </button>
            </div>

            <ul v-if="isSectionOpen(section.id)" class="course-list course-list--tree">
              <CourseTreeNode
                v-for="child in orderedChildren(section)"
                :key="child.id"
                :node="child"
                :level="0"
                :open-state="openNested"
                :show-favorite="isAuthorized"
                :is-favorite="isFavoriteNode"
                @toggle-section="toggleNested"
                @navigate="goToCourse"
                @toggle-favorite="toggleFavorite"
              />
            </ul>
          </div>

          <div v-if="standalone.length && isAuthorized" class="section-card">
            <div class="section-header-row">
              <button
                type="button"
                class="section-toggle"
                :disabled="!standalone.length"
                @click="standaloneOpen = !standaloneOpen"
                :aria-expanded="standaloneOpen"
                aria-label="Раскрыть/свернуть"
              >
                <span class="triangle" :class="{ 'triangle--open': standaloneOpen }"></span>
              </button>
              <div class="section-title-btn section-title-btn--static">
                <h2 class="section-title">Курсы без раздела</h2>
              </div>
            </div>
            <ul v-if="standaloneOpen" class="course-list course-list--tree">
              <CourseTreeNode
                v-for="course in standalone"
                :key="course.id"
                :node="course"
                :level="0"
                :open-state="openNested"
                :show-favorite="isAuthorized"
                :is-favorite="isFavoriteNode"
                @navigate="goToCourse"
                @toggle-favorite="toggleFavorite"
              />
            </ul>
          </div>

          <div v-if="(!sections.length && !standalone.length) || (!isAuthorized)" class="section-card empty-state">
            <div class="empty-state__content">
              <h2 class="empty-state__title">Нет доступных курсов</h2>
              <p class="empty-state__text">
                Войдите в систему, чтобы увидеть доступные курсы
              </p>
              <button
                class="button button--primary empty-state__button"
                @click="router.push('/login')"
              >
                Войти
              </button>
            </div>
          </div>
        </div>

        <aside v-if="isAuthorized" class="home__sidebar">
          <div class="section-card side-card">
            <div class="side-card__header">
              <h3 class="side-card__title">Избранные курсы</h3>
            </div>
            <div v-if="sidebarLoading" class="side-state">Загрузка...</div>
            <div v-else-if="favorites.length === 0" class="side-state">Пока пусто</div>
            <ul v-else class="fav-list">
              <li
                v-for="(fav, idx) in favorites"
                :key="fav.course_id"
                class="fav-item"
                :class="favoriteDragClass(idx)"
                @dragover.prevent="onFavoriteDragOver(idx, $event)"
                @drop.prevent="onFavoriteDrop(idx)"
                @dragleave="onFavoriteDragLeave(idx)"
              >
                <button
                  v-if="favorites.length > 1"
                  class="fav-btn fav-btn--drag"
                  type="button"
                  title="Перетащить"
                  aria-label="Перетащить"
                  draggable="true"
                  @click.stop.prevent
                  @dragstart="onFavoriteDragStart(idx, $event)"
                  @dragend="onFavoriteDragEnd"
                >
                  <span class="material-symbols-rounded" aria-hidden="true">drag_indicator</span>
                </button>
                <button type="button" class="fav-link" @click="goToCourse({ id: fav.course_id, title: fav.title, type: 'course' })">
                  {{ fav.title }}
                </button>
                <div class="fav-actions">
                  <button class="fav-btn fav-btn--danger" type="button" title="Удалить" @click="removeFavorite(fav.course_id)">✕</button>
                </div>
              </li>
            </ul>
            <div v-if="favoriteError" class="form-error">{{ favoriteError }}</div>
          </div>

          <div class="section-card side-card">
            <div class="side-card__header">
              <h3 class="side-card__title">Недавние задачи</h3>
            </div>
            <div v-if="sidebarLoading" class="side-state">Загрузка...</div>
            <div v-else-if="recentProblems.length === 0" class="side-state">Пока нет посылок</div>
            <ul v-else class="recent-list">
              <li v-for="item in recentProblems" :key="item.problem_id" class="recent-item">
                <button type="button" class="recent-link" @click="goToProblem(item)" :title="item.title">
                  <UiIdPill class="recent-id" :id="item.problem_id" title="ID задачи" />
                  <span class="recent-title">{{ item.title }}</span>
                </button>
                <div class="recent-meta">
                  <div v-if="item.last_submitted_at" class="recent-time">
                    {{ formatDate(item.last_submitted_at) }}
                  </div>
                  <div v-if="item.last_score != null" class="recent-score">
                    Скор: {{ formatScore(item.last_score) }}
                  </div>
                </div>
              </li>
            </ul>
          </div>

          <div class="section-card side-card">
            <div class="side-card__header">
              <h3 class="side-card__title">Свежие обновления</h3>
            </div>
            <div v-if="sidebarLoading" class="side-state">Загрузка...</div>
            <div v-else-if="updates.length === 0" class="side-state">Пока нет новостей</div>
            <ul v-else class="updates-list">
              <li v-for="u in updates" :key="u.id" class="update-item">
                <div class="update-title">{{ u.title }}</div>
                <div v-if="u.created_at" class="update-time">{{ formatDate(u.created_at) }}</div>
                <div v-if="u.body" class="update-body">{{ u.body }}</div>
              </li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { courseApi, homeApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiIdPill from '@/components/ui/UiIdPill.vue'
import CourseTreeNode from '@/components/ui/CourseTreeNode.vue'
import { useUserStore } from '@/stores/UserStore'
import { formatDateTimeMsk } from '@/utils/datetime'
import { arrayMove } from '@/utils/arrayMove'

const courses = ref([])
const openSections = ref({})
const openNested = ref({})
const standaloneOpen = ref(true)
const sidebarLoading = ref(false)
const favorites = ref([])
const recentProblems = ref([])
const updates = ref([])
const favoriteError = ref('')
const draggingFavoriteIdx = ref(null)
const dragOverFavoriteIdx = ref(null)
const dragOverFavoritePos = ref('before') // 'before' | 'after'
const router = useRouter()
const userStore = useUserStore()

let user = userStore.getCurrentUser()
let isAuthorized = computed(() => user.value != null)
const isTeacher = computed(() => String(userStore.currentUser?.role || '') === 'teacher')

const canEditSection = (s) => {
  if (!isAuthorized.value) return false
  if (!s) return false
  // Prefer server-side permission flag when present.
  if (typeof s.can_manage === 'boolean') return s.can_manage
  if (s.is_root) return isTeacher.value
  return Number(s.owner_id) === Number(userStore.currentUser?.id)
}

const hasChildren = item => Array.isArray(item?.children) && item.children.length > 0
// Root nodes from the API are sections; render them even if empty so teachers can add content.
const sections = computed(() => courses.value.filter(item => item?.type === 'section'))
const standalone = computed(() => courses.value.filter(item => item?.type !== 'section'))

const orderedChildren = section => {
  const list = section.children || []
  return [
    ...list.filter(item => hasChildren(item)),
    ...list.filter(item => !hasChildren(item)),
  ]
}

const isSectionOpen = id => !!openSections.value[String(id)]
const toggleSection = id => {
  const key = String(id)
  openSections.value = { ...openSections.value, [key]: !openSections.value[key] }
}

const toggleNested = id => {
  const key = String(id)
  openNested.value = { ...openNested.value, [key]: !openNested.value[key] }
}

const goToCourse = (item) => {
  // Use the type field from API to determine route, fallback to checking children
  const name = item.type === 'course' ? 'course' : 'section'
  router.push({ name, params: { id: item.id }, query: { title: item.title } })
}

const goToProblem = (itemOrId, title) => {
  // goToProblem(item) OR goToProblem(id, title)
  let problemId = itemOrId
  let contestId = null
  let courseTitle = null
  let contestTitle = null

  if (itemOrId && typeof itemOrId === 'object') {
    problemId = itemOrId.problem_id
    contestId = itemOrId.contest_id
    courseTitle = itemOrId.course_title
    contestTitle = itemOrId.contest_title
    title = itemOrId.title
  }

  const query = {}
  if (contestId != null) query.contest = contestId
  // Optional hints for breadcrumbs fallbacks.
  if (courseTitle) query.course_title = courseTitle
  if (contestTitle) query.title = contestTitle
  if (Object.keys(query).length === 0 && title) query.title = title

  router.push({ name: 'problem', params: { id: problemId }, query })
}

const formatDate = (iso) => formatDateTimeMsk(iso)
const formatScore = (v) => {
  if (v == null) return ''
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v)
  // Keep it compact, but deterministic.
  const s = n.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')
  return s
}

const isFavorite = (courseId) => {
  const cid = Number(courseId)
  return favorites.value.some(x => Number(x.course_id) === cid)
}
const isFavoriteNode = (item) => isFavorite(item?.id)

const loadSidebar = async () => {
  if (!isAuthorized.value) {
    favorites.value = []
    recentProblems.value = []
    updates.value = []
    return
  }

  sidebarLoading.value = true
  try {
    const data = await homeApi.getHomeSidebar()
    favorites.value = Array.isArray(data?.favorites) ? data.favorites : []
    recentProblems.value = Array.isArray(data?.recent_problems) ? data.recent_problems : []
    updates.value = Array.isArray(data?.updates) ? data.updates : []
  } catch (err) {
    console.error('Не удалось загрузить сайдбар', err)
  } finally {
    sidebarLoading.value = false
  }
}

const _friendlyFavoriteError = (err) => {
  const msg = String(err?.message || '')
  if (msg.includes('Favorites limit')) return 'Лимит избранного: максимум 5 курсов'
  return err?.message || 'Не удалось обновить избранное'
}

const toggleFavorite = async (course) => {
  if (!isAuthorized.value || course?.type !== 'course') return
  favoriteError.value = ''

  try {
    const cid = Number(course.id)
    const res = isFavorite(cid)
      ? await homeApi.removeFavoriteCourse(cid)
      : await homeApi.addFavoriteCourse(cid)
    const items = Array.isArray(res?.items) ? res.items : []
    if (items.length) favorites.value = items
    else await loadSidebar()
  } catch (err) {
    console.error('Failed to toggle favorite', err)
    favoriteError.value = _friendlyFavoriteError(err)
    await loadSidebar()
  }
}

const removeFavorite = async (courseId) => {
  if (!isAuthorized.value) return
  favoriteError.value = ''
  try {
    const res = await homeApi.removeFavoriteCourse(Number(courseId))
    favorites.value = Array.isArray(res?.items) ? res.items : []
  } catch (err) {
    console.error('Failed to remove favorite', err)
    favoriteError.value = _friendlyFavoriteError(err)
    await loadSidebar()
  }
}

const favoriteDragClass = (idx) => {
  if (favorites.value.length <= 1) return {}
  return {
    'fav-item--dragging': draggingFavoriteIdx.value === idx,
    'fav-item--drag-over-before': dragOverFavoriteIdx.value === idx && dragOverFavoritePos.value === 'before',
    'fav-item--drag-over-after': dragOverFavoriteIdx.value === idx && dragOverFavoritePos.value === 'after',
  }
}

const onFavoriteDragStart = (idx, e) => {
  if (favorites.value.length <= 1) return
  draggingFavoriteIdx.value = idx
  dragOverFavoriteIdx.value = idx
  dragOverFavoritePos.value = 'before'
  try {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(idx))
  } catch (_) {
    // ignore
  }
}

const onFavoriteDragEnd = () => {
  draggingFavoriteIdx.value = null
  dragOverFavoriteIdx.value = null
  dragOverFavoritePos.value = 'before'
}

const onFavoriteDragOver = (idx, e) => {
  if (favorites.value.length <= 1) return
  if (draggingFavoriteIdx.value == null) return
  dragOverFavoriteIdx.value = idx

  const rect = e.currentTarget?.getBoundingClientRect?.()
  if (!rect) return
  const mid = rect.top + rect.height / 2
  dragOverFavoritePos.value = e.clientY > mid ? 'after' : 'before'
}

const onFavoriteDragLeave = (idx) => {
  if (dragOverFavoriteIdx.value === idx) dragOverFavoriteIdx.value = null
}

const onFavoriteDrop = async (targetIdx) => {
  const from = draggingFavoriteIdx.value
  if (from == null) return

  const list = Array.isArray(favorites.value) ? [...favorites.value] : []
  if (!list.length) return onFavoriteDragEnd()

  const target = Number(targetIdx)
  const f = Number(from)
  const pos = dragOverFavoritePos.value

  let to
  if (pos === 'before') {
    to = f < target ? target - 1 : target
  } else {
    to = f < target ? target : target + 1
  }
  const max = list.length - 1
  to = Math.max(0, Math.min(to, max))

  if (!Number.isInteger(f) || !Number.isInteger(to) || f === to) return onFavoriteDragEnd()

  const prev = favorites.value
  const next = arrayMove(list, f, to)
  favorites.value = next

  try {
    const res = await homeApi.reorderFavoriteCourses(next.map(x => x.course_id))
    favorites.value = Array.isArray(res?.items) ? res.items : next
  } catch (err) {
    console.error('Failed to reorder favorites', err)
    favorites.value = prev
    favoriteError.value = _friendlyFavoriteError(err)
    await loadSidebar()
  } finally {
    onFavoriteDragEnd()
  }
}

const load = async () => {
  try {
    const data = await courseApi.getCourses()
    courses.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('Не удалось загрузить курсы', err)
  }
}

onMounted(load)
onMounted(loadSidebar)
</script>

<style scoped>
.home {
  min-height: 100vh;
  padding: 0 0 24px;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

.home__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 10px 16px 0;
}

.home__layout {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.home__main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.home__sidebar {
  flex: 0 0 360px;
  width: 360px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 92px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 10px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e9f1;
}

/* legacy class, kept for other inline sections if any */
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1 1 auto;
  min-width: 0;
  background: none;
  padding: 6px 4px 10px;
  text-align: left;
  color: var(--color-text-title);
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-toggle {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border: 1px solid var(--color-border-default);
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

.section-title-btn {
  flex: 1 1 auto;
  min-width: 0;
  background: none;
  border: none;
  padding: 6px 4px 10px;
  text-align: left;
  cursor: pointer;
  color: var(--color-text-title);
}

.section-title-btn--static {
  cursor: default;
}

.nested-header-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.section-toggle--nested {
  width: 28px;
  height: 28px;
  border-radius: 8px;
}

.section-open-btn {
  flex: 0 0 auto;
  border: 1px solid var(--color-border-default);
  background: #fff;
  color: var(--color-text-primary);
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
}

.section-open-btn:hover {
  opacity: 0.9;
}

.section-header--inline {
  padding: 0;
  gap: 8px;
  color: var(--color-text-primary);
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.course-title {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.4;
  color: var(--color-text-primary);
}

.triangle {
  width: 0;
  height: 0;
  border-left: 7px solid var(--color-text-primary);
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  transition: transform 0.2s ease;
}

.triangle--open { transform: rotate(90deg); }
.triangle--nested { border-left-width: 6px; border-top-width: 4px; border-bottom-width: 4px; }

.course-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  list-style: none;
  padding: 0;
  margin: 8px 0 0;
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
  gap: 10px;
  padding: 9px 10px;
  background: var(--color-button-secondary);
  border-radius: 8px;
  border: 1px solid var(--color-border-default);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  flex: 1 1 auto;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.course-link {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 400;
  line-height: 1.4;
  color: var(--color-text-primary);
  background: none;
  border: none;
  padding: 6px 0;
  text-align: left;
  flex: 1 1 auto;
  cursor: pointer;
  min-width: 0;
}

.course-link--section {
  font-weight: 500;
}

.item-icon {
  flex: 0 0 auto;
  color: rgba(22, 33, 89, 0.70);
}

.item-icon--section {
  color: rgba(37, 99, 235, 0.95);
}

.item-icon--course {
  color: rgba(22, 33, 89, 0.80);
}

.item-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.course-link:hover,
.badge:hover {
  opacity: 0.9;
}

.star-btn {
  border: 1px solid var(--color-border-default, #e0e0e0);
  background: #fff;
  color: var(--color-text-muted, #666);
  border-radius: 10px;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex: 0 0 auto;
}

.star-btn:hover {
  border-color: var(--color-primary, #3b82f6);
  color: var(--color-text-primary, #000);
}

.star-btn--on {
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.45);
  background: rgba(251, 191, 36, 0.12);
}

.side-card__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.side-card__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}
.side-card {
  padding: 20px;
  border-radius: 20px;
}
.side-state {
  color: var(--color-text-muted);
  font-size: 14px;
  padding: 6px 2px;
}

.fav-list,
.recent-list,
.updates-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.fav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid #e5e9f1;
  background: var(--color-button-secondary);
  position: relative;
}

.fav-item--dragging {
  opacity: 0.65;
}

.fav-item--drag-over-before::before,
.fav-item--drag-over-after::after {
  content: '';
  position: absolute;
  left: 10px;
  right: 10px;
  height: 2px;
  background: var(--color-primary, #2f6fed);
  border-radius: 2px;
}

.fav-item--drag-over-before::before {
  top: -2px;
}

.fav-item--drag-over-after::after {
  bottom: -2px;
}

.fav-link {
  text-align: left;
  background: transparent;
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.35;
  padding: 6px 8px;
  border-radius: 10px;
  flex: 1 1 auto;
  cursor: pointer;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fav-link:hover {
  background: var(--color-button-secondary-hover);
}

.fav-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
}

.fav-btn {
  border: 1px solid var(--color-border-default, #e0e0e0);
  background: #fff;
  padding: 6px 8px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
}

.fav-btn--drag {
  width: 26px;
  height: 26px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  border-radius: 9px;
  margin-right: 2px;
  background: rgba(255, 255, 255, 0.55);
}

.fav-btn--drag:active {
  cursor: grabbing;
}

.fav-btn--drag :deep(.material-symbols-rounded) {
  font-size: 18px;
  line-height: 1;
}

.fav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fav-btn--danger {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.08);
  color: rgb(185, 28, 28);
}

@media (hover: hover) and (pointer: fine) {
  .fav-btn--danger {
    display: none;
  }

  .fav-item:hover .fav-btn--danger,
  .fav-item:focus-within .fav-btn--danger {
    display: inline-flex;
  }
}

.recent-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid #e5e9f1;
  background: var(--color-button-secondary);
}

.recent-link {
  text-align: left;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: transparent;
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.35;
  padding: 6px 8px;
  border-radius: 10px;
  cursor: pointer;
  min-width: 0;
}

.recent-id {
  flex: 0 0 auto;
}

.recent-title {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-link:hover {
  background: var(--color-button-secondary-hover);
}

.recent-time {
  font-size: 12px;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.recent-meta {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 0 8px;
}

.recent-score {
  font-size: 12px;
  color: var(--color-text-primary);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.update-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 10px;
  border: 1px solid #e5e9f1;
  border-radius: 12px;
  background: rgba(245, 247, 255, 0.6);
}

.update-title {
  font-size: 14px;
  font-weight: 700;
}

.update-time {
  font-size: 12px;
  color: var(--color-text-muted);
}

.update-body {
  font-size: 13px;
  color: var(--color-text-primary);
  white-space: pre-wrap;
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
  color: var(--color-text-title);
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
  .home__content { padding: 10px 32px 0; }
}

@media (max-width: 960px) {
  .home__layout { flex-direction: column; }
  .home__sidebar { width: 100%; flex: 0 0 auto; position: static; top: auto; }
}
</style>

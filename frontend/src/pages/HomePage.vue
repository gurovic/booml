<template>
  <div class="home">
    <UiHeader />
    <div class="home__content">
      <div class="home__layout">
        <div class="home__main">
          <div v-for="section in sections" :key="section.id" class="section-card">
            <div class="section-header-row">
              <button type="button" class="section-header" @click="toggleSection(section.id)">
                <span class="triangle" :class="{ 'triangle--open': isSectionOpen(section.id) }"></span>
                <h2 class="section-title">{{ section.title }}</h2>
              </button>
              <button
                v-if="isAuthorized"
                type="button"
                class="section-open-btn"
                @click="goToCourse(section)"
                title="Открыть страницу раздела"
              >
                Открыть
              </button>
            </div>

            <ul v-if="isSectionOpen(section.id)" class="course-list">
              <li
                v-for="child in orderedChildren(section)"
                :key="child.id"
                class="course-item"
              >
                <template v-if="hasChildren(child)">
                  <button type="button" class="section-header section-header--inline" @click="toggleNested(child.id)">
                    <span class="triangle triangle--nested" :class="{ 'triangle--open': isNestedOpen(child.id) }"></span>
                    <h3 class="course-title course-title--section">{{ child.title }}</h3>
                  </button>
                  <div v-if="isNestedOpen(child.id) && (child.children || []).length" class="badge-list">
                    <div v-for="grand in child.children" :key="grand.id" class="badge-row">
                      <button
                        type="button"
                        class="badge"
                        @click="goToCourse(grand)"
                      >
                        {{ grand.title }}
                      </button>
                      <button
                        v-if="isAuthorized && grand.type === 'course'"
                        type="button"
                        class="star-btn"
                        :class="{ 'star-btn--on': isFavorite(grand.id) }"
                        :title="isFavorite(grand.id) ? 'Убрать из избранного' : 'Добавить в избранное'"
                        @click.stop.prevent="toggleFavorite(grand)"
                      >
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path
                            d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27Z"
                            stroke="currentColor"
                            stroke-width="1.8"
                            stroke-linejoin="round"
                            :fill="isFavorite(grand.id) ? 'currentColor' : 'transparent'"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div class="course-row">
                    <button type="button" class="course-link" @click="goToCourse(child)">
                      {{ child.title }}
                    </button>
                    <button
                      v-if="isAuthorized && child.type === 'course'"
                      type="button"
                      class="star-btn"
                      :class="{ 'star-btn--on': isFavorite(child.id) }"
                      :title="isFavorite(child.id) ? 'Убрать из избранного' : 'Добавить в избранное'"
                      @click.stop.prevent="toggleFavorite(child)"
                    >
                      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path
                          d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27Z"
                          stroke="currentColor"
                          stroke-width="1.8"
                          stroke-linejoin="round"
                          :fill="isFavorite(child.id) ? 'currentColor' : 'transparent'"
                        />
                      </svg>
                    </button>
                  </div>
                </template>
              </li>
            </ul>
          </div>

          <div v-if="standalone.length && isAuthorized" class="section-card">
            <button type="button" class="section-header" @click="standaloneOpen = !standaloneOpen">
              <span class="triangle" :class="{ 'triangle--open': standaloneOpen }"></span>
              <h2 class="section-title">Курсы без раздела</h2>
            </button>
            <ul v-if="standaloneOpen" class="course-list">
              <li v-for="course in standalone" :key="course.id" class="course-item">
                <div class="course-row">
                  <button type="button" class="course-link" @click="goToCourse(course)">
                    {{ course.title }}
                  </button>
                  <button
                    v-if="isAuthorized && course.type === 'course'"
                    type="button"
                    class="star-btn"
                    :class="{ 'star-btn--on': isFavorite(course.id) }"
                    :title="isFavorite(course.id) ? 'Убрать из избранного' : 'Добавить в избранное'"
                    @click.stop.prevent="toggleFavorite(course)"
                  >
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path
                        d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27Z"
                        stroke="currentColor"
                        stroke-width="1.8"
                        stroke-linejoin="round"
                        :fill="isFavorite(course.id) ? 'currentColor' : 'transparent'"
                      />
                    </svg>
                  </button>
                </div>
              </li>
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
              <div class="side-card__meta">до 5</div>
            </div>
            <div v-if="sidebarLoading" class="side-state">Загрузка...</div>
            <div v-else-if="favorites.length === 0" class="side-state">Пока пусто</div>
            <ul v-else class="fav-list">
              <li v-for="(fav, idx) in favorites" :key="fav.course_id" class="fav-item">
                <button type="button" class="fav-link" @click="goToCourse({ id: fav.course_id, title: fav.title, type: 'course' })">
                  {{ fav.title }}
                </button>
                <div class="fav-actions">
                  <button class="fav-btn" type="button" title="Вверх" :disabled="idx === 0" @click="moveFavorite(idx, -1)">↑</button>
                  <button class="fav-btn" type="button" title="Вниз" :disabled="idx === favorites.length - 1" @click="moveFavorite(idx, 1)">↓</button>
                  <button class="fav-btn fav-btn--danger" type="button" title="Удалить" @click="removeFavorite(fav.course_id)">✕</button>
                </div>
              </li>
            </ul>
            <div v-if="favoriteError" class="form-error">{{ favoriteError }}</div>
          </div>

          <div class="section-card side-card">
            <div class="side-card__header">
              <h3 class="side-card__title">Недавние задачи</h3>
              <div class="side-card__meta">топ 5</div>
            </div>
            <div v-if="sidebarLoading" class="side-state">Загрузка...</div>
            <div v-else-if="recentProblems.length === 0" class="side-state">Пока нет посылок</div>
            <ul v-else class="recent-list">
              <li v-for="item in recentProblems" :key="item.problem_id" class="recent-item">
                <button type="button" class="recent-link" @click="goToProblem(item.problem_id, item.title)">
                  {{ item.title }}
                </button>
                <div v-if="item.last_submitted_at" class="recent-time">
                  {{ formatDate(item.last_submitted_at) }}
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
import { useUserStore } from '@/stores/UserStore'
import { formatDateTimeMsk } from '@/utils/datetime'

const courses = ref([])
const openSections = ref({})
const openNested = ref({})
const standaloneOpen = ref(true)
const sidebarLoading = ref(false)
const favorites = ref([])
const recentProblems = ref([])
const updates = ref([])
const favoriteError = ref('')
const router = useRouter()
const userStore = useUserStore()

let user = userStore.getCurrentUser()
let isAuthorized = computed(() => user.value != null)

const hasChildren = item => Array.isArray(item?.children) && item.children.length > 0
const sections = computed(() => courses.value.filter(hasChildren))
const standalone = computed(() => courses.value.filter(item => !hasChildren(item)))

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

const isNestedOpen = id => !!openNested.value[String(id)]
const toggleNested = id => {
  const key = String(id)
  openNested.value = { ...openNested.value, [key]: !openNested.value[key] }
}

const goToCourse = (item) => {
  // Use the type field from API to determine route, fallback to checking children
  const name = item.type === 'course' ? 'course' : 'section'
  router.push({ name, params: { id: item.id }, query: { title: item.title } })
}

const goToProblem = (problemId, title) => {
  router.push({ name: 'problem', params: { id: problemId }, query: { title } })
}

const formatDate = (iso) => formatDateTimeMsk(iso)

const isFavorite = (courseId) => {
  const cid = Number(courseId)
  return favorites.value.some(x => Number(x.course_id) === cid)
}

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

const moveFavorite = async (idx, delta) => {
  const list = [...favorites.value]
  const next = idx + delta
  if (idx < 0 || next < 0 || idx >= list.length || next >= list.length) return

  const tmp = list[idx]
  list[idx] = list[next]
  list[next] = tmp
  favorites.value = list

  try {
    const res = await homeApi.reorderFavoriteCourses(list.map(x => x.course_id))
    favorites.value = Array.isArray(res?.items) ? res.items : list
  } catch (err) {
    console.error('Failed to reorder favorites', err)
    favoriteError.value = _friendlyFavoriteError(err)
    await loadSidebar()
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
  padding: 24px 16px 0;
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
  padding: 14px 14px 16px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e9f1;
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

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-open-btn {
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
  flex: 1 1 auto;
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
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.35);
  background: rgba(245, 158, 11, 0.08);
}

.side-card__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e9f1;
}

.side-card__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
}

.side-card__meta {
  font-size: 12px;
  color: var(--color-text-muted);
  white-space: nowrap;
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
  background: rgba(245, 247, 255, 0.55);
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
  background: rgba(59, 130, 246, 0.08);
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

.fav-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fav-btn--danger {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.08);
  color: rgb(185, 28, 28);
}

.recent-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid #e5e9f1;
  background: rgba(245, 247, 255, 0.55);
}

.recent-link {
  text-align: left;
  background: transparent;
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.35;
  padding: 6px 8px;
  border-radius: 10px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-link:hover {
  background: rgba(59, 130, 246, 0.08);
}

.recent-time {
  font-size: 12px;
  color: var(--color-text-muted);
  padding: 0 8px;
  white-space: nowrap;
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
  .home__content { padding: 28px 32px 0; }
}

@media (max-width: 960px) {
  .home__layout { flex-direction: column; }
  .home__sidebar { width: 100%; flex: 0 0 auto; position: static; top: auto; }
}
</style>

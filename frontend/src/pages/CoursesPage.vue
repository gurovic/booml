<template>
  <div class="courses-page">
    <UiHeader />

    <main class="courses-content">
      <UiBreadcrumbs />

      <section class="courses-panel">
        <div class="courses-head">
          <h1 class="courses-title">Мои курсы</h1>

          <div v-if="isTeacher" class="tabs" role="tablist" aria-label="Фильтр курсов">
            <button
              type="button"
              class="tab"
              :class="{ 'tab--active': activeTab === 'mine' }"
              role="tab"
              :aria-selected="activeTab === 'mine'"
              @click="switchTab('mine')"
            >
              Для меня
            </button>
            <button
              type="button"
              class="tab"
              :class="{ 'tab--active': activeTab === 'admin' }"
              role="tab"
              :aria-selected="activeTab === 'admin'"
              @click="switchTab('admin')"
            >
              Администрирую
            </button>
          </div>
        </div>

        <div class="courses-toolbar">
          <div class="search">
            <span class="search__icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" stroke="currentColor" stroke-width="2"/>
                <path d="M16.5 16.5 21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </span>
            <input
              v-model="search"
              type="search"
              class="search__input"
              placeholder="Поиск по названию"
              autocomplete="off"
              @input="onSearchInput"
            />
            <button
              v-if="search.trim()"
              class="search__clear"
              type="button"
              title="Очистить"
              @click="clearSearch"
            >
              ×
            </button>
          </div>
        </div>

        <div v-if="loading" class="state">Загрузка...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else>
          <div v-if="items.length === 0" class="empty">
            <div class="empty__title">Ничего не найдено</div>
            <div class="empty__hint">
              <span v-if="search.trim()">Попробуйте изменить запрос.</span>
              <span v-else>Пока нет доступных курсов по этому фильтру.</span>
            </div>
          </div>

          <ul v-else class="course-list">
            <li v-for="c in items" :key="c.id" class="course-item">
              <button type="button" class="course-card" @click="openCourse(c)">
                <div class="course-card__main">
                  <div class="course-card__title">{{ c.title }}</div>
                  <div class="course-card__meta">
                    <span class="pill" :class="{ 'pill--open': c.is_open }">
                      {{ c.is_open ? 'открытый' : 'приватный' }}
                    </span>
                    <span v-if="c.section_title" class="pill pill--muted">
                      {{ c.section_title }}
                    </span>
                    <span v-if="c.role" class="pill pill--muted">
                      {{ roleLabel(c.role) }}
                    </span>
                  </div>
                </div>

                <div class="course-card__actions">
                  <button
                    v-if="isAuthorized"
                    type="button"
                    class="star-btn"
                    :class="{ 'star-btn--on': !!c.is_favorite }"
                    :title="c.is_favorite ? 'Убрать из избранного' : 'Добавить в избранное'"
                    @click.stop.prevent="toggleFavorite(c)"
                  >
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path
                        d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27Z"
                        stroke="currentColor"
                        stroke-width="1.8"
                        stroke-linejoin="round"
                        :fill="c.is_favorite ? 'currentColor' : 'transparent'"
                      />
                    </svg>
                  </button>
                </div>
              </button>
            </li>
          </ul>

          <div v-if="totalPages > 1" class="pager">
            <button class="pager__btn" type="button" :disabled="page === 1" @click="setPage(page - 1)">
              Назад
            </button>
            <div class="pager__info">Стр. {{ page }} / {{ totalPages }}</div>
            <button class="pager__btn" type="button" :disabled="page === totalPages" @click="setPage(page + 1)">
              Вперёд
            </button>
          </div>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { courseApi, homeApi } from '@/api'
import { useUserStore } from '@/stores/UserStore'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'

const router = useRouter()
const userStore = useUserStore()

const isAuthorized = computed(() => !!userStore.currentUser)
const isTeacher = computed(() => String(userStore.currentUser?.role || '') === 'teacher')

const activeTab = ref('mine') // mine | admin
const search = ref('')
const page = ref(1)
const pageSize = 10
const totalPages = ref(1)
const items = ref([])
const loading = ref(false)
const error = ref('')

const roleLabel = (role) => {
  if (role === 'owner') return 'владелец'
  if (role === 'teacher') return 'учитель'
  if (role === 'student') return 'ученик'
  return String(role || '')
}

const openCourse = (course) => {
  if (!course?.id) return
  router.push({ name: 'course', params: { id: course.id }, query: { title: course.title } })
}

const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await courseApi.browseCourses({
      tab: activeTab.value,
      q: search.value,
      page: page.value,
      page_size: pageSize,
    })
    items.value = Array.isArray(res?.items) ? res.items : []
    totalPages.value = Number(res?.total_pages || 1) || 1
  } catch (err) {
    console.error('Failed to load courses', err)
    error.value = err?.message || 'Не удалось загрузить курсы'
    items.value = []
    totalPages.value = 1
  } finally {
    loading.value = false
  }
}

const setPage = (p) => {
  const n = Number(p)
  if (!Number.isFinite(n) || n < 1 || n > totalPages.value) return
  page.value = n
  load()
}

const switchTab = (tab) => {
  if (tab !== 'mine' && tab !== 'admin') return
  activeTab.value = tab
  page.value = 1
  load()
}

let _searchTimer = null
const onSearchInput = () => {
  if (_searchTimer) clearTimeout(_searchTimer)
  _searchTimer = setTimeout(() => {
    page.value = 1
    load()
  }, 250)
}

const clearSearch = () => {
  search.value = ''
  page.value = 1
  load()
}

const toggleFavorite = async (course) => {
  if (!isAuthorized.value || !course?.id) return
  try {
    const cid = Number(course.id)
    if (course.is_favorite) await homeApi.removeFavoriteCourse(cid)
    else await homeApi.addFavoriteCourse(cid)
    await load()
  } catch (err) {
    console.error('Failed to toggle favorite', err)
    error.value = err?.message || 'Не удалось обновить избранное'
  }
}

onMounted(() => {
  if (!isAuthorized.value) {
    router.push({ name: 'login' })
    return
  }
  if (!isTeacher.value && activeTab.value === 'admin') activeTab.value = 'mine'
  load()
})
</script>

<style scoped>
.courses-page {
  min-height: 100vh;
  background: var(--color-bg-default, #f6f7fb);
  font-family: var(--font-default, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif);
  color: var(--color-text-primary, #0f172a);
}

.courses-content {
  max-width: 980px;
  margin: 0 auto;
  padding: 24px 16px 40px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.courses-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.courses-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.courses-title {
  margin: 0;
  font-size: 38px;
  font-weight: 400;
  color: var(--color-title-text, rgba(22, 33, 89, 0.96));
}

.tabs {
  display: flex;
  gap: 8px;
  padding: 4px;
  border-radius: 12px;
  background: rgba(22, 33, 89, 0.08);
  border: 1px solid rgba(22, 33, 89, 0.10);
}

.tab {
  border: none;
  background: transparent;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  color: rgba(22, 33, 89, 0.75);
}

.tab--active {
  background: #ffffff;
  color: rgba(22, 33, 89, 0.96);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.courses-toolbar {
  display: flex;
  justify-content: flex-end;
}

.state {
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-surface-border, #e5e9f1);
  box-shadow: 0 3px 10px var(--color-surface-shadow, rgba(0, 0, 0, 0.08));
}

.state--error {
  border-color: rgba(220, 38, 38, 0.35);
  color: #991b1b;
}

.empty {
  padding: 18px 16px;
  border-radius: 12px;
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-surface-border, #e5e9f1);
  box-shadow: 0 3px 10px var(--color-surface-shadow, rgba(0, 0, 0, 0.08));
}

.empty__title {
  font-weight: 700;
}

.empty__hint {
  margin-top: 6px;
  color: rgba(22, 33, 89, 0.68);
}

.course-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.course-card {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 14px;
  border-radius: 14px;
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-surface-border, #e5e9f1);
  box-shadow: 0 3px 10px var(--color-surface-shadow, rgba(0, 0, 0, 0.08));
  cursor: pointer;
  text-align: left;
}

.course-card:hover {
  filter: brightness(0.99);
}

.course-card__main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.course-card__title {
  font-size: 18px;
  font-weight: 800;
  color: rgba(22, 33, 89, 0.96);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.course-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 12px;
  background: rgba(22, 33, 89, 0.08);
  border: 1px solid rgba(22, 33, 89, 0.12);
  color: rgba(22, 33, 89, 0.78);
}

.pill--open {
  background: rgba(16, 185, 129, 0.10);
  border-color: rgba(16, 185, 129, 0.25);
  color: rgba(5, 150, 105, 0.95);
}

.pill--muted {
  background: rgba(22, 33, 89, 0.06);
}

.course-card__actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 0;
}

.pager__btn {
  border: 1px solid rgba(22, 33, 89, 0.18);
  background: #ffffff;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 700;
  color: rgba(22, 33, 89, 0.9);
}

.pager__btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.pager__info {
  color: rgba(22, 33, 89, 0.75);
  font-weight: 700;
}

/* Reuse the same search styling as ContestPage dialog. */
.search {
  position: relative;
  width: min(560px, 100%);
}

.search__icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: rgba(22, 33, 89, 0.55);
  pointer-events: none;
}

.search__input {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  border: 1px solid rgba(22, 33, 89, 0.18);
  background: #ffffff;
  padding: 0 40px 0 40px;
  font-size: 16px;
  color: rgba(22, 33, 89, 0.92);
}

.search__input:focus {
  outline: 2px solid rgba(22, 33, 89, 0.28);
  outline-offset: 2px;
}

.search__clear {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: rgba(22, 33, 89, 0.08);
  cursor: pointer;
  color: rgba(22, 33, 89, 0.8);
  font-size: 18px;
  line-height: 1;
}

.search__clear:hover {
  background: rgba(22, 33, 89, 0.12);
}
</style>

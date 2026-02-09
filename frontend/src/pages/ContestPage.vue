<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <UiBreadcrumbs :contest="contest" />
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Загрузка...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else-if="contest">
          <div class="contest-header">
            <h2 class="contest-title">{{ contestTitle }}</h2>
            <div class="contest-actions">
              <button
                v-if="canManageContest"
                class="button button--primary"
                @click="showAddProblemDialog = true"
              >
                Добавить задачу
              </button>
              <router-link
                :to="leaderboardRoute"
                class="button button--secondary contest-link"
              >
                Таблица лидеров
              </router-link>
            </div>
          </div>
          <div v-if="contest.description" class="contest-description">
            {{ contest.description }}
          </div>
          <UiLinkList
            :title="problemsTitle"
            :items="problemItems"
          >
            <template #action="{ item }">
              <div v-if="canManageContest" class="problem-order-actions">
                <button
                  class="problem-order-btn problem-order-btn--danger"
                  type="button"
                  title="Удалить из контеста"
                  @click.stop.prevent="removeProblem(item)"
                >
                  ✕
                </button>
                <button
                  class="problem-order-btn"
                  type="button"
                  title="Вверх"
                  :disabled="isFirstProblem(item)"
                  @click.stop.prevent="moveProblem(item, -1)"
                >
                  ↑
                </button>
                <button
                  class="problem-order-btn"
                  type="button"
                  title="Вниз"
                  :disabled="isLastProblem(item)"
                  @click.stop.prevent="moveProblem(item, 1)"
                >
                  ↓
                </button>
              </div>
            </template>
          </UiLinkList>
          <p v-if="!problemItems.length" class="note">В этом контесте пока нет задач.</p>
        </template>
        <div v-else class="state">Контест не найден.</div>
      </section>
    </main>

    <!-- Add Problem Dialog -->
    <div v-if="showAddProblemDialog" class="dialog-overlay" @click="closeAddProblemDialog">
      <div class="dialog" @click.stop>
        <div class="dialog__header">
          <h2 class="dialog__title">Добавить задачу в контест</h2>
          <button class="dialog__close" @click="closeAddProblemDialog">×</button>
        </div>
        <div class="dialog__body">
          <div class="dialog-toolbar">
            <div class="search">
              <span class="search__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z" stroke="currentColor" stroke-width="2"/>
                  <path d="M16.5 16.5 21 21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </span>
              <input
                v-model="problemSearch"
                type="search"
                class="search__input"
                placeholder="Поиск по названию"
                autocomplete="off"
                @input="onSearchInput"
              />
              <button
                v-if="problemSearch.trim()"
                class="search__clear"
                type="button"
                title="Очистить"
                @click="clearSearch"
              >
                ×
              </button>
            </div>
          </div>
          <div v-if="loadingProblems" class="dialog-loading">Загрузка задач...</div>
          <div v-else-if="availableProblems.length === 0" class="dialog-empty">
            <p v-if="problemSearch.trim()">
              Ничего не найдено по запросу "{{ problemSearch.trim() }}".
            </p>
            <p v-else>
              Нет доступных задач. Создайте задачу в <router-link :to="{ name: 'polygon' }">Полигоне</router-link>.
            </p>
          </div>
          <div v-else class="problem-list">
            <label
              v-for="problem in availableProblems"
              :key="problem.id"
              class="problem-item problem-item--checkbox"
              :class="{
                'problem-item--disabled': isProblemInContest(problem.id),
              }"
            >
              <input
                class="problem-item__checkbox"
                type="checkbox"
                :disabled="isProblemInContest(problem.id)"
                :checked="isSelected(problem.id)"
                @change="toggleSelected(problem.id, $event.target.checked)"
              />
              <div class="problem-item__info">
                <div class="problem-item__title">{{ problem.title }}</div>
                <div class="problem-item__meta">
                  <span v-if="problem.author_username" class="problem-item__author">
                    Автор: {{ problem.author_username }}
                  </span>
                  <span class="problem-item__rating">Рейтинг: {{ problem.rating }}</span>
                  <span
                    class="problem-item__status"
                    :class="problem.is_published ? 'problem-item__status--published' : ''"
                  >
                    {{ problem.is_published ? 'Опубликована' : 'Черновик' }}
                  </span>
                  <span v-if="isProblemInContest(problem.id)" class="problem-item__already">
                    Уже в контесте
                  </span>
                </div>
              </div>
            </label>

            <div v-if="totalPages > 1" class="pager">
              <button class="pager__btn" type="button" :disabled="page <= 1" @click="setPage(page - 1)">
                Назад
              </button>
              <div class="pager__info">Стр. {{ page }} / {{ totalPages }}</div>
              <button class="pager__btn" type="button" :disabled="page >= totalPages" @click="setPage(page + 1)">
                Вперед
              </button>
            </div>
          </div>
          <div v-if="addProblemError" class="form-error">{{ addProblemError }}</div>
        </div>
        <div class="dialog__footer">
          <button class="button button--secondary" @click="closeAddProblemDialog">
            Отмена
          </button>
          <button
            class="button button--primary"
            @click="addProblemsToContest"
            :disabled="isAddingProblem || selectedProblemIds.length === 0"
          >
            {{ isAddingProblem ? 'Добавление...' : `Добавить (${selectedProblemIds.length})` }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contestApi } from '@/api'
import { getPolygonProblems } from '@/api/polygon'
import { useUserStore } from '@/stores/UserStore'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'
import UiLinkList from '@/components/ui/UiLinkList.vue'

const route = useRoute()
const userStore = useUserStore()
const contestId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(contestId.value) && contestId.value > 0)

const contest = ref(null)
const isLoading = ref(false)
const error = ref('')
const showAddProblemDialog = ref(false)
const loadingProblems = ref(false)
const availableProblems = ref([])
const selectedProblemIds = ref([])
const isAddingProblem = ref(false)
const addProblemError = ref('')
const problemSearch = ref('')
const page = ref(1)
const totalPages = ref(1)
const pageSize = 10

const contestTitle = computed(() => {
  if (contest.value?.title) return contest.value.title
  return hasValidId.value ? `Контест ${contestId.value}` : 'Контест'
})

const problemsTitle = computed(() => (contest.value ? 'Задачи' : contestTitle.value))

const canManageContest = computed(() => {
  if (!userStore.currentUser || !contest.value) return false
  return !!contest.value.can_manage
})

const problemItems = computed(() => {
  const problems = Array.isArray(contest.value?.problems) ? contest.value.problems : []
  return problems
    .filter(problem => problem?.id != null)
    .map(problem => ({
      id: problem.id,
      text: problem.title || `Problem ${problem.id}`,
      route: { name: 'problem', params: { id: problem.id }, query: { contest: contestId.value } },
    }))
})

const leaderboardRoute = computed(() => {
  const title = contest.value?.title
  const query = title ? { title } : {}
  return { name: 'contest-leaderboard', params: { id: contestId.value }, query }
})

const loadContest = async () => {
  if (!hasValidId.value) {
    contest.value = null
    error.value = 'Некорректный id контеста.'
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    contest.value = await contestApi.getContest(contestId.value)
  } catch (err) {
    console.error('Failed to load contest.', err)
    error.value = err?.message || 'Не удалось загрузить контест.'
  } finally {
    isLoading.value = false
  }
}

const loadAvailableProblems = async () => {
  loadingProblems.value = true
  try {
    const res = await getPolygonProblems({ q: problemSearch.value, page: page.value, page_size: pageSize })
    const items = Array.isArray(res) ? res : (res?.items || [])
    const tp = Array.isArray(res) ? 1 : Number(res?.total_pages || 1)
    totalPages.value = Number.isFinite(tp) && tp > 0 ? tp : 1
    availableProblems.value = items
  } catch (err) {
    console.error('Failed to load problems:', err)
    addProblemError.value = 'Не удалось загрузить задачи'
  } finally {
    loadingProblems.value = false
  }
}

const closeAddProblemDialog = () => {
  showAddProblemDialog.value = false
  selectedProblemIds.value = []
  addProblemError.value = ''
  problemSearch.value = ''
  page.value = 1
  totalPages.value = 1
}

const isProblemInContest = (problemId) => {
  const set = new Set((contest.value?.problems || []).map(p => p.id))
  return set.has(Number(problemId))
}

const isSelected = (problemId) => {
  return selectedProblemIds.value.includes(Number(problemId))
}

const toggleSelected = (problemId, checked) => {
  const id = Number(problemId)
  if (isProblemInContest(id)) return
  if (checked) {
    if (!selectedProblemIds.value.includes(id)) selectedProblemIds.value = [...selectedProblemIds.value, id]
  } else {
    selectedProblemIds.value = selectedProblemIds.value.filter(x => x !== id)
  }
}

let _searchTimer = null
const onSearchInput = () => {
  if (_searchTimer) clearTimeout(_searchTimer)
  _searchTimer = setTimeout(() => {
    page.value = 1
    loadAvailableProblems()
  }, 250)
}

const clearSearch = () => {
  problemSearch.value = ''
  page.value = 1
  loadAvailableProblems()
}

const setPage = (next) => {
  const n = Number(next)
  if (!Number.isFinite(n) || n < 1) return
  page.value = n
  loadAvailableProblems()
}

const addProblemsToContest = async () => {
  if (!selectedProblemIds.value.length) return

  isAddingProblem.value = true
  addProblemError.value = ''

  try {
    await contestApi.bulkAddProblemsToContest(contestId.value, selectedProblemIds.value)
    
    // Reload contest to get updated problem list
    await loadContest()
    
    // Close dialog
    closeAddProblemDialog()
  } catch (err) {
    console.error('Failed to add problem:', err)
    addProblemError.value = err?.message || 'Не удалось добавить задачу'
  } finally {
    isAddingProblem.value = false
  }
}

const _problemIndex = (problemId) => {
  const list = Array.isArray(contest.value?.problems) ? contest.value.problems : []
  return list.findIndex(p => Number(p?.id) === Number(problemId))
}

const isFirstProblem = (item) => _problemIndex(item?.id) <= 0
const isLastProblem = (item) => {
  const list = Array.isArray(contest.value?.problems) ? contest.value.problems : []
  const idx = _problemIndex(item?.id)
  return idx < 0 || idx >= list.length - 1
}

const moveProblem = async (item, delta) => {
  const list = Array.isArray(contest.value?.problems) ? [...contest.value.problems] : []
  const idx = list.findIndex(p => Number(p?.id) === Number(item?.id))
  const next = idx + delta
  if (idx < 0 || next < 0 || next >= list.length) return

  const tmp = list[idx]
  list[idx] = list[next]
  list[next] = tmp
  contest.value = { ...contest.value, problems: list }

  try {
    await contestApi.reorderContestProblems(contestId.value, list.map(p => p.id))
  } catch (err) {
    console.error('Failed to reorder problems:', err)
    error.value = err?.message || 'Не удалось поменять порядок задач'
    await loadContest()
  }
}

const removeProblem = async (item) => {
  const pid = Number(item?.id)
  if (!Number.isFinite(pid)) return
  if (!confirm('Удалить задачу из контеста?')) return

  try {
    await contestApi.removeProblemFromContest(contestId.value, pid)
    await loadContest()
  } catch (err) {
    console.error('Failed to remove problem:', err)
    error.value = err?.message || 'Не удалось удалить задачу'
    await loadContest()
  }
}

watch(contestId, () => {
  loadContest()
}, { immediate: true })

watch(showAddProblemDialog, (newValue) => {
  if (newValue) {
    selectedProblemIds.value = []
    page.value = 1
    totalPages.value = 1
    loadAvailableProblems()
  }
})
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

.contest-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 4px 4px 0;
}

.contest-title {
  margin: 0;
}

.contest-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.contest-link {
  display: inline-flex;
  align-items: center;
  color: #1E264A;
  text-decoration: none;
}

.contest-description {
  padding: 12px 16px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border-default);
  color: var(--color-text-secondary);
  font-size: 15px;
  line-height: 1.5;
  margin-bottom: 12px;
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
  max-width: 700px;
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
  min-height: 200px;
}

.dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-default, #e0e0e0);
}

.dialog-toolbar {
  margin-bottom: 12px;
}

.search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 2px solid var(--color-border-default, #e0e0e0);
  border-radius: 999px;
  background: var(--color-bg-default, #fff);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.search:focus-within {
  border-color: var(--color-primary, #3b82f6);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.search__icon {
  color: var(--color-text-muted, #666);
  display: inline-flex;
}

.search__input {
  width: 100%;
  border: none;
  outline: none;
  font-size: 16px;
  background: transparent;
}

.search__input::placeholder {
  color: var(--color-text-muted, #666);
}

.search__clear {
  border: 1px solid var(--color-border-default, #e0e0e0);
  background: #fff;
  border-radius: 999px;
  width: 32px;
  height: 32px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  line-height: 1;
  color: var(--color-text-muted, #666);
}

.search__clear:hover {
  border-color: var(--color-primary, #3b82f6);
  color: var(--color-text-primary, #000);
}

.dialog-loading,
.dialog-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--color-text-muted, #666);
}

.dialog-empty a {
  color: var(--color-primary, #3b82f6);
  text-decoration: underline;
}

.problem-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.problem-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--color-bg-default, #fff);
  border: 2px solid var(--color-border-default, #e0e0e0);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.problem-item--checkbox {
  cursor: pointer;
}

.problem-item--disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.problem-item__checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.problem-item--disabled .problem-item__checkbox {
  cursor: not-allowed;
}

.problem-item:hover {
  border-color: var(--color-primary, #3b82f6);
  background: var(--color-bg-hover, #f8f9fa);
}

.problem-item__info {
  flex: 1;
}

.problem-item__title {
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-primary, #000);
  margin-bottom: 4px;
}

.problem-item__meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
}

.problem-item__author {
  color: var(--color-text-muted, #666);
}

.problem-item__rating {
  color: var(--color-text-muted, #666);
}

.problem-item__status {
  color: var(--color-text-muted, #666);
}

.problem-item__status--published {
  color: var(--color-success, #10b981);
  font-weight: 500;
}

.problem-item__already {
  color: var(--color-text-muted, #666);
  border: 1px solid var(--color-border-default, #e0e0e0);
  padding: 2px 8px;
  border-radius: 999px;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-default, #e0e0e0);
}

.pager__btn {
  border: 1px solid var(--color-border-default);
  background: #fff;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
}

.pager__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pager__info {
  font-size: 13px;
  color: var(--color-text-muted);
}

.problem-order-actions {
  display: inline-flex;
  gap: 6px;
  margin-right: 8px;
}

.problem-order-btn {
  border: 1px solid var(--color-border-default);
  background: rgba(255, 255, 255, 0.65);
  padding: 6px 10px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
}

.problem-order-btn--danger {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.08);
  color: rgb(185, 28, 28);
}

.problem-order-btn--danger:hover {
  border-color: rgba(239, 68, 68, 0.6);
  background: rgba(239, 68, 68, 0.12);
}

.problem-order-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
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

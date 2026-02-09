<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Loading contest...</div>
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
                Leaderboard
              </router-link>
            </div>
          </div>
          <div v-if="contest.description" class="contest-description">
            {{ contest.description }}
          </div>
          <UiLinkList
            :title="problemsTitle"
            :items="problemItems"
          />
          <p v-if="!problemItems.length" class="note">This contest has no problems yet.</p>
        </template>
        <div v-else class="state">Contest not found.</div>
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
          <div v-if="loadingProblems" class="dialog-loading">Загрузка задач...</div>
          <div v-else-if="availableProblems.length === 0" class="dialog-empty">
            <p>У вас нет задач. Создайте задачу в <router-link :to="{ name: 'polygon' }">Полигоне</router-link>.</p>
          </div>
          <div v-else class="problem-list">
            <div
              v-for="problem in availableProblems"
              :key="problem.id"
              class="problem-item"
              :class="{ 'problem-item--selected': selectedProblemId === problem.id }"
              @click="selectedProblemId = problem.id"
            >
              <div class="problem-item__info">
                <div class="problem-item__title">{{ problem.title }}</div>
                <div class="problem-item__meta">
                  <span class="problem-item__rating">Рейтинг: {{ problem.rating }}</span>
                  <span
                    class="problem-item__status"
                    :class="problem.is_published ? 'problem-item__status--published' : ''"
                  >
                    {{ problem.is_published ? 'Опубликована' : 'Черновик' }}
                  </span>
                </div>
              </div>
              <div v-if="selectedProblemId === problem.id" class="problem-item__check">✓</div>
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
            @click="addProblemToContest"
            :disabled="isAddingProblem || !selectedProblemId"
          >
            {{ isAddingProblem ? 'Добавление...' : 'Добавить' }}
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
const selectedProblemId = ref(null)
const isAddingProblem = ref(false)
const addProblemError = ref('')

const contestTitle = computed(() => {
  if (contest.value?.title) return contest.value.title
  return hasValidId.value ? `Contest ${contestId.value}` : 'Contest'
})

const problemsTitle = computed(() => (contest.value ? 'Problems' : contestTitle.value))

const canManageContest = computed(() => {
  if (!userStore.currentUser || !contest.value) return false
  return !!contest.value.can_manage
})

const problemItems = computed(() => {
  const problems = Array.isArray(contest.value?.problems) ? contest.value.problems : []
  return problems
    .filter(problem => problem?.id != null)
    .map(problem => ({
      text: problem.title || `Problem ${problem.id}`,
      route: { name: 'problem', params: { id: problem.id }},
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
    error.value = 'Invalid contest id.'
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    contest.value = await contestApi.getContest(contestId.value)
  } catch (err) {
    console.error('Failed to load contest.', err)
    error.value = err?.message || 'Failed to load contest.'
  } finally {
    isLoading.value = false
  }
}

const loadAvailableProblems = async () => {
  loadingProblems.value = true
  try {
    const problems = await getPolygonProblems()
    // Filter out problems already in contest
    const contestProblemIds = new Set(
      (contest.value?.problems || []).map(p => p.id)
    )
    availableProblems.value = problems.filter(p => !contestProblemIds.has(p.id))
  } catch (err) {
    console.error('Failed to load problems:', err)
    addProblemError.value = 'Не удалось загрузить задачи'
  } finally {
    loadingProblems.value = false
  }
}

const closeAddProblemDialog = () => {
  showAddProblemDialog.value = false
  selectedProblemId.value = null
  addProblemError.value = ''
}

const addProblemToContest = async () => {
  if (!selectedProblemId.value) return

  isAddingProblem.value = true
  addProblemError.value = ''

  try {
    await contestApi.addProblemToContest(contestId.value, selectedProblemId.value)
    
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

watch(contestId, () => {
  loadContest()
}, { immediate: true })

watch(showAddProblemDialog, (newValue) => {
  if (newValue) {
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
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--color-bg-default, #fff);
  border: 2px solid var(--color-border-default, #e0e0e0);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.problem-item:hover {
  border-color: var(--color-primary, #3b82f6);
  background: var(--color-bg-hover, #f8f9fa);
}

.problem-item--selected {
  border-color: var(--color-primary, #3b82f6);
  background: var(--color-primary-light, #eff6ff);
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
  font-size: 13px;
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

.problem-item__check {
  font-size: 24px;
  color: var(--color-primary, #3b82f6);
  font-weight: bold;
  margin-left: 12px;
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

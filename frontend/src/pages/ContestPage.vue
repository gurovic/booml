<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <UiBreadcrumbs :contest="contest" />
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Загрузка...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else-if="contest">
          <div
            class="contest-header"
            :class="{ 'contest-header--teacher': canManageContest }"
          >
            <h1 class="contest-title">{{ contestTitle }}</h1>
            <div
              class="contest-actions"
              :class="{ 'contest-actions--teacher': canManageContest }"
            >
              <button
                type="button"
                class="button button--secondary contest-rules-btn"
                @click="showRulesModal = true"
              >
                Правила
              </button>
              <button
                v-if="canManageContest"
                class="button button--primary"
                @click="showAddProblemDialog = true"
              >
                Добавить задачу
              </button>
              <button
                v-if="canManageContest"
                class="button button--secondary"
                type="button"
                @click="openContestSettingsDialog"
              >
                Настройки контеста
              </button>
              <button
                v-if="canEditContest && contestHasTimeLimit"
                class="button button--secondary"
                type="button"
                @click="openTimingDialog"
              >
                Изменить время
              </button>
              <router-link
                v-if="canOpenLeaderboard"
                :to="leaderboardRoute"
                class="button button--secondary contest-link"
              >
                Результаты
              </router-link>
              <router-link
                v-if="canManageContest"
                :to="contestSubmissionsRoute"
                class="button button--secondary contest-link"
              >
                Все посылки
              </router-link>
              <ContestNotificationsWidget
                v-if="contest?.id && contestAllowsNotifications"
                :contest-id="contest.id"
                :can-manage="canManageContest"
                :contest-title="contestTitle"
                :questions-enabled="contestAllowsStudentQuestions"
              />
            </div>
          </div>
          <div v-if="contest.description" class="contest-description">
            {{ contest.description }}
          </div>
          <div v-if="contestHasTimeLimit" class="contest-timing">
            <div class="contest-timing__top">
              <p class="contest-timing__state">{{ contestTimeStateLabel }}</p>
              <span class="contest-timing__chip">
                Дорешка: {{ contestUpsolvingLabel }}
              </span>
            </div>
            <div v-if="contestCountdown" class="contest-timer">
              <p class="contest-timer__label">{{ contestCountdown.label }}</p>
              <p class="contest-timer__value">{{ contestCountdown.value }}</p>
            </div>
            <p class="contest-timing__line">
              Начало: {{ contestStartLabel }}
            </p>
            <p class="contest-timing__line">
              Дедлайн: {{ contestEndLabel }}
            </p>
            <p
              v-if="contestSubmitBlockedReason && !canManageContest"
              class="contest-timing__warning"
            >
              {{ contestSubmitBlockedReason }}
            </p>
          </div>
          <template v-if="contestCanViewProblems">
            <UiLinkList
              class="contest-problems-list"
              :title="problemsTitle"
              :items="problemItems"
              :reorderable="canReorderProblems"
              @reorder="onReorderProblem"
            >
              <template #action="{ item }">
                <div v-if="canManageContest" class="problem-order-actions">
                  <button
                    class="problem-order-btn problem-order-btn--danger"
                    type="button"
                    title="Удалить из контеста"
                    data-hover-only="true"
                    @click.stop.prevent="removeProblem(item)"
                  >
                    ✕
                  </button>
                </div>
              </template>
            </UiLinkList>
            <p v-if="!problemItems.length" class="note">В этом контесте пока нет задач.</p>
          </template>
          <p v-else class="note">
            {{ contestProblemsLockedReason }}
          </p>
        </template>
        <div v-else class="state">Контест не найден.</div>
      </section>
    </main>

    <ContestRulesModal v-model="showRulesModal" />

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
                <div class="problem-item__title">
                  <UiIdPill class="problem-item__id" :id="problem.id" title="ID задачи" />
                  <span class="problem-item__title-text">{{ problem.title }}</span>
                </div>
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

    <div v-if="showTimingDialog" class="dialog-overlay" @click="closeTimingDialog">
      <div class="dialog dialog--timing" @click.stop>
        <div class="dialog__header">
          <h2 class="dialog__title">Изменить время контеста</h2>
          <button class="dialog__close" @click="closeTimingDialog">×</button>
        </div>
        <div class="dialog__body">
          <div class="timing-form">
            <div class="timing-form__row">
              <div class="timing-form__field">
                <label for="edit-contest-start-time" class="timing-form__label">Начало</label>
                <input
                  id="edit-contest-start-time"
                  v-model="editTiming.start_time"
                  type="datetime-local"
                  class="timing-form__input"
                />
              </div>
              <div class="timing-form__field">
                <label for="edit-contest-end-time" class="timing-form__label">Окончание</label>
                <input
                  id="edit-contest-end-time"
                  v-model="editTiming.end_time"
                  type="datetime-local"
                  class="timing-form__input"
                />
              </div>
            </div>
            <label class="timing-form__checkbox">
              <input type="checkbox" v-model="editTiming.allow_upsolving" />
              <span>Разрешить дорешку после окончания</span>
            </label>
            <div v-if="timingError" class="form-error">{{ timingError }}</div>
          </div>
        </div>
        <div class="dialog__footer">
          <button class="button button--secondary" @click="closeTimingDialog">Отмена</button>
          <button
            class="button button--primary"
            type="button"
            :disabled="isUpdatingTiming"
            @click="saveTimingChanges"
          >
            {{ isUpdatingTiming ? 'Сохранение...' : 'Сохранить' }}
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="canManageContest && showContestSettingsDialog"
      class="dialog-overlay dialog-overlay--settings"
      @click="closeContestSettingsDialog"
    >
      <div class="dialog dialog--settings" @click.stop>
        <div class="dialog__header">
          <h2 class="dialog__title">Настройки контеста</h2>
          <button class="dialog__close" @click="closeContestSettingsDialog">×</button>
        </div>
        <div class="dialog__body">
          <div class="settings-modal">
            <section class="settings-card">
              <div class="settings-section__head">
                <h3 class="settings-section__title">Шаг 1. Уведомления в контесте</h3>
                <span
                  class="settings-state"
                  :class="contestSettings.allow_notifications ? 'settings-state--on' : 'settings-state--off'"
                >
                  {{ contestSettings.allow_notifications ? 'Включено' : 'Выключено' }}
                </span>
              </div>
              <label class="settings-option">
                <input
                  v-model="contestSettings.allow_notifications"
                  type="checkbox"
                  class="settings-option__checkbox"
                />
                <span class="settings-option__content">
                  <span class="settings-option__title">Показывать объявления и вопросы в контесте</span>
                  <span class="settings-option__hint">
                    Если выключено, виджет уведомлений полностью скрывается у учителя и учеников.
                  </span>
                </span>
              </label>
            </section>
            <div
              class="settings-dependency"
              :class="contestSettings.allow_notifications ? 'settings-dependency--ok' : 'settings-dependency--blocked'"
            >
              <span class="settings-dependency__icon" aria-hidden="true">→</span>
              <span v-if="contestSettings.allow_notifications">
                Уведомления включены. Теперь можно настраивать вопросы учеников.
              </span>
              <span v-else>
                Чтобы разрешить вопросы, сначала включите уведомления в шаге 1.
              </span>
            </div>
            <section
              class="settings-card"
              :class="{ 'settings-card--blocked': !contestSettings.allow_notifications }"
            >
              <div class="settings-section__head">
                <h3 class="settings-section__title">Шаг 2. Вопросы учеников</h3>
                <span
                  class="settings-state"
                  :class="
                    !contestSettings.allow_notifications
                      ? 'settings-state--blocked'
                      : (contestSettings.allow_student_questions ? 'settings-state--on' : 'settings-state--off')
                  "
                >
                  {{
                    !contestSettings.allow_notifications
                      ? 'Недоступно'
                      : (contestSettings.allow_student_questions ? 'Включено' : 'Выключено')
                  }}
                </span>
              </div>
              <p v-if="!contestSettings.allow_notifications" class="settings-lock-note">
                Вопросы недоступны, пока уведомления выключены.
              </p>
              <label
                class="settings-option"
                :class="{ 'settings-option--disabled': !contestSettings.allow_notifications }"
              >
                <input
                  v-model="contestSettings.allow_student_questions"
                  type="checkbox"
                  class="settings-option__checkbox"
                  :disabled="!contestSettings.allow_notifications"
                />
                <span class="settings-option__content">
                  <span class="settings-option__title">Разрешить ученикам задавать вопросы</span>
                  <span class="settings-option__hint">
                    Доступно только когда уведомления включены. При отключении уведомлений вопросы выключаются автоматически.
                  </span>
                </span>
              </label>
            </section>
            <div v-if="contestSettingsError" class="form-error">{{ contestSettingsError }}</div>
          </div>
        </div>
        <div class="dialog__footer">
          <button
            class="button button--secondary"
            type="button"
            :disabled="isUpdatingQuestionSettings"
            @click="closeContestSettingsDialog"
          >
            Отмена
          </button>
          <button
            class="button button--primary"
            type="button"
            :disabled="isUpdatingQuestionSettings"
            @click="saveContestSettings"
          >
            {{ isUpdatingQuestionSettings ? 'Сохранение...' : 'Сохранить' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { contestApi } from '@/api'
import { getPolygonProblems } from '@/api/polygon'
import { useUserStore } from '@/stores/UserStore'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'
import UiLinkList from '@/components/ui/UiLinkList.vue'
import UiIdPill from '@/components/ui/UiIdPill.vue'
import ContestNotificationsWidget from '@/components/contest/ContestNotificationsWidget.vue'
import ContestRulesModal from '@/components/contest/ContestRulesModal.vue'
import { CONTEST_RULES_DONT_SHOW_KEY } from '@/utils/contestRules'
import { arrayMove } from '@/utils/arrayMove'
import { toContestProblemLabel } from '@/utils/contestProblemLabel'
import { formatCountdown, formatDateTimeMsk, toTimestamp } from '@/utils/datetime'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const contestId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(contestId.value) && contestId.value > 0)

const contest = ref(null)
const isLoading = ref(false)
const error = ref('')
const showRulesModal = ref(false)
const showAddProblemDialog = ref(false)
const showTimingDialog = ref(false)
const showContestSettingsDialog = ref(false)
const loadingProblems = ref(false)
const availableProblems = ref([])
const selectedProblemIds = ref([])
const isAddingProblem = ref(false)
const isUpdatingTiming = ref(false)
const isUpdatingQuestionSettings = ref(false)
const addProblemError = ref('')
const timingError = ref('')
const contestSettingsError = ref('')
const problemSearch = ref('')
const page = ref(1)
const totalPages = ref(1)
const pageSize = 10
const nowTs = ref(Date.now())
let clockTimer = null
let contestSyncTimer = null
const autoUnlockSyncInFlight = ref(false)
const lastAutoUnlockAttemptTs = ref(0)
const periodicSyncInFlight = ref(false)
const editTiming = ref({
  start_time: '',
  end_time: '',
  allow_upsolving: false,
})
const contestSettings = ref({
  allow_notifications: true,
  allow_student_questions: true,
})

const contestTitle = computed(() => {
  if (contest.value?.title) return contest.value.title
  return hasValidId.value ? `Контест ${contestId.value}` : 'Контест'
})
const isAuthorized = computed(() => !!userStore.currentUser)

const problemsTitle = computed(() => (contest.value ? 'Задачи' : contestTitle.value))

const contestHasTimeLimit = computed(() => !!contest.value?.has_time_limit)
const contestStartTs = computed(() => toTimestamp(contest.value?.start_time))
const contestEndTs = computed(() => toTimestamp(contest.value?.end_time))
const contestStartLabel = computed(() => formatDateTimeMsk(contest.value?.start_time))
const contestEndLabel = computed(() => formatDateTimeMsk(contest.value?.end_time))
const contestUpsolvingLabel = computed(() => {
  return contest.value?.allow_upsolving ? 'Да' : 'Нет'
})
const contestTimeState = computed(() => {
  if (!contestHasTimeLimit.value) return 'always_open'
  const now = nowTs.value
  if (contestStartTs.value != null && now < contestStartTs.value) return 'not_started'
  if (contestEndTs.value != null && now >= contestEndTs.value) {
    return contest.value?.allow_upsolving ? 'upsolving' : 'finished'
  }
  return 'running'
})
const contestTimeStateLabel = computed(() => {
  const state = contestTimeState.value
  const labels = {
    not_started: 'Контест ещё не начался',
    running: 'Контест идёт',
    upsolving: 'Идёт дорешка',
    finished: 'Контест завершён',
  }
  return labels[state] || 'Соревновательный режим'
})
const contestCountdown = computed(() => {
  if (!contestHasTimeLimit.value) return null
  const now = nowTs.value
  if (contestTimeState.value === 'not_started' && contestStartTs.value != null) {
    const secondsLeft = Math.max(0, Math.ceil((contestStartTs.value - now) / 1000))
    return { label: 'До начала', value: formatCountdown(secondsLeft) }
  }
  if (contestTimeState.value === 'running' && contestEndTs.value != null) {
    const secondsLeft = Math.max(0, Math.ceil((contestEndTs.value - now) / 1000))
    return { label: 'До конца', value: formatCountdown(secondsLeft) }
  }
  return null
})
const contestSubmitBlockedReason = computed(() => {
  if (!contest.value) return ''
  if (contestTimeState.value === 'not_started') return 'Контест ещё не начался.'
  if (contestTimeState.value === 'finished') return 'Контест завершён, отправка недоступна.'
  if (contest.value.can_submit) return ''
  return contest.value.submit_block_reason || ''
})

const canManageContest = computed(() => {
  if (!userStore.currentUser || !contest.value) return false
  return !!contest.value.can_manage
})
const contestAllowsNotifications = computed(() => contest.value?.allow_notifications !== false)
const contestAllowsStudentQuestions = computed(
  () => contestAllowsNotifications.value && contest.value?.allow_student_questions !== false
)
const canEditContest = computed(() => {
  if (!userStore.currentUser || !contest.value) return false
  return !!contest.value.can_edit
})

const canReorderProblems = computed(() => {
  const list = Array.isArray(contest.value?.problems) ? contest.value.problems : []
  return canManageContest.value && list.length > 1
})
const contestCanViewProblems = computed(() => contest.value?.can_view_problems !== false)
const canOpenLeaderboard = computed(() => canManageContest.value || contestCanViewProblems.value)
const shouldAutoSyncContest = computed(() => contestHasTimeLimit.value && !canManageContest.value)
const contestProblemsLockedReason = computed(
  () => contest.value?.problems_locked_reason || 'Задачи откроются после начала контеста.'
)

const isAuthRequiredError = (err) => {
  const status = Number(err?.status)
  return status === 401 || status === 403
}

const problemItems = computed(() => {
  const problems = Array.isArray(contest.value?.problems) ? contest.value.problems : []
  return problems
    .filter(problem => problem?.id != null)
    .map((problem, index) => {
      const label = toContestProblemLabel(index)
      return {
        id: problem.id,
        idPill: label,
        idPillPrefix: '',
        idPillTitle: `Problem ${label}`,
        text: problem.title || `Problem ${problem.id}`,
        route: {
          name: 'problem',
          params: { id: problem.id },
          query: { contest: contestId.value, problem_label: label },
        },
      }
    })
})

const leaderboardRoute = computed(() => {
  const title = contest.value?.title
  const query = title ? { title } : {}
  return { name: 'contest-leaderboard', params: { id: contestId.value }, query }
})

const contestSubmissionsRoute = computed(() => {
  const title = contest.value?.title
  const query = title ? { title } : {}
  return { name: 'contest-submissions', params: { id: contestId.value }, query }
})

const loadContest = async ({ silent = false } = {}) => {
  if (!hasValidId.value) {
    contest.value = null
    error.value = 'Некорректный id контеста.'
    return
  }

  if (!silent) {
    isLoading.value = true
    error.value = ''
  }
  try {
    contest.value = await contestApi.getContest(contestId.value)
    if (!silent && contest.value) {
      try {
        if (!localStorage.getItem(CONTEST_RULES_DONT_SHOW_KEY)) {
          showRulesModal.value = true
        }
      } catch {
        showRulesModal.value = true
      }
    }
  } catch (err) {
    console.error('Failed to load contest.', err)
    if (!isAuthorized.value && isAuthRequiredError(err)) {
      await router.replace({ name: 'auth-required', query: { redirect: route.fullPath } })
      return
    }
    if (!silent) {
      error.value = err?.message || 'Не удалось загрузить контест.'
    }
  } finally {
    if (!silent) {
      isLoading.value = false
    }
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

const toLocalDateTimeInput = (isoString) => {
  if (!isoString) return ''
  const dt = new Date(isoString)
  if (Number.isNaN(dt.getTime())) return ''
  const pad = (v) => String(v).padStart(2, '0')
  const yyyy = dt.getFullYear()
  const mm = pad(dt.getMonth() + 1)
  const dd = pad(dt.getDate())
  const hh = pad(dt.getHours())
  const min = pad(dt.getMinutes())
  return `${yyyy}-${mm}-${dd}T${hh}:${min}`
}

const toIsoDateTime = (localValue) => {
  if (!localValue) return null
  const dt = new Date(localValue)
  if (Number.isNaN(dt.getTime())) return null
  return dt.toISOString()
}

const openTimingDialog = () => {
  if (!contest.value) return
  editTiming.value = {
    start_time: toLocalDateTimeInput(contest.value.start_time),
    end_time: toLocalDateTimeInput(contest.value.end_time),
    allow_upsolving: !!contest.value.allow_upsolving,
  }
  timingError.value = ''
  showTimingDialog.value = true
}

const closeTimingDialog = (force = false) => {
  if (!force && isUpdatingTiming.value) return
  showTimingDialog.value = false
  timingError.value = ''
}

const saveTimingChanges = async () => {
  if (!contest.value) return

  timingError.value = ''
  const startIso = toIsoDateTime(editTiming.value.start_time)
  const endIso = toIsoDateTime(editTiming.value.end_time)
  if (!startIso || !endIso) {
    timingError.value = 'Укажите корректные дату и время начала/окончания.'
    return
  }
  if (new Date(endIso).getTime() <= new Date(startIso).getTime()) {
    timingError.value = 'Время окончания должно быть позже времени начала.'
    return
  }

  isUpdatingTiming.value = true
  try {
    await contestApi.updateContest(contest.value.id, {
      has_time_limit: true,
      start_time: startIso,
      end_time: endIso,
      allow_upsolving: !!editTiming.value.allow_upsolving,
    })
    await loadContest()
    closeTimingDialog(true)
  } catch (err) {
    console.error('Failed to update contest timing:', err)
    timingError.value = err?.message || 'Не удалось обновить время контеста.'
  } finally {
    isUpdatingTiming.value = false
  }
}

const openContestSettingsDialog = () => {
  if (!contest.value || !canManageContest.value) return
  contestSettings.value = {
    allow_notifications: contestAllowsNotifications.value,
    allow_student_questions: contestAllowsStudentQuestions.value,
  }
  contestSettingsError.value = ''
  showContestSettingsDialog.value = true
}

const closeContestSettingsDialog = (force = false) => {
  if (!force && isUpdatingQuestionSettings.value) return
  showContestSettingsDialog.value = false
  contestSettingsError.value = ''
}

const saveContestSettings = async () => {
  if (!contest.value || !canManageContest.value || isUpdatingQuestionSettings.value) return
  isUpdatingQuestionSettings.value = true
  contestSettingsError.value = ''
  const allowNotifications = contestSettings.value.allow_notifications !== false
  const desiredAllowStudentQuestions =
    allowNotifications && contestSettings.value.allow_student_questions !== false
  try {
    const response = await contestApi.updateContestQuestionSettings(contest.value.id, {
      allow_notifications: allowNotifications,
      allow_student_questions: desiredAllowStudentQuestions,
    })
    const notificationsEnabled = response?.allow_notifications !== false
    const persistedAllowStudentQuestions = response?.allow_student_questions !== false
    contest.value = {
      ...contest.value,
      allow_notifications: notificationsEnabled,
      allow_student_questions: persistedAllowStudentQuestions,
    }
    contestSettings.value = {
      allow_notifications: notificationsEnabled,
      allow_student_questions: persistedAllowStudentQuestions,
    }
    closeContestSettingsDialog(true)
  } catch (err) {
    console.error('Failed to update contest question settings:', err)
    contestSettingsError.value = err?.message || 'Не удалось обновить настройки контеста.'
  } finally {
    isUpdatingQuestionSettings.value = false
  }
}

watch(
  () => contestSettings.value.allow_notifications,
  (enabled) => {
    if (enabled !== false) return
    contestSettings.value.allow_student_questions = false
  }
)

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

const onReorderProblem = async ({ from, to }) => {
  const list = Array.isArray(contest.value?.problems) ? [...contest.value.problems] : []
  if (!list.length) return

  const next = arrayMove(list, from, to)
  contest.value = { ...contest.value, problems: next }

  try {
    await contestApi.reorderContestProblems(contestId.value, next.map(p => p.id))
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

const startClock = () => {
  if (clockTimer != null) return
  clockTimer = window.setInterval(() => {
    nowTs.value = Date.now()
  }, 1000)
}

const stopClock = () => {
  if (clockTimer == null) return
  window.clearInterval(clockTimer)
  clockTimer = null
}

const syncContestSilently = async () => {
  if (!shouldAutoSyncContest.value) return
  if (periodicSyncInFlight.value || autoUnlockSyncInFlight.value) return
  periodicSyncInFlight.value = true
  try {
    await loadContest({ silent: true })
  } finally {
    periodicSyncInFlight.value = false
  }
}

const startContestSync = () => {
  if (contestSyncTimer != null) return
  contestSyncTimer = window.setInterval(() => {
    void syncContestSilently()
  }, 5000)
}

const stopContestSync = () => {
  if (contestSyncTimer == null) return
  window.clearInterval(contestSyncTimer)
  contestSyncTimer = null
}

onMounted(() => {
  startClock()
  startContestSync()
})

onBeforeUnmount(() => {
  stopClock()
  stopContestSync()
})

watch(contestId, () => {
  loadContest()
}, { immediate: true })

watch(
  [nowTs, contestHasTimeLimit, contestStartTs, contestCanViewProblems, isLoading],
  async () => {
    if (!contest.value) return
    if (!contestHasTimeLimit.value) return
    if (contestCanViewProblems.value) return
    if (contestStartTs.value == null) return
    if (nowTs.value < contestStartTs.value) return
    if (isLoading.value || autoUnlockSyncInFlight.value) return
    if (nowTs.value - lastAutoUnlockAttemptTs.value < 5000) return

    lastAutoUnlockAttemptTs.value = nowTs.value
    autoUnlockSyncInFlight.value = true
    try {
      await loadContest({ silent: true })
    } finally {
      autoUnlockSyncInFlight.value = false
    }
  }
)

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
  padding: 0 16px 40px;
}

.contest-panel {
  display: flex;
  flex-direction: column;
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 16px 4px 0;
}

.contest-header--teacher {
  flex-direction: column;
  align-items: stretch;
  gap: 14px;
}

.contest-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0;
}

.contest-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.contest-actions--teacher {
  width: 100%;
  display: flex;
  flex-wrap: nowrap;
  gap: 10px;
  align-items: stretch;
  overflow-x: auto;
  scrollbar-width: thin;
}

.contest-actions--teacher > .button,
.contest-actions--teacher > .contest-link {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  flex: 1 1 auto;
  min-width: 0;
  white-space: nowrap;
  padding: 10px 16px;
}

.contest-actions--teacher :deep(.contest-notify) {
  flex: 1 1 auto;
  min-width: 0;
}

.contest-actions--teacher :deep(.contest-notify__trigger) {
  width: 100%;
  min-width: 0;
  min-height: 44px;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  padding: 10px 16px;
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

.contest-timing {
  padding: 14px 16px 16px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border-default);
  margin-top: 12px;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.contest-description + .contest-timing {
  margin-top: 0;
}

.contest-timing__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.contest-timing__state {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.contest-timing__chip {
  font-size: 12px;
  font-weight: 600;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
}

.contest-timer {
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  padding: 12px 14px;
}

.contest-timer__label {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #334155;
}

.contest-timer__value {
  margin: 0;
  font-size: clamp(26px, 3.2vw, 36px);
  line-height: 1.05;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.contest-timing__line {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.contest-timing__warning {
  margin: 2px 0 0;
  font-size: 13px;
  color: var(--color-text-danger);
}

:deep(.contest-problems-list > h2) {
  display: none;
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

.dialog--timing {
  max-width: 640px;
}

.dialog-overlay--settings {
  background: radial-gradient(1000px 600px at 50% 0%, rgba(15, 23, 42, 0.45), rgba(0, 0, 0, 0.56));
  backdrop-filter: blur(4px);
}

.dialog--settings {
  max-width: 660px;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
}

.dialog--settings .dialog__header {
  background: rgba(255, 255, 255, 0.92);
  border-bottom-color: rgba(15, 23, 42, 0.08);
}

.dialog--settings .dialog__footer {
  background: rgba(255, 255, 255, 0.92);
  border-top-color: rgba(15, 23, 42, 0.08);
}

.settings-modal {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-card {
  border: 1px solid rgba(37, 99, 235, 0.16);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.08), rgba(59, 130, 246, 0.03));
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-card--blocked {
  border-color: rgba(120, 53, 15, 0.22);
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.04));
}

.settings-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.settings-section__title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: rgba(15, 23, 42, 0.92);
}

.settings-state {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  border-radius: 999px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}

.settings-state--on {
  background: rgba(16, 185, 129, 0.14);
  border-color: rgba(16, 185, 129, 0.35);
  color: #047857;
}

.settings-state--off {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.3);
  color: #b91c1c;
}

.settings-state--blocked {
  background: rgba(245, 158, 11, 0.16);
  border-color: rgba(245, 158, 11, 0.34);
  color: #92400e;
}

.settings-dependency {
  border-radius: 12px;
  border: 1px solid transparent;
  padding: 10px 12px;
  font-size: 13px;
  line-height: 1.4;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.settings-dependency__icon {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.2;
  flex: 0 0 auto;
}

.settings-dependency--ok {
  background: rgba(16, 185, 129, 0.09);
  border-color: rgba(16, 185, 129, 0.22);
  color: #047857;
}

.settings-dependency--blocked {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.3);
  color: #92400e;
}

.settings-lock-note {
  margin: -2px 0 0;
  font-size: 13px;
  line-height: 1.4;
  color: #92400e;
  font-weight: 600;
}

.settings-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  padding: 12px;
  cursor: pointer;
}

.settings-option--disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.settings-option__checkbox {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  flex: 0 0 auto;
}

.settings-option__content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.settings-option__title {
  font-size: 14px;
  font-weight: 700;
  color: rgba(15, 23, 42, 0.92);
}

.settings-option__hint {
  font-size: 13px;
  line-height: 1.45;
  color: rgba(15, 23, 42, 0.68);
}

.timing-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timing-form__row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.timing-form__field {
  min-width: 0;
}

.timing-form__label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 600;
}

.timing-form__input {
  width: 100%;
  min-height: 42px;
  border: 1px solid var(--color-border-default, #d0d0d0);
  border-radius: 10px;
  padding: 9px 11px;
  font-size: 14px;
  font-family: inherit;
}

.timing-form__input:focus {
  outline: none;
  border-color: var(--color-primary, #3b82f6);
}

.timing-form__checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.timing-form__checkbox input[type='checkbox'] {
  width: 18px;
  height: 18px;
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
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary, #000);
  margin-bottom: 4px;
}

.problem-item__id {
  flex: 0 0 auto;
}

.problem-item__title-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
    padding: 0 24px 48px;
  }
}

@media (max-width: 700px) {
  .timing-form__row {
    grid-template-columns: 1fr;
  }
}
</style>

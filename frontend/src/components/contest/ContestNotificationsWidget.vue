<template>
  <div class="contest-notify">
    <button
      type="button"
      class="button button--secondary contest-notify__trigger"
      :class="{ 'contest-notify__trigger--unread': unreadCount > 0 }"
      @click="togglePanel"
    >
      <span class="material-symbols-rounded contest-notify__trigger-icon">notifications_active</span>
      <span class="contest-notify__trigger-text">Уведомления</span>
      <span v-if="unreadCount > 0" class="contest-notify__badge">{{ unreadBadge }}</span>
    </button>

    <transition name="contest-notify-overlay">
      <div v-if="isOpen" class="contest-notify__overlay" @click="closePanel">
        <section class="contest-notify__panel" @click.stop>
          <header class="contest-notify__header">
            <div class="contest-notify__title-wrap">
              <h3 class="contest-notify__title">Уведомления контеста</h3>
              <p class="contest-notify__subtitle">{{ contestTitleSafe }}</p>
            </div>
            <div class="contest-notify__header-actions">
              <span v-if="unreadCount > 0" class="contest-notify__unread-pill">
                Непрочитанные: {{ unreadCount }}
              </span>
              <button type="button" class="contest-notify__close" @click="closePanel">×</button>
            </div>
          </header>

          <div class="contest-notify__body">
            <div v-if="loadError" class="contest-notify__error">{{ loadError }}</div>

            <section v-if="canManage" class="contest-notify__compose">
              <h4 class="contest-notify__compose-title">Объявление участникам</h4>
              <textarea
                v-model="announcementText"
                class="contest-notify__textarea"
                placeholder="Введите текст объявления"
                maxlength="4000"
              />

              <div class="contest-notify__audience">
                <button
                  type="button"
                  class="contest-notify__audience-btn"
                  :class="{ 'contest-notify__audience-btn--active': announcementAudience === 'all' }"
                  @click="announcementAudience = 'all'"
                >
                  Всем
                </button>
                <button
                  type="button"
                  class="contest-notify__audience-btn"
                  :class="{ 'contest-notify__audience-btn--active': announcementAudience === 'selected' }"
                  @click="announcementAudience = 'selected'"
                >
                  Выбранным
                </button>
              </div>

              <div v-if="announcementAudience === 'selected'" class="contest-notify__recipients">
                <p class="contest-notify__recipients-title">Кому отправить:</p>
                <div class="contest-notify__recipients-list">
                  <label
                    v-for="participant in participants"
                    :key="participant.id"
                    class="contest-notify__recipient"
                  >
                    <input
                      type="checkbox"
                      :checked="selectedRecipientIds.includes(participant.id)"
                      @change="toggleRecipient(participant.id, $event.target.checked)"
                    />
                    <span>{{ participant.username }}</span>
                  </label>
                </div>
              </div>

              <div class="contest-notify__compose-actions">
                <button
                  type="button"
                  class="button button--primary"
                  :disabled="isSendingAnnouncement"
                  @click="sendAnnouncement"
                >
                  {{ isSendingAnnouncement ? 'Отправка...' : 'Отправить объявление' }}
                </button>
              </div>
            </section>

            <section v-else-if="questionsEnabledEffective" class="contest-notify__compose">
              <h4 class="contest-notify__compose-title">Задать вопрос преподавателю</h4>
              <textarea
                v-model="questionText"
                class="contest-notify__textarea"
                placeholder="Введите ваш вопрос"
                maxlength="4000"
              />
              <div class="contest-notify__compose-actions">
                <button
                  type="button"
                  class="button button--primary"
                  :disabled="isSendingQuestion"
                  @click="sendQuestion"
                >
                  {{ isSendingQuestion ? 'Отправка...' : 'Отправить вопрос' }}
                </button>
              </div>
            </section>

            <div v-if="questionsEnabledEffective" class="contest-notify__tabs">
              <button
                type="button"
                class="contest-notify__tab"
                :class="{ 'contest-notify__tab--active': activeTab === 'announcements' }"
                @click="activeTab = 'announcements'"
              >
                Объявления
                <span class="contest-notify__tab-count">{{ announcementItems.length }}</span>
              </button>
              <button
                type="button"
                class="contest-notify__tab"
                :class="{ 'contest-notify__tab--active': activeTab === 'questions' }"
                @click="activeTab = 'questions'"
              >
                {{ questionsTitle }}
                <span class="contest-notify__tab-count">{{ questionThreads.length }}</span>
              </button>
            </div>

            <section class="contest-notify__stream contest-notify__stream--main">
              <header class="contest-notify__stream-header">
                <h4 class="contest-notify__stream-title">{{ activeTabTitle }}</h4>
                <button
                  type="button"
                  class="contest-notify__refresh"
                  :disabled="isLoading"
                  @click="loadNotifications"
                >
                  Обновить
                </button>
              </header>

              <div v-if="isLoading" class="contest-notify__state">Загрузка...</div>

              <div v-else-if="activeTab === 'announcements' && !announcementItems.length" class="contest-notify__state">
                Пока нет объявлений.
              </div>
              <div v-else-if="activeTab === 'announcements'" class="contest-notify__items">
                <article
                  v-for="item in announcementItems"
                  :key="item.id"
                  class="contest-notify__item contest-notify__item--announcement"
                  :class="{ 'contest-notify__item--unread': item.is_read === false }"
                >
                  <div class="contest-notify__item-topline">
                    <span class="contest-notify__kind">Объявление</span>
                    <span class="contest-notify__time">{{ formatTime(item.created_at) }}</span>
                  </div>
                  <h5 class="contest-notify__item-author">От: {{ item.author?.username || 'unknown' }}</h5>
                  <p class="contest-notify__item-text">{{ item.text }}</p>
                  <div class="contest-notify__item-meta">
                    <span v-if="item.audience_label" class="contest-notify__meta-pill">{{ item.audience_label }}</span>
                    <span v-if="canManage && item.recipient_count > 0" class="contest-notify__meta-pill">
                      Получателей: {{ item.recipient_count }}
                    </span>
                  </div>
                </article>
              </div>

              <div v-else-if="!questionThreads.length" class="contest-notify__state">
                Пока нет вопросов.
              </div>
              <div v-else class="contest-notify__threads">
                <article
                  v-for="thread in questionThreads"
                  :key="thread.question.id"
                  class="contest-notify__thread"
                  :class="{ 'contest-notify__thread--unread': thread.isUnread }"
                >
                  <div class="contest-notify__thread-question">
                    <div class="contest-notify__item-topline">
                      <span class="contest-notify__kind contest-notify__kind--question">Вопрос</span>
                      <span class="contest-notify__time">{{ formatTime(thread.question.created_at) }}</span>
                    </div>
                    <h5 class="contest-notify__item-author">{{ thread.question.author?.username || 'unknown' }}</h5>
                    <p class="contest-notify__item-text contest-notify__item-text--question">
                      {{ thread.question.text }}
                    </p>
                  </div>

                  <div v-if="thread.answers.length" class="contest-notify__answers">
                    <div
                      v-for="answer in thread.answers"
                      :key="answer.id"
                      class="contest-notify__answer-row"
                      :class="{ 'contest-notify__answer-row--unread': answer.is_read === false }"
                    >
                      <div class="contest-notify__item-topline">
                        <span class="contest-notify__kind contest-notify__kind--answer">Ответ</span>
                        <span class="contest-notify__time">{{ formatTime(answer.created_at) }}</span>
                      </div>
                      <h5 class="contest-notify__answer-author">{{ answer.author?.username || 'unknown' }}</h5>
                      <p class="contest-notify__item-text contest-notify__item-text--answer">{{ answer.text }}</p>
                    </div>
                  </div>

                  <div v-if="canManage" class="contest-notify__answer-form">
                    <textarea
                      v-model="answerDrafts[thread.question.id]"
                      class="contest-notify__answer-input"
                      placeholder="Введите ответ"
                      maxlength="4000"
                    />
                    <button
                      type="button"
                      class="button button--secondary"
                      :disabled="isSendingAnswerId === thread.question.id"
                      @click="sendAnswer(thread.question)"
                    >
                      {{ isSendingAnswerId === thread.question.id ? 'Отправка...' : 'Ответить' }}
                    </button>
                  </div>
                </article>
              </div>
            </section>
          </div>
        </section>
      </div>
    </transition>

    <div class="contest-notify__toasts" aria-live="polite">
      <transition-group name="contest-toast">
        <article
          v-for="toast in toasts"
          :key="toast.id"
          class="contest-notify__toast"
          :class="`contest-notify__toast--${toast.kind}`"
          @mouseenter="pauseToast(toast.id)"
          @mouseleave="resumeToast(toast.id)"
        >
          <button class="contest-notify__toast-close" type="button" @click.stop="closeToast(toast.id)">
            ×
          </button>
          <p class="contest-notify__toast-title">{{ toast.title }}</p>
          <p class="contest-notify__toast-text">{{ toast.text }}</p>
        </article>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { contestApi } from '@/api'
import { useUserStore } from '@/stores/UserStore'

const LONG_POLL_RETRY_DELAY_MS = 1500

const props = defineProps({
  contestId: {
    type: Number,
    required: true,
  },
  canManage: {
    type: Boolean,
    default: false,
  },
  contestTitle: {
    type: String,
    default: '',
  },
  questionsEnabled: {
    type: Boolean,
    default: true,
  },
})

const userStore = useUserStore()

const isOpen = ref(false)
const isLoading = ref(false)
const loadError = ref('')
const items = ref([])
const unreadCount = ref(0)
const participants = ref([])

const announcementText = ref('')
const announcementAudience = ref('all')
const selectedRecipientIds = ref([])
const questionText = ref('')
const activeTab = ref('announcements')
const isSendingAnnouncement = ref(false)
const isSendingQuestion = ref(false)
const isSendingAnswerId = ref(null)
const answerDrafts = reactive({})

const toasts = ref([])
const toastTimers = new Map()
const questionsEnabledFromApi = ref(true)
let toastSeq = 0
let longPollSessionId = 0
let wasUnmounted = false

const contestTitleSafe = computed(() => props.contestTitle || `Контест #${props.contestId}`)
const unreadBadge = computed(() => (unreadCount.value > 99 ? '99+' : String(unreadCount.value)))
const questionsEnabledEffective = computed(() => Boolean(props.questionsEnabled) && questionsEnabledFromApi.value)
const questionsTitle = computed(() => (props.canManage ? 'Вопросы учеников' : 'Мои вопросы и ответы'))
const activeTabTitle = computed(() => {
  if (!questionsEnabledEffective.value) return 'Объявления'
  return activeTab.value === 'questions' ? questionsTitle.value : 'Объявления'
})
const currentUserId = computed(() => {
  const raw = userStore.currentUser?.id
  return Number.isInteger(raw) ? raw : Number(raw) || null
})

const toTs = (iso) => {
  const parsed = Date.parse(iso || '')
  return Number.isNaN(parsed) ? 0 : parsed
}

const sortByCreatedDesc = (a, b) => {
  const delta = toTs(b?.created_at) - toTs(a?.created_at)
  if (delta !== 0) return delta
  return Number(b?.id || 0) - Number(a?.id || 0)
}

const sortByCreatedAsc = (a, b) => {
  const delta = toTs(a?.created_at) - toTs(b?.created_at)
  if (delta !== 0) return delta
  return Number(a?.id || 0) - Number(b?.id || 0)
}

const announcementItems = computed(() => {
  return [...items.value]
    .filter(item => item.kind === 'announcement')
    .sort(sortByCreatedDesc)
})

const questionItems = computed(() => {
  if (!questionsEnabledEffective.value) return []
  return [...items.value]
    .filter(item => item.kind === 'question')
    .sort(sortByCreatedDesc)
})

const answersByQuestionId = computed(() => {
  if (!questionsEnabledEffective.value) return new Map()
  const map = new Map()
  for (const answer of items.value.filter(item => item.kind === 'answer' && item.parent_id != null)) {
    const parentId = Number(answer.parent_id)
    if (!Number.isFinite(parentId)) continue
    const bucket = map.get(parentId) || []
    bucket.push(answer)
    map.set(parentId, bucket)
  }
  for (const [key, bucket] of map.entries()) {
    map.set(key, [...bucket].sort(sortByCreatedAsc))
  }
  return map
})

const questionThreads = computed(() => {
  return questionItems.value.map((question) => {
    const answers = answersByQuestionId.value.get(Number(question.id)) || []
    const isUnread = question.is_read === false || answers.some(answer => answer.is_read === false)
    return {
      question,
      answers,
      isUnread,
    }
  })
})

const normalizeItem = (raw) => {
  if (!raw || typeof raw !== 'object' || raw.id == null) return null
  return {
    id: Number(raw.id),
    kind: String(raw.kind || 'announcement'),
    audience: String(raw.audience || ''),
    audience_label: String(raw.audience_label || ''),
    text: String(raw.text || ''),
    created_at: raw.created_at || null,
    author: {
      id: raw.author?.id ?? null,
      username: raw.author?.username || '',
    },
    parent_id: raw.parent_id ?? null,
    parent_author_id: raw.parent_author_id ?? null,
    is_read: raw.is_read !== false,
    recipient_count: Number(raw.recipient_count || 0),
    recipient_ids: Array.isArray(raw.recipient_ids)
      ? raw.recipient_ids.map(Number).filter(Number.isFinite)
      : [],
    recipient_usernames: Array.isArray(raw.recipient_usernames) ? raw.recipient_usernames : [],
    answer_count: Number(raw.answer_count || 0),
  }
}

const upsertItem = (item) => {
  const normalized = normalizeItem(item)
  if (!normalized) return

  const idx = items.value.findIndex(row => Number(row.id) === Number(normalized.id))
  if (idx >= 0) {
    const next = [...items.value]
    next[idx] = { ...next[idx], ...normalized }
    items.value = next
    return
  }

  items.value = [normalized, ...items.value]
}

const kindLabel = (kind) => {
  if (kind === 'question') return 'Новый вопрос'
  if (kind === 'answer') return 'Новый ответ'
  return 'Новое объявление'
}

const formatTime = (iso) => {
  if (!iso) return '-'
  const dt = new Date(iso)
  if (Number.isNaN(dt.getTime())) return '-'
  return dt.toLocaleString('ru-RU', {
    timeZone: 'Europe/Moscow',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const addToast = (item) => {
  if (!item?.text) return
  if (!questionsEnabledEffective.value && item.kind !== 'announcement') return
  if (currentUserId.value != null && Number(item.author?.id) === Number(currentUserId.value)) {
    return
  }

  toastSeq += 1
  const toast = {
    id: toastSeq,
    kind: item.kind || 'announcement',
    title: kindLabel(item.kind),
    text: item.text,
    remainingMs: 8000,
    lastStartAt: null,
  }

  const prev = [...toasts.value]
  const next = [toast, ...prev].slice(0, 5)
  const nextIds = new Set(next.map(row => row.id))
  for (const row of prev) {
    if (!nextIds.has(row.id)) {
      const timer = toastTimers.get(row.id)
      if (timer != null) {
        window.clearTimeout(timer)
      }
      toastTimers.delete(row.id)
    }
  }
  toasts.value = next
  resumeToast(toast.id)
}

const closeToast = (toastId) => {
  const timer = toastTimers.get(toastId)
  if (timer != null) {
    window.clearTimeout(timer)
  }
  toastTimers.delete(toastId)
  toasts.value = toasts.value.filter(row => row.id !== toastId)
}

const pauseToast = (toastId) => {
  const toast = toasts.value.find(row => row.id === toastId)
  if (!toast) return

  const timer = toastTimers.get(toastId)
  if (timer != null) {
    window.clearTimeout(timer)
    toastTimers.delete(toastId)
  }

  if (toast.lastStartAt != null) {
    const elapsed = Date.now() - toast.lastStartAt
    toast.remainingMs = Math.max(0, Number(toast.remainingMs || 0) - elapsed)
  }
  toast.lastStartAt = null
}

const resumeToast = (toastId) => {
  const toast = toasts.value.find(row => row.id === toastId)
  if (!toast) return
  if (toastTimers.has(toastId)) return

  if (Number(toast.remainingMs || 0) <= 0) {
    closeToast(toastId)
    return
  }

  toast.lastStartAt = Date.now()
  const timer = window.setTimeout(() => {
    closeToast(toastId)
  }, Number(toast.remainingMs || 0))
  toastTimers.set(toastId, timer)
}

const loadNotifications = async ({
  silent = false,
  emitForNew = false,
  requestOptions = {},
} = {}) => {
  const contestId = Number(props.contestId)
  if (!Number.isFinite(contestId) || contestId <= 0) return false

  const previousById = new Map(items.value.map(item => [Number(item.id), item]))

  if (!silent) {
    isLoading.value = true
    loadError.value = ''
  }

  try {
    const response = await contestApi.getContestNotifications(contestId, {
      limit: 300,
      ...requestOptions,
    })
    if (wasUnmounted || Number(props.contestId) !== contestId) {
      return false
    }
    const list = Array.isArray(response?.items) ? response.items : []
    questionsEnabledFromApi.value = response?.questions_enabled !== false
    const questionsEnabledNow = Boolean(props.questionsEnabled) && questionsEnabledFromApi.value
    const normalized = list.map(normalizeItem).filter(Boolean).sort(sortByCreatedDesc)
    const visibleItems = questionsEnabledNow
      ? normalized
      : normalized.filter(item => item.kind === 'announcement')

    items.value = visibleItems
    const apiUnreadCount = Number(response?.unread_count || 0)
    unreadCount.value = questionsEnabledNow
      ? apiUnreadCount
      : visibleItems.filter(item => item.is_read === false).length
    participants.value = Array.isArray(response?.participants) ? response.participants : []

    if (emitForNew) {
      const newItems = visibleItems.filter(item => !previousById.has(Number(item.id)))
      if (newItems.length) {
        if (isOpen.value) {
          const unreadIds = newItems
            .filter(item => item.is_read === false)
            .map(item => Number(item.id))
            .filter(Number.isFinite)
          if (unreadIds.length) {
            await markRead(unreadIds)
          }
        } else {
          for (const item of newItems) {
            addToast(item)
          }
        }
      }
    }
    return true
  } catch (err) {
    if (!silent) {
      loadError.value = err?.message || 'Не удалось загрузить уведомления.'
    }
    return false
  } finally {
    if (!silent) {
      isLoading.value = false
    }
  }
}

const markRead = async (ids = null) => {
  if (!props.contestId) return
  try {
    const response = await contestApi.markContestNotificationsRead(props.contestId, ids)
    unreadCount.value = Number(response?.unread_count || 0)

    if (Array.isArray(ids)) {
      const idSet = new Set(ids.map(Number))
      items.value = items.value.map(item => (idSet.has(Number(item.id)) ? { ...item, is_read: true } : item))
    } else {
      items.value = items.value.map(item => ({ ...item, is_read: true }))
    }
  } catch (_) {
    // Temporary errors are ignored, next sync will recover state.
  }
}

const openPanel = async () => {
  isOpen.value = true
  await loadNotifications()
  if (unreadCount.value > 0) {
    await markRead()
  }
}

const closePanel = () => {
  isOpen.value = false
}

const togglePanel = () => {
  if (isOpen.value) {
    closePanel()
  } else {
    void openPanel()
  }
}

const toggleRecipient = (participantId, checked) => {
  const normalized = Number(participantId)
  if (!Number.isFinite(normalized)) return

  if (checked) {
    if (!selectedRecipientIds.value.includes(normalized)) {
      selectedRecipientIds.value = [...selectedRecipientIds.value, normalized]
    }
    return
  }

  selectedRecipientIds.value = selectedRecipientIds.value.filter(id => id !== normalized)
}

const sendAnnouncement = async () => {
  const text = announcementText.value.trim()
  if (!text || isSendingAnnouncement.value) return

  const payload = {
    text,
    audience: announcementAudience.value,
  }

  if (announcementAudience.value === 'selected') {
    if (!selectedRecipientIds.value.length) {
      loadError.value = 'Выберите хотя бы одного участника.'
      return
    }
    payload.recipient_ids = selectedRecipientIds.value
  }

  isSendingAnnouncement.value = true
  loadError.value = ''
  try {
    const response = await contestApi.sendContestNotification(props.contestId, payload)
    const item = normalizeItem(response?.notification)
    if (item) {
      item.is_read = true
      upsertItem(item)
    }
    activeTab.value = 'announcements'
    announcementText.value = ''
    selectedRecipientIds.value = []
    announcementAudience.value = 'all'
  } catch (err) {
    loadError.value = err?.message || 'Не удалось отправить объявление.'
  } finally {
    isSendingAnnouncement.value = false
  }
}

const sendQuestion = async () => {
  if (!questionsEnabledEffective.value) return
  const text = questionText.value.trim()
  if (!text || isSendingQuestion.value) return

  isSendingQuestion.value = true
  loadError.value = ''
  try {
    const response = await contestApi.askContestQuestion(props.contestId, { text })
    const item = normalizeItem(response?.notification)
    if (item) {
      item.is_read = true
      upsertItem(item)
    }
    activeTab.value = 'questions'
    questionText.value = ''
  } catch (err) {
    loadError.value = err?.message || 'Не удалось отправить вопрос.'
  } finally {
    isSendingQuestion.value = false
  }
}

const sendAnswer = async (questionItem) => {
  if (!questionsEnabledEffective.value) return
  const questionId = Number(questionItem?.id)
  if (!Number.isFinite(questionId) || isSendingAnswerId.value != null) return

  const text = String(answerDrafts[questionId] || '').trim()
  if (!text) return

  isSendingAnswerId.value = questionId
  loadError.value = ''
  try {
    const response = await contestApi.answerContestQuestion(props.contestId, questionId, { text })
    const item = normalizeItem(response?.notification)
    if (item) {
      item.is_read = true
      upsertItem(item)
      activeTab.value = 'questions'
      items.value = items.value.map(row => {
        if (Number(row.id) !== questionId || row.kind !== 'question') return row
        return { ...row, answer_count: Number(row.answer_count || 0) + 1 }
      })
    }
    answerDrafts[questionId] = ''
  } catch (err) {
    loadError.value = err?.message || 'Не удалось отправить ответ.'
  } finally {
    isSendingAnswerId.value = null
  }
}

const delay = async (ms) => {
  if (typeof window === 'undefined') return
  await new Promise(resolve => window.setTimeout(resolve, ms))
}

const getLatestNotificationId = () => {
  let maxId = 0
  for (const item of items.value) {
    const normalized = Number(item?.id || 0)
    if (!Number.isFinite(normalized)) continue
    if (normalized > maxId) maxId = normalized
  }
  return maxId
}

const stopLongPolling = () => {
  longPollSessionId += 1
}

const runLongPolling = async (sessionId) => {
  while (!wasUnmounted && sessionId === longPollSessionId && props.contestId) {
    const sinceId = getLatestNotificationId()
    const ok = await loadNotifications({
      silent: true,
      emitForNew: true,
      requestOptions: {
        since_id: sinceId,
      },
    })
    if (wasUnmounted || sessionId !== longPollSessionId) return
    if (!ok) {
      await delay(LONG_POLL_RETRY_DELAY_MS)
    }
  }
}

const startLongPolling = () => {
  if (!props.contestId) return
  longPollSessionId += 1
  const sessionId = longPollSessionId
  void runLongPolling(sessionId)
}

watch(
  () => props.contestId,
  async () => {
    items.value = []
    unreadCount.value = 0
    participants.value = []
    questionsEnabledFromApi.value = true
    activeTab.value = 'announcements'
    stopLongPolling()

    if (props.contestId) {
      await loadNotifications()
      startLongPolling()
    }
  },
  { immediate: true }
)

watch(questionsEnabledEffective, (enabled) => {
  if (!enabled && activeTab.value !== 'announcements') {
    activeTab.value = 'announcements'
  }
  if (!enabled) {
    items.value = items.value.filter(item => item.kind === 'announcement')
    unreadCount.value = items.value.filter(item => item.is_read === false).length
    const keptToasts = toasts.value.filter(toast => toast.kind === 'announcement')
    const keptToastIds = new Set(keptToasts.map(toast => toast.id))
    for (const [toastId, timer] of toastTimers.entries()) {
      if (keptToastIds.has(toastId)) continue
      window.clearTimeout(timer)
      toastTimers.delete(toastId)
    }
    toasts.value = keptToasts
  } else if (isOpen.value) {
    void loadNotifications({ silent: true })
  }
})

watch(announcementAudience, (next) => {
  if (next !== 'selected') {
    selectedRecipientIds.value = []
  }
})

onBeforeUnmount(() => {
  wasUnmounted = true
  stopLongPolling()
  for (const timer of toastTimers.values()) {
    window.clearTimeout(timer)
  }
  toastTimers.clear()
})
</script>

<style scoped>
.contest-notify {
  position: relative;
}

.contest-notify__trigger {
  position: relative;
  min-width: 170px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--color-border-default);
  background: var(--color-button-secondary);
}

.contest-notify__trigger--unread {
  border-color: #d9817b;
}

.contest-notify__trigger-icon {
  font-size: 20px;
}

.contest-notify__trigger-text {
  font-weight: 500;
}

.contest-notify__badge {
  margin-left: auto;
  min-width: 22px;
  height: 22px;
  border-radius: 999px;
  padding: 0 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #dc2626;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.contest-notify__overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: rgba(21, 28, 59, 0.38);
  display: flex;
  justify-content: flex-end;
}

.contest-notify__panel {
  width: min(680px, 100vw);
  height: 100%;
  background: var(--color-bg-card);
  border-left: 1px solid var(--color-border-default);
  box-shadow: -10px 0 24px rgba(15, 23, 42, 0.16);
  display: flex;
  flex-direction: column;
}

.contest-notify__header {
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.contest-notify__title-wrap {
  min-width: 0;
}

.contest-notify__title {
  margin: 0;
  font-size: 20px;
}

.contest-notify__subtitle {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.contest-notify__header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.contest-notify__unread-pill {
  font-size: 12px;
  font-weight: 600;
  border-radius: 999px;
  padding: 5px 10px;
  color: #b42318;
  background: #fef3f2;
  border: 1px solid #fecdca;
}

.contest-notify__close {
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  background: #fff;
  color: var(--color-text-muted);
  font-size: 22px;
  line-height: 1;
}

.contest-notify__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 14px 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.contest-notify__error {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-error-border);
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.contest-notify__compose {
  border: 1px solid var(--color-border-default);
  border-radius: 14px;
  padding: 12px;
  background: var(--color-bg-muted);
}

.contest-notify__compose-title {
  margin: 0 0 10px;
  font-size: 16px;
}

.contest-notify__textarea,
.contest-notify__answer-input {
  width: 100%;
  resize: vertical;
  min-height: 80px;
  max-height: 220px;
  border-radius: 10px;
  border: 1px solid var(--color-border-default);
  padding: 10px 12px;
  font-family: var(--font-default);
  font-size: 14px;
  color: var(--color-text-primary);
  background: #fff;
}

.contest-notify__audience {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.contest-notify__audience-btn {
  border: 1px solid var(--color-border-default);
  border-radius: 999px;
  padding: 6px 12px;
  background: #fff;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 500;
}

.contest-notify__audience-btn--active {
  border-color: rgba(39, 52, 106, 0.45);
  color: var(--color-primary);
  background: rgba(39, 52, 106, 0.08);
}

.contest-notify__recipients {
  margin-top: 10px;
}

.contest-notify__recipients-title {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.contest-notify__recipients-list {
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  background: #fff;
  max-height: 140px;
  overflow: auto;
}

.contest-notify__recipient {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-border-light);
  font-size: 14px;
}

.contest-notify__recipient:last-child {
  border-bottom: none;
}

.contest-notify__compose-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.contest-notify__tabs {
  display: flex;
  gap: 8px;
}

.contest-notify__tab {
  flex: 1;
  border: 1px solid var(--color-border-default);
  background: #fff;
  border-radius: 12px;
  padding: 9px 12px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--color-text-muted);
  font-size: 14px;
  font-weight: 500;
}

.contest-notify__tab--active {
  background: #eef1fb;
  border-color: #c9d0ef;
  color: var(--color-primary);
}

.contest-notify__tab-count {
  min-width: 24px;
  height: 24px;
  padding: 0 7px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  background: #fff;
  border: 1px solid var(--color-border-light);
}

.contest-notify__stream {
  border: 1px solid var(--color-border-light);
  border-radius: 14px;
  overflow: visible;
  background: #fff;
}

.contest-notify__stream--main {
  min-height: 320px;
}

.contest-notify__stream-header {
  padding: 11px 12px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.contest-notify__stream-title {
  margin: 0;
  font-size: 16px;
}

.contest-notify__refresh {
  border: 1px solid var(--color-border-default);
  background: #fff;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.contest-notify__state {
  padding: 16px 12px;
  color: var(--color-text-muted);
}

.contest-notify__items,
.contest-notify__threads {
  max-height: none;
  overflow: visible;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.contest-notify__item,
.contest-notify__thread {
  border-radius: 12px;
  border: 1px solid #d7def3;
  padding: 14px;
  background: #fbfcff;
}

.contest-notify__item--announcement {
  border-left: 5px solid #4f78d7;
}

.contest-notify__thread {
  border-left: 4px solid #7f99e2;
  background: #f8fbff;
  padding: 0;
  overflow: hidden;
}

.contest-notify__item--unread,
.contest-notify__thread--unread {
  border-color: #cdd9fb;
  background: #f3f7ff;
}

.contest-notify__item-topline {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.contest-notify__kind,
.contest-notify__meta-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
}

.contest-notify__kind {
  color: var(--color-primary);
  background: rgba(39, 52, 106, 0.1);
}

.contest-notify__kind--question {
  color: #2f4f99;
  background: #e9f0ff;
}

.contest-notify__kind--answer {
  color: #315f8a;
  background: #eaf5ff;
}

.contest-notify__meta-pill {
  color: var(--color-text-muted);
  background: var(--color-bg-muted);
  border: 1px solid var(--color-border-light);
}

.contest-notify__time {
  font-size: 12px;
  color: var(--color-text-muted);
}

.contest-notify__item-author {
  margin: 8px 0 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-title-text);
}

.contest-notify__item-text {
  margin: 10px 0 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.55;
}

.contest-notify__item-text--question,
.contest-notify__item-text--answer {
  margin-top: 10px;
}

.contest-notify__item-meta {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.contest-notify__thread-question {
  padding: 14px 15px 15px;
}

.contest-notify__answers {
  border-top: 1px solid #dbe4fb;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.contest-notify__answer-row {
  padding: 12px 15px 13px;
}

.contest-notify__answer-row + .contest-notify__answer-row {
  border-top: 1px dashed #d7e0f5;
}

.contest-notify__answer-row--unread {
  background: #f5f9ff;
}

.contest-notify__answer-author {
  margin: 7px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: #3f5b90;
}

.contest-notify__answer-form {
  margin-top: 0;
  padding: 14px 15px 15px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #fff;
}

.contest-notify__thread-question + .contest-notify__answer-form,
.contest-notify__answers + .contest-notify__answer-form {
  border-top: 1px solid #dbe4fb;
}

.contest-notify__answer-input {
  min-height: 86px;
}

.contest-notify__thread--unread .contest-notify__thread-question {
  background: #edf3ff;
}

.contest-notify__item--unread .contest-notify__item-topline,
.contest-notify__thread--unread .contest-notify__item-topline {
  color: #2b478c;
}

.contest-notify__toasts {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 1400;
  width: min(360px, calc(100vw - 36px));
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.contest-notify__toast {
  position: relative;
  border-radius: 12px;
  border: 1px solid var(--color-border-default);
  background: #fff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.16);
  padding: 10px 40px 10px 12px;
  pointer-events: auto;
}

.contest-notify__toast--announcement {
  border-left: 5px solid #5b8def;
}

.contest-notify__toast--question {
  border-left: 5px solid #f59e0b;
}

.contest-notify__toast--answer {
  border-left: 5px solid #10b981;
}

.contest-notify__toast-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-title-text);
}

.contest-notify__toast-text {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-primary);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.contest-notify__toast-close {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 22px;
  height: 22px;
  border: 1px solid var(--color-border-default);
  border-radius: 6px;
  background: #fff;
  color: var(--color-text-muted);
  font-size: 16px;
  line-height: 1;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.16s ease;
}

.contest-notify__toast:hover .contest-notify__toast-close,
.contest-notify__toast:focus-within .contest-notify__toast-close {
  opacity: 1;
  pointer-events: auto;
}

.contest-notify-overlay-enter-active,
.contest-notify-overlay-leave-active {
  transition: opacity 0.2s ease;
}

.contest-notify-overlay-enter-from,
.contest-notify-overlay-leave-to {
  opacity: 0;
}

.contest-toast-enter-active,
.contest-toast-leave-active {
  transition: all 0.22s ease;
}

.contest-toast-enter-from,
.contest-toast-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

@media (max-width: 900px) {
  .contest-notify__panel {
    width: 100vw;
  }

  .contest-notify__trigger {
    min-width: 0;
    width: 100%;
  }

  .contest-notify__toasts {
    right: 10px;
    bottom: 10px;
    width: min(320px, calc(100vw - 20px));
  }
}
</style>

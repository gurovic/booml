<template>
  <div class="notebook-page">
    <UiHeader />

    <main class="notebook-main">
      <div class="notebook-title-row">
        <h1 class="notebook-title">{{ notebookTitle }}</h1>
      </div>

      <div
        v-if="viewState.kind !== 'ready'"
        class="notebook-state"
        :class="{ 'notebook-state--error': viewState.kind === 'error' }"
      >
        {{ viewState.message }}
      </div>
      <div v-else class="notebook-layout">
        <aside class="notebook-files">
          <div class="files-header">
            <h2 class="files-title">Файлы</h2>
            <button type="button" class="files-upload-button" disabled>
              Загрузить
            </button>
          </div>
          <div class="files-list">
            <div v-if="files.length === 0" class="files-empty">
              {{ sessionStatus === 'running' ? 'В сессии пока нет файлов' : 'Файлы появятся после запуска сессии' }}
            </div>
            <button
              v-for="file in files"
              :key="file.path || file.name"
              type="button"
              class="file-item"
            >
              <span class="file-icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M6 3h7l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.6"
                  />
                  <path d="M13 3v6h6" fill="none" stroke="currentColor" stroke-width="1.6" />
                </svg>
              </span>
              <span class="file-name">{{ file.name }}</span>
            </button>
          </div>
        </aside>

        <section class="notebook-workspace">
          <div class="notebook-toolbar">
            <div class="toolbar-group">
              <button
                v-for="action in toolbarActions"
                :key="action.id"
                type="button"
                :class="['toolbar-pill', 'toolbar-pill--' + action.id]"
                :aria-label="getToolbarActionLabel(action.id)"
                @click="createNotebookCell(action.id)"
              >
                <span class="toolbar-label">{{ action.label }}</span>
              </button>
            </div>
            <div class="toolbar-group toolbar-group--right">
              <div ref="sessionMenuRef" class="toolbar-session-wrap">
                <button
                  type="button"
                  class="toolbar-pill toolbar-session"
                  :aria-expanded="sessionMenuOpen ? 'true' : 'false'"
                  aria-label="Открыть меню управления сессией"
                  @click="toggleSessionMenu"
                >
                  <span class="toolbar-label">Сессия</span>
                  <span :class="['toolbar-session-dot', sessionIndicatorClass]" aria-hidden="true"></span>
                </button>
                <div v-if="sessionMenuOpen" class="session-menu" aria-label="Панель управления сессией">
                  <div class="session-menu-meta">
                    Статус: {{ sessionStatusLabel }}
                  </div>
                  <button
                    type="button"
                    class="session-menu-item"
                    :disabled="!canStartSession"
                    @click="startSession"
                  >
                    Запустить
                  </button>
                  <button
                    type="button"
                    class="session-menu-item"
                    :disabled="!canRestartSession"
                    @click="restartSession"
                  >
                    Перезапустить
                  </button>
                  <button
                    type="button"
                    class="session-menu-item"
                    :disabled="sessionActionBusy || !hasValidId"
                    @click="refreshSessionFiles"
                  >
                    Обновить файлы
                  </button>
                  <button
                    type="button"
                    class="session-menu-item session-menu-item--danger"
                    :disabled="!canStopSession"
                    @click="stopSession"
                  >
                    Остановить
                  </button>
                  <div v-if="sessionActionError" class="session-menu-error">
                    {{ sessionActionError }}
                  </div>
                </div>
              </div>
              <div class="toolbar-pill toolbar-pill--static">
                <span class="toolbar-label">Настройки</span>
              </div>
            </div>
          </div>

          <div class="cells-list">
            <div v-if="orderedCells.length === 0" class="cells-empty">
              В блокноте пока нет ячеек
            </div>

            <div
              v-for="cell in orderedCells"
              :key="cell.id"
              class="cell-stack"
            >
              <div class="cell-row" :class="{ 'cell-row--selected': selectedCellId === cell.id }">
                <article
                  class="cell-card"
                  role="button"
                  tabindex="0"
                  :aria-label="getCellSelectionLabel(cell)"
                  @click="selectCell(cell.id)"
                  @keydown.enter.prevent="selectCell(cell.id)"
                  @keydown.space.prevent="selectCell(cell.id)"
                >
                  <div
                    class="cell-body"
                    :class="{ 'cell-body--text': cell.cell_type === 'text' }"
                  >
                    <button
                      v-if="cell.cell_type === 'code'"
                      class="cell-run-button"
                      type="button"
                      disabled
                      title="Запуск ячейки"
                      :aria-label="`Запустить кодовую ячейку ${cell.id}`"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">play_arrow</span>
                    </button>

                    <div class="cell-content">
                    <div v-if="cell.cell_type === 'code'" class="code-block">
                      <NotebookCodeEditor
                        v-model="cell.content"
                        @update:modelValue="() => scheduleSave(cell)"
                        @blur="() => flushSave(cell)"
                      />
                    </div>

                      <div v-else class="text-block">
                        <textarea
                          v-model="cell.content"
                          class="text-editor"
                          placeholder="Введите заметку"
                          :aria-label="`Текст ячейки ${cell.id}`"
                          @focus="selectCell(cell.id)"
                          @input="() => scheduleSave(cell)"
                          @blur="() => flushSave(cell)"
                        ></textarea>
                      </div>
                    </div>
                  </div>

                <div v-if="cell.output" class="cell-output">
                  <span
                    class="cell-output-icon"
                    :class="{ 'cell-output-icon--error': isErrorOutput(cell.output) }"
                  >
                    <span
                      v-if="isErrorOutput(cell.output)"
                      class="material-symbols-rounded"
                      aria-hidden="true"
                    >
                      error
                    </span>
                    <span v-else class="material-symbols-rounded" aria-hidden="true">
                      more_horiz
                    </span>
                  </span>
                  <div class="cell-output-content" v-html="cell.output"></div>
                </div>
                </article>

                <div v-if="selectedCellId === cell.id" class="cell-actions">
                    <button
                      type="button"
                      class="cell-action-btn"
                      :title="`Переместить ячейку ${cell.id} вверх`"
                      :aria-label="`Переместить ячейку ${cell.id} вверх`"
                      :disabled="isCellFirst(cell)"
                      @click.stop="shiftCell(cell, -1)"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">arrow_upward</span>
                    </button>
                    <button
                      type="button"
                      class="cell-action-btn"
                      :title="`Переместить ячейку ${cell.id} вниз`"
                      :aria-label="`Переместить ячейку ${cell.id} вниз`"
                      :disabled="isCellLast(cell)"
                      @click.stop="shiftCell(cell, 1)"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">arrow_downward</span>
                    </button>
                    <button
                      type="button"
                      class="cell-action-btn cell-action-btn--danger"
                      :title="`Удалить ячейку ${cell.id}`"
                      :aria-label="`Удалить ячейку ${cell.id}`"
                      @click.stop="removeCell(cell)"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">delete</span>
                    </button>
                </div>
              </div>

              <div class="cell-insert-zone">
                <div class="footer-group cell-insert-group">
                  <button
                    v-for="action in footerActions"
                    :key="`${cell.id}-${action.id}`"
                    type="button"
                    class="footer-pill"
                    :aria-label="getInsertActionLabel(action.id, cell.id)"
                    @click="createNotebookCell(action.id)"
                  >
                    {{ action.label }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import UiHeader from '@/components/ui/UiHeader.vue'
import NotebookCodeEditor from '@/components/NotebookCodeEditor.vue'
import {
  createCell,
  deleteCell,
  getNotebook,
  getNotebookSessionFiles,
  getNotebookSessionId,
  moveCell,
  resetNotebookSession,
  saveCodeCell,
  saveTextCell,
  startNotebookSession,
  stopNotebookSession,
} from '@/api/notebook'

const route = useRoute()

const notebook = ref(null)
const state = ref('idle')
const stateMessage = ref('')
const selectedCellId = ref(null)
const sessionStatus = ref('stopped')
const sessionMenuOpen = ref(false)
const sessionActionBusy = ref(false)
const sessionActionError = ref('')
const sessionMenuRef = ref(null)
const sessionFiles = ref([])
const saveTimers = new Map()
const lastSavedContent = new Map()

const notebookId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(notebookId.value) && notebookId.value > 0)
const sessionId = computed(() => {
  if (!hasValidId.value) return ''
  return getNotebookSessionId(notebookId.value)
})

const notebookTitle = computed(() => {
  if (notebook.value?.title) return notebook.value.title
  return hasValidId.value ? `Блокнот ${notebookId.value}` : 'Блокнот'
})

const viewState = computed(() => {
  if (state.value === 'loading') {
    return { kind: 'loading', message: 'Загрузка блокнота...' }
  }
  if (state.value === 'not_found') {
    return { kind: 'error', message: 'Блокнот не найден' }
  }
  if (state.value === 'error') {
    return { kind: 'error', message: stateMessage.value || 'Не удалось загрузить блокнот.' }
  }
  return { kind: 'ready', message: '' }
})

const orderedCells = computed(() => {
  const list = Array.isArray(notebook.value?.cells) ? notebook.value.cells : []
  return [...list].sort((a, b) => (a.execution_order ?? 0) - (b.execution_order ?? 0))
})

const sessionIndicatorClass = computed(() => {
  if (sessionStatus.value === 'running') return 'toolbar-session-dot--running'
  if (sessionStatus.value === 'starting') return 'toolbar-session-dot--starting'
  return 'toolbar-session-dot--stopped'
})

const sessionStatusLabel = computed(() => {
  if (sessionStatus.value === 'running') return 'запущена'
  if (sessionStatus.value === 'starting') return 'запускается'
  return 'не запущена'
})

const canStartSession = computed(() => {
  return hasValidId.value && !sessionActionBusy.value && sessionStatus.value !== 'running'
})

const canRestartSession = computed(() => {
  return hasValidId.value && !sessionActionBusy.value && sessionStatus.value === 'running'
})

const canStopSession = computed(() => {
  return hasValidId.value && !sessionActionBusy.value && sessionStatus.value === 'running'
})

const files = computed(() => {
  if (!Array.isArray(sessionFiles.value)) return []
  return sessionFiles.value.map((file) => {
    const path = String(file?.path || '')
    const parts = path.split('/')
    const name = parts[parts.length - 1] || path
    return {
      ...file,
      name,
    }
  })
})

const toolbarActions = [
  { id: 'code', label: '+ Код', variant: 'primary' },
  { id: 'text', label: '+ Текст', variant: 'primary' },
]
const footerActions = [
  { id: 'code', label: '+ Код' },
  { id: 'text', label: '+ Текст' },
]

const getToolbarActionLabel = (actionId) => {
  if (actionId === 'code') return 'Добавить новую кодовую ячейку'
  if (actionId === 'text') return 'Добавить новую текстовую ячейку'
  return 'Выполнить действие с ячейками'
}

const getCellSelectionLabel = (cell) => {
  const typeLabel = cell?.cell_type === 'text' ? 'текстовая' : 'кодовая'
  return `Выбрать ${typeLabel} ячейку ${cell?.id}`
}

const getInsertActionLabel = (actionId, cellId) => {
  if (actionId === 'code') return `Добавить кодовую ячейку после ячейки ${cellId}`
  if (actionId === 'text') return `Добавить текстовую ячейку после ячейки ${cellId}`
  return `Добавить ячейку после ${cellId}`
}

const closeSessionMenu = () => {
  sessionMenuOpen.value = false
}

const toggleSessionMenu = () => {
  sessionMenuOpen.value = !sessionMenuOpen.value
}

const handleDocumentClick = (event) => {
  if (!sessionMenuOpen.value) return
  if (sessionMenuRef.value?.contains(event.target)) return
  closeSessionMenu()
}

const handleEscapeKey = (event) => {
  if (event.key !== 'Escape') return
  closeSessionMenu()
}

const refreshSessionFiles = async ({ silent = false } = {}) => {
  if (!hasValidId.value || !sessionId.value) {
    sessionStatus.value = 'stopped'
    sessionFiles.value = []
    return
  }

  try {
    const payload = await getNotebookSessionFiles(sessionId.value)
    sessionFiles.value = Array.isArray(payload?.files) ? payload.files : []
    sessionStatus.value = 'running'
    if (!silent) {
      sessionActionError.value = ''
    }
  } catch (error) {
    sessionFiles.value = []
    if (error?.status === 404) {
      sessionStatus.value = 'stopped'
      if (!silent) {
        sessionActionError.value = 'Сессия не запущена.'
      }
      return
    }
    if (!silent) {
      sessionActionError.value = error?.message || 'Не удалось получить файлы сессии.'
    }
  }
}

const runSessionAction = async (action) => {
  if (!hasValidId.value || !sessionId.value || sessionActionBusy.value) return
  sessionActionBusy.value = true
  sessionActionError.value = ''
  const previousStatus = sessionStatus.value
  sessionStatus.value = 'starting'
  try {
    await action()
  } catch (error) {
    sessionStatus.value = previousStatus
    sessionActionError.value = error?.message || 'Не удалось выполнить действие с сессией.'
  } finally {
    sessionActionBusy.value = false
  }
}

const startSession = async () => {
  await runSessionAction(async () => {
    await startNotebookSession(notebookId.value)
    sessionStatus.value = 'running'
    await refreshSessionFiles({ silent: true })
    closeSessionMenu()
  })
}

const restartSession = async () => {
  await runSessionAction(async () => {
    await resetNotebookSession(sessionId.value)
    sessionStatus.value = 'running'
    await refreshSessionFiles({ silent: true })
    closeSessionMenu()
  })
}

const stopSession = async () => {
  await runSessionAction(async () => {
    await stopNotebookSession(sessionId.value)
    sessionStatus.value = 'stopped'
    sessionFiles.value = []
    closeSessionMenu()
  })
}

const seedSavedContent = (cells) => {
  lastSavedContent.clear()
  saveTimers.forEach((timer) => clearTimeout(timer))
  saveTimers.clear()
  cells.forEach((cell) => {
    lastSavedContent.set(cell.id, typeof cell.content === 'string' ? cell.content : '')
  })
}

const saveCellContent = async (cell) => {
  if (!cell?.id || !hasValidId.value) return
  const content = typeof cell.content === 'string' ? cell.content : ''
  const lastSaved = lastSavedContent.get(cell.id)
  if (content === lastSaved) return

  try {
    if (cell.cell_type === 'code') {
      await saveCodeCell(notebookId.value, cell.id, content, cell.output || '')
    } else if (cell.cell_type === 'text') {
      await saveTextCell(notebookId.value, cell.id, content)
    }
    lastSavedContent.set(cell.id, content)
  } catch (error) {
    console.warn('Failed to autosave cell', cell.id, error)
  }
}

const scheduleSave = (cell) => {
  if (!cell?.id) return
  const existing = saveTimers.get(cell.id)
  if (existing) clearTimeout(existing)
  const timer = setTimeout(() => {
    saveTimers.delete(cell.id)
    saveCellContent(cell)
  }, 1000)
  saveTimers.set(cell.id, timer)
}

const flushSave = (cell) => {
  if (!cell?.id) return
  const timer = saveTimers.get(cell.id)
  if (timer) {
    clearTimeout(timer)
    saveTimers.delete(cell.id)
  }
  saveCellContent(cell)
}

const clearCellTimer = (cellId) => {
  const timer = saveTimers.get(cellId)
  if (timer) {
    clearTimeout(timer)
    saveTimers.delete(cellId)
  }
}

const selectCell = (cellId) => {
  selectedCellId.value = cellId
}

const createNotebookCell = async (type) => {
  if (!hasValidId.value || !['code', 'text'].includes(type)) return
  try {
    const response = await createCell(notebookId.value, type)
    const created = response?.cell
    if (!created || !notebook.value) {
      await loadNotebook()
      return
    }
    if (!Array.isArray(notebook.value.cells)) {
      notebook.value.cells = []
    }
    notebook.value.cells.push(created)
    lastSavedContent.set(created.id, typeof created.content === 'string' ? created.content : '')
    selectedCellId.value = created.id
  } catch (error) {
    console.warn('Failed to create cell', error)
  }
}

const getCellIndex = (cellId) => {
  return orderedCells.value.findIndex((item) => item.id === cellId)
}

const isCellFirst = (cell) => getCellIndex(cell.id) <= 0

const isCellLast = (cell) => {
  const index = getCellIndex(cell.id)
  return index === -1 || index === orderedCells.value.length - 1
}

const applyCellOrder = (order) => {
  if (!Array.isArray(order) || !Array.isArray(notebook.value?.cells)) return
  const nextOrder = new Map(order.map((item) => [item.id, item.execution_order]))
  notebook.value.cells.forEach((cell) => {
    if (nextOrder.has(cell.id)) {
      cell.execution_order = nextOrder.get(cell.id)
    }
  })
}

const shiftCell = async (cell, direction) => {
  if (!cell?.id || !hasValidId.value) return
  const currentIndex = getCellIndex(cell.id)
  if (currentIndex < 0) return
  const targetIndex = currentIndex + direction
  if (targetIndex < 0 || targetIndex >= orderedCells.value.length) return

  try {
    const response = await moveCell(notebookId.value, cell.id, targetIndex)
    applyCellOrder(response?.order)
  } catch (error) {
    console.warn('Failed to move cell', cell.id, error)
  }
}

const removeCell = async (cell) => {
  if (!cell?.id || !hasValidId.value || !notebook.value) return

  try {
    await deleteCell(notebookId.value, cell.id)
    clearCellTimer(cell.id)
    lastSavedContent.delete(cell.id)

    const list = Array.isArray(notebook.value.cells) ? notebook.value.cells : []
    notebook.value.cells = list.filter((item) => item.id !== cell.id)
    orderedCells.value.forEach((item, index) => {
      item.execution_order = index
    })

    if (selectedCellId.value === cell.id) {
      selectedCellId.value = null
    }
  } catch (error) {
    console.warn('Failed to delete cell', cell.id, error)
  }
}

const isErrorOutput = (output) => {
  if (!output || typeof output !== 'string') return false
  const text = output.toLowerCase()
  return text.includes('error') || text.includes('exception') || text.includes('traceback')
}

const loadNotebook = async () => {
  if (!hasValidId.value) {
    notebook.value = null
    state.value = 'error'
    stateMessage.value = 'Некорректный идентификатор блокнота.'
    sessionStatus.value = 'stopped'
    sessionFiles.value = []
    return
  }

  state.value = 'loading'
  stateMessage.value = ''
  selectedCellId.value = null
  try {
    notebook.value = await getNotebook(notebookId.value)
    if (Array.isArray(notebook.value?.cells)) {
      seedSavedContent(notebook.value.cells)
    }
    await refreshSessionFiles({ silent: true })
    state.value = 'ready'
  } catch (err) {
    const message = err?.message || 'Не удалось загрузить блокнот.'
    state.value = message.includes('404') ? 'not_found' : 'error'
    stateMessage.value = message
    notebook.value = null
    sessionStatus.value = 'stopped'
    sessionFiles.value = []
  }
}

watch(notebookId, () => {
  loadNotebook()
}, { immediate: true })

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleEscapeKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleEscapeKey)
  saveTimers.forEach((timer) => clearTimeout(timer))
  saveTimers.clear()
})
</script>

<style scoped>
.notebook-page {
  min-height: 100vh;
  background: var(--color-bg-default);
  font-family: var(--font-default);
  color: var(--color-text-primary);
  --cell-delete-bg-color: #d9534f;
}

.notebook-main {
  padding: 20px 30px 50px;
}

.notebook-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.notebook-title {
  font-family: var(--font-title);
  font-size: 48px;
  color: var(--color-title-text);
}

.notebook-state {
  padding: 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  font-size: 15px;
  color: var(--color-text-muted);
}

.notebook-state--error {
  border-color: var(--color-border-danger);
  color: var(--color-text-danger);
}

.notebook-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
  align-items: start;
}

.notebook-files {
  background: var(--color-bg-card);
  border-radius: 20px;
  padding: 10px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.25);
}

.files-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.files-title {
  margin: 0;
  font-size: 20px;
}

.files-upload-button {
  display: inline-flex;
  align-items: center;
  box-sizing: border-box;
  height: 29px;
  padding: 5px 10px;
  border-radius: 10px;
  border: none;
  background: var(--color-button-primary);
  color: var(--color-button-text-primary);
  font-size: 16px;
  line-height: 1;
  cursor: not-allowed;
  opacity: 0.9;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.files-empty {
  padding: 10px;
  background: var(--color-bg-primary);
  border-radius: 10px;
  color: var(--color-text-muted);
}

.file-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 10px;
  border-radius: 10px;
  background: var(--color-button-secondary);
  border: none;
  text-align: left;
}

.file-icon {
  width: 20px;
  height: 20px;
  color: var(--color-text-primary);
  display: inline-flex;
}

.file-icon svg {
  width: 100%;
  height: 100%;
}

.file-name {
  font-size: 16px;
  color: var(--color-text-primary);
}

.notebook-workspace {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.notebook-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.25);
  gap: 10px;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.toolbar-group--right {
  margin-left: auto;
}

.toolbar-pill {
  box-sizing: border-box;
  height: 29px;
  padding: 5px 10px;
  background: var(--color-button-primary);
  border: none;
  color: #fff;
  border-radius: 10px;
  font-size: 16px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  opacity: 1;
  user-select: none;
}

.toolbar-pill--static {
  cursor: default;
}

.toolbar-session-wrap {
  position: relative;
}

.toolbar-session {
  justify-content: space-between;
}

.toolbar-session-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.toolbar-session-dot--running {
  background: var(--color-session-active);
}

.toolbar-session-dot--starting {
  background: var(--color-session-starting);
}

.toolbar-session-dot--stopped {
  background: var(--color-session-stopped);
}


.session-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 180px;
  padding: 8px;
  border-radius: 12px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 20;
}

.session-menu-item {
  border: none;
  border-radius: 8px;
  padding: 8px 10px;
  text-align: left;
  background: var(--color-button-secondary);
  color: var(--color-text-primary);
  cursor: pointer;
}

.session-menu-item:disabled {
  opacity: 0.6;
  cursor: default;
}

.session-menu-item--danger {
  color: var(--color-text-danger);
}

.session-menu-meta {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.session-menu-error {
  color: var(--color-text-danger);
  font-size: 13px;
  line-height: 1.35;
}

.cells-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.cell-stack {
  position: relative;
}

.cell-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  align-items: start;
  position: relative;
  padding-right: 0;
  transition: padding-right 0.15s ease;
}

.cell-row--selected {
  padding-right: 52px;
}

.cells-empty {
  padding: 14px;
  background: var(--color-bg-card);
  border-radius: 16px;
  border: 1px dashed var(--color-border-light);
  color: var(--color-text-muted);
}

.cell-card {
  background: var(--color-bg-card);
  border-radius: 15px;
  padding: 10px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.25);
  transition: border-color 0.15s ease;
}

.cell-row--selected .cell-card {
  border-color: var(--color-border-primary, #6b8df7);
}

.cell-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: start;
}

.cell-body--text {
  grid-template-columns: 1fr;
}

.cell-run-button {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: none;
  background: var(--color-button-primary);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: not-allowed;
  opacity: 0.9;
}

.cell-run-button .material-symbols-rounded {
  font-size: 24px;
  line-height: 1;
  font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 20 !important;
  color: #fff;
}

.cell-content {
  flex: 1;
}

.code-block {
  background: var(--color-bg-primary);
  border-radius: 10px;
  padding: 10px 0;
}

.text-block {
  background: var(--color-bg-primary);
  border-radius: 10px;
  padding: 0;
}

.text-editor {
  width: 100%;
  height: 40px;
  min-height: 40px;
  border: none;
  border-radius: 10px;
  background: transparent;
  padding: 10px;
  resize: vertical;
  font: inherit;
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.45;
}

.text-editor:focus {
  outline: 1px solid var(--color-border-primary, #6b8df7);
}

.cell-actions {
  display: flex;
  flex-direction: column;
  gap: 5px;
  background: var(--color-bg-card);
  border-radius: 15px;
  padding: 5px;
  border: none;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.25);
  position: absolute;
  top: 0;
  right: 0;
  z-index: 3;
}

.cell-insert-zone {
  height: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: height 0.15s ease;
}

.cell-insert-group {
  opacity: 0;
  pointer-events: none;
  transform: translateY(-4px);
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.cell-insert-zone:hover {
  height: 59px;
}

.cell-insert-zone:hover .cell-insert-group {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.cell-stack:last-child .cell-insert-zone {
  height: 59px;
}

.cell-stack:last-child .cell-insert-group {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.cell-action-btn {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: none;
  background: var(--color-button-primary);
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cell-action-btn .material-symbols-rounded {
  color: #fff;
  font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 20;
}

.cell-action-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.cell-action-btn--danger {
  background: var(--cell-delete-bg-color);
}

.cell-output {
  margin-top: 8px;
  background: transparent;
  border-radius: 0;
  padding: 0;
  display: grid;
  grid-template-columns: 30px 1fr;
  column-gap: 15px;
  align-items: start;
  color: var(--color-text-primary);
}

.cell-output-icon {
  width: 30px;
  height: 30px;
  border-radius: 0;
  background: transparent;
  color: var(--color-text-muted);
  display: inline-flex;
  align-items: flex-start;
  justify-content: center;
  margin-top: 0;
}

.cell-output-icon--error {
  color: var(--color-error-text);
}

.cell-output-content {
  flex: 1;
  min-width: 0;
  margin-left: 0;
}

.cell-output-content :deep(:first-child) {
  margin-top: 0;
}

.cell-output-content :deep(pre) {
  margin: 0;
  font-family: var(--font-default);
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.cells-footer {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 10px;
}

.footer-group {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px;
  border-radius: 20px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.25);
}

.footer-pill {
  padding: 5px 10px;
  border-radius: 15px;
  border: none;
  background: var(--color-button-primary);
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  box-shadow: none;
}

@media (max-width: 1024px) {
  .notebook-layout {
    grid-template-columns: 1fr;
  }

  .notebook-files {
    order: 2;
  }

  .notebook-workspace {
    order: 1;
  }
}

@media (max-width: 720px) {
  .cell-row,
  .cell-row--selected {
    padding-right: 0;
  }

  .cell-body {
    grid-template-columns: 1fr;
  }

  .cell-actions {
    flex-direction: row;
    justify-content: flex-end;
    position: static;
    margin-top: 8px;
  }

  .cell-content {
    margin-right: 0;
  }
}
</style>

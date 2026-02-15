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
              Файлы появятся после запуска сессии
            </div>
            <button
              v-for="file in files"
              :key="file.name"
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
              <div
                v-for="action in toolbarActions"
                :key="action.id"
                :class="['toolbar-pill', 'toolbar-pill--' + action.id]"
              >
                <span class="toolbar-label">{{ action.label }}</span>
              </div>
            </div>
            <div class="toolbar-group toolbar-group--right">
              <div class="toolbar-pill toolbar-session">
                <span class="toolbar-label">Сессия</span>
                <span class="toolbar-session-dot" aria-hidden="true"></span>
              </div>
              <div class="toolbar-pill">
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
              <div class="cell-row">
                <article class="cell-card">
                  <div class="cell-body">
                    <button
                      v-if="cell.cell_type === 'code'"
                      class="cell-run-button"
                      type="button"
                      disabled
                      title="Запуск ячейки"
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
                        {{ cell.content || ' ' }}
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

                <div class="cell-actions">
                    <button
                      v-for="action in cellActions"
                      :key="action.id"
                      type="button"
                      class="cell-action-btn"
                      disabled
                      :title="action.title"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">{{ action.icon }}</span>
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
                    disabled
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
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import UiHeader from '@/components/ui/UiHeader.vue'
import NotebookCodeEditor from '@/components/NotebookCodeEditor.vue'
import { getNotebook, saveCodeCell, saveTextCell } from '@/api/notebook'

const route = useRoute()

const notebook = ref(null)
const state = ref('idle')
const stateMessage = ref('')
const saveTimers = new Map()
const lastSavedContent = new Map()

const notebookId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(notebookId.value) && notebookId.value > 0)

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

const files = computed(() => {
  return Array.isArray(notebook.value?.files) ? notebook.value.files : []
})

const toolbarActions = [
  { id: 'code', label: '+ Код', variant: 'primary' },
  { id: 'text', label: '+ Текст', variant: 'primary' },
  { id: 'run', label: 'Выполнить всё', variant: 'primary' },
]
const footerActions = [
  { id: 'code', label: '+ Код' },
  { id: 'text', label: '+ Текст' },
]

const cellActions = [
  { id: 'up', title: 'Вверх', icon: 'arrow_upward' },
  { id: 'down', title: 'Вниз', icon: 'arrow_downward' },
  { id: 'delete', title: 'Удалить', icon: 'delete' },
  { id: 'more', title: 'Еще', icon: 'more_horiz' },
]

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
    return
  }

  state.value = 'loading'
  stateMessage.value = ''
  try {
    notebook.value = await getNotebook(notebookId.value)
    if (Array.isArray(notebook.value?.cells)) {
      seedSavedContent(notebook.value.cells)
    }
    state.value = 'ready'
  } catch (err) {
    const message = err?.message || 'Не удалось загрузить блокнот.'
    state.value = message.includes('404') ? 'not_found' : 'error'
    stateMessage.value = message
    notebook.value = null
  }
}

watch(notebookId, () => {
  loadNotebook()
}, { immediate: true })
</script>

<style scoped>
.notebook-page {
  min-height: 100vh;
  background: var(--color-bg-default);
  font-family: var(--font-default);
  color: var(--color-text-primary);
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
  color: #fff;
  border-radius: 10px;
  font-size: 16px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: not-allowed;
  opacity: 0.9;
}
.toolbar-pill--run::before {
  content: "\25B6";
  font-size: 12px;
}

.toolbar-session-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--color-session-active);
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
}

.cell-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: start;
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
  padding: 10px;
  font-size: 14px;
  color: var(--color-text-primary);
  white-space: pre-wrap;
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
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.cell-row:hover .cell-actions {
  opacity: 1;
  pointer-events: auto;
}

.cell-row:hover {
  padding-right: 50px;
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
  cursor: not-allowed;
  display: flex;
  align-items: center;
  justify-content: center;
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
  cursor: not-allowed;
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
  .cell-row {
    grid-template-columns: 1fr;
  }

  .cell-body {
    grid-template-columns: 1fr;
  }

  .cell-actions {
    flex-direction: row;
    justify-content: flex-end;
  }

  .cell-content {
    margin-right: 0;
  }
}
</style>











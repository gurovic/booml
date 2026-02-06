<template>
  <div class="notebook-page">
    <UiHeader />

    <main class="notebook-main">
      <div class="container notebook-container">
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
              <button type="button" class="files-add-button" title="Загрузить файл" disabled>
                <svg class="files-add-icon" viewBox="0 0 24 24" aria-hidden="true">
                  <path
                    d="M12 6v12M6 12h12"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                  />
                </svg>
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
              <div
                v-for="action in toolbarActions"
                :key="action.id"
                :class="['toolbar-pill', action.variant === 'ghost' ? 'toolbar-pill--ghost' : '']"
              >
                <span class="toolbar-label">{{ action.label }}</span>
              </div>
            </div>

            <div class="cells-list">
              <div v-if="orderedCells.length === 0" class="cells-empty">
                В блокноте пока нет ячеек
              </div>

              <div
                v-for="cell in orderedCells"
                :key="cell.id"
                class="cell-row"
              >
                <article class="cell-card">
                  <div class="cell-body">
                    <button
                      v-if="cell.cell_type === 'code'"
                      class="cell-run-button"
                      type="button"
                      disabled
                      title="Запуск ячейки"
                    >
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <polygon points="8,5 19,12 8,19" fill="currentColor" />
                      </svg>
                    </button>

                    <div class="cell-content">
                      <div v-if="cell.cell_type === 'code'" class="code-block">
                        <div class="code-lines">
                          <span
                            v-for="(line, idx) in codeLines(cell.content)"
                            :key="`${cell.id}-line-${idx}`"
                            class="code-line"
                            v-text="line || ' '"
                          ></span>
                        </div>
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
                    <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                      <path
                        d="M5 12.5l4 4 10-10"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
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
            </div>

            <div class="cells-footer">
              <div class="footer-group">
                <button
                  v-for="action in footerActions"
                  :key="action.id"
                  type="button"
                  class="footer-pill"
                  disabled
                >
                  {{ action.label }}
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import UiHeader from '@/components/ui/UiHeader.vue'
import { getNotebook } from '@/api/notebook'

const route = useRoute()

const notebook = ref(null)
const state = ref('idle')
const stateMessage = ref('')

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
  { id: 'code', label: '+ Code', variant: 'primary' },
  { id: 'text', label: '+ Text', variant: 'primary' },
  { id: 'run', label: 'Run all', variant: 'ghost' },
]

const footerActions = [
  { id: 'code', label: '+ Code' },
  { id: 'text', label: '+ Text' },
]

const cellActions = [
  { id: 'up', title: 'Вверх', icon: 'arrow_upward' },
  { id: 'down', title: 'Вниз', icon: 'arrow_downward' },
  { id: 'delete', title: 'Удалить', icon: 'delete' },
]

const codeLines = (content) => {
  const text = typeof content === 'string' ? content : ''
  const lines = text.split('\n')
  return lines.length ? lines : ['']
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
  padding: 24px 0 40px;
}

.notebook-container {
  max-width: 1280px;
}

.notebook-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.notebook-title {
  font-family: var(--font-title);
  font-size: 44px;
  margin: 0;
  color: #0f172a;
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
  grid-template-columns: 320px 1fr;
  gap: 24px;
  align-items: start;
}

.notebook-files {
  background: var(--color-bg-card);
  border-radius: 20px;
  padding: 18px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 20px rgba(30, 38, 74, 0.08);
}

.files-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.files-title {
  margin: 0;
  font-size: 22px;
}

.files-add-button {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: none;
  background: var(--color-button-primary);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  cursor: not-allowed;
  opacity: 0.6;
}

.files-add-icon {
  width: 18px;
  height: 18px;
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.files-empty {
  padding: 12px 10px;
  background: var(--color-bg-primary);
  border-radius: 12px;
  font-size: 14px;
  color: var(--color-text-muted);
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--color-button-secondary);
  border: none;
  text-align: left;
}

.file-icon {
  width: 22px;
  height: 22px;
  color: #1f2a5a;
  display: inline-flex;
}

.file-icon svg {
  width: 100%;
  height: 100%;
}

.file-name {
  font-size: 15px;
  color: var(--color-text-primary);
}

.notebook-workspace {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.notebook-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--color-bg-card);
  border-radius: 16px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 20px rgba(30, 38, 74, 0.08);
}

.toolbar-pill {
  padding: 6px 14px;
  background: var(--color-button-primary);
  color: #fff;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 500;
}

.toolbar-pill--ghost {
  background: #e9ecff;
  color: #1f2a5a;
}

.cells-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.cell-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: start;
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
  border-radius: 20px;
  padding: 16px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 10px 24px rgba(30, 38, 74, 0.08);
}

.cell-body {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  align-items: start;
}

.cell-run-button {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  border: none;
  background: var(--color-button-primary);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: not-allowed;
  opacity: 0.9;
}

.cell-run-button svg {
  width: 22px;
  height: 22px;
}

.cell-content {
  flex: 1;
}

.code-block {
  background: var(--color-bg-primary);
  border-radius: 14px;
  padding: 16px 18px;
}

.code-lines {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 15px;
  line-height: 1.6;
  color: #1f2a5a;
}

.code-line {
  display: block;
  padding-left: 36px;
  position: relative;
  white-space: pre;
}

.code-lines {
  counter-reset: line;
}

.code-line::before {
  counter-increment: line;
  content: counter(line);
  position: absolute;
  left: 0;
  width: 28px;
  text-align: right;
  color: #9aa3c7;
}

.text-block {
  background: var(--color-bg-primary);
  border-radius: 14px;
  padding: 16px 18px;
  font-size: 15px;
  color: var(--color-text-primary);
  white-space: pre-wrap;
}

.cell-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--color-bg-card);
  border-radius: 16px;
  padding: 8px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 16px rgba(30, 38, 74, 0.08);
}

.cell-action-btn {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  border: none;
  background: var(--color-button-primary);
  color: #fff;
  font-size: 16px;
  cursor: not-allowed;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cell-output {
  margin-top: 14px;
  background: #f0edff;
  border-radius: 12px;
  padding: 12px 14px 12px 14px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  color: #1f2a5a;
  font-size: 15px;
}

.cell-output-icon {
  width: 28px;
  height: 28px;
  border-radius: 10px;
  background: #8b7bd4;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  margin-top: 2px;
}

.cell-output-icon svg {
  width: 18px;
  height: 18px;
}

.cell-output-icon--error {
  background: #f1b6b4;
  color: #7a1d1d;
}

.cell-output-content {
  flex: 1;
  min-width: 0;
}

.cell-output-content :deep(:first-child) {
  margin-top: 0;
}

.cell-output-content :deep(pre) {
  margin: 0;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.cells-footer {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 8px;
}

.footer-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 18px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 18px rgba(30, 38, 74, 0.12);
}

.footer-pill {
  padding: 8px 16px;
  border-radius: 12px;
  border: none;
  background: var(--color-button-primary);
  color: #fff;
  font-size: 14px;
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

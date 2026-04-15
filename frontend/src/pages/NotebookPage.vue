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
            <button
              type="button"
              class="files-upload-button"
              :disabled="!canManageFiles || fileActionBusy"
              @click="openFilePicker"
            >
              Загрузить
            </button>
            <input
              ref="fileInputRef"
              type="file"
              class="files-hidden-input"
              @change="handleFilePicked"
            >
          </div>
          <div class="files-list">
            <div v-if="files.length === 0" class="files-empty">
              {{ sessionStatus === 'running' ? 'В сессии пока нет файлов' : 'Файлы появятся после запуска сессии' }}
            </div>
            <div
              v-for="file in files"
              :key="file.path || file.name"
              class="file-item"
              role="button"
              tabindex="0"
              :title="`Скачать ${file.path || file.name}`"
              @click="downloadSessionFile(file)"
              @keydown.enter.prevent="downloadSessionFile(file)"
              @keydown.space.prevent="downloadSessionFile(file)"
            >
              <span class="file-main">
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
              </span>
              <span class="file-actions">
                <button
                  type="button"
                  class="file-action-btn"
                  :title="`Скачать ${file.path || file.name}`"
                  :aria-label="`Скачать ${file.path || file.name}`"
                  @click.stop="downloadSessionFile(file)"
                >
                  <span class="material-symbols-rounded" aria-hidden="true">download</span>
                </button>
                <button
                  type="button"
                  class="file-action-btn file-action-btn--danger"
                  :title="`Удалить ${file.path || file.name}`"
                  :aria-label="`Удалить ${file.path || file.name}`"
                  :disabled="!canManageFiles || fileActionBusy"
                  @click.stop="removeSessionFile(file)"
                >
                  <span class="material-symbols-rounded" aria-hidden="true">delete</span>
                </button>
              </span>
            </div>
          </div>
          <div v-if="fileActionError" class="files-error">{{ fileActionError }}</div>
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
              <button
                type="button"
                class="toolbar-pill toolbar-pill--run-all"
                :disabled="!canRunAll"
                aria-label="Выполнить все кодовые ячейки"
                @click="runAllCodeCells"
              >
                <span class="material-symbols-rounded toolbar-icon" aria-hidden="true">play_arrow</span>
                <span class="toolbar-label">Выполнить всё</span>
              </button>
            </div>
            <div class="toolbar-group toolbar-group--right">
              <div class="toolbar-device-toggle" role="group" aria-label="Устройство выполнения блокнота">
                <button
                  v-for="device in computeDeviceOptions"
                  :key="device.value"
                  type="button"
                  class="toolbar-device-option"
                  :class="{ 'toolbar-device-option--active': currentComputeDevice === device.value }"
                  :aria-pressed="currentComputeDevice === device.value ? 'true' : 'false'"
                  :disabled="!canChangeComputeDevice"
                  :title="deviceToggleTitle"
                  @click="saveNotebookDevice(device.value)"
                >
                  {{ device.label }}
                </button>
              </div>
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
              <div ref="settingsMenuRef" class="toolbar-settings-wrap">
                <button
                  type="button"
                  class="toolbar-pill toolbar-settings-button"
                  :aria-expanded="settingsMenuOpen ? 'true' : 'false'"
                  aria-label="Открыть настройки блокнота"
                  @click="toggleSettingsMenu"
                >
                  <span class="toolbar-label">Настройки</span>
                </button>
                <div v-if="settingsMenuOpen" class="settings-menu" aria-label="Панель настроек блокнота">
                  <h3 class="settings-menu-title">Настройки</h3>
                  <div class="settings-row">
                    <label class="settings-label" for="notebook-title-input">Название:</label>
                    <input
                      id="notebook-title-input"
                      v-model="notebookTitleDraft"
                      type="text"
                      class="settings-input"
                      maxlength="200"
                      placeholder="Название блокнота"
                    >
                  </div>
                  <div class="settings-row">
                    <span class="settings-label">Задача:</span>
                    <button
                      type="button"
                      class="settings-problem-link"
                      :disabled="!linkedProblemId"
                      @click="goToLinkedProblem"
                    >
                      {{ linkedProblemTitle }}
                    </button>
                  </div>
                  <div class="settings-actions">
                    <button
                      type="button"
                      class="settings-action settings-action--danger"
                      :disabled="settingsBusy"
                      @click="removeNotebookFromSettings"
                    >
                      Удалить блокнот
                    </button>
                    <button
                      type="button"
                      class="settings-action"
                      :disabled="settingsBusy"
                      @click="saveNotebookTitle"
                    >
                      Сохранить
                    </button>
                  </div>
                  <div v-if="settingsError" class="settings-error">{{ settingsError }}</div>
                </div>
              </div>
            </div>
          </div>
          <div v-if="deviceError" class="toolbar-error">{{ deviceError }}</div>

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
                  @keydown="(event) => handleCellCardKeydown(event, cell.id)"
                >
                  <div
                    class="cell-body"
                    :class="{ 'cell-body--text': cell.cell_type === 'text' }"
                  >
                    <button
                      v-if="cell.cell_type === 'code'"
                      class="cell-run-button"
                      type="button"
                      :disabled="!canRunCells || isCellRunning(cell.id) || runAllInProgress"
                      :title="canRunCells ? `Запустить ячейку ${cell.id}` : 'Сначала запустите сессию'"
                      :aria-label="`Запустить кодовую ячейку ${cell.id}`"
                      @click.stop="runCodeCell(cell)"
                    >
                      <span
                        class="material-symbols-rounded"
                        :class="{ 'cell-run-button-icon--spinning': isCellRunning(cell.id) }"
                        aria-hidden="true"
                      >
                        {{ isCellRunning(cell.id) ? 'autorenew' : 'play_arrow' }}
                      </span>
                    </button>

                    <div class="cell-content">
                      <div v-if="cell.cell_type === 'code'" class="code-block">
                        <NotebookCodeEditor
                          v-model="cell.content"
                          @update:modelValue="() => scheduleSave(cell)"
                          @blur="() => flushSave(cell)"
                        />
                      </div>

                      <div
                        v-else
                        class="text-block"
                        :class="{ 'text-block--editing': isEditingTextCell(cell.id) }"
                      >
                        <div
                          v-if="isEditingTextCell(cell.id)"
                          class="text-editor-shell"
                          @click.stop
                        >
                          <textarea
                            :ref="(element) => setTextEditorRef(cell.id, element)"
                            v-model="cell.content"
                            class="text-editor"
                            placeholder="Введите заметку"
                            :aria-label="`Текст ячейки ${cell.id}`"
                            @focus="selectCell(cell.id)"
                            @input="handleTextCellInput(cell)"
                            @blur="handleTextCellBlur(cell)"
                            @keydown.esc.stop.prevent="exitTextEditMode(cell)"
                          ></textarea>
                        </div>
                        <div
                          v-if="hasTextCellContent(cell)"
                          :ref="(element) => setTextRenderedRef(cell.id, element)"
                          class="text-rendered"
                          :class="{ 'text-rendered--editing': isEditingTextCell(cell.id) }"
                          @click.stop="selectCell(cell.id)"
                          @dblclick.stop="enterTextEditMode(cell)"
                          v-html="renderTextCellMarkdown(cell.content)"
                        ></div>
                        <div
                          v-else-if="!isEditingTextCell(cell.id)"
                          class="text-rendered text-rendered--empty"
                          @click.stop="selectCell(cell.id)"
                          @dblclick.stop="enterTextEditMode(cell)"
                        >
                          Двойной клик, чтобы добавить текст
                        </div>
                      </div>
                    </div>
                  </div>

                <div v-if="cell.output" class="cell-output">
                  <div
                    class="cell-output-menu-wrap"
                    @click.stop
                  >
                    <button
                      type="button"
                      class="cell-output-icon cell-output-menu-trigger"
                      :class="{ 'cell-output-icon--error': isErrorOutput(cell) }"
                      title="Действия с выводом"
                      aria-label="Открыть меню вывода"
                      @click.stop="toggleOutputMenu(cell.id)"
                    >
                      <span
                        v-if="isErrorOutput(cell)"
                        class="material-symbols-rounded"
                        aria-hidden="true"
                      >
                        error
                      </span>
                      <span v-else class="material-symbols-rounded" aria-hidden="true">
                        more_horiz
                      </span>
                    </button>
                    <div
                      v-if="outputMenuCellId === cell.id"
                      class="cell-output-menu"
                      aria-label="Меню вывода"
                    >
                      <button
                        type="button"
                        class="cell-output-menu-item"
                        @click.stop="copyOutput(cell)"
                      >
                        Копировать вывод
                      </button>
                      <button
                        type="button"
                        class="cell-output-menu-item"
                        @click.stop="downloadOutput(cell)"
                      >
                        Скачать вывод (.txt)
                      </button>
                      <button
                        type="button"
                        class="cell-output-menu-item"
                        @click.stop="clearOutput(cell)"
                      >
                        Очистить вывод
                      </button>
                    </div>
                  </div>
                  <div class="cell-output-content">
                    <template v-if="hasStructuredOutput(cell)">
                      <div
                        v-for="stream in getStructuredOutput(cell).streams"
                        :key="`${cell.id}-stream-${stream.channel}`"
                        :class="[
                          'cell-output-stream',
                          stream.channel === 'stderr' ? 'cell-output-stream--stderr' : 'cell-output-stream--stdout',
                        ]"
                      >
                        <div class="cell-output-stream-label">{{ stream.channel }}</div>
                        <pre>{{ stream.text }}</pre>
                      </div>

                      <div
                        v-for="(item, index) in getStructuredOutput(cell).rich_outputs"
                        :key="`${cell.id}-rich-${index}`"
                        class="cell-output-rich-item"
                      >
                        <iframe
                          v-if="isHtmlOutput(item) && richOutputNeedsIframe(item)"
                          class="cell-output-iframe"
                          :srcdoc="buildRichOutputSrcDoc(item)"
                          sandbox="allow-scripts allow-same-origin"
                          loading="lazy"
                          title="HTML output"
                        ></iframe>
                        <div
                          v-else-if="isHtmlOutput(item)"
                          class="cell-output-html"
                          v-html="item.data"
                        ></div>
                        <div
                          v-else-if="item.type === 'text/markdown'"
                          class="cell-output-markdown"
                          v-html="renderMarkdownOutput(item.data)"
                        ></div>
                        <img
                          v-else-if="isRichOutputImage(item)"
                          class="cell-output-image"
                          :src="getRichOutputImageSrc(item)"
                          :alt="item.name || 'Output image'"
                        >
                        <pre v-else>{{ formatRichOutputText(item) }}</pre>

                        <div v-if="item.metadata" class="cell-output-metadata">
                          {{ formatOutputMetadata(item.metadata) }}
                        </div>
                      </div>

                      <div v-if="getStructuredOutput(cell).error" class="cell-output-error">
                        <pre>{{ getStructuredOutput(cell).error }}</pre>
                      </div>

                      <div
                        v-if="getStructuredOutput(cell).artifacts.length > 0"
                        class="cell-output-artifacts"
                      >
                        <div class="cell-output-artifacts-title">Artifacts</div>
                        <ul class="cell-output-files">
                          <li
                            v-for="artifact in getStructuredOutput(cell).artifacts"
                            :key="artifact.path || artifact.name || artifact.url"
                          >
                            <a
                              v-if="artifact.url"
                              :href="artifact.url"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {{ artifact.name || artifact.path || artifact.url }}
                            </a>
                            <span v-else>{{ artifact.name || artifact.path }}</span>
                            <img
                              v-if="isArtifactImage(artifact)"
                              class="cell-output-image cell-output-image--artifact"
                              :src="artifact.url"
                              :alt="artifact.name || artifact.path || 'Artifact image'"
                            >
                          </li>
                        </ul>
                      </div>

                      <div class="cell-output-meta">
                        <span :class="['cell-output-status', `cell-output-status--${getStructuredOutput(cell).status}`]">
                          {{ getOutputStatusLabel(getStructuredOutput(cell).status) }}
                        </span>
                        <span>время: {{ formatDurationMs(getStructuredOutput(cell).meta.duration_ms) }}</span>
                        <span>память: {{ formatMemoryBytes(getStructuredOutput(cell).meta.memory_bytes) }}</span>
                      </div>
                    </template>

                    <div v-else v-html="cell.output"></div>
                  </div>
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
                    @click="createNotebookCell(action.id, cell.id)"
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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import UiHeader from '@/components/ui/UiHeader.vue'
import NotebookCodeEditor from '@/components/NotebookCodeEditor.vue'
import markdownKatex from '@/utils/markdownKatex'
import {
  createCell,
  deleteNotebookSessionFile,
  deleteCell,
  deleteNotebook,
  getNotebook,
  getNotebookSessionFileDownloadUrl,
  getNotebookSessionFiles,
  getNotebookSessionId,
  moveCell,
  resetNotebookSession,
  renameNotebook,
  runNotebookCell,
  saveCodeCell,
  saveTextCell,
  startNotebookSession,
  stopNotebookSession,
  updateNotebookDevice,
  uploadNotebookSessionFile,
} from '@/api/notebook'

const route = useRoute()
const router = useRouter()

const notebook = ref(null)
const state = ref('idle')
const stateMessage = ref('')
const selectedCellId = ref(null)
const sessionStatus = ref('stopped')
const sessionMenuOpen = ref(false)
const settingsMenuOpen = ref(false)
const sessionActionBusy = ref(false)
const sessionActionError = ref('')
const sessionMenuRef = ref(null)
const settingsMenuRef = ref(null)
const sessionFiles = ref([])
const fileInputRef = ref(null)
const fileActionBusy = ref(false)
const fileActionError = ref('')
const deviceError = ref('')
const runningCellIds = ref(new Set())
const runAllInProgress = ref(false)
const queuedCellRunIds = ref([])
const outputMenuCellId = ref(null)
const settingsBusy = ref(false)
const settingsError = ref('')
const notebookTitleDraft = ref('')
const editingTextCellId = ref(null)
const saveTimers = new Map()
const lastSavedContent = new Map()
const textEditorRefs = new Map()
const textRenderedRefs = new Map()
let mathTypesetQueued = false
let mathTypesetChain = Promise.resolve()

const OUTPUT_STORAGE_PREFIX = '__booml_output_v2__:'
const markdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})
markdownRenderer.use(markdownKatex, {
  throwOnError: false,
})

const textCellMarkdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

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

const linkedProblemId = computed(() => {
  const value = Number(notebook.value?.problem_id)
  return Number.isInteger(value) && value > 0 ? value : null
})

const linkedProblemTitle = computed(() => {
  if (notebook.value?.problem_title) return notebook.value.problem_title
  if (linkedProblemId.value) return `Задача ${linkedProblemId.value}`
  return 'Задача не привязана'
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

const currentComputeDevice = computed(() => {
  const device = String(notebook.value?.compute_device || '').toLowerCase()
  return device === 'gpu' ? 'gpu' : 'cpu'
})

const deviceToggleTitle = computed(() => {
  if (sessionStatus.value === 'running' || sessionStatus.value === 'starting') {
    return 'Изменение применится после перезапуска сессии'
  }
  return 'Устройство применится при запуске сессии'
})

const canChangeComputeDevice = computed(() => {
  return hasValidId.value && !settingsBusy.value && !sessionActionBusy.value && sessionStatus.value !== 'starting'
})

const canStartSession = computed(() => {
  return hasValidId.value && !sessionActionBusy.value && !settingsBusy.value && sessionStatus.value !== 'running'
})

const canRestartSession = computed(() => {
  return hasValidId.value && !sessionActionBusy.value && !settingsBusy.value && sessionStatus.value === 'running'
})

const canStopSession = computed(() => {
  return hasValidId.value && !sessionActionBusy.value && sessionStatus.value === 'running'
})

const canRunCells = computed(() => {
  return hasValidId.value && sessionStatus.value === 'running' && !sessionActionBusy.value
})

const hasCodeCells = computed(() => {
  return orderedCells.value.some((cell) => cell.cell_type === 'code')
})

const canRunAll = computed(() => {
  return canRunCells.value && !runAllInProgress.value && hasCodeCells.value
})

const canManageFiles = computed(() => {
  return hasValidId.value && sessionStatus.value === 'running'
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
const computeDeviceOptions = [
  { value: 'cpu', label: 'CPU' },
  { value: 'gpu', label: 'GPU' },
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

const handleCellCardKeydown = (event, cellId) => {
  if (event.target !== event.currentTarget) return
  if (event.key !== 'Enter' && event.key !== ' ') return
  event.preventDefault()
  selectCell(cellId)
}

const isCellRunning = (cellId) => {
  return runningCellIds.value.has(cellId)
}

const waitMs = (delay) => new Promise((resolve) => setTimeout(resolve, delay))

const waitForCellIdle = async (cellId) => {
  while (isCellRunning(cellId)) {
    await waitMs(120)
  }
}

const waitForNoRunningCells = async () => {
  while (runningCellIds.value.size > 0) {
    await waitMs(120)
  }
}

const clearQueuedCellRuns = () => {
  queuedCellRunIds.value = []
}

const setCellRunning = (cellId, running) => {
  const next = new Set(runningCellIds.value)
  if (running) {
    next.add(cellId)
  } else {
    next.delete(cellId)
  }
  runningCellIds.value = next
}

const OUTPUT_MODEL_FORMAT = 'booml_output_v2'

const buildSessionFileUrl = (sessionIdentifier, path) => {
  if (!sessionIdentifier || !path) return ''
  return `/api/sessions/file/?session_id=${encodeURIComponent(sessionIdentifier)}&path=${encodeURIComponent(path)}`
}

const detectMimeFromName = (name) => {
  const normalized = String(name || '').toLowerCase()
  if (normalized.endsWith('.png')) return 'image/png'
  if (normalized.endsWith('.jpg') || normalized.endsWith('.jpeg')) return 'image/jpeg'
  if (normalized.endsWith('.gif')) return 'image/gif'
  if (normalized.endsWith('.webp')) return 'image/webp'
  if (normalized.endsWith('.svg')) return 'image/svg+xml'
  return ''
}

const normalizeRichOutputItem = (item, sessionIdentifier) => {
  if (!item || typeof item !== 'object') return null
  const type = String(item.type || 'text/plain')
  const path = item.path ? String(item.path) : ''
  const name = item.name ? String(item.name) : ''
  const url = item.url ? String(item.url) : buildSessionFileUrl(sessionIdentifier, path)
  return {
    type,
    data: item.data ?? '',
    metadata: item.metadata ?? null,
    name,
    path,
    url,
  }
}

const normalizeArtifactItem = (item, sessionIdentifier) => {
  if (!item || typeof item !== 'object') return null
  const path = item.path ? String(item.path) : ''
  const name = item.name ? String(item.name) : path
  if (!name && !path) return null
  const url = item.url ? String(item.url) : buildSessionFileUrl(sessionIdentifier, path)
  return {
    name,
    path,
    url,
    mime: detectMimeFromName(name || path),
  }
}

const normalizeStructuredOutput = (payload) => {
  const streams = Array.isArray(payload?.streams)
    ? payload.streams
      .filter((item) => item && typeof item === 'object' && item.text)
      .map((item) => ({
        channel: String(item.channel || 'stdout').toLowerCase() === 'stderr' ? 'stderr' : 'stdout',
        text: String(item.text),
      }))
    : []
  const richOutputs = Array.isArray(payload?.rich_outputs)
    ? payload.rich_outputs
      .filter((item) => item && typeof item === 'object')
      .map((item) => ({
        type: String(item.type || 'text/plain'),
        data: item.data ?? '',
        metadata: item.metadata ?? null,
        name: item.name ? String(item.name) : '',
        path: item.path ? String(item.path) : '',
        url: item.url ? String(item.url) : '',
      }))
    : []
  const artifacts = Array.isArray(payload?.artifacts)
    ? payload.artifacts
      .filter((item) => item && typeof item === 'object')
      .map((item) => ({
        name: item.name ? String(item.name) : '',
        path: item.path ? String(item.path) : '',
        url: item.url ? String(item.url) : '',
        mime: item.mime ? String(item.mime) : detectMimeFromName(item.name || item.path || ''),
      }))
    : []
  const meta = payload?.meta && typeof payload.meta === 'object' ? payload.meta : {}
  const durationMsRaw = Number(meta.duration_ms)
  const memoryBytesRaw = Number(meta.memory_bytes)
  return {
    kind: 'structured',
    format: OUTPUT_MODEL_FORMAT,
    version: Number(payload?.version || 2),
    status: String(payload?.status || 'success'),
    meta: {
      duration_ms: Number.isFinite(durationMsRaw) && durationMsRaw >= 0 ? Math.round(durationMsRaw) : null,
      memory_bytes: Number.isFinite(memoryBytesRaw) && memoryBytesRaw >= 0 ? Math.round(memoryBytesRaw) : null,
    },
    created_at: payload?.created_at ? String(payload.created_at) : '',
    streams,
    rich_outputs: richOutputs,
    artifacts,
    error: payload?.error ? String(payload.error) : '',
  }
}

const extractMemoryBytes = (result) => {
  const direct = Number(result?.memory_bytes)
  if (Number.isFinite(direct) && direct >= 0) return Math.round(direct)

  const statsMemoryBytes = Number(result?.stats?.memory_bytes)
  if (Number.isFinite(statsMemoryBytes) && statsMemoryBytes >= 0) return Math.round(statsMemoryBytes)

  const statsMemMb = Number(result?.stats?.mem_mb)
  if (Number.isFinite(statsMemMb) && statsMemMb >= 0) return Math.round(statsMemMb * 1024 * 1024)

  const outputs = Array.isArray(result?.outputs) ? result.outputs : []
  for (const item of outputs) {
    const bytes = Number(item?.metadata?.memory_bytes)
    if (Number.isFinite(bytes) && bytes >= 0) return Math.round(bytes)
  }
  return null
}

const buildStructuredOutput = (result, options = {}) => {
  const durationMsRaw = Number(options?.durationMs)
  const durationMs = Number.isFinite(durationMsRaw) && durationMsRaw >= 0 ? Math.round(durationMsRaw) : null
  const memoryBytes = extractMemoryBytes(result)
  const currentSessionId = String(result?.session_id || sessionId.value || '')
  const streams = []
  if (result?.stdout) streams.push({ channel: 'stdout', text: String(result.stdout) })
  if (result?.stderr) streams.push({ channel: 'stderr', text: String(result.stderr) })

  const richOutputs = Array.isArray(result?.outputs)
    ? result.outputs
      .map((item) => normalizeRichOutputItem(item, currentSessionId))
      .filter(Boolean)
    : []
  const artifacts = Array.isArray(result?.artifacts)
    ? result.artifacts
      .map((item) => normalizeArtifactItem(item, currentSessionId))
      .filter(Boolean)
    : []

  return normalizeStructuredOutput({
    format: OUTPUT_MODEL_FORMAT,
    version: 2,
    status: String(result?.status || (result?.error ? 'error' : 'success')),
    meta: {
      duration_ms: durationMs,
      memory_bytes: memoryBytes,
    },
    created_at: new Date().toISOString(),
    streams,
    rich_outputs: richOutputs,
    artifacts,
    error: result?.error || '',
  })
}

const serializeOutputModel = (model) => {
  return `${OUTPUT_STORAGE_PREFIX}${JSON.stringify(model)}`
}

const parseCellOutput = (raw) => {
  if (!raw || typeof raw !== 'string') return null
  const trimmed = raw.trim()
  let payloadText = ''

  if (trimmed.startsWith(OUTPUT_STORAGE_PREFIX)) {
    payloadText = trimmed.slice(OUTPUT_STORAGE_PREFIX.length)
  } else if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    payloadText = trimmed
  }

  if (payloadText) {
    try {
      const parsed = JSON.parse(payloadText)
      if (parsed?.format === OUTPUT_MODEL_FORMAT) {
        return normalizeStructuredOutput(parsed)
      }
    } catch (_) {
      // fall through to legacy output
    }
  }

  return {
    kind: 'legacy',
    html: raw,
  }
}

const setCellOutput = (cell, output, parsedModel = null) => {
  if (!cell) return
  cell.output = output
  cell._outputRaw = output
  cell._outputModel = parsedModel || parseCellOutput(output)
}

const getCellOutputModel = (cell) => {
  if (!cell?.output || typeof cell.output !== 'string') return null
  if (cell._outputRaw === cell.output && cell._outputModel) return cell._outputModel
  const parsed = parseCellOutput(cell.output)
  cell._outputRaw = cell.output
  cell._outputModel = parsed
  return parsed
}

const hasStructuredOutput = (cell) => {
  const parsed = getCellOutputModel(cell)
  return parsed?.kind === 'structured'
}

const getStructuredOutput = (cell) => {
  const parsed = getCellOutputModel(cell)
  return parsed?.kind === 'structured' ? parsed : null
}

const stripHtmlTags = (value) => {
  if (!value || typeof value !== 'string') return ''
  const container = document.createElement('div')
  container.innerHTML = value
  return (container.innerText || container.textContent || '').trim()
}

const renderMarkdownOutput = (value) => {
  const source = String(value || '')
  if (!source) return ''
  return markdownRenderer.render(source)
}

const renderTextCellMarkdown = (value) => {
  const source = String(value || '')
  if (!source) return ''
  return textCellMarkdownRenderer.render(source)
}

const hasTextCellContent = (cell) => {
  return Boolean(String(cell?.content || '').trim())
}

const isEditingTextCell = (cellId) => {
  return editingTextCellId.value === cellId
}

const resizeTextEditor = (element) => {
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.max(element.scrollHeight, 44)}px`
}

const setTextEditorRef = (cellId, element) => {
  if (!cellId) return
  if (element) {
    textEditorRefs.set(cellId, element)
    resizeTextEditor(element)
    return
  }
  textEditorRefs.delete(cellId)
}

const setTextRenderedRef = (cellId, element) => {
  if (!cellId) return
  if (element) {
    textRenderedRefs.set(cellId, element)
    scheduleMathTypeset()
    return
  }
  textRenderedRefs.delete(cellId)
}

const runMathTypeset = async () => {
  if (typeof window === 'undefined') return
  const mathJax = window.MathJax
  if (!mathJax?.typesetPromise) return

  const elements = [...textRenderedRefs.values()].filter(Boolean)
  if (elements.length === 0) return

  try {
    await nextTick()
    if (typeof mathJax.typesetClear === 'function') {
      mathJax.typesetClear(elements)
    }
    await mathJax.typesetPromise(elements)
  } catch (error) {
    console.warn('Failed to typeset MathJax content', error)
  }
}

const scheduleMathTypeset = () => {
  if (mathTypesetQueued) return
  mathTypesetQueued = true
  mathTypesetChain = mathTypesetChain
    .catch(() => {})
    .then(async () => {
      await nextTick()
      mathTypesetQueued = false
      await runMathTypeset()
    })
}

const focusTextEditor = (cellId) => {
  nextTick(() => {
    const editor = textEditorRefs.get(cellId)
    if (!editor) return
    resizeTextEditor(editor)
    editor.focus()
    const end = editor.value.length
    editor.setSelectionRange(end, end)
  })
}

const enterTextEditMode = (cell) => {
  if (!cell?.id || cell.cell_type !== 'text') return
  selectedCellId.value = cell.id
  editingTextCellId.value = cell.id
  focusTextEditor(cell.id)
  scheduleMathTypeset()
}

const exitTextEditMode = (cell) => {
  if (!cell?.id || editingTextCellId.value !== cell.id) return
  flushSave(cell)
  editingTextCellId.value = null
}

const handleTextCellInput = (cell) => {
  scheduleSave(cell)
  nextTick(() => {
    resizeTextEditor(textEditorRefs.get(cell?.id))
  })
  scheduleMathTypeset()
}

const handleTextCellBlur = (cell) => {
  flushSave(cell)
  if (editingTextCellId.value === cell?.id) {
    editingTextCellId.value = null
  }
  scheduleMathTypeset()
}

const isHtmlOutput = (item) => {
  const type = String(item?.type || '').toLowerCase()
  return type === 'text/html'
}

const richOutputNeedsIframe = (item) => {
  if (!isHtmlOutput(item)) return false
  const html = String(item?.data || '')
  return html.includes('<script')
}

const buildRichOutputSrcDoc = (item) => {
  const html = String(item?.data || '')
  return [
    '<!doctype html>',
    '<html>',
    '<head><meta charset="utf-8"><style>body{margin:0;padding:0;font-family:Roboto,sans-serif;background:transparent;}</style></head>',
    '<body>',
    html,
    '</body>',
    '</html>',
  ].join('')
}

const isImageMime = (mime) => {
  return String(mime || '').toLowerCase().startsWith('image/')
}

const isRichOutputImage = (item) => {
  if (!item) return false
  if (isImageMime(item.type)) return Boolean(item.data || item.url || item.path)
  return false
}

const getRichOutputImageSrc = (item) => {
  if (!item) return ''
  const type = String(item.type || 'image/png')
  if (item.data) {
    const data = String(item.data)
    if (data.startsWith('data:')) return data
    return `data:${type};base64,${data}`
  }
  if (item.url) return String(item.url)
  return ''
}

const isArtifactImage = (artifact) => {
  return Boolean(artifact?.url) && isImageMime(artifact?.mime)
}

const formatRichOutputText = (item) => {
  if (!item) return ''
  if (typeof item.data === 'string') return item.data
  if (item.data == null) return ''
  try {
    return JSON.stringify(item.data, null, 2)
  } catch (_) {
    return String(item.data)
  }
}

const formatOutputMetadata = (metadata) => {
  if (!metadata || typeof metadata !== 'object') return ''
  const pairs = Object.entries(metadata)
    .slice(0, 8)
    .map(([key, value]) => `${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`)
  return pairs.join(' | ')
}

const getOutputStatusLabel = (status) => {
  if (status === 'success') return 'Успешно'
  if (status === 'error') return 'Ошибка'
  if (status === 'input_required') return 'Нужен ввод'
  if (status === 'running') return 'Выполняется'
  return status || 'Готово'
}

const formatDurationMs = (value) => {
  const ms = Number(value)
  if (!Number.isFinite(ms) || ms < 0) return '—'
  if (ms < 1000) return `${Math.round(ms)} мс`
  return `${(ms / 1000).toFixed(ms >= 10000 ? 0 : 2)} с`
}

const formatMemoryBytes = (value) => {
  const bytes = Number(value)
  if (!Number.isFinite(bytes) || bytes < 0) return '—'
  if (bytes < 1024) return `${Math.round(bytes)} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

const structuredOutputToText = (model) => {
  if (!model || model.kind !== 'structured') return ''
  const chunks = []
  model.streams.forEach((stream) => {
    if (stream?.text) {
      chunks.push(`[${stream.channel}]`)
      chunks.push(stream.text)
    }
  })
  model.rich_outputs.forEach((item) => {
    const type = String(item?.type || '').toLowerCase()
    if (type === 'text/plain') {
      chunks.push(formatRichOutputText(item))
      return
    }
    if (type === 'text/markdown') {
      chunks.push(String(item?.data || ''))
      return
    }
    if (type === 'text/html') {
      chunks.push(stripHtmlTags(String(item?.data || '')))
      return
    }
    if (isImageMime(type)) {
      chunks.push(`[image ${item?.name || item?.path || ''}]`.trim())
      return
    }
    chunks.push(formatRichOutputText(item))
  })
  if (model.error) {
    chunks.push('[error]')
    chunks.push(model.error)
  }
  if (Array.isArray(model.artifacts) && model.artifacts.length > 0) {
    chunks.push('[artifacts]')
    model.artifacts.forEach((artifact) => {
      chunks.push(artifact?.name || artifact?.path || '')
    })
  }
  return chunks.filter(Boolean).join('\n')
}

const runCodeCell = async (cell, options = {}) => {
  const { refreshFiles = true } = options
  if (runAllInProgress.value && !options.fromRunAll) return
  if (!cell?.id || cell.cell_type !== 'code' || !canRunCells.value || isCellRunning(cell.id)) return
  setCellRunning(cell.id, true)
  const startedAt = typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now()
  try {
    // Avoid duplicate save request from pending autosave timer when user runs immediately after typing.
    clearCellTimer(cell.id)
    const content = typeof cell.content === 'string' ? cell.content : ''
    setCellOutput(cell, '')
    await saveCodeCell(notebookId.value, cell.id, content, '')
    lastSavedContent.set(cell.id, content)
    const result = await runNotebookCell(sessionId.value, cell.id)
    const finishedAt = typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now()
    const outputModel = buildStructuredOutput(result, { durationMs: finishedAt - startedAt })
    const outputPayload = serializeOutputModel(outputModel)
    setCellOutput(cell, outputPayload, outputModel)
    await saveCodeCell(notebookId.value, cell.id, content, outputPayload)
    if (refreshFiles) {
      await refreshSessionFiles({ silent: true })
    }
  } catch (error) {
    const message = error?.message || 'Не удалось выполнить ячейку.'
    const failedAt = typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now()
    const outputModel = buildStructuredOutput({
      status: 'error',
      error: message,
      stdout: '',
      stderr: '',
      outputs: [],
      artifacts: [],
      session_id: sessionId.value,
    }, { durationMs: failedAt - startedAt })
    const outputPayload = serializeOutputModel(outputModel)
    setCellOutput(cell, outputPayload, outputModel)
    try {
      await saveCodeCell(notebookId.value, cell.id, cell.content || '', outputPayload)
    } catch (_) {
      // No-op: local output is still shown.
    }
  } finally {
    setCellRunning(cell.id, false)
  }
}

const runAllCodeCells = async () => {
  if (!canRunAll.value) return
  runAllInProgress.value = true
  clearQueuedCellRuns()
  try {
    await waitForNoRunningCells()
    const codeCells = orderedCells.value.filter((cell) => cell.cell_type === 'code')
    for (const cell of codeCells) {
      await waitForCellIdle(cell.id)
      await runCodeCell(cell, { refreshFiles: false, fromRunAll: true })
    }
    await refreshSessionFiles({ silent: true })
  } finally {
    runAllInProgress.value = false
  }
}

const closeSessionMenu = () => {
  sessionMenuOpen.value = false
}

const closeSettingsMenu = () => {
  settingsMenuOpen.value = false
  settingsError.value = ''
}

const toggleSessionMenu = () => {
  closeSettingsMenu()
  sessionMenuOpen.value = !sessionMenuOpen.value
}

const closeOutputMenu = () => {
  outputMenuCellId.value = null
}

const toggleOutputMenu = (cellId) => {
  outputMenuCellId.value = outputMenuCellId.value === cellId ? null : cellId
}

const extractCellOutputText = (cell) => {
  if (!cell?.output) return ''
  const model = getCellOutputModel(cell)
  if (model?.kind === 'structured') {
    return structuredOutputToText(model)
  }
  if (model?.kind === 'legacy') {
    return stripHtmlTags(model.html)
  }
  return stripHtmlTags(cell.output)
}

const copyOutput = async (cell) => {
  if (!cell?.output) return
  const text = extractCellOutputText(cell)
  if (!text) {
    closeOutputMenu()
    return
  }
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
  } catch (error) {
    console.warn('Failed to copy output', error)
  } finally {
    closeOutputMenu()
  }
}

const downloadOutput = (cell) => {
  if (!cell?.id || !cell.output) return
  const text = extractCellOutputText(cell)
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `notebook-${notebookId.value}-cell-${cell.id}-output.txt`
  link.rel = 'noopener noreferrer'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  closeOutputMenu()
}

const clearOutput = async (cell) => {
  if (!cell?.id || !hasValidId.value || cell.cell_type !== 'code') return
  const content = typeof cell.content === 'string' ? cell.content : ''
  try {
    await saveCodeCell(notebookId.value, cell.id, content, '')
    setCellOutput(cell, '')
  } catch (error) {
    console.warn('Failed to clear output', cell.id, error)
  } finally {
    closeOutputMenu()
  }
}

const toggleSettingsMenu = () => {
  closeSessionMenu()
  closeOutputMenu()
  settingsError.value = ''
  notebookTitleDraft.value = notebook.value?.title || ''
  settingsMenuOpen.value = !settingsMenuOpen.value
}

const saveNotebookTitle = async () => {
  if (!hasValidId.value || settingsBusy.value) return
  const title = (notebookTitleDraft.value || '').trim()
  if (!title) {
    settingsError.value = 'Название блокнота не может быть пустым.'
    return
  }
  if (title.length > 200) {
    settingsError.value = 'Максимальная длина названия: 200 символов.'
    return
  }

  settingsBusy.value = true
  settingsError.value = ''
  try {
    const result = await renameNotebook(notebookId.value, title)
    if (notebook.value) {
      notebook.value.title = result?.title || title
    }
    closeSettingsMenu()
  } catch (error) {
    settingsError.value = error?.message || 'Не удалось сохранить название.'
  } finally {
    settingsBusy.value = false
  }
}

const saveNotebookDevice = async (device) => {
  const normalized = String(device || '').toLowerCase()
  if (!canChangeComputeDevice.value || normalized === currentComputeDevice.value) return
  if (normalized !== 'cpu' && normalized !== 'gpu') {
    deviceError.value = 'Недопустимое устройство вычислений.'
    return
  }

  settingsBusy.value = true
  deviceError.value = ''
  try {
    const result = await updateNotebookDevice(notebookId.value, normalized)
    if (notebook.value) {
      notebook.value.compute_device = result?.compute_device || normalized
    }
  } catch (error) {
    deviceError.value = error?.message || 'Не удалось обновить устройство вычислений.'
  } finally {
    settingsBusy.value = false
  }
}

const goToLinkedProblem = async () => {
  if (!linkedProblemId.value) return
  closeSettingsMenu()
  await router.push(`/problem/${linkedProblemId.value}`)
}

const removeNotebookFromSettings = async () => {
  if (!hasValidId.value || settingsBusy.value) return
  settingsBusy.value = true
  settingsError.value = ''
  try {
    await deleteNotebook(notebookId.value)
    const fallbackTarget = linkedProblemId.value ? `/problem/${linkedProblemId.value}` : '/'
    await router.push(fallbackTarget)
  } catch (error) {
    settingsError.value = error?.message || 'Не удалось удалить блокнот.'
  } finally {
    settingsBusy.value = false
  }
}

const handleDocumentClick = (event) => {
  const target = event.target
  if (sessionMenuOpen.value && !sessionMenuRef.value?.contains(target)) {
    closeSessionMenu()
  }
  if (settingsMenuOpen.value && !settingsMenuRef.value?.contains(target)) {
    closeSettingsMenu()
  }
  if (outputMenuCellId.value && !target?.closest?.('.cell-output-menu-wrap')) {
    closeOutputMenu()
  }
}

const handleEscapeKey = (event) => {
  if (event.key !== 'Escape') return
  closeSessionMenu()
  closeOutputMenu()
  closeSettingsMenu()
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
      fileActionError.value = ''
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

const openFilePicker = () => {
  if (!canManageFiles.value || fileActionBusy.value) return
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
    fileInputRef.value.click()
  }
}

const handleFilePicked = async (event) => {
  const input = event?.target
  const file = input?.files?.[0]
  if (!file || !sessionId.value || !canManageFiles.value) return
  fileActionBusy.value = true
  fileActionError.value = ''
  try {
    await uploadNotebookSessionFile(sessionId.value, file)
    await refreshSessionFiles({ silent: true })
  } catch (error) {
    fileActionError.value = error?.message || 'Не удалось загрузить файл.'
  } finally {
    fileActionBusy.value = false
    if (input) input.value = ''
  }
}

const downloadSessionFile = (file) => {
  const path = file?.path
  if (!path || !sessionId.value) return
  const href = getNotebookSessionFileDownloadUrl(sessionId.value, path)
  const link = document.createElement('a')
  link.href = href
  link.download = file?.name || ''
  link.rel = 'noopener noreferrer'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const removeSessionFile = async (file) => {
  const path = file?.path
  if (!path || !sessionId.value || !canManageFiles.value || fileActionBusy.value) return
  fileActionBusy.value = true
  fileActionError.value = ''
  try {
    await deleteNotebookSessionFile(sessionId.value, path)
    await refreshSessionFiles({ silent: true })
  } catch (error) {
    fileActionError.value = error?.message || 'Не удалось удалить файл.'
  } finally {
    fileActionBusy.value = false
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
    fileActionError.value = ''
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

const createNotebookCell = async (type, targetCellId = null) => {
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

    if (targetCellId) {
      const targetIndex = notebook.value.cells.findIndex(cell => cell.id === targetCellId)
      if (targetIndex !== -1) {
        notebook.value.cells.splice(targetIndex + 1, 0, created)
        notebook.value.cells.forEach((cell, index) => {
          cell.execution_order = index
        })
      } else {
        notebook.value.cells.push(created)
      }
    } else {
      notebook.value.cells.push(created)
    }

    lastSavedContent.set(created.id, typeof created.content === 'string' ? created.content : '')
    selectedCellId.value = created.id
    if (created.cell_type === 'text') {
      enterTextEditMode(created)
    }
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
    if (editingTextCellId.value === cell.id) {
      editingTextCellId.value = null
    }
  } catch (error) {
    console.warn('Failed to delete cell', cell.id, error)
  }
}

const isErrorOutput = (cell) => {
  if (!cell?.output || typeof cell.output !== 'string') return false
  const model = getCellOutputModel(cell)
  if (model?.kind === 'structured') {
    return model.status === 'error' || Boolean(model.error)
  }
  const text = cell.output.toLowerCase()
  return text.includes('error') || text.includes('exception') || text.includes('traceback')
}

const loadNotebook = async () => {
  if (!hasValidId.value) {
    notebook.value = null
    state.value = 'error'
    stateMessage.value = 'Некорректный идентификатор блокнота.'
    sessionStatus.value = 'stopped'
    sessionFiles.value = []
    fileActionError.value = ''
    deviceError.value = ''
    return
  }

  state.value = 'loading'
  stateMessage.value = ''
  selectedCellId.value = null
  editingTextCellId.value = null
  deviceError.value = ''
  closeOutputMenu()
  try {
    notebook.value = await getNotebook(notebookId.value)
    notebookTitleDraft.value = notebook.value?.title || ''
    if (Array.isArray(notebook.value?.cells)) {
      notebook.value.cells.forEach((cell) => {
        if (typeof cell.output === 'string' && cell.output) {
          cell._outputRaw = cell.output
          cell._outputModel = parseCellOutput(cell.output)
        } else {
          cell._outputRaw = ''
          cell._outputModel = null
        }
      })
      seedSavedContent(notebook.value.cells)
    }
    await refreshSessionFiles({ silent: true })
    state.value = 'ready'
    scheduleMathTypeset()
  } catch (err) {
    const message = err?.message || 'Не удалось загрузить блокнот.'
    state.value = message.includes('404') ? 'not_found' : 'error'
    stateMessage.value = message
    notebook.value = null
    sessionStatus.value = 'stopped'
    sessionFiles.value = []
    fileActionError.value = ''
    deviceError.value = ''
  }
}

watch(notebookId, () => {
  loadNotebook()
}, { immediate: true })

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleEscapeKey)
  window.addEventListener('booml-mathjax-ready', scheduleMathTypeset)
  scheduleMathTypeset()
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleEscapeKey)
  window.removeEventListener('booml-mathjax-ready', scheduleMathTypeset)
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
  overflow-wrap: anywhere;
  word-break: break-word;
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
  cursor: pointer;
  opacity: 1;
}

.files-upload-button:disabled {
  cursor: not-allowed;
  opacity: 0.75;
}

.files-hidden-input {
  display: none;
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
  justify-content: space-between;
  gap: 8px;
  padding: 10px;
  border-radius: 10px;
  background: var(--color-button-secondary);
  border: none;
  text-align: left;
  cursor: pointer;
}

.file-main {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.file-item:hover .file-actions,
.file-item:focus-visible .file-actions,
.file-item:focus-within .file-actions {
  opacity: 1;
  pointer-events: auto;
}

.file-action-btn {
  width: 24px;
  height: 24px;
  border-radius: 8px;
  border: none;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.file-action-btn .material-symbols-rounded {
  font-size: 18px;
  line-height: 1;
}

.file-action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.file-action-btn--danger {
  color: var(--color-text-danger);
}

.files-error {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text-danger);
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

.toolbar-pill:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.toolbar-icon {
  font-size: 18px;
  line-height: 1;
  color: #fff;
  font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 20;
}

.toolbar-settings-wrap {
  position: relative;
}

.toolbar-settings-button {
  justify-content: center;
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

.toolbar-device-toggle {
  display: inline-flex;
  align-items: center;
  height: 29px;
  padding: 2px;
  border-radius: 10px;
  background: var(--color-button-secondary);
  border: 1px solid var(--color-border-light);
  gap: 2px;
}

.toolbar-device-option {
  min-width: 42px;
  height: 23px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
}

.toolbar-device-option--active {
  background: var(--color-button-primary);
  color: var(--color-button-text-primary);
}

.toolbar-device-option:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.toolbar-error {
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 56, 60, 0.08);
  color: var(--color-text-danger);
  font-size: 13px;
  line-height: 1.3;
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

.settings-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 340px;
  max-width: min(92vw, 340px);
  padding: 8px;
  border-radius: 12px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 30;
}

.settings-menu-title {
  margin: 0;
  font-size: 16px;
  line-height: 1.2;
}

.settings-row {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 8px;
}

.settings-label {
  font-size: 14px;
  line-height: 1.2;
  white-space: nowrap;
}

.settings-input,
.settings-problem-link {
  width: 100%;
  min-height: 28px;
  border: none;
  border-radius: 8px;
  padding: 4px 10px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font: inherit;
  font-size: 14px;
  text-align: left;
  text-decoration: none;
}

.settings-problem-link {
  cursor: pointer;
}

.settings-problem-link:disabled {
  opacity: 0.6;
  cursor: default;
}

.settings-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.settings-action {
  border: none;
  border-radius: 8px;
  background: var(--color-button-primary);
  color: var(--color-button-text-primary);
  padding: 6px 10px;
  font: inherit;
  font-size: 14px;
  cursor: pointer;
}

.settings-action:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.settings-action--danger {
  background: var(--color-button-primary);
}

.settings-error {
  font-size: 12px;
  color: var(--color-text-danger);
  line-height: 1.25;
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
  cursor: pointer;
  opacity: 1;
}

.cell-run-button .material-symbols-rounded {
  font-size: 24px;
  line-height: 1;
  font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 20 !important;
  color: #fff;
}

.cell-run-button-icon--spinning {
  animation: cell-run-spin 0.9s linear infinite;
}

@keyframes cell-run-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.cell-run-button:disabled {
  cursor: not-allowed;
  opacity: 0.7;
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
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.text-block--editing {
  gap: 8px;
}

.text-editor-shell {
  background: var(--color-bg-primary);
  border-radius: 10px;
  padding: 0;
}

.text-editor {
  width: 100%;
  min-height: 44px;
  border: none;
  border-radius: 10px;
  background: transparent;
  padding: 10px;
  resize: none;
  overflow: hidden;
  font: inherit;
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.45;
}

.text-editor:focus {
  outline: none;
}

.text-rendered {
  min-height: 24px;
  padding: 2px 10px 0;
  color: var(--color-text-primary);
  cursor: text;
}

.text-rendered--editing {
  padding-top: 0;
}

.text-rendered--empty {
  color: var(--color-text-muted);
}

.text-rendered :deep(*:first-child) {
  margin-top: 0;
}

.text-rendered :deep(*:last-child) {
  margin-bottom: 0;
}

.text-rendered :deep(p) {
  margin: 0 0 10px;
  line-height: 1.5;
}

.text-rendered :deep(h1),
.text-rendered :deep(h2),
.text-rendered :deep(h3),
.text-rendered :deep(h4),
.text-rendered :deep(h5),
.text-rendered :deep(h6) {
  margin: 0 0 10px;
  line-height: 1.25;
}

.text-rendered :deep(ul),
.text-rendered :deep(ol),
.text-rendered :deep(blockquote),
.text-rendered :deep(pre) {
  margin: 0 0 10px;
}

.text-rendered :deep(ul),
.text-rendered :deep(ol) {
  padding-left: 22px;
}

.text-rendered :deep(code) {
  font-family: var(--font-code, monospace);
}

.text-rendered :deep(pre) {
  padding: 10px;
  border-radius: 10px;
  background: var(--color-bg-primary);
  overflow-x: auto;
}

.text-rendered :deep(blockquote) {
  padding-left: 12px;
  border-left: 3px solid var(--color-border-light);
  color: var(--color-text-muted);
}

.text-rendered :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.text-rendered :deep(th),
.text-rendered :deep(td) {
  border: 1px solid var(--color-border-light);
  padding: 6px 8px;
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
  border-radius: 0;
  background: transparent;
  border: none;
  padding: 0;
  color: var(--color-text-muted);
  display: inline-flex;
  align-items: flex-start;
  justify-content: center;
  margin-top: 0;
}

.cell-output-menu-wrap {
  position: relative;
  display: inline-flex;
  width: 30px;
  justify-content: center;
  align-items: flex-start;
}

.cell-output-menu-trigger {
  cursor: pointer;
}

.cell-output-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 170px;
  padding: 6px;
  border-radius: 10px;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-card);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 12;
}

.cell-output-menu-item {
  border: none;
  border-radius: 8px;
  background: var(--color-button-secondary);
  color: var(--color-text-primary);
  text-align: left;
  font: inherit;
  font-size: 14px;
  line-height: 1.3;
  padding: 7px 8px;
  cursor: pointer;
}

.cell-output-menu-item:hover {
  filter: brightness(0.98);
}

.cell-output-icon--error {
  color: var(--color-error-text);
}

.cell-output-content {
  flex: 1;
  min-width: 0;
  margin-left: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cell-output-stream {
  border-radius: 8px;
  border: 1px solid var(--color-border-light);
  background: rgba(255, 255, 255, 0.24);
  padding: 8px;
}

.cell-output-stream--stderr {
  border-color: var(--color-border-danger, #ff8d93);
  background: rgba(255, 56, 60, 0.08);
}

.cell-output-stream-label {
  font-size: 12px;
  color: var(--color-text-muted);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.cell-output-rich-item,
.cell-output-error,
.cell-output-artifacts {
  border-radius: 8px;
  border: 1px solid var(--color-border-light);
  background: rgba(255, 255, 255, 0.24);
  padding: 8px;
}

.cell-output-error {
  border-color: var(--color-border-danger, #ff8d93);
  background: rgba(255, 56, 60, 0.08);
}

.cell-output-html :deep(table),
.cell-output-markdown :deep(table) {
  border-collapse: collapse;
  width: 100%;
}

.cell-output-html :deep(td),
.cell-output-html :deep(th),
.cell-output-markdown :deep(td),
.cell-output-markdown :deep(th) {
  border: 1px solid var(--color-border-light);
  padding: 4px 6px;
}

.cell-output-iframe {
  width: 100%;
  min-height: 220px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  background: #fff;
}

.cell-output-image {
  max-width: min(100%, 900px);
  border-radius: 8px;
  border: 1px solid var(--color-border-light);
  background: #fff;
}

.cell-output-image--artifact {
  margin-top: 6px;
  max-width: 320px;
}

.cell-output-metadata {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.cell-output-artifacts-title {
  margin-bottom: 6px;
  font-size: 12px;
  text-transform: uppercase;
  color: var(--color-text-muted);
}

.cell-output-meta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.cell-output-status {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
  line-height: 1.2;
  border: 1px solid transparent;
}

.cell-output-status--success {
  color: #1a7f37;
  background: rgba(26, 127, 55, 0.12);
  border-color: rgba(26, 127, 55, 0.26);
}

.cell-output-status--error {
  color: #b42318;
  background: rgba(255, 56, 60, 0.12);
  border-color: rgba(255, 56, 60, 0.28);
}

.cell-output-status--running,
.cell-output-status--input_required {
  color: #8a6d1b;
  background: rgba(236, 209, 0, 0.2);
  border-color: rgba(236, 209, 0, 0.35);
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

.cell-output-content :deep(.cell-output-block + .cell-output-block) {
  margin-top: 10px;
}

.cell-output-content :deep(.cell-output-files) {
  margin: 0;
  padding-left: 18px;
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

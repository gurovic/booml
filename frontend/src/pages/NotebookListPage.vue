<template>
  <div class="notebook-page" @dragover="onDragOverPage" @drop="onDropOnPage">
    <UiHeader />

    <main class="notebook-main">
      <div class="notebook-title-row">
        <h1 class="notebook-title">Блокноты</h1>
      </div>

      <Transition name="crumbs-collapse">
        <nav
          v-if="viewState.kind === 'ready' && isInFolder"
          class="crumbs"
          aria-label="Навигация по папкам"
        >
          <div class="crumbs__inner">
            <template v-for="(item, idx) in breadcrumbItems" :key="item.key">
              <span v-if="idx !== 0" class="crumbs__sep" aria-hidden="true">/</span>

              <button
                type="button"
                class="crumbs__link"
                :class="{
                  'crumbs__current': isCurrentFolder(item.folderId),
                  'crumbs__link--droppable': canDropToTargetFolder(item.folderId),
                  'crumbs__link--drop-target': isBreadcrumbDropTarget(item.folderId),
                }"
                :title="item.title"
                :aria-label="item.title"
                :aria-current="isCurrentFolder(item.folderId) ? 'page' : null"
                @click="goToFolder(item.folderId)"
                @dragover="onDragOverBreadcrumb($event, item.folderId)"
                @dragleave="onDragLeaveBreadcrumb($event, item.folderId)"
                @drop="onDropOnBreadcrumb($event, item.folderId)"
              >
                <span v-if="item.isRoot" class="material-symbols-rounded crumbs__home-icon" aria-hidden="true">home</span>
                <span v-else class="crumbs__label">{{ item.label }}</span>
              </button>
            </template>
          </div>
        </nav>
      </Transition>

      <div
        v-if="viewState.kind !== 'ready'"
        class="notebook-state"
        :class="{ 'notebook-state--error': viewState.kind === 'error' }"
      >
        {{ viewState.message }}
      </div>

      <template v-else>
        <section class="notebook-workspace">
          <div class="selection-toolbar">
            <Transition name="toolbar-swap" mode="out-in">
              <div v-if="selectedCount === 0" key="idle" class="selection-toolbar-idle">
                <div class="toolbar-idle-layout">
                  <label class="toolbar-search-wrap" aria-label="Поиск по блокнотам и папкам">
                    <span class="material-symbols-rounded toolbar-search-icon" aria-hidden="true">search</span>
                    <input
                      v-model="searchQuery"
                      type="search"
                      class="toolbar-search"
                      placeholder="Поиск по блокнотам и папкам"
                      aria-label="Поиск по блокнотам и папкам"
                    >
                  </label>
                  <div class="toolbar-idle-buttons">
                    <button
                      type="button"
                      class="toolbar-pill"
                      :disabled="!canCreateInCurrentFolder"
                      @click="openCreateFolderDialog"
                    >
                      Новая папка
                    </button>
                    <button
                      type="button"
                      class="toolbar-pill"
                      :disabled="!canCreateInCurrentFolder"
                      @click="openCreateNotebookDialog"
                    >
                      Новый блокнот
                    </button>
                    <button
                      type="button"
                      class="toolbar-pill toolbar-pill--secondary"
                      :disabled="importBusy || !canCreateInCurrentFolder"
                      @click="openImportNotebookPicker"
                    >
                      {{ importBusy ? 'Импорт...' : 'Импорт блокнота' }}
                    </button>
                  </div>
                </div>
              </div>

              <div v-else key="selection" class="selection-toolbar-selected">
                <div class="selection-toolbar-selected-layout">
                  <div class="selection-toolbar__summary">
                    <span>{{ selectedCount }} выбрано</span>
                  </div>
                  <div class="selection-toolbar__actions">
                    <button
                      type="button"
                      class="selection-action"
                      :disabled="!canBulkRename"
                      @click="renameSelectedEntry"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">edit</span>
                      <span>Переименовать</span>
                    </button>
                    <button
                      type="button"
                      class="selection-action"
                      :disabled="!canBulkMove"
                      @click="openMoveSelectedDialog"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">arrow_right_alt</span>
                      <span>Переместить</span>
                    </button>
                    <button
                      type="button"
                      class="selection-action"
                      :disabled="!canBulkExport || exportBusy"
                      @click="exportSelectedEntries"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">download</span>
                      <span>{{ exportBusy ? 'Экспорт...' : 'Экспорт' }}</span>
                    </button>
                    <button
                      type="button"
                      class="selection-action selection-action--danger"
                      :disabled="!canBulkDelete"
                      @click="deleteSelectedEntries"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">delete</span>
                      <span>Удалить</span>
                    </button>
                    <button
                      type="button"
                      class="selection-action selection-action--secondary"
                      @click="clearSelection"
                    >
                      <span class="material-symbols-rounded" aria-hidden="true">deselect</span>
                      <span>Снять выделение</span>
                    </button>
                  </div>
                </div>
              </div>
            </Transition>

            <input
              ref="importNotebookInputRef"
              type="file"
              class="hidden-file-input"
              accept=".ipynb,.json,application/json"
              @change="handleImportNotebookPicked"
            >
          </div>

          <div v-if="actionError" class="workspace-error">{{ actionError }}</div>

          <div v-if="explorerEntries.length === 0" class="cells-empty">
            {{ emptyStateText }}
          </div>

          <div v-else class="explorer-list" @click.self="clearSelection">
            <div class="explorer-table-head">
              <span class="explorer-head-cell explorer-head-cell--name">Название</span>
              <span class="explorer-head-cell explorer-head-cell--updated">Последнее изменение</span>
              <span class="explorer-head-cell explorer-head-cell--date">Дата создания</span>
              <span class="explorer-head-cell explorer-head-cell--size">Размер</span>
              <span class="explorer-head-cell explorer-head-cell--actions" aria-hidden="true"></span>
            </div>

            <Transition name="explorer-results-fade" mode="out-in">
              <div :key="searchResultsTransitionKey" class="explorer-items" @click.self="clearSelection">
                <article
                  v-for="entry in explorerEntries"
                  :key="entryKey(entry)"
                  :draggable="canDragEntry(entry)"
                  :class="[
                    'explorer-item',
                    { 'explorer-item--droppable': entry.kind === 'folder' && canDropOnFolder(entry) },
                    { 'explorer-item--drop-target': dropTargetFolderId === entry.id },
                    { 'explorer-item--selected': isEntrySelected(entry) },
                  ]"
                  @dragstart="onDragStart($event, entry)"
                  @dragend="onDragEnd"
                  @dragover="onDragOverEntry($event, entry)"
                  @dragleave="onDragLeaveEntry($event, entry)"
                  @drop="onDropOnEntry($event, entry)"
                  @click="handleEntryCardClick($event, entry)"
                  @dblclick="handleEntryCardDoubleClick($event, entry)"
                >
                  <button
                    type="button"
                    class="explorer-item-main"
                    :aria-label="entryAriaLabel(entry)"
                    @click.stop="handleEntryClick($event, entry)"
                    @dblclick.stop="handleEntryDoubleClick(entry)"
                    @keydown.enter.prevent="handleEntryOpen(entry)"
                  >
                    <span class="material-symbols-rounded explorer-icon" aria-hidden="true">
                      {{ entry.kind === 'folder' ? (entry.is_system ? 'folder_managed' : 'folder') : 'description' }}
                    </span>
                    <span class="explorer-title">{{ entry.title }}</span>
                  </button>

                  <span class="explorer-cell explorer-cell--updated">{{ formatEntryUpdatedAtForEntry(entry) }}</span>
                  <span class="explorer-cell explorer-cell--date">{{ formatEntryCreatedAtForEntry(entry) }}</span>
                  <span class="explorer-cell explorer-cell--size">{{ formatEntrySize(entry) }}</span>

                  <div class="explorer-actions">
                  <button
                    type="button"
                    class="item-menu-trigger"
                    :class="{ 'item-menu-trigger--open': isEntryMenuOpen(entry) }"
                    aria-label="Открыть меню действий"
                    title="Действия"
                    @click.stop="toggleEntryMenu(entry)"
                  >
                    <span class="material-symbols-rounded" aria-hidden="true">more_vert</span>
                  </button>

                    <Transition name="entry-menu-pop">
                      <div
                        v-if="isEntryMenuOpen(entry)"
                        class="entry-menu"
                        role="menu"
                        :aria-label="`Действия для ${entry.title}`"
                        @click.stop
                      >
                        <button
                          type="button"
                          class="entry-menu-item"
                          aria-label="Переименовать"
                          title="Переименовать"
                          :disabled="!canRenameEntry(entry)"
                          @click.stop="openEntryRename(entry)"
                        >
                          <span class="material-symbols-rounded" aria-hidden="true">edit</span>
                          <span>Переименовать</span>
                        </button>

                        <button
                          type="button"
                          class="entry-menu-item"
                          aria-label="Переместить"
                          title="Переместить"
                          :disabled="!canMoveEntry(entry)"
                          @click.stop="openMoveEntryDialog(entry)"
                        >
                          <span class="material-symbols-rounded" aria-hidden="true">arrow_right_alt</span>
                          <span>Переместить</span>
                        </button>

                        <button
                          type="button"
                          class="entry-menu-item"
                          aria-label="Экспорт"
                          title="Экспорт"
                          :disabled="exportBusy"
                          @click.stop="exportEntryFromMenu(entry)"
                        >
                          <span class="material-symbols-rounded" aria-hidden="true">download</span>
                          <span>Экспорт</span>
                        </button>

                        <button
                          type="button"
                          class="entry-menu-item"
                          :aria-label="selectActionLabel(entry)"
                          :title="selectActionLabel(entry)"
                          @click.stop="toggleEntrySelection(entry)"
                        >
                          <span class="material-symbols-rounded" aria-hidden="true">task_alt</span>
                          <span>{{ selectActionLabel(entry) }}</span>
                        </button>

                        <button
                          type="button"
                          class="entry-menu-item entry-menu-item--danger"
                          aria-label="Удалить"
                          title="Удалить"
                          :disabled="!canDeleteEntry(entry)"
                          @click.stop="handleEntryDelete(entry)"
                        >
                          <span class="material-symbols-rounded" aria-hidden="true">delete</span>
                          <span>Удалить</span>
                        </button>
                      </div>
                    </Transition>
                  </div>
                </article>
              </div>
            </Transition>
          </div>
        </section>
      </template>
    </main>

    <Transition name="dialog-shell">
      <div
        v-if="dialog.open"
        class="dialog-backdrop"
        role="dialog"
        aria-modal="true"
        @click.self="closeDialog"
      >
        <div class="dialog-card">
          <h3 class="dialog-title">{{ dialogTitle }}</h3>
          <input
            v-model="dialogName"
            type="text"
            class="dialog-input"
            maxlength="200"
            placeholder="Введите название"
            @keydown.enter.prevent="submitDialog"
          >
          <div class="dialog-actions">
            <button type="button" class="settings-action settings-action--secondary" @click="closeDialog">
              Отмена
            </button>
            <button
              type="button"
              class="settings-action"
              :disabled="dialogBusy"
              @click="submitDialog"
            >
              {{ dialogSubmitLabel }}
            </button>
          </div>
          <div v-if="dialogError" class="settings-error">{{ dialogError }}</div>
        </div>
      </div>
    </Transition>

    <Transition name="dialog-shell">
      <div
        v-if="moveDialog.open"
        class="dialog-backdrop"
        role="dialog"
        aria-modal="true"
        @click.self="closeMoveDialog"
      >
        <div class="dialog-card dialog-card--move">
          <h3 class="dialog-title">{{ moveDialogTitle }}</h3>
          <label class="move-target-search-wrap" aria-label="Поиск папки для перемещения">
            <span class="material-symbols-rounded move-target-search-icon" aria-hidden="true">search</span>
            <input
              v-model="moveDialogSearchQuery"
              type="search"
              class="move-target-search"
              placeholder="Поиск папки"
              aria-label="Поиск папки"
            >
          </label>

          <div v-if="filteredMoveTargetOptions.length === 0" class="move-target-empty">
            Папки не найдены
          </div>
          <div v-else class="move-target-list">
            <button
              v-for="option in filteredMoveTargetOptions"
              :key="option.key"
              type="button"
              class="move-target"
              :disabled="isMoveDialogTargetDisabled(option.folderId)"
              @click="moveEntryFromDialog(option.folderId)"
            >
              <span class="material-symbols-rounded move-target-icon" aria-hidden="true">
                {{ option.folderId == null ? 'home' : 'folder' }}
              </span>
              <span class="move-target-meta">
                <span class="move-target-title">{{ option.label }}</span>
                <span class="move-target-subtitle">{{ option.subtitle }}</span>
              </span>
            </button>
          </div>
          <div class="dialog-actions">
            <button type="button" class="settings-action settings-action--secondary" :disabled="moveDialog.busy" @click="closeMoveDialog">
              Закрыть
            </button>
          </div>
          <div v-if="moveDialog.error" class="settings-error">{{ moveDialog.error }}</div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import UiHeader from '@/components/ui/UiHeader.vue'
import {
  createNotebook,
  createNotebookFolder,
  deleteNotebook,
  deleteNotebookFolder,
  exportNotebookFile,
  exportNotebooksArchive,
  getNotebookTree,
  importNotebookFile,
  moveNotebookFolder,
  moveNotebookToFolder,
  renameNotebook,
  renameNotebookFolder,
} from '@/api/notebook'

const router = useRouter()
const viewState = ref({
  kind: 'loading',
  message: 'Загружаем блокноты...',
})
const tree = ref({
  folders: [],
  notebooks: [],
  tasks_folder_id: null,
})
const currentFolderId = ref(null)
const actionError = ref('')
const draggedEntries = ref([])
const dropTargetFolderId = ref(null)
const dropBreadcrumbTargetKey = ref(null)

const dialog = ref({
  open: false,
  mode: '',
  targetId: null,
  targetFolderId: null,
})
const dialogName = ref('')
const dialogError = ref('')
const dialogBusy = ref(false)
const importNotebookInputRef = ref(null)
const importBusy = ref(false)
const exportBusy = ref(false)
const searchQuery = ref('')
const openEntryMenuKey = ref(null)
const selectedEntryKeys = ref([])
const selectionAnchorKey = ref(null)
const moveDialogSearchQuery = ref('')
const moveDialog = ref({
  open: false,
  entries: [],
  busy: false,
  error: '',
})
let dragPreviewEl = null
let transparentDragImage = null

const folders = computed(() => tree.value.folders || [])
const notebooks = computed(() => tree.value.notebooks || [])
const tasksFolderId = computed(() => tree.value.tasks_folder_id ?? null)
const foldersById = computed(() => {
  const map = {}
  folders.value.forEach((item) => {
    map[item.id] = item
  })
  return map
})
const isInFolder = computed(() => currentFolderId.value != null)
const currentFolder = computed(() => {
  if (!isInFolder.value) return null
  return folders.value.find((item) => item.id === currentFolderId.value) || null
})

const breadcrumbItems = computed(() => {
  const items = [
    {
      key: 'root',
      label: '',
      title: 'Все блокноты',
      folderId: null,
      isRoot: true,
    },
  ]

  const chain = []
  let currentId = currentFolderId.value
  const visited = new Set()
  while (currentId != null) {
    if (visited.has(currentId)) break
    visited.add(currentId)

    const folder = foldersById.value[currentId]
    if (!folder) break
    chain.unshift(folder)
    currentId = folder.parent_id ?? null
  }

  chain.forEach((folder) => {
    items.push({
      key: `folder:${folder.id}`,
      label: folder.title,
      title: folder.title,
      folderId: folder.id,
      isRoot: false,
    })
  })

  return items
})

function isFolderInsideTasksTree(folderId) {
  if (folderId == null || tasksFolderId.value == null) return false

  let currentId = folderId
  const visited = new Set()
  while (currentId != null) {
    if (visited.has(currentId)) return false
    visited.add(currentId)

    if (currentId === tasksFolderId.value) return true
    const currentFolder = foldersById.value[currentId]
    if (!currentFolder) return false
    currentId = currentFolder.parent_id ?? null
  }
  return false
}

function isFolderDescendantOrSelf(folderId, ancestorId) {
  if (folderId == null || ancestorId == null) return false

  let currentId = folderId
  const visited = new Set()
  while (currentId != null) {
    if (visited.has(currentId)) return false
    visited.add(currentId)

    if (currentId === ancestorId) return true
    const currentFolder = foldersById.value[currentId]
    if (!currentFolder) return false
    currentId = currentFolder.parent_id ?? null
  }
  return false
}

const canCreateInCurrentFolder = computed(() => !isFolderInsideTasksTree(currentFolderId.value))
const normalizedSearchQuery = computed(() => searchQuery.value.trim().toLowerCase())
const isSearchActive = computed(() => normalizedSearchQuery.value.length > 0)

const rootNotebooks = computed(() => notebooks.value.filter((item) => item.folder_id == null))
const rootFolders = computed(() => folders.value.filter((item) => item.parent_id == null))
const childFolders = computed(() => {
  if (!isInFolder.value) return []
  return folders.value.filter((item) => item.parent_id === currentFolderId.value)
})

const currentFolderNotebooks = computed(() => {
  if (!isInFolder.value) return rootNotebooks.value
  return notebooks.value.filter((item) => item.folder_id === currentFolderId.value)
})

const scopedExplorerEntries = computed(() => {
  const folderEntries = (isInFolder.value ? childFolders.value : rootFolders.value).map((folder) => ({
    ...folder,
    kind: 'folder',
  }))

  if (isInFolder.value) {
    const notebookEntries = currentFolderNotebooks.value.map((item) => ({
      ...item,
      kind: 'notebook',
    }))
    return [...folderEntries, ...notebookEntries]
  }

  const notebookEntries = rootNotebooks.value.map((item) => ({
    ...item,
    kind: 'notebook',
  }))

  return [...folderEntries, ...notebookEntries]
})

const allExplorerEntries = computed(() => {
  const folderEntries = folders.value.map((folder) => ({
    ...folder,
    kind: 'folder',
  }))
  const notebookEntries = notebooks.value.map((item) => ({
    ...item,
    kind: 'notebook',
  }))
  return [...folderEntries, ...notebookEntries]
})

function matchesSearchEntry(entry, query) {
  if (!entry || !query) return false

  const title = String(entry.title || '').toLowerCase()
  return title.includes(query)
}

const explorerEntries = computed(() => {
  if (!isSearchActive.value) return scopedExplorerEntries.value
  const query = normalizedSearchQuery.value
  return allExplorerEntries.value.filter((entry) => matchesSearchEntry(entry, query))
})
const searchResultsTransitionKey = computed(() => {
  if (!isSearchActive.value) return '__no-search-animation__'
  const visibleKeys = explorerEntries.value.map((entry) => entryKey(entry))
  if (visibleKeys.length === 0) return 'search:__empty__'
  return `search:${visibleKeys.join('|')}`
})

const explorerEntriesByKey = computed(() => {
  const map = {}
  explorerEntries.value.forEach((entry) => {
    map[entryKey(entry)] = entry
  })
  return map
})

const selectedEntries = computed(() => {
  return selectedEntryKeys.value
    .map((key) => explorerEntriesByKey.value[key])
    .filter((entry) => !!entry)
})

const selectedCount = computed(() => selectedEntries.value.length)
const canBulkRename = computed(() => selectedEntries.value.length === 1 && canRenameEntry(selectedEntries.value[0]))
const canBulkMove = computed(() => {
  return selectedEntries.value.length > 0 && selectedEntries.value.every((entry) => canMoveEntry(entry))
})
const canBulkExport = computed(() => selectedEntries.value.length > 0)
const canBulkDelete = computed(() => {
  return selectedEntries.value.length > 0 && selectedEntries.value.every((entry) => canDeleteEntry(entry))
})

const emptyStateText = computed(() => {
  if (isSearchActive.value) return 'Ничего не найдено по вашему запросу'
  if (isInFolder.value) return 'В этой папке пока нет папок и блокнотов'
  return 'Пока нет папок и блокнотов'
})

const dialogTitle = computed(() => {
  if (dialog.value.mode === 'create-folder') return 'Создать папку'
  if (dialog.value.mode === 'create-notebook') return 'Создать блокнот'
  if (dialog.value.mode === 'rename-folder') return 'Переименовать папку'
  if (dialog.value.mode === 'rename-notebook') return 'Переименовать блокнот'
  return 'Изменение'
})

const dialogSubmitLabel = computed(() => {
  if (dialog.value.mode === 'create-folder' || dialog.value.mode === 'create-notebook') return 'Создать'
  return 'Сохранить'
})

const moveDialogTitle = computed(() => {
  const entries = moveDialog.value.entries || []
  if (entries.length === 0) return 'Перемещение'
  if (entries.length === 1) {
    const [entry] = entries
    if (entry.kind === 'folder') return `Переместить папку «${entry.title}»`
    return `Переместить блокнот «${entry.title}»`
  }
  return `Переместить выбранные элементы (${entries.length})`
})

const moveTargetOptions = computed(() => {
  const folderOptions = folders.value
    .map((folder) => ({
      key: `folder:${folder.id}`,
      folderId: folder.id,
      label: folder.title,
      subtitle: getFolderPathLabel(folder.id),
    }))
    .sort((a, b) => a.subtitle.localeCompare(b.subtitle, 'ru'))

  return [
    {
      key: 'root',
      folderId: null,
      label: 'Домой',
      subtitle: 'Все блокноты',
    },
    ...folderOptions,
  ]
})
const normalizedMoveDialogSearchQuery = computed(() => moveDialogSearchQuery.value.trim().toLowerCase())
const filteredMoveTargetOptions = computed(() => {
  const query = normalizedMoveDialogSearchQuery.value
  if (!query) return moveTargetOptions.value

  return moveTargetOptions.value.filter((option) => {
    const label = String(option.label || '').toLowerCase()
    const subtitle = String(option.subtitle || '').toLowerCase()
    return label.includes(query) || subtitle.includes(query)
  })
})

function normalizeFolderSelection() {
  if (!isInFolder.value) return
  if (!currentFolder.value) {
    currentFolderId.value = null
  }
}

function normalizeSelectedEntries() {
  const validKeys = new Set()
  folders.value.forEach((folder) => validKeys.add(`folder-${folder.id}`))
  notebooks.value.forEach((notebook) => validKeys.add(`notebook-${notebook.id}`))
  selectedEntryKeys.value = selectedEntryKeys.value.filter((key) => validKeys.has(key))
  if (selectionAnchorKey.value && !validKeys.has(selectionAnchorKey.value)) {
    selectionAnchorKey.value = null
  }
}

async function loadTree({ keepFolder = true } = {}) {
  if (!keepFolder) {
    viewState.value = {
      kind: 'loading',
      message: 'Загружаем блокноты...',
    }
  }

  actionError.value = ''
  try {
    const response = await getNotebookTree()
    tree.value = {
      folders: Array.isArray(response?.folders) ? response.folders : [],
      notebooks: Array.isArray(response?.notebooks) ? response.notebooks : [],
      tasks_folder_id: response?.tasks_folder_id ?? null,
    }

    if (!keepFolder) {
      currentFolderId.value = null
    }
    normalizeFolderSelection()
    normalizeSelectedEntries()
    viewState.value = {
      kind: 'ready',
      message: '',
    }
  } catch (error) {
    viewState.value = {
      kind: 'error',
      message: error?.message || 'Не удалось загрузить список блокнотов',
    }
  }
}

function entryKey(entry) {
  return `${entry.kind}-${entry.id}`
}

function entryAriaLabel(entry) {
  if (entry.kind === 'folder') return `Выбрать папку ${entry.title}. Двойной клик открывает папку`
  return `Выбрать блокнот ${entry.title}. Двойной клик открывает блокнот`
}

function formatEntryCreatedAt(rawValue) {
  if (!rawValue) return '—'
  const parsedDate = new Date(rawValue)
  if (Number.isNaN(parsedDate.getTime())) return '—'
  return parsedDate.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatEntryCreatedAtForEntry(entry) {
  if (entry?.kind === 'folder' && entry?.is_system) return '—'
  return formatEntryCreatedAt(entry?.created_at)
}

function formatEntryUpdatedAt(rawValue) {
  return formatEntryCreatedAt(rawValue)
}

function formatEntryUpdatedAtForEntry(entry) {
  if (entry?.kind === 'folder') return '—'
  return formatEntryUpdatedAt(entry?.updated_at)
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return '—'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  const precision = unitIndex === 0 ? 0 : size >= 100 ? 0 : 1
  return `${size.toFixed(precision)} ${units[unitIndex]}`
}

function formatEntrySize(entry) {
  const rawSize = Number(entry?.size_bytes)
  if (!Number.isFinite(rawSize)) return '—'
  return formatBytes(rawSize)
}

function getFolderPathLabel(folderId) {
  if (folderId == null) return 'Все блокноты'

  const labels = []
  let currentId = folderId
  const visited = new Set()
  while (currentId != null) {
    if (visited.has(currentId)) break
    visited.add(currentId)
    const folder = foldersById.value[currentId]
    if (!folder) break
    labels.unshift(folder.title)
    currentId = folder.parent_id ?? null
  }
  return labels.length ? labels.join(' / ') : 'Неизвестная папка'
}

function breadcrumbTargetKey(folderId) {
  return folderId == null ? '__root__' : `folder:${folderId}`
}

function isCurrentFolder(folderId) {
  return (folderId ?? null) === (currentFolderId.value ?? null)
}

function isBreadcrumbDropTarget(folderId) {
  return dropBreadcrumbTargetKey.value === breadcrumbTargetKey(folderId)
}

function isEntrySelected(entry) {
  return selectedEntryKeys.value.includes(entryKey(entry))
}

function clearSelection() {
  selectedEntryKeys.value = []
  selectionAnchorKey.value = null
}

function getVisibleEntryKeys() {
  return explorerEntries.value.map((entry) => entryKey(entry))
}

function normalizeSelectionOrder(keySet) {
  const keys = getVisibleEntryKeys()
  return keys.filter((key) => keySet.has(key))
}

function getSelectionRange(anchorKey, targetKey) {
  const keys = getVisibleEntryKeys()
  const from = keys.indexOf(anchorKey)
  const to = keys.indexOf(targetKey)
  if (from < 0 || to < 0) return [targetKey]
  const start = Math.min(from, to)
  const end = Math.max(from, to)
  return keys.slice(start, end + 1)
}

function toggleEntrySelection(entry) {
  const key = entryKey(entry)
  const next = new Set(selectedEntryKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selectedEntryKeys.value = normalizeSelectionOrder(next)
  selectionAnchorKey.value = key
  closeEntryMenu()
}

function handleEntryClick(event, entry) {
  const key = entryKey(entry)
  const isAdditive = !!(event.metaKey || event.ctrlKey)
  const isRange = !!event.shiftKey
  const visibleKeys = getVisibleEntryKeys()

  if (isRange) {
    const anchor = selectionAnchorKey.value && visibleKeys.includes(selectionAnchorKey.value)
      ? selectionAnchorKey.value
      : key
    const rangeKeys = getSelectionRange(anchor, key)
    if (isAdditive) {
      const next = new Set(selectedEntryKeys.value)
      rangeKeys.forEach((rangeKey) => next.add(rangeKey))
      selectedEntryKeys.value = normalizeSelectionOrder(next)
    } else {
      selectedEntryKeys.value = rangeKeys
    }
    selectionAnchorKey.value = anchor
    return
  }

  if (isAdditive) {
    const next = new Set(selectedEntryKeys.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    selectedEntryKeys.value = normalizeSelectionOrder(next)
    selectionAnchorKey.value = key
    return
  }

  selectedEntryKeys.value = [key]
  selectionAnchorKey.value = key
}

function handleEntryDoubleClick(entry) {
  handleEntryOpen(entry)
}

function isEventFromEntryActions(event) {
  const target = event?.target
  return target instanceof Element && !!target.closest('.item-menu-trigger, .entry-menu')
}

function handleEntryCardClick(event, entry) {
  if (isEventFromEntryActions(event)) return
  handleEntryClick(event, entry)
}

function handleEntryCardDoubleClick(event, entry) {
  if (isEventFromEntryActions(event)) return
  handleEntryDoubleClick(entry)
}

function isEntryMenuOpen(entry) {
  return openEntryMenuKey.value === entryKey(entry)
}

function closeEntryMenu() {
  openEntryMenuKey.value = null
}

function toggleEntryMenu(entry) {
  const key = entryKey(entry)
  if (openEntryMenuKey.value === key) {
    openEntryMenuKey.value = null
    return
  }
  openEntryMenuKey.value = key
}

function handleDocumentClick(event) {
  const target = event.target
  if (!(target instanceof Element) || !target.closest('.explorer-actions')) {
    closeEntryMenu()
  }

  if (!(target instanceof Element)) return
  const clickedOnEntry = !!target.closest('.explorer-item')
  const clickedOnInteractive = !!target.closest('button, a, input, textarea, select, label, [role="menu"]')
  if (!clickedOnEntry && !clickedOnInteractive) {
    clearSelection()
  }
}

function handleDocumentKeydown(event) {
  if (event.key !== 'Escape') return
  if (dialog.value.open || moveDialog.value.open) return
  if (selectedCount.value === 0) return
  clearSelection()
}

function getDragPreviewIcon(entries) {
  const list = Array.isArray(entries) ? entries : []
  if (list.length > 1) return 'library_books'
  const [entry] = list
  if (entry?.kind === 'folder') return entry.is_system ? 'folder_managed' : 'folder'
  return 'description'
}

function formatElementsCountRu(count) {
  const value = Number(count)
  if (!Number.isFinite(value)) return '0 элементов'
  const n = Math.abs(Math.trunc(value))
  const mod100 = n % 100
  const mod10 = n % 10
  if (mod100 >= 11 && mod100 <= 14) return `${n} элементов`
  if (mod10 === 1) return `${n} элемент`
  if (mod10 >= 2 && mod10 <= 4) return `${n} элемента`
  return `${n} элементов`
}

function getDragPreviewTitle(entries) {
  const list = Array.isArray(entries) ? entries : []
  if (list.length > 1) return formatElementsCountRu(list.length)
  return list[0]?.title || ''
}

function ensureTransparentDragImage() {
  if (transparentDragImage) return transparentDragImage
  const image = new Image()
  image.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=='
  transparentDragImage = image
  return image
}

function updateDragPreviewPosition(event) {
  if (!dragPreviewEl) return
  const x = Number(event?.clientX)
  const y = Number(event?.clientY)
  if (!Number.isFinite(x) || !Number.isFinite(y)) return
  if (x <= 1 && y <= 1) return
  dragPreviewEl.style.transform = `translate3d(${x + 14}px, ${y + 14}px, 0)`
  if (dragPreviewEl.style.opacity !== '1') {
    dragPreviewEl.style.opacity = '1'
  }
  if (dragPreviewEl.style.filter !== 'none') {
    dragPreviewEl.style.filter = 'none'
  }
}

function removeDragPreview() {
  if (!dragPreviewEl) return
  dragPreviewEl.style.transition = 'none'
  dragPreviewEl.style.opacity = '0'
  dragPreviewEl.style.filter = 'none'
  dragPreviewEl.remove()
  dragPreviewEl = null
}

function handlePointerRelease() {
  removeDragPreview()
}

function createDragPreview(entries, event) {
  const previewEntries = Array.isArray(entries) ? entries.filter((entry) => !!entry) : []
  if (previewEntries.length === 0) return

  removeDragPreview()

  const preview = document.createElement('div')
  preview.className = 'drag-preview'
  preview.style.position = 'fixed'
  preview.style.left = '0'
  preview.style.top = '0'
  preview.style.zIndex = '10000'
  preview.style.display = 'inline-flex'
  preview.style.alignItems = 'center'
  preview.style.gap = '8px'
  preview.style.maxWidth = 'min(430px, 70vw)'
  preview.style.padding = '8px 10px'
  preview.style.borderRadius = '12px'
  preview.style.border = '1px solid rgba(22, 33, 89, 0.18)'
  preview.style.background = 'rgba(255, 255, 255, 0.98)'
  preview.style.boxShadow = '0 12px 24px rgba(13, 20, 56, 0.2)'
  preview.style.pointerEvents = 'none'
  preview.style.opacity = '0'
  preview.style.filter = 'blur(1.5px)'
  preview.style.transform = 'translate3d(-9999px, -9999px, 0)'
  preview.style.transition = 'opacity 0.14s ease, filter 0.2s ease'

  const icon = document.createElement('span')
  icon.className = 'material-symbols-rounded'
  icon.setAttribute('aria-hidden', 'true')
  icon.style.fontSize = '20px'
  icon.style.lineHeight = '1'
  icon.textContent = getDragPreviewIcon(previewEntries)

  const title = document.createElement('span')
  title.style.fontSize = '15px'
  title.style.fontWeight = '600'
  title.style.lineHeight = '1.2'
  title.style.color = 'var(--color-text-primary)'
  title.style.whiteSpace = 'nowrap'
  title.style.overflow = 'hidden'
  title.style.textOverflow = 'ellipsis'
  title.textContent = getDragPreviewTitle(previewEntries)

  preview.append(icon, title)
  document.body.appendChild(preview)
  dragPreviewEl = preview
  updateDragPreviewPosition(event)
}

function handleDocumentDragOver(event) {
  updateDragPreviewPosition(event)
}

function handleDocumentDrag(event) {
  updateDragPreviewPosition(event)
}

function normalizeMoveEntries(entries) {
  const list = Array.isArray(entries) ? entries.filter((entry) => !!entry) : []
  if (list.length === 0) return []

  const uniqueByKey = new Map()
  list.forEach((entry) => {
    uniqueByKey.set(entryKey(entry), entry)
  })
  const uniqueEntries = Array.from(uniqueByKey.values())
  const orderKeys = uniqueEntries.map((entry) => entryKey(entry))

  const folderEntries = uniqueEntries.filter((entry) => entry.kind === 'folder')
  const topLevelFolders = folderEntries.filter((folder) => {
    return !folderEntries.some(
      (otherFolder) => otherFolder.id !== folder.id && isFolderDescendantOrSelf(folder.id, otherFolder.id),
    )
  })

  const notebookEntries = uniqueEntries.filter((entry) => entry.kind === 'notebook').filter((notebook) => {
    if (notebook.folder_id == null) return true
    return !topLevelFolders.some((folder) => isFolderDescendantOrSelf(notebook.folder_id, folder.id))
  })

  const normalized = [...topLevelFolders, ...notebookEntries]
  const normalizedByKey = new Map(normalized.map((entry) => [entryKey(entry), entry]))
  return orderKeys.map((key) => normalizedByKey.get(key)).filter((entry) => !!entry)
}

function getDragBatchEntries(entry) {
  if (!entry) return []
  const key = entryKey(entry)
  const hasSelectedTarget = selectedEntryKeys.value.includes(key)
  const sourceEntries = hasSelectedTarget ? selectedEntries.value : [entry]
  return normalizeMoveEntries(sourceEntries)
}

function canDragEntry(entry) {
  if (!entry) return false

  if (entry.kind === 'folder') {
    if (entry.is_system) return false
    return !isFolderInsideTasksTree(entry.id)
  }

  return !isFolderInsideTasksTree(entry.folder_id)
}

function canRenameEntry(entry) {
  if (!entry) return false
  if (entry.kind === 'folder') return !entry.is_system
  return true
}

function canDeleteEntry(entry) {
  if (!entry) return false
  if (entry.kind === 'folder') return !entry.is_system
  return true
}

function canMoveEntry(entry) {
  if (!entry) return false
  return canMoveEntryAnywhere(entry)
}

function selectActionLabel(entry) {
  return isEntrySelected(entry) ? 'Снять выделение' : 'Выбрать'
}

function canDropOnFolder(targetEntry) {
  if (!targetEntry || targetEntry.kind !== 'folder') return false
  return canDropToTargetFolder(targetEntry.id)
}

function canDropToTargetFolder(targetFolderId) {
  return canMoveEntriesToTargetFolder(draggedEntries.value, targetFolderId)
}

function canMoveEntryToTargetFolder(entry, targetFolderId) {
  if (!entry) return false
  if (targetFolderId != null && isFolderInsideTasksTree(targetFolderId)) return false

  if (entry.kind === 'folder') {
    if (!canDragEntry(entry)) return false
    if (entry.id === targetFolderId) return false
    if ((entry.parent_id ?? null) === (targetFolderId ?? null)) return false
    if (targetFolderId != null && isFolderDescendantOrSelf(targetFolderId, entry.id)) return false
    return true
  }

  if (entry.kind === 'notebook') {
    if (!canDragEntry(entry)) return false
    return (entry.folder_id ?? null) !== (targetFolderId ?? null)
  }

  return false
}

function canMoveEntryAnywhere(entry) {
  const targetIds = [null, ...folders.value.map((folder) => folder.id)]
  return targetIds.some((targetId) => canMoveEntryToTargetFolder(entry, targetId))
}

function canMoveEntriesToTargetFolder(entries, targetFolderId) {
  const normalized = normalizeMoveEntries(entries)
  if (normalized.length === 0) return false
  return normalized.every((entry) => canMoveEntryToTargetFolder(entry, targetFolderId))
}

function isMoveDialogTargetDisabled(targetFolderId) {
  const entries = moveDialog.value.entries || []
  if (entries.length === 0 || moveDialog.value.busy) return true
  return !canMoveEntriesToTargetFolder(entries, targetFolderId)
}

function onDragStart(event, entry) {
  const dragBatch = getDragBatchEntries(entry)
  if (dragBatch.length === 0 || !dragBatch.every((item) => canDragEntry(item))) {
    event.preventDefault()
    actionError.value = 'Выбранные элементы нельзя перетащить'
    return
  }

  closeEntryMenu()
  draggedEntries.value = dragBatch.map((item) => ({ ...item }))
  dropTargetFolderId.value = null
  dropBreadcrumbTargetKey.value = null
  createDragPreview(dragBatch, event)
  if (event.dataTransfer) {
    event.dataTransfer.setDragImage(ensureTransparentDragImage(), 0, 0)
    event.dataTransfer.effectAllowed = 'move'
    const first = dragBatch[0]
    event.dataTransfer.setData('text/plain', `${first.kind}:${first.id}`)
  }
}

function onDragEnd() {
  removeDragPreview()
  draggedEntries.value = []
  dropTargetFolderId.value = null
  dropBreadcrumbTargetKey.value = null
}

function onDragOverPage(event) {
  if (draggedEntries.value.length === 0) return
  event.preventDefault()
}

function onDropOnPage(event) {
  if (draggedEntries.value.length === 0) return
  event.preventDefault()
  removeDragPreview()
  dropTargetFolderId.value = null
  dropBreadcrumbTargetKey.value = null
  draggedEntries.value = []
}

function onDragOverEntry(event, entry) {
  if (entry.kind !== 'folder') return
  if (!canDropOnFolder(entry)) return

  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
  dropTargetFolderId.value = entry.id
  dropBreadcrumbTargetKey.value = null
}

function onDragLeaveEntry(event, entry) {
  const currentTarget = event?.currentTarget
  const nextTarget = event?.relatedTarget
  if (currentTarget instanceof Element && nextTarget instanceof Node && currentTarget.contains(nextTarget)) {
    return
  }
  if (currentTarget instanceof Element) {
    const x = Number(event?.clientX)
    const y = Number(event?.clientY)
    if (Number.isFinite(x) && Number.isFinite(y)) {
      const rect = currentTarget.getBoundingClientRect()
      if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
        return
      }
    }
  }
  if (dropTargetFolderId.value === entry.id) {
    dropTargetFolderId.value = null
  }
}

async function onDropOnEntry(event, entry) {
  if (entry.kind !== 'folder') return
  event.preventDefault()
  removeDragPreview()

  if (!canDropOnFolder(entry)) {
    dropTargetFolderId.value = null
    dropBreadcrumbTargetKey.value = null
    draggedEntries.value = []
    return
  }

  await moveDraggedEntriesToFolder(entry.id)
}

function goToFolder(folderId) {
  clearSelection()
  currentFolderId.value = folderId ?? null
}

function onDragOverBreadcrumb(event, targetFolderId) {
  if (!canDropToTargetFolder(targetFolderId)) return
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
  dropBreadcrumbTargetKey.value = breadcrumbTargetKey(targetFolderId)
  dropTargetFolderId.value = null
}

function onDragLeaveBreadcrumb(event, targetFolderId) {
  const currentTarget = event?.currentTarget
  const nextTarget = event?.relatedTarget
  if (currentTarget instanceof Element && nextTarget instanceof Node && currentTarget.contains(nextTarget)) {
    return
  }
  if (currentTarget instanceof Element) {
    const x = Number(event?.clientX)
    const y = Number(event?.clientY)
    if (Number.isFinite(x) && Number.isFinite(y)) {
      const rect = currentTarget.getBoundingClientRect()
      if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
        return
      }
    }
  }
  if (dropBreadcrumbTargetKey.value === breadcrumbTargetKey(targetFolderId)) {
    dropBreadcrumbTargetKey.value = null
  }
}

async function onDropOnBreadcrumb(event, targetFolderId) {
  event.preventDefault()
  removeDragPreview()
  if (!canDropToTargetFolder(targetFolderId)) {
    dropBreadcrumbTargetKey.value = null
    dropTargetFolderId.value = null
    draggedEntries.value = []
    return
  }

  await moveDraggedEntriesToFolder(targetFolderId)
}

async function moveDraggedEntriesToFolder(targetFolderId) {
  const dragged = normalizeMoveEntries(draggedEntries.value)
  if (dragged.length === 0) return
  removeDragPreview()

  actionError.value = ''
  try {
    for (const entry of dragged) {
      await moveEntryToFolder(entry, targetFolderId, { reload: false })
    }
    await loadTree()
  } catch (error) {
    actionError.value = error?.message || 'Не удалось переместить элемент'
  } finally {
    dropTargetFolderId.value = null
    dropBreadcrumbTargetKey.value = null
    draggedEntries.value = []
    removeDragPreview()
  }
}

async function moveEntryToFolder(entry, targetFolderId, { reload = true } = {}) {
  if (!entry || !canMoveEntryToTargetFolder(entry, targetFolderId)) {
    throw new Error('Перемещение в выбранную папку недоступно')
  }

  if (entry.kind === 'folder') {
    await moveNotebookFolder(entry.id, targetFolderId)
    if (currentFolderId.value === entry.id) {
      currentFolderId.value = targetFolderId ?? null
    }
  } else if (entry.kind === 'notebook') {
    await moveNotebookToFolder(entry.id, targetFolderId)
  }

  if (reload) {
    await loadTree()
  }
}

function openMoveEntryDialog(entry) {
  openMoveDialog(entry ? [entry] : [])
}

function openMoveSelectedDialog() {
  openMoveDialog(selectedEntries.value)
}

function openMoveDialog(entries) {
  const candidateEntries = Array.isArray(entries) ? entries.filter((entry) => !!entry) : []
  if (candidateEntries.length === 0) return
  if (!candidateEntries.every((entry) => canMoveEntry(entry))) {
    actionError.value = 'Для выбранных элементов недоступно перемещение'
    closeEntryMenu()
    return
  }

  closeEntryMenu()
  moveDialogSearchQuery.value = ''
  moveDialog.value = {
    open: true,
    entries: candidateEntries.map((entry) => ({ ...entry })),
    busy: false,
    error: '',
  }
}

function closeMoveDialog() {
  moveDialogSearchQuery.value = ''
  moveDialog.value = {
    open: false,
    entries: [],
    busy: false,
    error: '',
  }
}

async function moveEntryFromDialog(targetFolderId) {
  const entries = normalizeMoveEntries(moveDialog.value.entries || [])
  if (entries.length === 0) return
  if (!canMoveEntriesToTargetFolder(entries, targetFolderId)) {
    moveDialog.value.error = 'Нельзя переместить в выбранную папку'
    return
  }

  moveDialog.value.busy = true
  moveDialog.value.error = ''
  try {
    for (const entry of entries) {
      await moveEntryToFolder(entry, targetFolderId, { reload: false })
    }
    await loadTree()
    clearSelection()
    closeMoveDialog()
  } catch (error) {
    moveDialog.value.error = error?.message || 'Не удалось переместить элемент'
  } finally {
    moveDialog.value.busy = false
  }
}

function openEntryRename(entry) {
  closeEntryMenu()
  if (entry.kind === 'folder') {
    openRenameFolderDialog(entry)
    return
  }
  openRenameNotebookDialog(entry)
}

async function handleEntryDelete(entry) {
  closeEntryMenu()
  if (entry.kind === 'folder') {
    await removeFolder(entry)
    return
  }
  await removeNotebook(entry)
}

function triggerBlobDownload(blob, filename) {
  const objectUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename || 'notebooks_export.zip'
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(objectUrl)
}

function collectExportPayload(entries) {
  const notebookIds = new Set()
  const folderIds = new Set()
  entries.forEach((entry) => {
    if (entry.kind === 'notebook') {
      notebookIds.add(entry.id)
      return
    }
    if (entry.kind === 'folder') {
      folderIds.add(entry.id)
    }
  })
  return {
    notebookIds: Array.from(notebookIds),
    folderIds: Array.from(folderIds),
  }
}

async function exportEntries(entries) {
  const selected = Array.isArray(entries) ? entries.filter((entry) => !!entry) : []
  if (selected.length === 0 || exportBusy.value) return

  const shouldUseArchive = selected.length > 1 || selected.some((entry) => entry.kind === 'folder')
  actionError.value = ''
  exportBusy.value = true
  try {
    if (!shouldUseArchive && selected[0].kind === 'notebook') {
      const notebookId = selected[0].id
      const { blob, filename } = await exportNotebookFile(notebookId)
      triggerBlobDownload(blob, filename || `notebook_${notebookId}.ipynb`)
      return
    }

    const payload = collectExportPayload(selected)
    const { blob, filename } = await exportNotebooksArchive(payload)
    triggerBlobDownload(blob, filename || 'notebooks_export.zip')
  } catch (error) {
    actionError.value = error?.message || 'Не удалось экспортировать выбранные элементы'
  } finally {
    exportBusy.value = false
  }
}

function exportEntryFromMenu(entry) {
  closeEntryMenu()
  if (!entry) return
  exportEntries([entry])
}

function exportSelectedEntries() {
  if (!canBulkExport.value) return
  exportEntries(selectedEntries.value)
}

function openImportNotebookPicker() {
  if (importBusy.value) return
  if (!canCreateInCurrentFolder.value) {
    actionError.value = 'В папке «Блокноты для задач» нельзя импортировать блокноты'
    return
  }
  importNotebookInputRef.value?.click()
}

async function handleImportNotebookPicked(event) {
  const input = event?.target
  const file = input?.files?.[0]
  if (!file) {
    if (input) input.value = ''
    return
  }

  actionError.value = ''
  importBusy.value = true
  try {
    await importNotebookFile(file)
    clearSelection()
    currentFolderId.value = null
    await loadTree()
  } catch (error) {
    actionError.value = error?.message || 'Не удалось импортировать блокнот'
  } finally {
    importBusy.value = false
    if (input) input.value = ''
  }
}

function renameSelectedEntry() {
  if (!canBulkRename.value) return
  const [entry] = selectedEntries.value
  if (!entry) return
  openEntryRename(entry)
}

async function deleteSelectedEntries() {
  if (!canBulkDelete.value) return

  const entries = selectedEntries.value.slice()
  const label = entries.length === 1 ? entries[0].title : `${entries.length} элементов`
  const shouldDelete = window.confirm(`Удалить выбранное: ${label}?`)
  if (!shouldDelete) return

  const selectedFolderIds = entries
    .filter((entry) => entry.kind === 'folder')
    .map((entry) => entry.id)

  const effectiveFolderIds = selectedFolderIds.filter((folderId) => {
    return !selectedFolderIds.some((otherId) => otherId !== folderId && isFolderDescendantOrSelf(folderId, otherId))
  })

  const selectedNotebooks = entries.filter((entry) => entry.kind === 'notebook')
  const notebookIdsToDelete = selectedNotebooks
    .filter((notebook) => {
      if (notebook.folder_id == null) return true
      return !effectiveFolderIds.some((folderId) => isFolderDescendantOrSelf(notebook.folder_id, folderId))
    })
    .map((notebook) => notebook.id)

  actionError.value = ''
  try {
    for (const notebookId of notebookIdsToDelete) {
      await deleteNotebook(notebookId)
    }
    for (const folderId of effectiveFolderIds) {
      await deleteNotebookFolder(folderId)
      if (currentFolderId.value === folderId) {
        currentFolderId.value = null
      }
    }
    clearSelection()
    await loadTree()
  } catch (error) {
    actionError.value = error?.message || 'Не удалось удалить выбранные элементы'
  }
}

function openFolder(folderId) {
  clearSelection()
  currentFolderId.value = folderId
}

function handleEntryOpen(entry) {
  if (entry.kind === 'folder') {
    openFolder(entry.id)
    return
  }
  openNotebook(entry.id)
}

function openNotebook(notebookId) {
  router.push(`/notebook/${notebookId}`)
}

function openCreateFolderDialog() {
  if (!canCreateInCurrentFolder.value) {
    actionError.value = 'В папке «Блокноты для задач» нельзя создавать папки'
    return
  }

  dialog.value = {
    open: true,
    mode: 'create-folder',
    targetId: null,
    targetFolderId: currentFolderId.value,
  }
  dialogName.value = ''
  dialogError.value = ''
}

function openCreateNotebookDialog() {
  if (!canCreateInCurrentFolder.value) {
    actionError.value = 'В папке «Блокноты для задач» нельзя создавать блокноты'
    return
  }

  dialog.value = {
    open: true,
    mode: 'create-notebook',
    targetId: null,
    targetFolderId: currentFolderId.value,
  }
  dialogName.value = ''
  dialogError.value = ''
}

function openRenameFolderDialog(folder) {
  if (!folder || folder.is_system) return

  dialog.value = {
    open: true,
    mode: 'rename-folder',
    targetId: folder.id,
    targetFolderId: null,
  }
  dialogName.value = folder.title
  dialogError.value = ''
}

function openRenameNotebookDialog(notebook) {
  dialog.value = {
    open: true,
    mode: 'rename-notebook',
    targetId: notebook.id,
    targetFolderId: null,
  }
  dialogName.value = notebook.title
  dialogError.value = ''
}

function closeDialog() {
  dialog.value.open = false
  dialogBusy.value = false
  dialogError.value = ''
}

async function submitDialog() {
  const title = dialogName.value.trim()
  if (!title) {
    dialogError.value = 'Название не может быть пустым'
    return
  }

  dialogBusy.value = true
  dialogError.value = ''
  actionError.value = ''

  try {
    if (dialog.value.mode === 'create-folder') {
      await createNotebookFolder(title, dialog.value.targetFolderId)
    } else if (dialog.value.mode === 'create-notebook') {
      await createNotebook({
        title,
        folderId: dialog.value.targetFolderId,
      })
    } else if (dialog.value.mode === 'rename-folder') {
      await renameNotebookFolder(dialog.value.targetId, title)
    } else if (dialog.value.mode === 'rename-notebook') {
      await renameNotebook(dialog.value.targetId, title)
    }
    closeDialog()
    await loadTree()
  } catch (error) {
    dialogError.value = error?.message || 'Не удалось сохранить изменения'
  } finally {
    dialogBusy.value = false
  }
}

async function removeFolder(folder) {
  if (!folder || folder.is_system) return

  const shouldDelete = window.confirm(
    `Удалить папку "${folder.title}"?\nВсе вложенные папки и блокноты будут удалены.`,
  )
  if (!shouldDelete) return

  actionError.value = ''
  try {
    await deleteNotebookFolder(folder.id)
    if (currentFolderId.value === folder.id) {
      currentFolderId.value = null
    }
    await loadTree()
  } catch (error) {
    actionError.value = error?.message || 'Не удалось удалить папку'
  }
}

async function removeNotebook(notebook) {
  if (!notebook) return

  const shouldDelete = window.confirm(`Удалить блокнот "${notebook.title}"?`)
  if (!shouldDelete) return

  actionError.value = ''
  try {
    await deleteNotebook(notebook.id)
    await loadTree()
  } catch (error) {
    actionError.value = error?.message || 'Не удалось удалить блокнот'
  }
}

onMounted(async () => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleDocumentKeydown)
  document.addEventListener('dragover', handleDocumentDragOver)
  document.addEventListener('drag', handleDocumentDrag)
  document.addEventListener('drop', removeDragPreview, true)
  document.addEventListener('dragend', removeDragPreview)
  document.addEventListener('pointerup', handlePointerRelease, true)
  document.addEventListener('mouseup', handlePointerRelease, true)
  document.addEventListener('touchend', handlePointerRelease, true)
  await loadTree({ keepFolder: false })
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleDocumentKeydown)
  document.removeEventListener('dragover', handleDocumentDragOver)
  document.removeEventListener('drag', handleDocumentDrag)
  document.removeEventListener('drop', removeDragPreview, true)
  document.removeEventListener('dragend', removeDragPreview)
  document.removeEventListener('pointerup', handlePointerRelease, true)
  document.removeEventListener('mouseup', handlePointerRelease, true)
  document.removeEventListener('touchend', handlePointerRelease, true)
  removeDragPreview()
})
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

.crumbs {
  width: 100%;
  padding: 8px 0 0;
  margin-bottom: 10px;
}

.crumbs-collapse-enter-active,
.crumbs-collapse-leave-active {
  transition: max-height 0.2s ease, opacity 0.2s ease, margin 0.2s ease, padding 0.2s ease;
  overflow: hidden;
}

.crumbs-collapse-enter-from,
.crumbs-collapse-leave-to {
  max-height: 0;
  opacity: 0;
  margin-bottom: 0;
  padding-top: 0;
}

.crumbs-collapse-enter-to,
.crumbs-collapse-leave-from {
  max-height: 78px;
  opacity: 1;
}

.crumbs__inner {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  padding: 6px 12px;
  border-radius: 12px;
  background: var(--color-button-secondary);
  border: 1px solid rgba(22, 33, 89, 0.1);
}

.crumbs__sep {
  color: rgba(22, 33, 89, 0.45);
  flex: 0 0 auto;
}

.crumbs__link {
  font: inherit;
  line-height: 1.2;
  appearance: none;
  border: none;
  background: transparent;
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: clamp(110px, 18vw, 240px);
  color: rgba(22, 33, 89, 0.92);
  text-decoration: none;
  border-radius: 8px;
  padding: 4px 6px;
  transition: background-color 0.15s ease, color 0.15s ease;
  cursor: pointer;
}

.crumbs__link:hover {
  background: rgba(22, 33, 89, 0.08);
}

.crumbs__current {
  font-weight: 600;
}

.crumbs__link--droppable {
  cursor: copy;
}

.crumbs__link--drop-target {
  background: rgba(22, 33, 89, 0.16);
}

.crumbs__label {
  display: inline-block;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.crumbs__home-icon {
  font-size: 18px;
  line-height: 1;
}

.notebook-workspace {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.selection-toolbar {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(246, 248, 255, 0.98));
  border-radius: 14px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.14);
  padding: 10px 12px;
  min-height: 56px;
  display: flex;
  align-items: center;
  overflow: hidden;
}

.selection-toolbar-idle,
.selection-toolbar-selected {
  width: 100%;
  min-height: 36px;
  display: flex;
  align-items: center;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
}

.toolbar-idle-layout,
.selection-toolbar-selected-layout {
  width: 100%;
  min-width: max-content;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-idle-buttons {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  margin-left: auto;
}

.toolbar-swap-enter-active,
.toolbar-swap-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.toolbar-swap-enter-from,
.toolbar-swap-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}

.selection-toolbar__summary {
  height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  background: rgba(39, 52, 106, 0.08);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.selection-toolbar__actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  margin-left: auto;
}

.selection-action {
  border: none;
  border-radius: 10px;
  min-height: 34px;
  padding: 0 11px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  color: var(--color-text-primary);
  font: inherit;
  font-size: 13px;
  line-height: 1;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 1px 0 rgba(22, 33, 89, 0.08);
  transition: background-color 0.15s ease, transform 0.15s ease;
}

.selection-action .material-symbols-rounded {
  font-size: 18px;
}

.selection-action:hover:not(:disabled) {
  background: rgba(39, 52, 106, 0.08);
}

.selection-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.selection-action--secondary {
  background: var(--color-button-secondary);
}

.selection-action--danger {
  color: var(--color-text-danger);
}

.selection-action--danger:hover:not(:disabled) {
  background: rgba(255, 56, 60, 0.12);
}

.explorer-list,
.cells-empty {
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.25);
}

.workspace-error {
  padding: 12px;
  border-radius: 12px;
  border: 1px solid var(--color-border-danger);
  background: rgba(255, 56, 60, 0.08);
  color: var(--color-text-danger);
  font-size: 14px;
}

.cells-empty {
  padding: 14px;
  color: var(--color-text-muted);
}

.explorer-list {
  --explorer-grid-columns: minmax(0, 1fr) 164px 164px 110px 72px;
  --explorer-col-gap: 6px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.explorer-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.explorer-results-fade-enter-active,
.explorer-results-fade-leave-active {
  transition: opacity 0.16s ease;
  will-change: opacity;
}

.explorer-results-fade-enter-from,
.explorer-results-fade-leave-to {
  opacity: 0;
}

.explorer-table-head {
  position: sticky;
  top: 0;
  z-index: 8;
  display: grid;
  grid-template-columns: var(--explorer-grid-columns);
  align-items: center;
  column-gap: var(--explorer-col-gap);
  margin: 0;
  padding: 10px 22px;
  border-bottom: 1px solid rgba(22, 33, 89, 0.12);
  background: #eef2ff;
  border-radius: 20px 20px 0 0;
}

.explorer-head-cell {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgba(22, 33, 89, 0.64);
}

.explorer-head-cell--actions {
  justify-self: end;
  width: 72px;
}

.explorer-item {
  display: grid;
  grid-template-columns: var(--explorer-grid-columns);
  align-items: center;
  column-gap: var(--explorer-col-gap);
  background: var(--color-bg-primary);
  border-radius: 12px;
  padding: 10px 12px;
  margin: 0 10px;
  cursor: pointer;
  transition: box-shadow 0.16s ease, opacity 0.16s ease;
}

.explorer-item:last-child {
  margin-bottom: 10px;
}

.drag-preview {
  position: fixed;
  left: 0;
  top: 0;
  z-index: 10000;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  max-width: min(720px, 86vw);
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--color-border-light);
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 16px 30px rgba(13, 20, 56, 0.24);
  pointer-events: none;
  transform: translate3d(-9999px, -9999px, 0);
  transition: max-width 0.22s ease, padding 0.22s ease, gap 0.22s ease;
}

.drag-preview--compact {
  max-width: min(430px, 70vw);
  padding: 8px 10px;
  gap: 8px;
}

.drag-preview__icon {
  font-size: 20px;
  line-height: 1;
}

.drag-preview__title {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.explorer-item--droppable {
  cursor: copy;
}

.explorer-item--drop-target {
  box-shadow:
    0 0 0 2px rgba(123, 142, 198, 0.82),
    0 0 0 4px rgba(39, 52, 106, 0.1);
}

.explorer-item--drop-target.explorer-item--selected {
  box-shadow:
    0 0 0 2px rgba(123, 142, 198, 0.82),
    0 0 0 4px rgba(39, 52, 106, 0.1),
    inset 0 0 0 1px rgba(39, 52, 106, 0.18);
}

.explorer-item--selected {
  background: rgba(66, 120, 255, 0.2);
  box-shadow: 0 0 0 1px rgba(39, 52, 106, 0.18) inset;
}

.explorer-item--selected .explorer-title {
  color: #14225c;
}

.explorer-item-main {
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
  text-align: left;
  cursor: inherit;
  color: inherit;
  padding: 0;
}

.explorer-icon {
  font-size: 22px;
}

.explorer-title {
  font-size: 16px;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.explorer-cell {
  font-size: 13px;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: opacity 0.16s ease;
}

.explorer-head-cell--date,
.explorer-head-cell--updated,
.explorer-head-cell--size,
.explorer-cell--updated,
.explorer-cell--date,
.explorer-cell--size {
  text-align: left;
  padding-right: 0;
}

.explorer-actions {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-self: end;
  transition: opacity 0.16s ease;
}

.item-menu-trigger {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 8px;
  background: #fff;
  color: var(--color-text-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
}

.item-menu-trigger .material-symbols-rounded {
  font-size: 18px;
  transition: transform 0.18s ease;
}

.item-menu-trigger:hover {
  background: rgba(22, 33, 89, 0.08);
}

.item-menu-trigger:active {
  transform: scale(0.96);
}

.item-menu-trigger--open {
  background: rgba(39, 52, 106, 0.12);
}

.entry-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 200px;
  padding: 6px;
  border-radius: 10px;
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-card);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
  z-index: 30;
  transform-origin: top right;
}

.entry-menu-pop-enter-active,
.entry-menu-pop-leave-active {
  transition:
    opacity 0.16s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.16s cubic-bezier(0.22, 1, 0.36, 1);
}

.entry-menu-pop-enter-from,
.entry-menu-pop-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(0.98);
}

.entry-menu-item {
  width: 100%;
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 7px 10px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-primary);
  font: inherit;
  font-size: 14px;
  text-align: left;
  cursor: pointer;
}

.entry-menu-item:hover:not(:disabled) {
  background: rgba(22, 33, 89, 0.08);
}

.entry-menu-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.entry-menu-item .material-symbols-rounded {
  font-size: 18px;
}

.entry-menu-item--danger {
  color: var(--color-text-danger);
}

.entry-menu-item--danger:hover:not(:disabled) {
  background: rgba(255, 56, 60, 0.12);
}

.toolbar-search-wrap {
  width: min(44vw, 520px);
  min-width: 260px;
  max-width: 100%;
  position: relative;
  display: inline-flex;
  align-items: center;
  flex: 1 1 auto;
}

.toolbar-search-icon {
  position: absolute;
  left: 12px;
  font-size: 18px;
  line-height: 1;
  color: rgba(22, 33, 89, 0.58);
  pointer-events: none;
}

.toolbar-search {
  box-sizing: border-box;
  height: 34px;
  width: 100%;
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  background: #fff;
  color: var(--color-text-primary);
  padding: 0 12px 0 36px;
  font: inherit;
  font-size: 14px;
  line-height: 1;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.toolbar-search::placeholder {
  color: var(--color-text-muted);
}

.toolbar-search:focus {
  outline: none;
  border-color: rgba(22, 33, 89, 0.28);
  box-shadow: none;
}

.toolbar-search:focus-visible {
  outline: none;
  box-shadow: none;
}

.hidden-file-input {
  display: none;
}

.toolbar-pill {
  box-sizing: border-box;
  height: 34px;
  padding: 0 12px;
  background: var(--color-button-primary);
  border: none;
  color: #fff;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  box-shadow: 0 1px 0 rgba(22, 33, 89, 0.14);
  transition: filter 0.15s ease, transform 0.15s ease;
}

.toolbar-pill:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.toolbar-pill:hover:not(:disabled) {
  filter: brightness(1.04);
}

.toolbar-pill--secondary {
  background: var(--color-button-secondary);
  color: var(--color-text-primary);
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(31, 36, 68, 0.35);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.dialog-shell-enter-active,
.dialog-shell-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-shell-enter-from,
.dialog-shell-leave-to {
  opacity: 0;
}

.dialog-shell-enter-active .dialog-card,
.dialog-shell-leave-active .dialog-card {
  transition:
    transform 0.22s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.22s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform, opacity;
}

.dialog-shell-enter-from .dialog-card,
.dialog-shell-leave-to .dialog-card {
  opacity: 0;
  transform: translateY(10px) scale(0.985);
}

.dialog-card {
  width: min(420px, 100%);
  background: var(--color-bg-card);
  border-radius: 16px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.24);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-card--move {
  width: min(560px, 100%);
}

.dialog-title {
  margin: 0;
  font-size: 20px;
}

.dialog-input {
  width: 100%;
  border: none;
  border-radius: 10px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font: inherit;
  font-size: 15px;
  padding: 10px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.settings-action {
  border: none;
  border-radius: 8px;
  background: var(--color-button-primary);
  color: var(--color-button-text-primary);
  padding: 6px 12px;
  font: inherit;
  font-size: 14px;
  cursor: pointer;
}

.settings-action:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.settings-action--secondary {
  background: var(--color-button-secondary);
  color: var(--color-text-primary);
}

.settings-error {
  font-size: 13px;
  color: var(--color-text-danger);
  line-height: 1.25;
}

.move-target-list {
  max-height: min(360px, 55vh);
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.move-target-search-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.move-target-search-icon {
  position: absolute;
  left: 12px;
  font-size: 18px;
  color: rgba(22, 33, 89, 0.58);
  pointer-events: none;
}

.move-target-search {
  box-sizing: border-box;
  width: 100%;
  height: 36px;
  padding: 0 12px 0 36px;
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  background: #fff;
  color: var(--color-text-primary);
  font: inherit;
  font-size: 14px;
  line-height: 1;
}

.move-target-search:focus,
.move-target-search:focus-visible {
  outline: none;
  border-color: rgba(22, 33, 89, 0.28);
  box-shadow: none;
}

.move-target-empty {
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  padding: 12px;
  background: #fff;
  color: var(--color-text-muted);
  font-size: 13px;
}

.move-target {
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  background: #fff;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  text-align: left;
  color: var(--color-text-primary);
  cursor: pointer;
}

.move-target:hover:not(:disabled) {
  border-color: var(--color-border-default);
}

.move-target:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.move-target-icon {
  font-size: 20px;
}

.move-target-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.move-target-title {
  font-size: 14px;
}

.move-target-subtitle {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .notebook-main {
    padding: 16px;
  }

  .selection-toolbar {
    min-height: 56px;
    padding: 9px 10px;
  }

  .toolbar-idle-layout,
  .selection-toolbar-selected-layout {
    width: auto;
    gap: 8px;
  }

  .toolbar-search-wrap {
    width: min(64vw, 320px);
    min-width: 180px;
  }

  .toolbar-pill,
  .selection-action {
    min-height: 32px;
    height: 32px;
    font-size: 12px;
  }

  .explorer-list {
    --explorer-grid-columns: minmax(0, 1fr) 108px 108px 80px 58px;
    --explorer-col-gap: 4px;
  }

  .explorer-actions {
    justify-content: flex-end;
  }
}
</style>

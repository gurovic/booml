<template>
  <div class="polygon-edit">
    <UiHeader />
    <div class="polygon-edit__content">
      <div class="polygon-edit__header">
        <div class="polygon-edit__header-left">
          <button class="polygon-edit__back-btn" @click="goBack" title="Вернуться">
            ← Назад к списку
          </button>
          <h1 class="polygon-edit__title">
            {{ problem?.title || 'Редактирование задачи' }}
            <UiIdPill v-if="problem?.id" :id="problem.id" title="ID задачи" />
          </h1>
        </div>
        <div class="polygon-edit__header-actions">
          <button 
            class="button button--secondary" 
            @click="saveProblem"
            :disabled="saving"
          >
            {{ saving ? 'Сохранение...' : 'Сохранить' }}
          </button>
          <button 
            v-if="!problem?.is_published"
            class="button button--primary" 
            @click="publishProblem"
            :disabled="publishing || saving || uploading"
          >
            {{ publishing ? 'Публикация...' : 'Опубликовать' }}
          </button>
          <span v-else class="polygon-edit__published-badge">
            Опубликована
          </span>
        </div>
      </div>

      <div v-if="loading" class="polygon-edit__loading">
        Загрузка...
      </div>

      <div v-else-if="error" class="polygon-edit__error">
        {{ error }}
      </div>

      <div v-else class="polygon-edit__form">
        <!-- Success/Error messages -->
        <div v-if="successMessage" class="message message--success">
          {{ successMessage }}
        </div>
        <div v-if="errorMessage" class="message message--error">
          {{ errorMessage }}
        </div>

        <!-- Basic Information Section -->
        <section class="form-section">
          <h2 class="form-section__title">Основная информация</h2>
          <div class="form-section__content">
            <div class="form-group">
              <label for="problem-title" class="form-label">
                Название задачи <span class="required">*</span>
              </label>
              <input
                id="problem-title"
                v-model="formData.title"
                type="text"
                class="form-input"
                :class="{ 'form-input--error': errors.title }"
                placeholder="Введите название задачи"
              />
              <div v-if="errors.title" class="form-error">{{ errors.title }}</div>
            </div>

            <div class="form-group">
              <label for="problem-rating" class="form-label">
                Рейтинг сложности <span class="required">*</span>
              </label>
              <input
                id="problem-rating"
                v-model.number="formData.rating"
                type="number"
                class="form-input"
                :class="{ 'form-input--error': errors.rating }"
                placeholder="800"
                min="800"
                max="3000"
                step="100"
              />
              <div class="form-help">От 800 до 3000, шаг 100</div>
              <div v-if="errors.rating" class="form-error">{{ errors.rating }}</div>
            </div>
          </div>
        </section>

        <!-- Problem Statement Section -->
        <section class="form-section">
          <h2 class="form-section__title">Условие задачи</h2>
          <div class="form-section__content">
            <div class="form-group">
              <label for="problem-statement" class="form-label">
                Условие (Markdown) <span class="required">*</span>
              </label>

              <div class="statement-toolbar">
                <button class="statement-tool-btn" type="button" @click="applyWrap('**', '**', 'жирный текст')" title="Жирный">
                  <strong>B</strong>
                </button>
                <button class="statement-tool-btn" type="button" @click="applyWrap('*', '*', 'курсив')" title="Курсив">
                  <em>I</em>
                </button>
                <button class="statement-tool-btn" type="button" @click="applyWrap('`', '`', 'code')" title="Inline code">
                  <code>{ }</code>
                </button>
                <button class="statement-tool-btn" type="button" @click="applyCodeBlock" title="Блок кода">
                  &lt;/&gt;
                </button>
                <button class="statement-tool-btn" type="button" @click="applyPrefix('## ')" title="Заголовок H2">
                  H2
                </button>
                <button class="statement-tool-btn" type="button" @click="applyPrefix('### ')" title="Заголовок H3">
                  H3
                </button>
                <button class="statement-tool-btn" type="button" @click="insertUnorderedList" title="Маркированный список">
                  • Список
                </button>
                <button class="statement-tool-btn" type="button" @click="insertOrderedList" title="Нумерованный список">
                  1. Список
                </button>
                <button class="statement-tool-btn" type="button" @click="insertTableTemplate" title="Таблица">
                  Таблица
                </button>
                <button class="statement-tool-btn" type="button" @click="insertLinkTemplate" title="Ссылка">
                  Ссылка
                </button>
                <button class="statement-tool-btn" type="button" @click="insertMathTemplate" title="Формула">
                  Σ Формула
                </button>
              </div>

              <div class="statement-toolbar statement-toolbar--secondary">
                <span class="statement-toolbar__label">Цвет текста</span>
                <button
                  v-for="preset in statementColorPresets"
                  :key="preset.color"
                  type="button"
                  class="statement-color-chip"
                  :class="{ 'statement-color-chip--active': customStatementColor === preset.color }"
                  :title="`Цвет: ${preset.label}`"
                  @click="setStatementColor(preset.color)"
                >
                  <span class="statement-color-chip__dot" :style="{ backgroundColor: preset.color }"></span>
                  {{ preset.label }}
                </button>
                <input
                  v-model="customStatementColor"
                  type="text"
                  class="statement-color-input"
                  placeholder="#2563eb"
                />
                <button class="statement-tool-btn" type="button" @click="applyColor(customStatementColor)">
                  Применить цвет
                </button>
              </div>

              <div class="statement-toolbar statement-toolbar--secondary statement-toolbar--image">
                <div class="statement-image-controls">
                  <input
                    v-model="statementImageAlt"
                    type="text"
                    class="form-input statement-image-controls__input"
                    placeholder="alt-текст картинки"
                  />
                  <input
                    v-model="statementImageUrl"
                    type="text"
                    class="form-input statement-image-controls__input"
                    placeholder="https://... или data:image/..."
                  />
                  <button class="statement-tool-btn" type="button" @click="insertImageByUrl">
                    Вставить картинку по URL
                  </button>
                  <input
                    id="statement-image-upload"
                    class="statement-image-upload"
                    type="file"
                    accept="image/*"
                    @change="handleStatementImageUpload"
                  />
                  <label class="file-upload-button statement-image-upload__label" for="statement-image-upload">
                    Загрузить картинку
                  </label>
                </div>
              </div>

              <div class="statement-view-switch">
                <button
                  type="button"
                  class="statement-view-switch__btn"
                  :class="{ 'statement-view-switch__btn--active': statementViewMode === 'edit' }"
                  @click="statementViewMode = 'edit'"
                >
                  Только редактор
                </button>
                <button
                  type="button"
                  class="statement-view-switch__btn"
                  :class="{ 'statement-view-switch__btn--active': statementViewMode === 'split' }"
                  @click="statementViewMode = 'split'"
                >
                  Редактор + предпросмотр
                </button>
                <button
                  type="button"
                  class="statement-view-switch__btn"
                  :class="{ 'statement-view-switch__btn--active': statementViewMode === 'preview' }"
                  @click="statementViewMode = 'preview'"
                >
                  Только предпросмотр
                </button>
              </div>

              <div class="statement-panels" :class="`statement-panels--${statementViewMode}`">
                <div v-if="statementViewMode !== 'preview'" class="statement-panel statement-panel--editor">
                  <p class="statement-panel__title">Редактор</p>
                  <textarea
                    id="problem-statement"
                    ref="statementInput"
                    v-model="formData.statement"
                    class="form-textarea statement-editor"
                    :class="{ 'form-input--error': errors.statement }"
                    placeholder="Введите условие задачи в формате Markdown"
                    rows="16"
                    @dragover.prevent
                    @drop.prevent="handleStatementDrop"
                    @paste="handleStatementPaste"
                    @keydown="handleStatementKeydown"
                  ></textarea>
                </div>

                <div v-if="statementViewMode !== 'edit'" class="statement-panel statement-panel--preview">
                  <p class="statement-panel__title">Предпросмотр</p>
                  <div class="statement-preview__content" v-html="statementPreviewHtml"></div>
                </div>
              </div>

              <div class="statement-stats">
                Строк: {{ statementLineCount }} · Слов: {{ statementWordCount }} · Символов: {{ statementCharCount }}
              </div>
              <div class="form-help">
                Поддерживаются Markdown, формулы KaTeX, таблицы, цветной текст и изображения; цвет задаётся
                синтаксисом <code>{color:#hex|текст}</code>, а картинку можно вставить по ссылке, перетащить в поле
                или вставить из буфера обмена.
              </div>
              <div v-if="errors.statement" class="form-error">{{ errors.statement }}</div>
            </div>
          </div>
        </section>

        <!-- Data Descriptor Section -->
        <section class="form-section">
          <h2 class="form-section__title">Настройки данных</h2>
          <div class="form-section__content">
            <div class="form-row">
              <div class="form-group">
                <label for="id-column" class="form-label">
                  Колонка идентификатора <span class="required">*</span>
                </label>
                <input
                  id="id-column"
                  v-model="formData.descriptor.id_column"
                  type="text"
                  class="form-input"
                  :class="{ 'form-input--error': errors.descriptor?.id_column }"
                  placeholder="id"
                />
                <div v-if="errors.descriptor?.id_column" class="form-error">
                  {{ errors.descriptor.id_column }}
                </div>
              </div>

              <div class="form-group">
                <label for="id-type" class="form-label">
                  Тип идентификатора <span class="required">*</span>
                </label>
                <select
                  id="id-type"
                  v-model="formData.descriptor.id_type"
                  class="form-select"
                  :class="{ 'form-input--error': errors.descriptor?.id_type }"
                >
                  <option
                    v-for="choice in idTypeChoices"
                    :key="choice.value"
                    :value="choice.value"
                  >
                    {{ choice.label }}
                  </option>
                </select>
                <div v-if="errors.descriptor?.id_type" class="form-error">
                  {{ errors.descriptor.id_type }}
                </div>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="target-column" class="form-label">
                  Колонка ответа <span class="required">*</span>
                </label>
                <input
                  id="target-column"
                  v-model="formData.descriptor.target_column"
                  type="text"
                  class="form-input"
                  :class="{ 'form-input--error': errors.descriptor?.target_column }"
                  placeholder="prediction"
                />
                <div v-if="errors.descriptor?.target_column" class="form-error">
                  {{ errors.descriptor.target_column }}
                </div>
              </div>

              <div class="form-group">
                <label for="target-type" class="form-label">
                  Тип ответа <span class="required">*</span>
                </label>
                <select
                  id="target-type"
                  v-model="formData.descriptor.target_type"
                  class="form-select"
                  :class="{ 'form-input--error': errors.descriptor?.target_type }"
                >
                  <option
                    v-for="choice in targetTypeChoices"
                    :key="choice.value"
                    :value="choice.value"
                  >
                    {{ choice.label }}
                  </option>
                </select>
                <div v-if="errors.descriptor?.target_type" class="form-error">
                  {{ errors.descriptor.target_type }}
                </div>
              </div>
            </div>

            <div class="form-group">
              <label class="form-checkbox">
                <input
                  type="checkbox"
                  v-model="formData.descriptor.check_order"
                  class="form-checkbox-input"
                />
                <span class="form-checkbox-label">Проверять порядок строк</span>
              </label>
              <div class="form-help">Если включено, порядок строк в ответе должен совпадать с эталоном</div>
            </div>

            <div class="form-group">
              <label for="metric-name" class="form-label">
                Метрика качества <span class="required">*</span>
              </label>
              <select
                id="metric-name"
                v-model="formData.descriptor.metric_name"
                class="form-select"
                :class="{ 'form-input--error': errors.descriptor?.metric_name }"
              >
                <option value="">Выберите метрику</option>
                <option
                  v-for="metric in availableMetrics"
                  :key="metric"
                  :value="metric"
                >
                  {{ metric.toUpperCase() }}
                </option>
              </select>
              <div class="form-help">
                Метрика для оценки решений участников
              </div>
              <div v-if="errors.descriptor?.metric_name" class="form-error">
                {{ errors.descriptor.metric_name }}
              </div>
            </div>

            <div class="form-group">
              <label for="metric-code" class="form-label">
                Пользовательский код метрики (опционально)
              </label>
              <textarea
                id="metric-code"
                v-model="formData.descriptor.metric_code"
                class="form-textarea"
                placeholder="def custom_metric(y_true, y_pred):
    # Ваш код здесь
    pass"
                rows="6"
              ></textarea>
              <div class="form-help">
                Python код для пользовательской метрики. Если не указано, используется стандартная метрика
              </div>
            </div>
          </div>
        </section>

        <!-- Data Files Section -->
        <section class="form-section">
          <h2 class="form-section__title">Файлы данных</h2>
          <div class="form-section__content">
            <div class="file-uploads">
              <!-- Train File -->
              <div class="file-upload-group">
                <label class="file-upload-label">
                  Тренировочные данные (train.csv/zip/rar)
                </label>
                <div class="file-upload-controls">
                  <input
                    type="file"
                    @change="handleFileSelect('train_file', $event)"
                    accept=".csv,.zip,.rar"
                    class="file-upload-input"
                    id="train-file"
                    ref="trainFileInput"
                  />
                  <label for="train-file" class="file-upload-button">
                    Выбрать файл
                  </label>
                  <span class="file-upload-name">
                    {{ selectedFiles.train_file?.name || problem?.files?.train_file?.name || 'Файл не выбран' }}
                  </span>
                </div>
                <div v-if="problem?.files?.train_file" class="file-current">
                  Текущий файл: 
                  <a :href="problem.files.train_file.url" download>
                    {{ problem.files.train_file.name }}
                  </a>
                </div>
              </div>

              <!-- Test File -->
              <div class="file-upload-group">
                <label class="file-upload-label">
                  Тестовые данные (test.csv/zip/rar)
                </label>
                <div class="file-upload-controls">
                  <input
                    type="file"
                    @change="handleFileSelect('test_file', $event)"
                    accept=".csv,.zip,.rar"
                    class="file-upload-input"
                    id="test-file"
                    ref="testFileInput"
                  />
                  <label for="test-file" class="file-upload-button">
                    Выбрать файл
                  </label>
                  <span class="file-upload-name">
                    {{ selectedFiles.test_file?.name || problem?.files?.test_file?.name || 'Файл не выбран' }}
                  </span>
                </div>
                <div v-if="problem?.files?.test_file" class="file-current">
                  Текущий файл: 
                  <a :href="problem.files.test_file.url" download>
                    {{ problem.files.test_file.name }}
                  </a>
                </div>
              </div>

              <!-- Sample Submission File -->
              <div class="file-upload-group">
                <label class="file-upload-label">
                  Пример решения (sample_submission.csv)
                </label>
                <div class="file-upload-controls">
                  <input
                    type="file"
                    @change="handleFileSelect('sample_submission_file', $event)"
                    accept=".csv"
                    class="file-upload-input"
                    id="sample-submission-file"
                    ref="sampleSubmissionFileInput"
                  />
                  <label for="sample-submission-file" class="file-upload-button">
                    Выбрать файл
                  </label>
                  <span class="file-upload-name">
                    {{ selectedFiles.sample_submission_file?.name || problem?.files?.sample_submission_file?.name || 'Файл не выбран' }}
                  </span>
                </div>
                <div v-if="problem?.files?.sample_submission_file" class="file-current">
                  Текущий файл: 
                  <a :href="problem.files.sample_submission_file.url" download>
                    {{ problem.files.sample_submission_file.name }}
                  </a>
                </div>
              </div>

              <!-- Answer File -->
              <div class="file-upload-group">
                <label class="file-upload-label">
                  Файл ответов (answer.csv) <span class="required">*</span>
                </label>
                <div class="file-upload-controls">
                  <input
                    type="file"
                    @change="handleFileSelect('answer_file', $event)"
                    accept=".csv"
                    class="file-upload-input"
                    id="answer-file"
                    ref="answerFileInput"
                  />
                  <label for="answer-file" class="file-upload-button">
                    Выбрать файл
                  </label>
                  <span class="file-upload-name">
                    {{ selectedFiles.answer_file?.name || problem?.files?.answer_file?.name || 'Файл не выбран' }}
                  </span>
                </div>
                <div v-if="problem?.files?.answer_file" class="file-current">
                  Текущий файл: 
                  <a :href="problem.files.answer_file.url" download>
                    {{ problem.files.answer_file.name }}
                  </a>
                </div>
              </div>

              <button
                v-if="hasSelectedFiles"
                class="button button--primary"
                @click="uploadFiles"
                :disabled="uploading"
              >
                {{ uploading ? 'Загрузка...' : 'Загрузить файлы' }}
              </button>
            </div>
          </div>
        </section>

        <!-- Action Buttons -->
        <div class="polygon-edit__actions">
          <button 
            class="button button--secondary" 
            @click="goBack"
          >
            Отмена
          </button>
          <button 
            class="button button--secondary" 
            @click="saveProblem"
            :disabled="saving"
          >
            {{ saving ? 'Сохранение...' : 'Сохранить' }}
          </button>
          <button 
            v-if="!problem?.is_published"
            class="button button--primary" 
            @click="publishProblem"
            :disabled="publishing || saving || uploading"
          >
            {{ publishing ? 'Публикация...' : 'Опубликовать' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  getPolygonProblem, 
  updatePolygonProblem, 
  uploadPolygonProblemFiles,
  publishPolygonProblem 
} from '@/api/polygon'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiIdPill from '@/components/ui/UiIdPill.vue'
import {
  renderProblemStatement,
  normalizeStatementColor,
  STATEMENT_COLOR_PRESETS,
} from '@/utils/problemMarkdown'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const saving = ref(false)
const uploading = ref(false)
const publishing = ref(false)
const error = ref(null)
const successMessage = ref(null)
const errorMessage = ref(null)

const problem = ref(null)
const availableMetrics = ref([])
const idTypeChoices = ref([])
const targetTypeChoices = ref([])

const formData = reactive({
  title: '',
  rating: 800,
  statement: '',
  descriptor: {
    id_column: 'id',
    target_column: 'prediction',
    id_type: 'int',
    target_type: 'float',
    check_order: false,
    metric_name: 'rmse',
    metric_code: '',
  }
})

const errors = reactive({
  title: null,
  rating: null,
  statement: null,
  descriptor: {}
})

const selectedFiles = reactive({
  train_file: null,
  test_file: null,
  sample_submission_file: null,
  answer_file: null,
})

const trainFileInput = ref(null)
const testFileInput = ref(null)
const sampleSubmissionFileInput = ref(null)
const answerFileInput = ref(null)

const fileInputRefs = { trainFileInput, testFileInput, sampleSubmissionFileInput, answerFileInput }
const statementInput = ref(null)
const statementViewMode = ref('split')
const statementImageUrl = ref('')
const statementImageAlt = ref('')
const statementColorPresets = STATEMENT_COLOR_PRESETS
const customStatementColor = ref(statementColorPresets[0]?.color || '#2563eb')

const hasSelectedFiles = computed(() => {
  return Object.values(selectedFiles).some(file => file !== null)
})

const statementPreviewHtml = computed(() => renderProblemStatement(formData.statement || ''))
const statementCharCount = computed(() => (formData.statement || '').length)
const statementWordCount = computed(() => {
  const raw = (formData.statement || '').trim()
  if (!raw) return 0
  return raw.split(/\s+/).filter(Boolean).length
})
const statementLineCount = computed(() => {
  const raw = formData.statement || ''
  if (!raw) return 0
  return raw.split(/\r\n?|\n/).length
})

const clearMessages = () => {
  successMessage.value = null
  errorMessage.value = null
  errors.title = null
  errors.rating = null
  errors.statement = null
  errors.descriptor = {}
}

const withStatementSelection = (transform) => {
  const input = statementInput.value
  if (!input || typeof transform !== 'function') return

  const source = formData.statement || ''
  const start = Number.isInteger(input.selectionStart) ? input.selectionStart : source.length
  const end = Number.isInteger(input.selectionEnd) ? input.selectionEnd : start
  const selected = source.slice(start, end)
  const result = transform({ source, start, end, selected })

  if (!result || typeof result.nextValue !== 'string') return

  formData.statement = result.nextValue

  nextTick(() => {
    const textarea = statementInput.value
    if (!textarea) return
    textarea.focus()

    const nextStart = Number.isInteger(result.selectionStart) ? result.selectionStart : start
    const nextEnd = Number.isInteger(result.selectionEnd) ? result.selectionEnd : nextStart
    const maxPos = formData.statement.length
    const clampedStart = Math.min(Math.max(nextStart, 0), maxPos)
    const clampedEnd = Math.min(Math.max(nextEnd, clampedStart), maxPos)

    textarea.setSelectionRange(clampedStart, clampedEnd)
  })
}

const setStatementValueAndCaret = (nextValue, caretPos) => {
  formData.statement = nextValue
  nextTick(() => {
    const textarea = statementInput.value
    if (!textarea) return
    textarea.focus()
    const maxPos = formData.statement.length
    const clamped = Math.min(Math.max(caretPos, 0), maxPos)
    textarea.setSelectionRange(clamped, clamped)
  })
}

const applyWrap = (prefix, suffix, fallbackText = 'текст') => {
  withStatementSelection(({ source, start, end, selected }) => {
    const inner = selected || fallbackText
    const insertion = `${prefix}${inner}${suffix}`
    return {
      nextValue: source.slice(0, start) + insertion + source.slice(end),
      selectionStart: start + prefix.length,
      selectionEnd: start + prefix.length + inner.length,
    }
  })
}

const applyPrefix = (prefix) => {
  withStatementSelection(({ source, start, end }) => {
    const blockStart = source.lastIndexOf('\n', Math.max(0, start - 1)) + 1
    const blockEndIndex = source.indexOf('\n', end)
    const blockEnd = blockEndIndex === -1 ? source.length : blockEndIndex
    const block = source.slice(blockStart, blockEnd)
    const lines = (block || '').split('\n')
    const prefixedBlock = lines.map(line => `${prefix}${line}`).join('\n')
    return {
      nextValue: source.slice(0, blockStart) + prefixedBlock + source.slice(blockEnd),
      selectionStart: blockStart,
      selectionEnd: blockStart + prefixedBlock.length,
    }
  })
}

const applyCodeBlock = () => {
  withStatementSelection(({ source, start, end, selected }) => {
    const body = selected || '# ваш код здесь'
    const needLeadingBreak = start > 0 && source[start - 1] !== '\n'
    const needTrailingBreak = end < source.length && source[end] !== '\n'
    const prefix = needLeadingBreak ? '\n' : ''
    const suffix = needTrailingBreak ? '\n' : ''
    const insertion = `${prefix}\`\`\`python\n${body}\n\`\`\`${suffix}`
    const cursorStart = start + prefix.length + '```python\n'.length
    return {
      nextValue: source.slice(0, start) + insertion + source.slice(end),
      selectionStart: cursorStart,
      selectionEnd: cursorStart + body.length,
    }
  })
}

const insertAtCursor = (snippet, cursorOffset = null) => {
  withStatementSelection(({ source, start, end }) => {
    const insertion = String(snippet || '')
    const cursorPos = cursorOffset == null ? start + insertion.length : start + cursorOffset
    return {
      nextValue: source.slice(0, start) + insertion + source.slice(end),
      selectionStart: cursorPos,
      selectionEnd: cursorPos,
    }
  })
}

const insertUnorderedList = () => {
  insertAtCursor('- Пункт 1\n- Пункт 2\n- Пункт 3\n')
}

const insertOrderedList = () => {
  insertAtCursor('1. Пункт 1\n2. Пункт 2\n3. Пункт 3\n')
}

const insertTableTemplate = () => {
  insertAtCursor('| Колонка | Описание |\n|---|---|\n| feature_1 | Что это за признак |\n| target | Что нужно предсказать |\n')
}

const insertLinkTemplate = () => {
  applyWrap('[', '](https://example.com)', 'текст ссылки')
}

const insertMathTemplate = () => {
  withStatementSelection(({ source, start, end, selected }) => {
    if (selected) {
      const insertion = `$${selected}$`
      return {
        nextValue: source.slice(0, start) + insertion + source.slice(end),
        selectionStart: start + 1,
        selectionEnd: start + 1 + selected.length,
      }
    }
    const insertion = '$$\n\n$$'
    return {
      nextValue: source.slice(0, start) + insertion + source.slice(end),
      selectionStart: start + 3,
      selectionEnd: start + 3,
    }
  })
}

const setStatementColor = (color) => {
  const normalized = normalizeStatementColor(color)
  if (!normalized) {
    errorMessage.value = 'Укажите цвет в формате #RRGGBB или #RGB'
    return
  }
  customStatementColor.value = normalized
}

const applyColor = (color) => {
  const normalized = normalizeStatementColor(color)
  if (!normalized) {
    errorMessage.value = 'Укажите цвет в формате #RRGGBB или #RGB'
    return
  }
  customStatementColor.value = normalized
  applyWrap(`{color:${normalized}|`, '}', 'цветной текст')
}

const sanitizeAltText = (value) => {
  return String(value || '')
    .replace(/\r|\n|\[|\]/g, ' ')
    .trim()
}

const isImageUrlAllowed = (value) => {
  const url = String(value || '').trim()
  if (!url) return false
  return /^https?:\/\//i.test(url) || /^data:image\//i.test(url)
}

const insertImageMarkdown = (src, altText = 'image') => {
  const safeAlt = sanitizeAltText(altText) || 'image'
  const safeSrc = String(src || '').trim()
  if (!isImageUrlAllowed(safeSrc)) {
    errorMessage.value = 'Поддерживаются только https://, http:// и data:image/...'
    return
  }

  withStatementSelection(({ source, start, end }) => {
    const needLeadingBreak = start > 0 && source[start - 1] !== '\n'
    const needTrailingBreak = end < source.length && source[end] !== '\n'
    const prefix = needLeadingBreak ? '\n' : ''
    const suffix = needTrailingBreak ? '\n' : ''
    const insertion = `${prefix}![${safeAlt}](${safeSrc})${suffix}`
    const nextPos = start + insertion.length
    return {
      nextValue: source.slice(0, start) + insertion + source.slice(end),
      selectionStart: nextPos,
      selectionEnd: nextPos,
    }
  })
}

const insertImageByUrl = () => {
  const url = (statementImageUrl.value || '').trim()
  if (!url) {
    errorMessage.value = 'Укажите URL изображения'
    return
  }
  if (!isImageUrlAllowed(url)) {
    errorMessage.value = 'Ссылка на изображение должна начинаться с https://, http:// или data:image/...'
    return
  }

  insertImageMarkdown(url, statementImageAlt.value || 'image')
  statementImageUrl.value = ''
}

const readFileAsDataUrl = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('Не удалось прочитать изображение'))
    reader.readAsDataURL(file)
  })
}

const fileNameWithoutExt = (fileName) => {
  const value = String(fileName || '').trim()
  return value.replace(/\.[^.]+$/, '')
}

const MAX_INLINE_IMAGE_BYTES = 4 * 1024 * 1024

const handleStatementImageFile = async (file) => {
  if (!file) return
  if (!String(file.type || '').startsWith('image/')) {
    errorMessage.value = 'Можно вставлять только изображения'
    return
  }
  if (file.size > MAX_INLINE_IMAGE_BYTES) {
    errorMessage.value = 'Изображение слишком большое. Лимит: 4MB'
    return
  }

  try {
    const dataUrl = await readFileAsDataUrl(file)
    insertImageMarkdown(dataUrl, fileNameWithoutExt(file.name) || statementImageAlt.value || 'image')
  } catch (err) {
    console.error('Failed to process statement image', err)
    errorMessage.value = 'Не удалось обработать изображение'
  }
}

const handleStatementImageUpload = async (event) => {
  const input = event?.target
  const file = input?.files?.[0]
  await handleStatementImageFile(file)
  if (input) input.value = ''
}

const handleStatementDrop = async (event) => {
  const files = Array.from(event?.dataTransfer?.files || []).filter(file =>
    String(file.type || '').startsWith('image/')
  )
  if (files.length > 0) {
    for (const file of files) {
      await handleStatementImageFile(file)
    }
    return
  }

  const droppedUrl = (event?.dataTransfer?.getData('text/uri-list') ||
    event?.dataTransfer?.getData('text/plain') ||
    '').trim()
  if (isImageUrlAllowed(droppedUrl)) {
    insertImageMarkdown(droppedUrl, statementImageAlt.value || 'image')
  }
}

const handleStatementPaste = async (event) => {
  const items = Array.from(event?.clipboardData?.items || [])
  const imageFiles = items
    .filter(item => item.kind === 'file' && String(item.type || '').startsWith('image/'))
    .map(item => item.getAsFile())
    .filter(Boolean)

  if (!imageFiles.length) return

  event.preventDefault()
  for (const file of imageFiles) {
    await handleStatementImageFile(file)
  }
}

const handleStatementKeydown = (event) => {
  if (event?.key !== 'Enter') return

  const textarea = statementInput.value
  if (!textarea) return

  const source = formData.statement || ''
  const start = Number.isInteger(textarea.selectionStart) ? textarea.selectionStart : 0
  const end = Number.isInteger(textarea.selectionEnd) ? textarea.selectionEnd : start
  if (start !== end) return

  const lineStart = source.lastIndexOf('\n', Math.max(0, start - 1)) + 1
  const lineEnd = source.indexOf('\n', start)
  const currentLineEnd = lineEnd === -1 ? source.length : lineEnd
  if (start !== currentLineEnd) return

  const line = source.slice(lineStart, currentLineEnd)
  const unorderedMatch = line.match(/^(\s*)([-*+])\s+(.*)$/)
  const orderedMatch = line.match(/^(\s*)(\d+)\.\s+(.*)$/)

  const continueWith = (prefix) => {
    event.preventDefault()
    const nextValue = source.slice(0, start) + `\n${prefix}` + source.slice(end)
    setStatementValueAndCaret(nextValue, start + prefix.length + 1)
  }

  const stopList = () => {
    event.preventDefault()
    const nextValue = source.slice(0, lineStart) + source.slice(currentLineEnd)
    setStatementValueAndCaret(nextValue, lineStart)
  }

  if (unorderedMatch) {
    const indent = unorderedMatch[1] || ''
    const marker = unorderedMatch[2] || '-'
    const content = unorderedMatch[3] || ''
    if (!content.trim()) {
      stopList()
      return
    }
    continueWith(`${indent}${marker} `)
    return
  }

  if (orderedMatch) {
    const indent = orderedMatch[1] || ''
    const current = Number(orderedMatch[2] || '1')
    const content = orderedMatch[3] || ''
    if (!content.trim()) {
      stopList()
      return
    }
    continueWith(`${indent}${current + 1}. `)
  }
}

const loadProblem = async () => {
  loading.value = true
  error.value = null
  
  try {
    const problemId = route.params.id
    const data = await getPolygonProblem(problemId)
    
    problem.value = data
    availableMetrics.value = data.available_metrics || []
    idTypeChoices.value = data.id_type_choices || []
    targetTypeChoices.value = data.target_type_choices || []
    
    // Populate form data
    formData.title = data.title || ''
    formData.rating = data.rating || 800
    formData.statement = data.statement || ''
    
    if (data.descriptor) {
      formData.descriptor.id_column = data.descriptor.id_column || 'id'
      formData.descriptor.target_column = data.descriptor.target_column || 'prediction'
      formData.descriptor.id_type = data.descriptor.id_type || 'int'
      formData.descriptor.target_type = data.descriptor.target_type || 'float'
      formData.descriptor.check_order = data.descriptor.check_order || false
      formData.descriptor.metric_name = data.descriptor.metric_name || 'rmse'
      formData.descriptor.metric_code = data.descriptor.metric_code || ''
    }
  } catch (err) {
    console.error('Failed to load problem', err)
    error.value = 'Не удалось загрузить данные задачи. Попробуйте позже.'
  } finally {
    loading.value = false
  }
}

const persistProblem = async ({ showSuccessMessage = true } = {}) => {
  saving.value = true
  
  try {
    const problemId = route.params.id
    const updateData = {
      title: formData.title,
      rating: formData.rating,
      statement: formData.statement,
      descriptor: {
        id_column: formData.descriptor.id_column,
        target_column: formData.descriptor.target_column,
        id_type: formData.descriptor.id_type,
        target_type: formData.descriptor.target_type,
        check_order: formData.descriptor.check_order,
        metric_name: formData.descriptor.metric_name,
        metric_code: formData.descriptor.metric_code,
      }
    }
    
    const data = await updatePolygonProblem(problemId, updateData)
    
    // Update problem data
    problem.value = { ...problem.value, ...data }
    
    if (showSuccessMessage) {
      successMessage.value = 'Задача успешно сохранена'
      setTimeout(() => { successMessage.value = null }, 3000)
    }
    return data
  } catch (err) {
    console.error('Failed to save problem', err)
    
    // Handle structured error response
    if (err.data && err.data.errors) {
      const responseErrors = err.data.errors
      
      // Assign errors but avoid empty objects
      if (responseErrors.title) errors.title = responseErrors.title
      if (responseErrors.rating) errors.rating = responseErrors.rating
      if (responseErrors.statement) errors.statement = responseErrors.statement
      if (responseErrors.descriptor && Object.keys(responseErrors.descriptor).length > 0) {
        errors.descriptor = responseErrors.descriptor
      }
      
      errorMessage.value = 'Проверьте правильность заполнения полей'
    } else {
      errorMessage.value = 'Не удалось сохранить задачу'
    }
    throw err
  } finally {
    saving.value = false
  }
}

const saveProblem = async () => {
  clearMessages()
  await persistProblem()
}

const handleFileSelect = (fieldName, event) => {
  const file = event.target.files[0]
  selectedFiles[fieldName] = file || null
}

const persistFiles = async ({ showSuccessMessage = true } = {}) => {
  if (!hasSelectedFiles.value) {
    return null
  }

  uploading.value = true
  
  try {
    const problemId = route.params.id
    const formDataToSend = new FormData()
    
    Object.entries(selectedFiles).forEach(([key, file]) => {
      if (file) {
        formDataToSend.append(key, file)
      }
    })
    
    const data = await uploadPolygonProblemFiles(problemId, formDataToSend)
    
    // Update problem files
    if (data.files) {
      problem.value.files = data.files
    }
    
    // Clear selected files
    Object.keys(selectedFiles).forEach(key => {
      selectedFiles[key] = null
    })
    
    // Reset file input elements
    Object.values(fileInputRefs).forEach(r => { if (r.value) r.value.value = '' })
    
    if (showSuccessMessage) {
      successMessage.value = 'Файлы успешно загружены'
      setTimeout(() => { successMessage.value = null }, 3000)
    }
    return data
  } catch (err) {
    console.error('Failed to upload files', err)
    errorMessage.value = 'Не удалось загрузить файлы. Проверьте формат файлов.'
    throw err
  } finally {
    uploading.value = false
  }
}

const uploadFiles = async () => {
  clearMessages()
  await persistFiles()
}

const publishProblem = async () => {
  clearMessages()
  publishing.value = true
  
  try {
    const problemId = route.params.id
    await persistProblem({ showSuccessMessage: false })
    await persistFiles({ showSuccessMessage: false })
    const data = await publishPolygonProblem(problemId)
    
    problem.value = {
      ...problem.value,
      is_published: true,
    }
    successMessage.value = data.message || 'Задача успешно опубликована'
    setTimeout(() => { successMessage.value = null }, 5000)
  } catch (err) {
    console.error('Failed to publish problem', err)
    
    // Handle structured error response
    if (err.data && err.data.errors) {
      if (Array.isArray(err.data.errors)) {
        errorMessage.value = err.data.errors.join('. ')
      } else {
        errorMessage.value = 'Не удалось опубликовать задачу'
      }
    } else {
      errorMessage.value = 'Не удалось опубликовать задачу'
    }
  } finally {
    publishing.value = false
  }
}

const goBack = () => {
  router.push('/polygon')
}

onMounted(loadProblem)
</script>

<style scoped>
.polygon-edit {
  min-height: 100vh;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

.polygon-edit__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 16px;
}

.polygon-edit__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  gap: 16px;
  flex-wrap: wrap;
}

.polygon-edit__header-left {
  flex: 1;
  min-width: 0;
}

.polygon-edit__back-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 0;
  margin-bottom: 8px;
  transition: opacity 0.2s ease;
}

.polygon-edit__back-btn:hover {
  opacity: 0.7;
}

.polygon-edit__title {
  font-family: var(--font-title);
  font-size: 32px;
  font-weight: 400;
  color: var(--color-title-text);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.polygon-edit__header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.polygon-edit__published-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-border);
}

.polygon-edit__loading,
.polygon-edit__error {
  text-align: center;
  padding: 48px 16px;
  font-size: 18px;
}

.polygon-edit__error {
  color: var(--color-error-text);
}

.polygon-edit__form {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.message {
  padding: 16px 20px;
  border-radius: 8px;
  font-size: 16px;
  margin-bottom: 16px;
}

.message--success {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-border);
}

.message--error {
  background: #fee;
  color: #c00;
  border: 1px solid #fcc;
}

.form-section {
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border-default);
  overflow: hidden;
}

.form-section__title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-title-text);
  margin: 0;
  padding: 20px 24px;
  background: var(--color-bg-muted);
  border-bottom: 1px solid var(--color-border-default);
}

.form-section__content {
  padding: 24px;
}

.form-group {
  margin-bottom: 24px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text-primary);
}

.required {
  color: #e74c3c;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  font-size: 16px;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-card);
  transition: border-color 0.2s ease;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-input--error,
.form-select--error,
.form-textarea--error {
  border-color: #e74c3c;
}

.form-textarea {
  resize: vertical;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.form-select {
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23333' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
  appearance: none;
}

.form-help {
  margin-top: 6px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.form-error {
  margin-top: 6px;
  font-size: 14px;
  color: #e74c3c;
}

.statement-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.statement-toolbar--secondary {
  align-items: center;
  padding: 10px;
  border: 1px solid var(--color-border-default);
  border-radius: 10px;
  background: #fbfdff;
}

.statement-toolbar--image {
  padding: 12px;
}

.statement-toolbar__label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin-right: 2px;
}

.statement-tool-btn {
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
  font-size: 13px;
  font-weight: 500;
  color: #0f172a;
  transition: all 0.15s ease;
}

.statement-tool-btn:hover {
  background: #f1f5ff;
  border-color: #b8c8ff;
}

.statement-color-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--color-border-default);
  border-radius: 999px;
  padding: 6px 10px;
  background: #fff;
  font-size: 12px;
  color: #1e293b;
}

.statement-color-chip--active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.statement-color-chip__dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.18);
}

.statement-color-input {
  width: 112px;
  min-height: 34px;
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  font-size: 13px;
  padding: 6px 10px;
}

.statement-image-controls {
  display: grid;
  grid-template-columns: minmax(0, 180px) minmax(0, 1fr) auto auto;
  gap: 8px;
  width: 100%;
}

.statement-image-controls__input {
  min-width: 0;
}

.statement-image-upload {
  display: none;
}

.statement-image-upload__label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0;
}

.statement-view-switch {
  display: inline-flex;
  gap: 6px;
  padding: 4px;
  border: 1px solid var(--color-border-default);
  border-radius: 10px;
  margin-bottom: 10px;
  background: #fff;
}

.statement-view-switch__btn {
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  color: #334155;
}

.statement-view-switch__btn--active {
  border-color: #b8c8ff;
  color: #1d4ed8;
  background: #eef4ff;
}

.statement-panels {
  display: grid;
  gap: 12px;
  margin-bottom: 8px;
  align-items: stretch;
}

.statement-panels--split {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: stretch;
}

.statement-panel {
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.statement-panel__title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: #64748b;
}

.statement-editor {
  min-height: 340px;
  flex: 1 1 auto;
}

.statement-preview__content {
  border: 1px solid var(--color-border-default);
  border-radius: 12px;
  min-height: 340px;
  height: 100%;
  flex: 1 1 auto;
  padding: 16px;
  background: #ffffff;
  font-size: 15px;
  line-height: 1.6;
  color: #0f172a;
  overflow: auto;
}

.statement-preview__content :deep(p) {
  margin: 0 0 14px;
}

.statement-preview__content :deep(h1),
.statement-preview__content :deep(h2),
.statement-preview__content :deep(h3) {
  margin: 20px 0 10px;
  line-height: 1.25;
}

.statement-preview__content :deep(ul),
.statement-preview__content :deep(ol) {
  margin: 10px 0 14px 24px;
  padding-left: 10px;
}

.statement-preview__content :deep(ul li) {
  list-style: disc;
}

.statement-preview__content :deep(ol li) {
  list-style: decimal;
}

.statement-preview__content :deep(li + li) {
  margin-top: 4px;
}

.statement-preview__content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}

.statement-preview__content :deep(th),
.statement-preview__content :deep(td) {
  border: 1px solid #d4dce8;
  padding: 8px 10px;
}

.statement-preview__content :deep(th) {
  background: #f8fafc;
}

.statement-preview__content :deep(img) {
  display: block;
  max-width: 100%;
  height: auto;
  margin: 14px 0;
  border-radius: 10px;
  border: 1px solid #d4dce8;
}

.statement-preview__content :deep(pre) {
  margin: 14px 0;
  padding: 12px;
  border-radius: 10px;
  overflow-x: auto;
  background: #0f172a;
  color: #e2e8f0;
}

.statement-preview__content :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.statement-preview__content :deep(p code),
.statement-preview__content :deep(li code) {
  padding: 0.1em 0.35em;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.08);
}

.statement-preview__content :deep(blockquote) {
  margin: 14px 0;
  padding: 10px 14px;
  border-left: 4px solid #2563eb;
  background: #f8fafc;
}

.statement-preview__content :deep(.statement-color) {
  font-weight: 700;
}

.statement-stats {
  font-size: 13px;
  color: #64748b;
}

.form-checkbox {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.form-checkbox-input {
  width: 18px;
  height: 18px;
  margin: 0;
  cursor: pointer;
}

.form-checkbox-label {
  margin-left: 10px;
  font-size: 16px;
  color: var(--color-text-primary);
}

.file-uploads {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.file-upload-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-upload-label {
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text-primary);
}

.file-upload-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-upload-input {
  display: none;
}

.file-upload-button {
  padding: 10px 20px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  transition: background-color 0.2s ease;
  white-space: nowrap;
}

.file-upload-button:hover {
  background: var(--color-bg-muted);
}

.file-upload-name {
  font-size: 14px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-current {
  font-size: 13px;
  color: var(--color-text-muted);
}

.file-current a {
  color: var(--color-primary);
  text-decoration: none;
}

.file-current a:hover {
  text-decoration: underline;
}

.polygon-edit__actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-default);
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .polygon-edit__title {
    font-size: 24px;
  }

  .statement-image-controls {
    grid-template-columns: 1fr;
  }

  .statement-view-switch {
    display: grid;
    width: 100%;
    grid-template-columns: 1fr;
  }

  .statement-panels--split {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .polygon-edit__header {
    flex-direction: column;
    align-items: stretch;
  }

  .polygon-edit__header-actions {
    justify-content: flex-start;
  }

  .file-upload-controls {
    flex-wrap: wrap;
  }
}
</style>

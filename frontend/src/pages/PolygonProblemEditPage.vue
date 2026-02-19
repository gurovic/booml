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
            :disabled="publishing"
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
              <textarea
                id="problem-statement"
                v-model="formData.statement"
                class="form-textarea"
                :class="{ 'form-input--error': errors.statement }"
                placeholder="Введите условие задачи в формате Markdown"
                rows="12"
              ></textarea>
              <div class="form-help">Поддерживается Markdown разметка</div>
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
            :disabled="publishing"
          >
            {{ publishing ? 'Публикация...' : 'Опубликовать' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  getPolygonProblem, 
  updatePolygonProblem, 
  uploadPolygonProblemFiles,
  publishPolygonProblem 
} from '@/api/polygon'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiIdPill from '@/components/ui/UiIdPill.vue'

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

const hasSelectedFiles = computed(() => {
  return Object.values(selectedFiles).some(file => file !== null)
})

const clearMessages = () => {
  successMessage.value = null
  errorMessage.value = null
  errors.title = null
  errors.rating = null
  errors.statement = null
  errors.descriptor = {}
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

const saveProblem = async () => {
  clearMessages()
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
    
    successMessage.value = 'Задача успешно сохранена'
    setTimeout(() => { successMessage.value = null }, 3000)
  } catch (err) {
    console.error('Failed to save problem', err)
    
    // Handle structured error response
    if (err.response && err.response.data && err.response.data.errors) {
      const responseErrors = err.response.data.errors
      
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
  } finally {
    saving.value = false
  }
}

const handleFileSelect = (fieldName, event) => {
  const file = event.target.files[0]
  selectedFiles[fieldName] = file || null
}

const uploadFiles = async () => {
  clearMessages()
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
    
    successMessage.value = 'Файлы успешно загружены'
    setTimeout(() => { successMessage.value = null }, 3000)
  } catch (err) {
    console.error('Failed to upload files', err)
    errorMessage.value = 'Не удалось загрузить файлы. Проверьте формат файлов.'
  } finally {
    uploading.value = false
  }
}

const publishProblem = async () => {
  clearMessages()
  publishing.value = true
  
  try {
    const problemId = route.params.id
    const data = await publishPolygonProblem(problemId)
    
    problem.value.is_published = true
    successMessage.value = data.message || 'Задача успешно опубликована'
    setTimeout(() => { successMessage.value = null }, 5000)
  } catch (err) {
    console.error('Failed to publish problem', err)
    
    // Handle structured error response
    if (err.response && err.response.data && err.response.data.errors) {
      if (Array.isArray(err.response.data.errors)) {
        errorMessage.value = err.response.data.errors.join('; ')
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

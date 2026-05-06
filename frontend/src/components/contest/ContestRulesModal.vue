<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="contest-rules-overlay"
      @click.self="close"
    >
      <div class="contest-rules-dialog">
        <div class="contest-rules-dialog__header">
          <h2 class="contest-rules-dialog__title">Правила контеста</h2>
          <button
            type="button"
            class="contest-rules-dialog__close"
            aria-label="Закрыть"
            @click="close"
          >
            ×
          </button>
        </div>
        <div class="contest-rules-dialog__body">
          <div class="contest-rules-content">
            <ul>
              <li>Решайте задачи в течение отведённого времени контеста.</li>
              <li>Отправка решений выполняется через форму на странице каждой задачи.</li>
              <li>Запрещается списывание, использование посторонней помощи и обмен решениями.</li>
              <li>Результаты отображаются в таблице лидеров после проверки решений.</li>
              <li>При нарушении правил работа может быть аннулирована.</li>
            </ul>
          </div>
        </div>
        <div class="contest-rules-dialog__footer">
          <label class="contest-rules-dont-show">
            <input
              v-model="dontShowAgain"
              type="checkbox"
              class="contest-rules-dont-show__input"
            />
            <span class="contest-rules-dont-show__label">Не показывать больше</span>
          </label>
          <button
            type="button"
            class="button button--primary contest-rules-agree-btn"
            @click="onAgree"
          >
            Соглашаюсь
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { CONTEST_RULES_DONT_SHOW_KEY } from '@/utils/contestRules'

defineProps({
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const dontShowAgain = ref(false)

function close() {
  emit('update:modelValue', false)
}

function onAgree() {
  if (dontShowAgain.value) {
    try {
      localStorage.setItem(CONTEST_RULES_DONT_SHOW_KEY, '1')
    } catch {
      // localStorage может быть недоступен
    }
  }
  close()
}
</script>

<style scoped>
.contest-rules-overlay {
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

.contest-rules-dialog {
  background: var(--color-bg-card, #fff);
  border-radius: 16px;
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.contest-rules-dialog__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-default, #e0e0e0);
}

.contest-rules-dialog__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary, #000);
}

.contest-rules-dialog__close {
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

.contest-rules-dialog__close:hover {
  background: var(--color-bg-muted, #f5f5f5);
}

.contest-rules-dialog__body {
  padding: 24px;
  overflow-y: auto;
}

.contest-rules-content {
  font-size: 15px;
  line-height: 1.6;
  color: var(--color-text-primary, #000);
}

.contest-rules-content ul {
  margin: 0;
  padding-left: 1.25em;
}

.contest-rules-content li {
  margin-bottom: 0.5em;
}

.contest-rules-content li:last-child {
  margin-bottom: 0;
}

.contest-rules-dialog__footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-default, #e0e0e0);
  background: var(--color-bg-muted, #f9f9f9);
}

.contest-rules-dont-show {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-text-primary, #000);
  user-select: none;
}

.contest-rules-dont-show__input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.contest-rules-dont-show__label {
  white-space: nowrap;
}

.contest-rules-agree-btn {
  min-width: 140px;
}
</style>

<style scoped>
.contest-rules-overlay {
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

.contest-rules-dialog {
  background: var(--color-bg-card, #fff);
  border-radius: 16px;
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.contest-rules-dialog__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-default, #e0e0e0);
}

.contest-rules-dialog__title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-primary, #000);
}

.contest-rules-dialog__close {
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

.contest-rules-dialog__close:hover {
  background: var(--color-bg-muted, #f5f5f5);
}

.contest-rules-dialog__body {
  padding: 24px;
  overflow-y: auto;
}

.contest-rules-content {
  font-size: 15px;
  line-height: 1.6;
  color: var(--color-text-primary, #000);
}

.contest-rules-content ul {
  margin: 0;
  padding-left: 1.25em;
}

.contest-rules-content li {
  margin-bottom: 0.5em;
}

.contest-rules-content li:last-child {
  margin-bottom: 0;
}

.contest-rules-dialog__footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-default, #e0e0e0);
  background: var(--color-bg-muted, #f9f9f9);
}

.contest-rules-dont-show {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-text-primary, #000);
  user-select: none;
}

.contest-rules-dont-show__input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.contest-rules-dont-show__label {
  white-space: nowrap;
}

.contest-rules-agree-btn {
  min-width: 140px;
}
</style>

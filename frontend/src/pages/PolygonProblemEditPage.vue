<template>
  <div class="polygon-edit">
    <UiHeader />
    <div class="polygon-edit__content">
      <div class="polygon-edit__header">
        <h1 class="polygon-edit__title">Редактирование задачи</h1>
      </div>

      <div v-if="loading" class="polygon-edit__loading">
        Загрузка...
      </div>

      <div v-else-if="error" class="polygon-edit__error">
        {{ error }}
      </div>

      <div v-else class="polygon-edit__message">
        <p>Страница редактирования задачи в разработке.</p>
        <p>Пока используйте старую версию по адресу: <a :href="`/polygon/problem/${problemId}/`">/polygon/problem/{{ problemId }}/</a></p>
        <button 
          class="button button--primary" 
          @click="goToOldEdit"
        >
          Открыть старую версию редактора
        </button>
        <button 
          class="button button--secondary" 
          @click="goBack"
        >
          Вернуться к списку задач
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import UiHeader from '@/components/ui/UiHeader.vue'

const router = useRouter()
const route = useRoute()
const problemId = ref(route.params.id)
const loading = ref(false)
const error = ref(null)

const goToOldEdit = () => {
  window.location.href = `/polygon/problem/${problemId.value}/`
}

const goBack = () => {
  router.push('/polygon')
}

onMounted(() => {
  // In the future, load problem data here
})
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
  margin-bottom: 32px;
}

.polygon-edit__title {
  font-family: var(--font-title);
  font-size: 36px;
  font-weight: 400;
  color: var(--color-title-text);
  margin: 0;
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

.polygon-edit__message {
  background: var(--color-bg-card);
  border-radius: 12px;
  padding: 32px;
  border: 1px solid var(--color-border-default);
}

.polygon-edit__message p {
  margin: 0 0 16px;
  font-size: 16px;
}

.polygon-edit__message a {
  color: var(--color-primary);
  text-decoration: underline;
}

.polygon-edit__message button {
  margin-right: 12px;
  margin-top: 8px;
}

@media (max-width: 768px) {
  .polygon-edit__title {
    font-size: 28px;
  }
}
</style>

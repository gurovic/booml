<template>
  <div class="auth-required-page">
    <UiHeader />
    <main class="auth-required-page__content container">
      <section class="auth-required-card">
        <h1 class="auth-required-card__title">Требуется авторизация</h1>
        <p class="auth-required-card__text">
          Этот раздел доступен только зарегистрированным пользователям.
        </p>
        <div class="auth-required-card__actions">
          <button
            type="button"
            class="button button--primary"
            @click="goToLogin"
          >
            Войти
          </button>
          <button
            type="button"
            class="button button--secondary"
            @click="goToRegister"
          >
            Регистрация
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UiHeader from '@/components/ui/UiHeader.vue'
import { resolveRedirectFromQuery } from '@/utils/redirect'

const route = useRoute()
const router = useRouter()

const redirectPath = computed(() => {
  return resolveRedirectFromQuery(route.query)
})

const goToLogin = () => {
  router.push({ name: 'login', query: { redirect: redirectPath.value } })
}

const goToRegister = () => {
  router.push({ name: 'register', query: { redirect: redirectPath.value } })
}
</script>

<style scoped>
.auth-required-page {
  min-height: 100vh;
  background: var(--color-bg-default);
}

.auth-required-page__content {
  padding-top: 48px;
  padding-bottom: 48px;
}

.auth-required-card {
  max-width: 640px;
  margin: 0 auto;
  padding: 32px;
  border-radius: 16px;
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-card);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.auth-required-card__title {
  margin: 0 0 12px;
  font-size: 32px;
  color: var(--color-title-text);
}

.auth-required-card__text {
  margin: 0;
  font-size: 16px;
  color: var(--color-text-secondary);
}

.auth-required-card__actions {
  display: flex;
  gap: 10px;
  margin-top: 24px;
  flex-wrap: wrap;
}
</style>

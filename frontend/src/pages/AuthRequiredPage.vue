<template>
  <div class="auth-required-page">
    <UiHeader />
    <main class="auth-required-page__content container">
      <section class="auth-required-card">
        <h1 class="auth-required-card__title">{{ reasonCopy.title }}</h1>
        <p class="auth-required-card__text">
          {{ reasonCopy.text }}
        </p>
        <div class="auth-required-card__actions">
          <button
            type="button"
            class="button button--primary"
            @click="goToRegister"
          >
            Зарегистрироваться
          </button>
          <button
            type="button"
            class="button button--secondary"
            @click="goToLogin"
          >
            Войти
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
import {
  buildAuthRedirect,
  resolveAuthReasonFromQuery,
  resolveRedirectFromQuery,
} from '@/utils/redirect'

const route = useRoute()
const router = useRouter()

const REASON_COPY = {
  submit: {
    title: 'Чтобы отправить решение, нужен аккаунт',
    text: 'После регистрации вы сможете отправлять решения, получать оценку и видеть результаты проверок.',
  },
  notebook: {
    title: 'Чтобы открыть тетрадь, нужен аккаунт',
    text: 'С аккаунтом вы получите персональную тетрадь, где можно запускать код и сохранять прогресс.',
  },
  submissions: {
    title: 'Чтобы смотреть свои посылки, нужен аккаунт',
    text: 'В личном кабинете доступны история отправок, статусы проверок и результаты по задачам.',
  },
  leaderboard: {
    title: 'Чтобы открыть лидерборд, нужен аккаунт',
    text: 'После входа вы сможете видеть личный прогресс и сравнивать результаты в рейтинге.',
  },
  generic: {
    title: 'Для этого действия нужен аккаунт',
    text: 'Войдите или зарегистрируйтесь, чтобы продолжить работу с учебными функциями платформы.',
  },
}

const reason = computed(() => resolveAuthReasonFromQuery(route.query))
const redirectPath = computed(() => resolveRedirectFromQuery(route.query))
const reasonCopy = computed(() => REASON_COPY[reason.value] || REASON_COPY.generic)
const authQuery = computed(() => (
  buildAuthRedirect({
    redirect: redirectPath.value,
    reason: reason.value,
  })
))

const goToLogin = () => {
  router.push({ name: 'login', query: authQuery.value })
}

const goToRegister = () => {
  router.push({ name: 'register', query: authQuery.value })
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
  max-width: 680px;
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
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.auth-required-card__actions {
  display: flex;
  gap: 10px;
  margin-top: 24px;
  flex-wrap: wrap;
}
</style>

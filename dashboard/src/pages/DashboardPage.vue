<template>
  <div class="dashboard">
    <header class="dashboard__header">
      <span class="dashboard__logo">BOOML</span>
      <nav class="dashboard__nav">
        <a :href="mainAppUrl" class="dashboard__nav-link">← На главную</a>
      </nav>
    </header>

    <div class="dashboard__content">
      <div v-if="loading" class="dashboard__state">Загрузка...</div>

      <div v-else-if="error" class="dashboard__state dashboard__state--error">
        {{ error }}
      </div>

      <template v-else>
        <h1 class="dashboard__title">Dashboard</h1>
        <p class="dashboard__description">Панель управления платформой. Доступна только администратору.</p>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { checkAuth } from '../api/user'

const mainAppUrl = process.env.VUE_APP_MAIN_APP_URL || 'http://localhost:8101'

const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const res = await checkAuth()
    if (!res?.is_authenticated) {
      window.location.href = `${mainAppUrl}/login`
      return
    }
    if (res?.is_platform_admin !== true) {
      window.location.href = mainAppUrl
      return
    }
  } catch (err) {
    error.value = 'Не удалось проверить авторизацию.'
  } finally {
    loading.value = false
  }
})
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f5f5;
  color: #222;
}
</style>

<style scoped>
.dashboard {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.dashboard__header {
  height: 64px;
  background: #2c3e50;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 24px;
}

.dashboard__logo {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.dashboard__nav {
  margin-left: auto;
}

.dashboard__nav-link {
  color: #fff;
  text-decoration: none;
  font-size: 15px;
  opacity: 0.85;
  transition: opacity 0.2s;
}

.dashboard__nav-link:hover {
  opacity: 1;
}

.dashboard__content {
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 24px;
  width: 100%;
}

.dashboard__title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 12px;
}

.dashboard__description {
  font-size: 16px;
  color: #555;
}

.dashboard__state {
  font-size: 16px;
  color: #555;
}

.dashboard__state--error {
  color: #c0392b;
}
</style>

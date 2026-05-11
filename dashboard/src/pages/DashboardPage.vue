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

        <!-- Errors log section -->
        <section class="log-section">
          <div class="log-section__header">
            <h2 class="log-section__title">Журнал ошибок (errors.csv)</h2>
            <span class="log-section__count">{{ errorLog.length }} записей</span>
          </div>
          <div v-if="errorLog.length === 0" class="log-section__empty">Ошибок не найдено</div>
          <div v-else class="log-table-wrap">
            <table class="log-table">
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Уровень</th>
                  <th>Logger</th>
                  <th>Модуль</th>
                  <th>Путь</th>
                  <th>Строка</th>
                  <th>Сообщение</th>
                  <th>Исключение</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in errorLog" :key="idx" :class="levelClass(row.level)">
                  <td class="log-table__ts">{{ row.timestamp }}</td>
                  <td><span class="log-badge" :class="levelClass(row.level)">{{ row.level }}</span></td>
                  <td class="log-table__logger">{{ row.logger }}</td>
                  <td>{{ row.module }}</td>
                  <td class="log-table__path">{{ row.pathname }}</td>
                  <td>{{ row.lineno }}</td>
                  <td class="log-table__msg">{{ row.message }}</td>
                  <td class="log-table__exc"><pre v-if="row.exception">{{ row.exception }}</pre></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- App log section -->
        <section class="log-section">
          <div class="log-section__header">
            <h2 class="log-section__title">Журнал приложения (app.log)</h2>
            <span class="log-section__count">{{ appLog.length }} записей</span>
          </div>
          <div v-if="appLog.length === 0" class="log-section__empty">Записей не найдено</div>
          <div v-else class="log-table-wrap">
            <table class="log-table">
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Уровень</th>
                  <th>Logger</th>
                  <th>Сообщение</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in appLog" :key="idx" :class="levelClass(row.level)">
                  <td class="log-table__ts">{{ row.timestamp }}</td>
                  <td><span class="log-badge" :class="levelClass(row.level)">{{ row.level }}</span></td>
                  <td class="log-table__logger">{{ row.logger }}</td>
                  <td class="log-table__msg">{{ row.message }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { checkAuth } from '../api/user'
import { getLogs } from '../api/logs'

const mainAppUrl = process.env.VUE_APP_MAIN_APP_URL || 'http://localhost:8101'

const loading = ref(true)
const error = ref('')
const appLog = ref([])
const errorLog = ref([])

function levelClass(level) {
  const l = (level || '').toUpperCase()
  if (l === 'ERROR' || l === 'CRITICAL') return 'level--error'
  if (l === 'WARNING' || l === 'WARN') return 'level--warning'
  if (l === 'INFO') return 'level--info'
  return 'level--debug'
}

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
    loading.value = false
    return
  }

  try {
    const logs = await getLogs()
    appLog.value = logs.app_log || []
    errorLog.value = logs.error_log || []
  } catch (err) {
    error.value = 'Не удалось загрузить журналы логов.'
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
  max-width: 1280px;
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
  margin-bottom: 32px;
}

.dashboard__state {
  font-size: 16px;
  color: #555;
}

.dashboard__state--error {
  color: #c0392b;
}

/* Log sections */
.log-section {
  margin-bottom: 48px;
}

.log-section__header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
}

.log-section__title {
  font-size: 20px;
  font-weight: 600;
}

.log-section__count {
  font-size: 13px;
  color: #888;
}

.log-section__empty {
  color: #aaa;
  font-size: 14px;
  padding: 12px 0;
}

.log-table-wrap {
  overflow-x: auto;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fff;
}

.log-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}

.log-table th {
  background: #f0f0f0;
  text-align: left;
  padding: 8px 10px;
  font-weight: 600;
  border-bottom: 1px solid #ddd;
  white-space: nowrap;
}

.log-table td {
  padding: 6px 10px;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: top;
}

.log-table tr:last-child td {
  border-bottom: none;
}

.log-table tr.level--error {
  background: #fff5f5;
}

.log-table tr.level--warning {
  background: #fffbf0;
}

.log-table__ts {
  white-space: nowrap;
  color: #666;
}

.log-table__logger {
  white-space: nowrap;
  color: #2980b9;
}

.log-table__msg {
  overflow-wrap: break-word;
  word-break: break-word;
  max-width: 400px;
}

.log-table__path {
  overflow-wrap: break-word;
  word-break: break-word;
  max-width: 200px;
  font-size: 11px;
  color: #888;
}

.log-table__exc pre {
  white-space: pre-wrap;
  overflow-wrap: break-word;
  word-break: break-word;
  font-size: 11px;
  color: #c0392b;
  max-width: 300px;
}

/* Level badges */
.log-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.log-badge.level--error {
  background: #fadbd8;
  color: #c0392b;
}

.log-badge.level--warning {
  background: #fdebd0;
  color: #d68910;
}

.log-badge.level--info {
  background: #d6eaf8;
  color: #1a5276;
}

.log-badge.level--debug {
  background: #e8f8f5;
  color: #1e8449;
}
</style>

<template>
  <div class="dashboard">
    <div class="dashboard__glow dashboard__glow--left"></div>
    <div class="dashboard__glow dashboard__glow--right"></div>

    <header class="dashboard__header">
      <div class="dashboard__header-inner">
        <a href="/" class="dashboard__brand">
          <img :src="projectLogo" alt="Booml logo" class="dashboard__brand-logo" />
          <span class="dashboard__brand-title">BOOML</span>
        </a>

        <div class="dashboard__header-actions">
          <div v-if="!loading && !error" class="dashboard__range-controls">
            <button
              v-for="range in ranges"
              :key="range.key"
              type="button"
              class="dashboard__range-button"
              :class="{ 'dashboard__range-button--active': activeRange === range.key }"
              @click="activeRange = range.key"
            >
              {{ range.label }}
            </button>
          </div>
          <a :href="mainAppUrl" class="dashboard__header-link">Основной сервис</a>
        </div>
      </div>
    </header>

    <main class="dashboard__main">
      <div v-if="loading" class="dashboard__state-card">
        <div class="dashboard__state-title">Собираем метрики</div>
        <div class="dashboard__state-text">Проверяем авторизацию и загружаем статистику запросов backend.</div>
      </div>

        <div v-else-if="error" class="dashboard__state-card dashboard__state-card--error">
          <div class="dashboard__state-title">Не удалось открыть дашборд</div>
          <div class="dashboard__state-text">{{ error }}</div>
        </div>

      <template v-else>
        <div v-if="refreshError" class="dashboard__inline-alert">
          {{ refreshError }}
        </div>

        <section class="dashboard__stats">
          <article
            v-for="card in statCards"
            :key="card.key"
            class="stat-card"
            :class="`stat-card--${card.tone}`"
          >
            <div class="stat-card__top">
              <div>
                <div class="stat-card__title">{{ card.title }}</div>
                <div class="stat-card__value">{{ card.value }}</div>
                <div v-if="card.subtitle" class="stat-card__subtitle">{{ card.subtitle }}</div>
              </div>
              <div class="stat-card__icon">
                <svg v-if="card.icon === 'server'" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="4" y="5" width="16" height="6" rx="2" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="2"/>
                  <rect x="4" y="13" width="16" height="6" rx="2" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="2"/>
                  <path d="M8 8h.01M8 16h.01M12 8h4M12 16h4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="2"/>
                </svg>
                <svg v-else-if="card.icon === 'traffic'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 16h4l2-8 4 10 2-6h4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                <svg v-else-if="card.icon === 'chip'" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="7" y="7" width="10" height="10" rx="2" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="2"/>
                  <path d="M9 1v4M15 1v4M9 19v4M15 19v4M1 9h4M1 15h4M19 9h4M19 15h4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="2"/>
                </svg>
                <svg v-else-if="card.icon === 'user'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4Zm-7 8a7 7 0 0 1 14 0" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                <svg v-else-if="card.icon === 'users'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M9 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3Zm8 0a3 3 0 1 0-3-3 3 3 0 0 0 3 3ZM3 19a6 6 0 0 1 12 0M14 19a5 5 0 0 1 7 0" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                <svg v-else-if="card.icon === 'pulse'" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3 12h4l2-5 4 10 2-5h6" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 8v5m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/>
                </svg>
              </div>
            </div>

            <div class="stat-card__footer">
              <div
                class="stat-card__delta"
                :class="{
                  'stat-card__delta--positive': card.deltaTone === 'positive',
                  'stat-card__delta--negative': card.deltaTone === 'negative',
                }"
              >
                {{ card.delta }}
              </div>
              <VChart
                class="stat-card__sparkline-chart"
                :option="card.sparkOption"
                autoresize
                aria-hidden="true"
              />
            </div>
          </article>
        </section>

        <section class="panel">
          <div class="panel__header">
            <div>
              <h2 class="panel__title">Активные сессии</h2>
              <p class="panel__subtitle">{{ activeSessionsSubtitle }}</p>
            </div>
          </div>

          <div class="chart-card">
            <div class="chart-card__plot">
              <VChart
                class="chart-card__chart"
                :option="activeSessionsChartOption"
                autoresize
              />
            </div>
          </div>
        </section>

        <div class="dashboard__insight-grid">
          <section class="panel panel--compact">
            <div class="panel__header panel__header--compact">
              <div>
                <h2 class="panel__title panel__title--compact">Запросы к серверу</h2>
                <p class="panel__subtitle panel__subtitle--compact">Ping и API запросы</p>
              </div>
            </div>

            <div class="chart-card chart-card--compact">
              <div class="chart-card__plot chart-card__plot--compact">
                <VChart
                  class="chart-card__chart chart-card__chart--compact"
                  :option="mainChartOption"
                  autoresize
                />
              </div>

              <div class="chart-card__legend">
                <div class="chart-card__legend-item">
                  <span class="chart-card__legend-swatch chart-card__legend-swatch--ping"></span>
                  Ping
                </div>
                <div class="chart-card__legend-item">
                  <span class="chart-card__legend-swatch chart-card__legend-swatch--user"></span>
                  Пользовательские обращения
                </div>
              </div>
            </div>

            <div class="panel__summary panel__summary--compact">
              <div class="summary-metric">
                <div class="summary-metric__label">Средняя задержка</div>
                <div class="summary-metric__value">{{ averageDurationLabel }}</div>
              </div>
              <div class="summary-metric">
                <div class="summary-metric__label">Частота 5xx</div>
                <div class="summary-metric__value">{{ errorRateLabel }}</div>
              </div>
            </div>
          </section>

          <section class="panel panel--compact resource-panel">
            <div class="panel__header panel__header--compact">
              <div>
                <h2 class="panel__title panel__title--compact">Использование ресурсов</h2>
                <p class="panel__subtitle panel__subtitle--compact">CPU, GPU и память</p>
              </div>
            </div>

            <div class="resource-panel__rings">
              <div class="resource-ring" :style="resourceRingStyle(resourceMetrics.cpu_percent, 'violet')">
                <div class="resource-ring__inner">
                  <div class="resource-ring__value">{{ formatPercentValue(resourceMetrics.cpu_percent) }}</div>
                  <div class="resource-ring__label">CPU</div>
                </div>
              </div>
              <div class="resource-ring" :style="resourceRingStyle(resourceMetrics.gpu_percent, 'blue')">
                <div class="resource-ring__inner">
                  <div class="resource-ring__value">{{ formatPercentValue(resourceMetrics.gpu_percent) }}</div>
                  <div class="resource-ring__label">GPU</div>
                </div>
              </div>
            </div>

            <div class="panel__summary resource-panel__summary">
              <div class="summary-metric">
                <div class="summary-metric__label">RAM</div>
                <div class="summary-metric__value summary-metric__value--small">
                  {{ formatGigabytes(resourceMetrics.ram_used_gb) }} / {{ formatGigabytes(resourceMetrics.ram_total_gb) }}
                </div>
              </div>
              <div class="summary-metric">
                <div class="summary-metric__label">VRAM</div>
                <div class="summary-metric__value summary-metric__value--small">
                  {{ formatGigabytes(resourceMetrics.vram_used_gb) }} / {{ formatGigabytes(resourceMetrics.vram_total_gb) }}
                </div>
              </div>
              <div class="summary-metric">
                <div class="summary-metric__label">Workers</div>
                <div class="summary-metric__value summary-metric__value--small">
                  {{ formatCount(resourceMetrics.workers_busy) }} / {{ formatCount(resourceMetrics.workers_total) }}
                </div>
              </div>
            </div>
          </section>

          <section class="panel panel--compact queue-panel">
            <div class="panel__header panel__header--compact">
              <div>
                <h2 class="panel__title panel__title--compact">Очередь решений</h2>
                <p class="panel__subtitle panel__subtitle--compact">История отправок на проверку</p>
              </div>
            </div>

            <div class="chart-card chart-card--compact">
              <div class="chart-card__plot chart-card__plot--compact">
                <VChart
                  class="chart-card__chart chart-card__chart--compact"
                  :option="queueChartOption"
                  autoresize
                />
              </div>
            </div>

            <div class="panel__summary queue-panel__summary">
              <div class="summary-metric">
                <div class="summary-metric__label">В очереди</div>
                <div class="summary-metric__value summary-metric__value--small">{{ formatCount(queueMetrics.pending) }}</div>
              </div>
              <div class="summary-metric">
                <div class="summary-metric__label">Выполняется</div>
                <div class="summary-metric__value summary-metric__value--small">{{ formatCount(queueMetrics.running) }}</div>
              </div>
              <div class="summary-metric">
                <div class="summary-metric__label">Ср. ожидание</div>
                <div class="summary-metric__value summary-metric__value--small">{{ formatDuration(queueMetrics.avg_wait_seconds) }}</div>
              </div>
              <div class="summary-metric">
                <div class="summary-metric__label">Макс. ожидание</div>
                <div class="summary-metric__value summary-metric__value--small">{{ formatDuration(queueMetrics.max_wait_seconds) }}</div>
              </div>
            </div>
          </section>
        </div>

        <section class="panel sessions-panel">
          <div class="panel__header">
            <div>
              <h2 class="panel__title panel__title--compact">Очередь выполнения ноутбуков</h2>
              <p class="panel__subtitle panel__subtitle--compact">Статус runtime-сессий по пользователям</p>
            </div>
            <div class="sessions-panel__updated">Обновлено: {{ sessionsUpdatedAtLabel }}</div>
          </div>

          <div class="sessions-table">
            <div class="sessions-table__head">
              <div>Ноутбук</div>
              <div>Пользователь</div>
              <div>Ячейки</div>
              <div>Тип выполнения</div>
              <div>GPU</div>
              <div>Статус</div>
              <div>Время ожидания</div>
            </div>
            <div v-if="sessionRows.length === 0" class="sessions-table__empty">
              Нет активных runtime-сессий
            </div>
            <template v-else>
              <div
                v-for="session in sessionRows"
                :key="session.session_id"
                class="sessions-table__row"
              >
                <div class="sessions-table__notebook">
                  <span class="sessions-table__avatar">{{ session.notebook_title.slice(0, 1).toUpperCase() }}</span>
                  <span>{{ session.notebook_title }}</span>
                </div>
                <div>{{ session.user }}</div>
                <div><span class="sessions-table__pill sessions-table__pill--violet">{{ formatCount(session.cells) }} ячеек</span></div>
                <div>{{ session.execution_type }}</div>
                <div>
                  <span class="sessions-table__pill" :class="session.gpu ? 'sessions-table__pill--blue' : 'sessions-table__pill--gray'">
                    {{ session.gpu ? 'Да' : 'Нет' }}
                  </span>
                </div>
                <div><span class="sessions-table__pill sessions-table__pill--green">{{ formatSessionStatus(session.status) }}</span></div>
                <div>{{ formatDuration(session.wait_seconds) }}</div>
              </div>
            </template>
          </div>

          <div class="sessions-panel__footer">
            Всего в работе: <strong>{{ formatCount(sessionsSummary.total_notebooks) }} ноутбуков · {{ formatCount(sessionsSummary.total_cells) }} ячеек</strong>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, ToolboxComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import projectLogo from '@/assets/logo.png'

import { getRequestMetrics, pingServer } from '../api/dashboard'
import { checkAuth } from '../api/user'

use([BarChart, CanvasRenderer, GridComponent, LineChart, ToolboxComponent, TooltipComponent])

const mainAppUrl = process.env.VUE_APP_MAIN_APP_URL || 'http://localhost:8101'

const ranges = [
  { key: '24h', label: '24h' },
  { key: '7d', label: '7d' },
  { key: '30d', label: '30d' },
]

const sparklinePalette = {
  violet: {
    line: '#735cf7',
    areaStart: 'rgba(115, 92, 247, 0.24)',
    areaEnd: 'rgba(115, 92, 247, 0.04)',
  },
  blue: {
    line: '#59b6df',
    areaStart: 'rgba(89, 182, 223, 0.24)',
    areaEnd: 'rgba(89, 182, 223, 0.04)',
  },
  mint: {
    line: '#4ac074',
    areaStart: 'rgba(74, 192, 116, 0.24)',
    areaEnd: 'rgba(74, 192, 116, 0.04)',
  },
  amber: {
    line: '#f78128',
    areaStart: 'rgba(247, 129, 40, 0.24)',
    areaEnd: 'rgba(247, 129, 40, 0.04)',
  },
}

const loading = ref(true)
const error = ref('')
const refreshError = ref('')
const activeRange = ref('24h')
const metricsPayload = ref(null)

let refreshTimer = null

const activeRangeData = computed(() => metricsPayload.value?.ranges?.[activeRange.value] || null)
const cards = computed(() => activeRangeData.value?.cards || null)
const points = computed(() => activeRangeData.value?.points || [])
const summary = computed(() => activeRangeData.value?.summary || null)
const queueMetrics = computed(() => activeRangeData.value?.queue || {
  pending: 0,
  running: 0,
  avg_wait_seconds: 0,
  max_wait_seconds: 0,
  points: [],
})
const resourceMetrics = computed(() => metricsPayload.value?.resources || {
  cpu_percent: 0,
  gpu_percent: 0,
  ram_used_gb: 0,
  ram_total_gb: 0,
  vram_used_gb: 0,
  vram_total_gb: 0,
  workers_busy: 0,
  workers_total: 0,
})
const sessionsSummary = computed(() => metricsPayload.value?.sessions || {
  updated_at: '',
  rows: [],
  total_notebooks: 0,
  total_cells: 0,
})
const sessionRows = computed(() => (sessionsSummary.value.rows || []).map((row) => ({
  ...row,
  notebook_title: row.notebook_title || 'notebook.ipynb',
  user: row.user || 'unknown',
})))
const sessionsUpdatedAtLabel = computed(() => (
  sessionsSummary.value.updated_at ? formatDateTime(sessionsSummary.value.updated_at) : 'н/д'
))

const averageDurationLabel = computed(() => formatMilliseconds(summary.value?.avg_duration_ms))
const errorRateLabel = computed(() => `${formatNumber(summary.value?.error_rate ?? 0)}%`)

const activeSessionsSubtitle = computed(() => {
  if (activeRange.value === '24h') {
    return 'Динамика за последние 24 часа'
  }
  if (activeRange.value === '7d') {
    return 'Динамика за последние 7 дней'
  }
  return 'Динамика за последние 30 дней'
})

const mainChartOption = computed(() => buildMainChartOption(points.value, activeRange.value))
const queueChartOption = computed(() => buildQueueChartOption(queueMetrics.value.points || [], activeRange.value))
const activeSessionsChartOption = computed(() => buildActiveSessionsChartOption(
  points.value,
  cards.value?.active_sessions?.points || [],
  activeRange.value,
))

const statCards = computed(() => {
  const cardMetrics = cards.value
  if (!cardMetrics) return []

  return [
    {
      key: 'active-sessions',
      title: 'Активные сессии',
      value: formatCount(cardMetrics.active_sessions?.value),
      delta: formatTrend(cardMetrics.active_sessions?.trend_percent, activeRange.value),
      deltaTone: trendTone(cardMetrics.active_sessions?.trend_percent),
      tone: 'violet',
      icon: 'pulse',
      sparkOption: buildSparklineOption(cardMetrics.active_sessions?.points || [], 'violet'),
    },
    {
      key: 'server-requests',
      title: 'Запросы к серверу',
      value: formatCount(cardMetrics.server_requests?.value),
      delta: formatTrend(cardMetrics.server_requests?.trend_percent, activeRange.value),
      deltaTone: trendTone(cardMetrics.server_requests?.trend_percent),
      tone: 'blue',
      icon: 'server',
      sparkOption: buildSparklineOption(cardMetrics.server_requests?.points || [], 'blue'),
    },
    {
      key: 'cpu-gpu-load',
      title: 'Нагрузка CPU/GPU',
      value: formatCpuGpuValue(cardMetrics.cpu_gpu_load?.cpu_percent, cardMetrics.cpu_gpu_load?.gpu_percent),
      delta: formatTrend(cardMetrics.cpu_gpu_load?.trend_percent, activeRange.value),
      deltaTone: trendTone(cardMetrics.cpu_gpu_load?.trend_percent),
      tone: 'amber',
      icon: 'chip',
      sparkOption: buildSparklineOption(cardMetrics.cpu_gpu_load?.points || [], 'amber'),
    },
    {
      key: 'online-users',
      title: 'Онлайн пользователи',
      value: formatCount(cardMetrics.online_users?.value),
      subtitle: formatOnlineUsersByRole(cardMetrics.online_users?.by_role),
      delta: formatTrend(cardMetrics.online_users?.trend_percent, activeRange.value),
      deltaTone: trendTone(cardMetrics.online_users?.trend_percent),
      tone: 'mint',
      icon: 'users',
      sparkOption: buildSparklineOption(cardMetrics.online_users?.points || [], 'mint'),
    },
  ]
})

function resourceRingStyle(value, tone) {
  const palette = {
    violet: '#735cf7',
    blue: '#59b6df',
  }
  const numeric = Math.max(0, Math.min(100, Number(value || 0)))
  return {
    '--resource-angle': `${numeric * 3.6}deg`,
    '--resource-color': palette[tone] || palette.violet,
  }
}

onMounted(async () => {
  try {
    const auth = await checkAuth()
    if (!auth?.is_authenticated) {
      window.location.href = `${mainAppUrl}/login`
      return
    }
    if (auth?.is_platform_admin !== true) {
      window.location.href = mainAppUrl
      return
    }

    await refreshMetrics({ initial: true })
    refreshTimer = window.setInterval(() => {
      refreshMetrics()
    }, 60000)
  } catch (_) {
    error.value = 'Не удалось проверить авторизацию.'
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
})

async function refreshMetrics({ initial = false } = {}) {
  try {
    refreshError.value = ''

    await pingServer()

    metricsPayload.value = await getRequestMetrics()
  } catch (err) {
    const message = normalizeError(err)
    if (initial) {
      error.value = message
    } else {
      refreshError.value = `Последнее обновление не удалось: ${message}`
    }
  }
}

function normalizeError(err) {
  if (!err?.message) {
    return 'Не удалось получить метрики.'
  }

  if (err.message === 'HTTP 403') {
    return 'Доступ к метрикам есть только у администратора платформы.'
  }

  if (err.message === 'HTTP 503') {
    return 'Prometheus сейчас не отвечает. Проверь сервис мониторинга.'
  }

  return err.message
}

function formatCount(value) {
  const numeric = Number(value || 0)
  if (numeric >= 1000000) {
    return `${trimZeros((numeric / 1000000).toFixed(1))}M`
  }
  if (numeric >= 1000) {
    return `${trimZeros((numeric / 1000).toFixed(1))}K`
  }
  return `${Math.round(numeric)}`
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('ru-RU', {
    minimumFractionDigits: Number.isInteger(Number(value || 0)) ? 0 : 1,
    maximumFractionDigits: 1,
  })
}

function formatOnlineUsersByRole(byRole) {
  if (!byRole) {
    return ''
  }
  const students = formatCount(byRole.students)
  const teachers = formatCount(byRole.teachers)
  const gpuUsers = formatCount(byRole.gpu_access)
  return `Ученики: ${students}, Учителя: ${teachers}, GPU: ${gpuUsers}`
}

function formatMilliseconds(value) {
  if (value == null) return '0 ms'
  const rounded = Math.round(Number(value))
  return `${rounded} ms`
}

function formatPercentValue(value) {
  return `${Math.round(Number(value || 0))}%`
}

function formatGigabytes(value) {
  const numeric = Number(value || 0)
  if (Number.isInteger(numeric)) {
    return `${numeric} GB`
  }
  return `${trimZeros(numeric.toFixed(1))} GB`
}

function formatCpuGpuValue(cpuValue, gpuValue) {
  return `${formatPercentValue(cpuValue)} / ${formatPercentValue(gpuValue)}`
}

function trimZeros(value) {
  return value.replace(/\.0$/, '')
}

function formatTrend(value, rangeKey) {
  if (value == null) {
    return 'Недостаточно данных для сравнения'
  }
  const sign = value > 0 ? '+' : ''
  return `${sign}${formatNumber(value)}% ${formatTrendPeriod(rangeKey)}`
}

function trendTone(value) {
  if (value == null) return null
  return value < 0 ? 'negative' : 'positive'
}

function formatTrendPeriod(rangeKey) {
  if (rangeKey === '24h') {
    return 'к предыдущим 24 ч'
  }
  if (rangeKey === '7d') {
    return 'к предыдущим 7 дн'
  }
  if (rangeKey === '30d') {
    return 'к предыдущим 30 дн'
  }
  return 'к предыдущему периоду'
}

function formatDuration(seconds) {
  const totalSeconds = Math.max(0, Math.round(Number(seconds || 0)))
  if (totalSeconds < 60) {
    return `${totalSeconds}s`
  }

  const minutes = Math.floor(totalSeconds / 60)
  const restSeconds = totalSeconds % 60
  if (minutes < 60) {
    return restSeconds ? `${minutes}m ${restSeconds}s` : `${minutes}m`
  }

  const hours = Math.floor(minutes / 60)
  const restMinutes = minutes % 60
  if (hours >= 24) {
    const days = Math.floor(hours / 24)
    const restHours = hours % 24
    return restHours ? `${days}d ${restHours}h` : `${days}d`
  }
  return restMinutes ? `${hours}h ${restMinutes}m` : `${hours}h`
}

function formatSessionStatus(status) {
  if (status === 'running') {
    return 'Выполняется'
  }
  if (status === 'queued') {
    return 'В очереди'
  }
  return status || 'н/д'
}

function formatDateTime(value) {
  if (!value) return 'н/д'
  return new Intl.DateTimeFormat('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: 'short',
  }).format(new Date(value))
}

function buildSparklineOption(values, tone) {
  const palette = sparklinePalette[tone] || sparklinePalette.violet
  const numericValues = values.map((value) => Number(value || 0))

  return {
    animation: false,
    grid: {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
    },
    xAxis: {
      type: 'category',
      data: numericValues.map((_, index) => index),
      show: false,
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      show: false,
      min: 0,
    },
    tooltip: {
      show: false,
    },
    series: [
      {
        type: 'line',
        data: numericValues,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: palette.line,
          width: 3,
          cap: 'round',
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: palette.areaStart },
              { offset: 1, color: palette.areaEnd },
            ],
          },
        },
      },
    ],
  }
}

function buildMainChartOption(sourcePoints, rangeKey) {
  const xAxisData = sourcePoints.map((point) => formatAxisLabel(point.timestamp, rangeKey))
  const pingValues = sourcePoints.map((point) => Number(point.ping_requests || 0))
  const userValues = sourcePoints.map((point) => Number(point.user_requests || 0))
  const labelInterval = Math.max(0, Math.ceil(Math.max(sourcePoints.length, 1) / 8) - 1)

  return {
    animationDuration: 500,
    textStyle: {
      fontFamily: 'Manrope, Avenir Next, Segoe UI, sans-serif',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(34, 42, 72, 0.94)',
      borderWidth: 0,
      textStyle: {
        color: '#ffffff',
      },
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: 'rgba(115, 92, 247, 0.28)',
          width: 1,
        },
      },
      formatter(params) {
        const point = sourcePoints[params?.[0]?.dataIndex] || null
        const title = point ? formatTooltipLabel(point.timestamp, rangeKey) : ''
        const rows = params
          .map((item) => `${item.marker}${item.seriesName}: ${formatCount(item.value)}`)
          .join('<br/>')
        return `${title}<br/>${rows}`
      },
    },
    toolbox: {
      show: true,
      top: 4,
      right: 6,
      itemSize: 16,
      iconStyle: {
        borderColor: '#5f6c92',
      },
      emphasis: {
        iconStyle: {
          borderColor: '#344362',
        },
      },
      feature: {
        restore: {
          title: 'Сбросить',
        },
        saveAsImage: {
          title: 'Сохранить',
          name: `booml-server-requests-${rangeKey}`,
          pixelRatio: 2,
          backgroundColor: '#ffffff',
        },
      },
    },
    grid: {
      top: 28,
      right: 14,
      bottom: 30,
      left: 52,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: '#8f9bc0',
          width: 1.5,
        },
      },
      axisLabel: {
        color: '#7c87ab',
        fontSize: 12,
        fontWeight: 600,
        margin: 16,
        interval: labelInterval,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(177, 189, 228, 0.38)',
          type: 'dashed',
        },
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: '#8f9bc0',
          width: 1.5,
        },
      },
      axisLabel: {
        color: '#7c87ab',
        fontSize: 12,
        fontWeight: 600,
        margin: 14,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(177, 189, 228, 0.38)',
          type: 'dashed',
        },
      },
    },
    series: [
      {
        name: 'Ping',
        type: 'line',
        data: pingValues,
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: {
          color: '#59b6df',
          width: 3,
        },
        itemStyle: {
          color: '#ffffff',
          borderColor: '#59b6df',
          borderWidth: 2,
        },
      },
      {
        name: 'Пользовательские обращения',
        type: 'line',
        data: userValues,
        smooth: true,
        symbol: 'circle',
        symbolSize: 9,
        lineStyle: {
          color: '#735cf7',
          width: 4,
        },
        itemStyle: {
          color: '#ffffff',
          borderColor: '#735cf7',
          borderWidth: 2.6,
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(115, 92, 247, 0.18)' },
              { offset: 1, color: 'rgba(115, 92, 247, 0.02)' },
            ],
          },
        },
      },
    ],
  }
}

function buildQueueChartOption(sourcePoints, rangeKey) {
  const xAxisData = sourcePoints.map((point) => formatAxisLabel(point.timestamp, rangeKey))
  const pendingValues = sourcePoints.map((point) => Number(point.pending || 0))
  const runningValues = sourcePoints.map((point) => Number(point.running || 0))
  const labelInterval = Math.max(0, Math.ceil(Math.max(sourcePoints.length, 1) / 8) - 1)

  return {
    animationDuration: 500,
    textStyle: {
      fontFamily: 'Manrope, Avenir Next, Segoe UI, sans-serif',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(34, 42, 72, 0.94)',
      borderWidth: 0,
      textStyle: {
        color: '#ffffff',
      },
      axisPointer: {
        type: 'shadow',
        shadowStyle: {
          color: 'rgba(247, 129, 40, 0.08)',
        },
      },
      formatter(params) {
        const point = sourcePoints[params?.[0]?.dataIndex] || null
        const title = point ? formatTooltipLabel(point.timestamp, rangeKey) : ''
        const rows = params
          .map((item) => `${item.marker}${item.seriesName}: ${formatCount(item.value)}`)
          .join('<br/>')
        return `${title}<br/>${rows}`
      },
    },
    grid: {
      top: 24,
      right: 12,
      bottom: 28,
      left: 48,
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: '#8f9bc0',
          width: 1.5,
        },
      },
      axisLabel: {
        color: '#7c87ab',
        fontSize: 12,
        fontWeight: 600,
        interval: labelInterval,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(177, 189, 228, 0.38)',
          type: 'dashed',
        },
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: '#8f9bc0',
          width: 1.5,
        },
      },
      axisLabel: {
        color: '#7c87ab',
        fontSize: 12,
        fontWeight: 600,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(177, 189, 228, 0.38)',
          type: 'dashed',
        },
      },
    },
    series: [
      {
        name: 'В очереди',
        type: 'bar',
        stack: 'queue',
        data: pendingValues,
        barWidth: '48%',
        itemStyle: {
          color: '#f78128',
          borderRadius: [9, 9, 0, 0],
        },
      },
      {
        name: 'Выполняется',
        type: 'bar',
        stack: 'queue',
        data: runningValues,
        barWidth: '48%',
        itemStyle: {
          color: '#735cf7',
          borderRadius: [9, 9, 0, 0],
        },
      },
    ],
  }
}

function buildActiveSessionsChartOption(sourcePoints, sessionValues, rangeKey) {
  const xAxisData = sourcePoints.map((point) => formatAxisLabel(point.timestamp, rangeKey))
  const values = sourcePoints.map((_, index) => Number(sessionValues[index] || 0))
  const labelInterval = Math.max(0, Math.ceil(Math.max(sourcePoints.length, 1) / 8) - 1)

  return {
    animationDuration: 500,
    textStyle: {
      fontFamily: 'Manrope, Avenir Next, Segoe UI, sans-serif',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(34, 42, 72, 0.94)',
      borderWidth: 0,
      textStyle: {
        color: '#ffffff',
      },
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: 'rgba(115, 92, 247, 0.28)',
          width: 1,
        },
      },
      formatter(params) {
        const point = sourcePoints[params?.[0]?.dataIndex] || null
        const title = point ? formatTooltipLabel(point.timestamp, rangeKey) : ''
        const value = params?.[0]?.value ?? 0
        return `${title}<br/>${params?.[0]?.marker || ''}Активные сессии: ${formatCount(value)}`
      },
    },
    toolbox: {
      show: true,
      top: 4,
      right: 6,
      itemSize: 16,
      iconStyle: {
        borderColor: '#5f6c92',
      },
      emphasis: {
        iconStyle: {
          borderColor: '#344362',
        },
      },
      feature: {
        restore: {
          title: 'Сбросить',
        },
        saveAsImage: {
          title: 'Сохранить',
          name: `booml-active-sessions-${rangeKey}`,
          pixelRatio: 2,
          backgroundColor: '#ffffff',
        },
      },
    },
    grid: {
      top: 28,
      right: 14,
      bottom: 30,
      left: 52,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: xAxisData,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: '#8f9bc0',
          width: 1.5,
        },
      },
      axisLabel: {
        color: '#7c87ab',
        fontSize: 12,
        fontWeight: 600,
        margin: 16,
        interval: labelInterval,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(177, 189, 228, 0.38)',
          type: 'dashed',
        },
      },
    },
    yAxis: {
      type: 'value',
      min: 0,
      axisTick: {
        show: false,
      },
      axisLine: {
        lineStyle: {
          color: '#8f9bc0',
          width: 1.5,
        },
      },
      axisLabel: {
        color: '#7c87ab',
        fontSize: 12,
        fontWeight: 600,
        margin: 14,
      },
      splitLine: {
        show: true,
        lineStyle: {
          color: 'rgba(177, 189, 228, 0.38)',
          type: 'dashed',
        },
      },
    },
    series: [
      {
        name: 'Активные сессии',
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: '#735cf7',
          width: 4,
          cap: 'round',
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(115, 92, 247, 0.18)' },
              { offset: 1, color: 'rgba(115, 92, 247, 0.02)' },
            ],
          },
        },
      },
    ],
  }
}

function formatAxisLabel(timestamp, rangeKey) {
  const date = new Date(timestamp)
  if (rangeKey === '24h') {
    return new Intl.DateTimeFormat('ru-RU', {
      hour: 'numeric',
      minute: '2-digit',
    }).format(date)
  }

  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: rangeKey === '30d' ? 'short' : undefined,
  }).format(date)
}

function formatTooltipLabel(timestamp, rangeKey) {
  const date = new Date(timestamp)
  if (rangeKey === '24h') {
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date)
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=Roboto:wght@400;500;700&display=swap');

:root {
  --dashboard-bg: #f4f7ff;
  --dashboard-surface: rgba(255, 255, 255, 0.96);
  --dashboard-surface-strong: #ffffff;
  --dashboard-ink: #202847;
  --dashboard-muted: #6f7a9b;
  --dashboard-line: #dfe6fb;
  --dashboard-shadow: 0 18px 42px rgba(76, 98, 170, 0.12);
  --dashboard-violet: #735cf7;
  --dashboard-violet-soft: rgba(115, 92, 247, 0.12);
  --dashboard-blue: #59b6df;
  --dashboard-blue-soft: rgba(89, 182, 223, 0.14);
  --dashboard-mint: #4ac074;
  --dashboard-mint-soft: rgba(74, 192, 116, 0.14);
  --dashboard-amber: #f78128;
  --dashboard-amber-soft: rgba(247, 129, 40, 0.14);
  --dashboard-danger: #ff5b4d;
  --dashboard-header: #2f3b78;
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  min-height: 100%;
}

body {
  margin: 0;
  font-family: 'Roboto', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  background:
    radial-gradient(circle at top left, rgba(115, 92, 247, 0.12), transparent 28%),
    radial-gradient(circle at top right, rgba(89, 182, 223, 0.14), transparent 24%),
    linear-gradient(180deg, #f9fbff 0%, #f2f5ff 100%);
  color: var(--dashboard-ink);
}

button,
a {
  font: inherit;
}
</style>

<style scoped>
.dashboard {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.dashboard__glow {
  position: absolute;
  width: 420px;
  height: 420px;
  border-radius: 999px;
  filter: blur(70px);
  opacity: 0.48;
  pointer-events: none;
}

.dashboard__glow--left {
  top: 72px;
  left: -120px;
  background: rgba(115, 92, 247, 0.24);
}

.dashboard__glow--right {
  top: 140px;
  right: -120px;
  background: rgba(89, 182, 223, 0.2);
}

.dashboard__header {
  position: relative;
  z-index: 1;
  height: 64px;
  background: #27346a;
}

.dashboard__header-inner {
  width: 100%;
  max-width: 1440px;
  height: 100%;
  margin: 0 auto;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.dashboard__brand {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}

.dashboard__brand-title {
  font-family: 'Dela Gothic One', sans-serif;
  font-size: 40px;
  line-height: 1;
  color: #fff;
}

.dashboard__brand-logo {
  width: 72px;
  height: 72px;
  object-fit: contain;
  margin-right: 5px;
}

.dashboard__header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dashboard__range-controls {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  border-radius: 12px;
  background: rgba(228, 218, 255, 0.22);
  box-shadow: inset 0 0 0 1px rgba(228, 218, 255, 0.2);
  backdrop-filter: blur(10px);
}

.dashboard__range-button {
  min-width: 54px;
  min-height: 40px;
  padding: 10px 14px;
  border: 0;
  border-radius: 10px;
  background: rgba(228, 218, 255, 0.88);
  color: #59617d;
  cursor: pointer;
  font-size: 15px;
  font-weight: 700;
  transition: transform 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.dashboard__range-button:hover {
  transform: translateY(-1px);
}

.dashboard__range-button--active {
  background: #ffffff;
  color: #27346a;
}

.dashboard__header-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 10px 20px;
  border-radius: 10px;
  background: #e4daff;
  color: #000;
  text-decoration: none;
  font-size: 16px;
  font-weight: 500;
  transition: opacity 0.2s ease;
}

.dashboard__header-link:hover {
  opacity: 0.9;
}

.dashboard__main {
  position: relative;
  z-index: 1;
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px 20px 40px;
}

.dashboard__state-card,
.panel,
.stat-card {
  backdrop-filter: blur(10px);
}

.dashboard__inline-alert {
  margin-bottom: 16px;
  padding: 14px 18px;
  border-radius: 18px;
  background: rgba(255, 91, 77, 0.1);
  border: 1px solid rgba(255, 91, 77, 0.18);
  color: #af3f37;
  font-size: 0.95rem;
  font-weight: 500;
}

.dashboard__state-card {
  max-width: 780px;
  margin: 32px auto 0;
  padding: 36px;
  border-radius: 28px;
  background: var(--dashboard-surface);
  box-shadow: var(--dashboard-shadow);
}

.dashboard__state-card--error {
  border: 1px solid rgba(255, 91, 77, 0.28);
}

.dashboard__state-title {
  font-size: 1.5rem;
  font-weight: 800;
}

.dashboard__state-text {
  margin-top: 10px;
  color: var(--dashboard-muted);
  line-height: 1.6;
}

.dashboard__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 20px;
}

.stat-card {
  position: relative;
  padding: 24px;
  border-radius: 28px;
  background: var(--dashboard-surface);
  box-shadow: var(--dashboard-shadow);
  overflow: hidden;
}

.stat-card__top,
.stat-card__footer {
  position: relative;
  z-index: 1;
}

.stat-card__top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.stat-card__title {
  color: var(--dashboard-muted);
  font-size: 1rem;
}

.stat-card__value {
  margin-top: 10px;
  font-size: clamp(2rem, 2vw, 2.4rem);
  font-weight: 800;
  letter-spacing: -0.04em;
}

.stat-card__subtitle {
  margin-top: 8px;
  color: var(--dashboard-muted);
  font-size: 0.82rem;
  line-height: 1.35;
}

.stat-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 62px;
  height: 62px;
  border-radius: 20px;
  flex: none;
}

.stat-card--violet .stat-card__icon {
  background: var(--dashboard-violet-soft);
  color: var(--dashboard-violet);
}

.stat-card--blue .stat-card__icon {
  background: var(--dashboard-blue-soft);
  color: var(--dashboard-blue);
}

.stat-card--mint .stat-card__icon {
  background: var(--dashboard-mint-soft);
  color: var(--dashboard-mint);
}

.stat-card--amber .stat-card__icon {
  background: var(--dashboard-amber-soft);
  color: var(--dashboard-amber);
}

.stat-card__icon svg {
  width: 28px;
  height: 28px;
}

.stat-card__footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  margin-top: 22px;
}

.stat-card__delta {
  font-size: 0.96rem;
  font-weight: 700;
  color: var(--dashboard-muted);
}

.stat-card__delta--positive {
  color: var(--dashboard-mint);
}

.stat-card__delta--negative {
  color: var(--dashboard-danger);
}

.stat-card__sparkline-chart {
  width: 132px;
  height: 40px;
  flex: none;
}

.panel {
  padding: 28px;
  border-radius: 32px;
  background: var(--dashboard-surface-strong);
  box-shadow: var(--dashboard-shadow);
}

.panel--compact {
  min-width: 0;
}

.dashboard__insight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.queue-panel {
  grid-column: 2;
}

.panel__header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.panel__header--compact {
  align-items: flex-start;
}

.panel__title {
  margin: 0;
  font-size: 2rem;
  font-weight: 800;
}

.panel__title--compact {
  font-size: 1.5rem;
}

.panel__subtitle {
  margin: 8px 0 0;
  color: var(--dashboard-muted);
  font-size: 1.1rem;
}

.panel__subtitle--compact {
  font-size: 0.98rem;
}

.chart-card {
  margin-top: 22px;
}

.chart-card--compact {
  margin-top: 18px;
}

.chart-card__plot {
  padding: 18px 18px 8px;
  border-radius: 26px;
  background:
    linear-gradient(180deg, rgba(246, 248, 255, 0.92) 0%, rgba(255, 255, 255, 0.96) 100%);
  border: 1px solid rgba(223, 230, 251, 0.9);
}

.chart-card__plot--compact {
  padding: 14px 14px 4px;
}

.chart-card__chart {
  width: 100%;
  height: min(52vw, 520px);
  min-height: 340px;
  display: block;
}

.chart-card__chart--compact {
  height: 320px;
  min-height: 320px;
}

.chart-card__legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 18px;
  color: #5f6c92;
  font-weight: 700;
}

.chart-card__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.chart-card__legend-swatch {
  display: inline-block;
  width: 18px;
  height: 4px;
  border-radius: 999px;
}

.chart-card__legend-swatch--ping {
  background: var(--dashboard-blue);
}

.chart-card__legend-swatch--user {
  background: var(--dashboard-violet);
}

.panel__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  padding-top: 24px;
  margin-top: 18px;
  border-top: 1px solid rgba(223, 230, 251, 0.9);
}

.panel__summary--compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.summary-metric__label {
  color: var(--dashboard-muted);
  font-size: 1rem;
}

.summary-metric__value {
  margin-top: 10px;
  font-size: 2rem;
  font-weight: 800;
  letter-spacing: -0.04em;
}

.summary-metric__value--small {
  font-size: 1.35rem;
  letter-spacing: 0;
}

.resource-panel__rings {
  display: grid;
  grid-template-columns: repeat(2, minmax(130px, 1fr));
  gap: 26px;
  justify-items: center;
  padding: 30px 20px 24px;
}

.resource-ring {
  --resource-angle: 0deg;
  --resource-color: var(--dashboard-violet);
  width: 142px;
  height: 142px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    conic-gradient(var(--resource-color) var(--resource-angle), rgba(226, 222, 247, 0.9) 0deg);
}

.resource-ring__inner {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  align-content: center;
  background: #ffffff;
}

.resource-ring__value {
  font-size: 2rem;
  line-height: 1;
  font-weight: 800;
}

.resource-ring__label {
  margin-top: 8px;
  color: var(--dashboard-muted);
  font-size: 1rem;
  font-weight: 500;
}

.resource-panel__summary,
.queue-panel__summary {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.queue-panel__summary {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.panel__footnote {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 24px;
  color: #7c87ab;
  font-size: 0.95rem;
  line-height: 1.5;
}

.sessions-panel {
  margin-top: 20px;
}

.sessions-panel__updated {
  color: var(--dashboard-muted);
  font-weight: 500;
  white-space: nowrap;
}

.sessions-table {
  margin-top: 18px;
  overflow-x: auto;
}

.sessions-table__head,
.sessions-table__row {
  display: grid;
  grid-template-columns: minmax(280px, 1.7fr) minmax(180px, 1fr) minmax(110px, 0.6fr) minmax(160px, 0.9fr) minmax(90px, 0.5fr) minmax(140px, 0.8fr) minmax(130px, 0.7fr);
  align-items: center;
  min-width: 1120px;
  gap: 14px;
}

.sessions-table__head {
  padding: 16px 18px;
  border-radius: 18px 18px 0 0;
  background: #ded8f2;
  color: #47506e;
  font-weight: 800;
}

.sessions-table__row {
  padding: 16px 18px;
  border-bottom: 1px solid rgba(223, 230, 251, 0.9);
  color: #5f6c92;
}

.sessions-table__notebook {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  color: var(--dashboard-ink);
  font-weight: 800;
}

.sessions-table__notebook span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sessions-table__avatar {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  background: rgba(115, 92, 247, 0.16);
  color: var(--dashboard-violet);
  font-weight: 800;
}

.sessions-table__pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.86rem;
  font-weight: 800;
}

.sessions-table__pill--violet {
  background: rgba(115, 92, 247, 0.14);
  color: var(--dashboard-violet);
}

.sessions-table__pill--blue {
  background: rgba(89, 182, 223, 0.22);
  color: #3786a8;
}

.sessions-table__pill--gray {
  background: rgba(95, 108, 146, 0.12);
  color: #5f6c92;
}

.sessions-table__pill--green {
  background: rgba(74, 192, 116, 0.16);
  color: var(--dashboard-mint);
}

.sessions-table__empty {
  min-width: 1120px;
  padding: 42px 18px;
  border-bottom: 1px solid rgba(223, 230, 251, 0.9);
  color: var(--dashboard-muted);
  text-align: center;
}

.sessions-panel__footer {
  margin-top: 22px;
  color: var(--dashboard-muted);
}

.sessions-panel__footer strong {
  color: var(--dashboard-ink);
}

@media (max-width: 1200px) {
  .dashboard__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard__insight-grid {
    grid-template-columns: 1fr;
  }

  .queue-panel {
    grid-column: auto;
  }

  .panel__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .dashboard__header-inner,
  .panel__header,
  .panel__footnote {
    flex-direction: column;
    align-items: stretch;
  }

  .dashboard__header {
    height: auto;
    padding: 10px 0;
  }

  .dashboard__header-actions,
  .dashboard__range-controls {
    justify-content: flex-start;
  }

  .chart-card__chart {
    height: 360px;
  }

  .chart-card__chart--compact {
    height: 300px;
    min-height: 300px;
  }

  .resource-panel__summary,
  .queue-panel__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .dashboard__main {
    padding: 18px 14px 28px;
  }

  .dashboard__header {
    padding: 10px 0;
  }

  .dashboard__range-controls {
    width: 100%;
    justify-content: space-between;
  }

  .dashboard__range-button {
    flex: 1 1 0;
    min-width: 0;
  }

  .dashboard__stats,
  .panel__summary {
    grid-template-columns: 1fr;
  }

  .resource-panel__rings {
    grid-template-columns: 1fr;
  }

  .panel,
  .stat-card,
  .dashboard__state-card {
    padding: 22px;
    border-radius: 24px;
  }

  .chart-card__plot {
    padding: 12px 10px 0;
  }

  .chart-card__chart {
    min-height: 290px;
    height: 300px;
  }

  .summary-metric__value {
    font-size: 1.7rem;
  }
}
</style>

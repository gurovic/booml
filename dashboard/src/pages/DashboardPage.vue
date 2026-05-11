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
              <h2 class="panel__title">Запросы к серверу</h2>
              <p class="panel__subtitle">Ping и API запросы</p>
            </div>

            <div class="panel__controls">
              <button
                v-for="range in ranges"
                :key="range.key"
                type="button"
                class="panel__range-button"
                :class="{ 'panel__range-button--active': activeRange === range.key }"
                @click="activeRange = range.key"
              >
                {{ range.label }}
              </button>
            </div>
          </div>

          <div class="chart-card">
            <div class="chart-card__plot">
              <VChart
                class="chart-card__chart"
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

          <div class="panel__summary">
            <div class="summary-metric">
              <div class="summary-metric__label">Средняя задержка</div>
              <div class="summary-metric__value">{{ averageDurationLabel }}</div>
            </div>
            <div class="summary-metric">
              <div class="summary-metric__label">Средний ping</div>
              <div class="summary-metric__value">{{ averagePingLabel }}</div>
            </div>
            <div class="summary-metric">
              <div class="summary-metric__label">Частота 5xx</div>
              <div class="summary-metric__value">{{ errorRateLabel }}</div>
            </div>
            <div class="summary-metric">
              <div class="summary-metric__label">Пик за период</div>
              <div class="summary-metric__value">{{ peakRequestsLabel }}</div>
            </div>
          </div>

          <div class="panel__footnote">
            <span>Текущее round-trip ping из дашборда: {{ livePingLabel }}</span>
            <span>Агрегация ряда: {{ granularityLabel }}</span>
            <span>Обновлено: {{ generatedAtLabel || 'н/д' }}</span>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, ToolboxComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import projectLogo from '@/assets/logo.png'

import { getRequestMetrics, pingServer } from '../api/dashboard'
import { checkAuth } from '../api/user'

use([CanvasRenderer, GridComponent, LineChart, ToolboxComponent, TooltipComponent])

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
const latestPingMs = ref(null)

let refreshTimer = null

const activeRangeData = computed(() => metricsPayload.value?.ranges?.[activeRange.value] || null)
const cards = computed(() => activeRangeData.value?.cards || null)
const points = computed(() => activeRangeData.value?.points || [])
const summary = computed(() => activeRangeData.value?.summary || null)

const generatedAtLabel = computed(() => (
  metricsPayload.value?.generated_at ? formatDateTime(metricsPayload.value.generated_at) : ''
))
const averageDurationLabel = computed(() => formatMilliseconds(summary.value?.avg_duration_ms))
const averagePingLabel = computed(() => formatMilliseconds(summary.value?.avg_ping_ms))
const errorRateLabel = computed(() => `${formatNumber(summary.value?.error_rate ?? 0)}%`)
const peakRequestsLabel = computed(() => formatCount(summary.value?.peak_requests ?? 0))
const livePingLabel = computed(() => formatMilliseconds(latestPingMs.value))
const granularityLabel = computed(() => {
  if (activeRangeData.value?.granularity === 'hour') {
    return 'почасовая'
  }
  if (activeRangeData.value?.granularity === 'day') {
    return 'подневная'
  }
  return 'н/д'
})

const mainChartOption = computed(() => buildMainChartOption(points.value, activeRange.value))

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
      delta: formatTrend(cardMetrics.online_users?.trend_percent, activeRange.value),
      deltaTone: trendTone(cardMetrics.online_users?.trend_percent),
      tone: 'mint',
      icon: 'users',
      sparkOption: buildSparklineOption(cardMetrics.online_users?.points || [], 'mint'),
    },
  ]
})

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

    const pingStartedAt = performance.now()
    await pingServer()
    latestPingMs.value = performance.now() - pingStartedAt

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

function formatMilliseconds(value) {
  if (value == null) return '0 ms'
  const rounded = Math.round(Number(value))
  return `${rounded} ms`
}

function formatPercentValue(value) {
  return `${Math.round(Number(value || 0))}%`
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
  gap: 8px;
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

.panel__header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.panel__title {
  margin: 0;
  font-size: 2rem;
  font-weight: 800;
}

.panel__subtitle {
  margin: 8px 0 0;
  color: var(--dashboard-muted);
  font-size: 1.1rem;
}

.panel__controls {
  display: inline-flex;
  gap: 10px;
  align-self: center;
}

.panel__range-button {
  min-width: 72px;
  height: 44px;
  padding: 0 16px;
  border: 0;
  border-radius: 15px;
  background: rgba(115, 92, 247, 0.16);
  color: #5c6280;
  cursor: pointer;
  font-weight: 700;
  transition: transform 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.panel__range-button:hover {
  transform: translateY(-1px);
}

.panel__range-button--active {
  background: #344362;
  color: #fff;
}

.chart-card {
  margin-top: 22px;
}

.chart-card__plot {
  padding: 18px 18px 8px;
  border-radius: 26px;
  background:
    linear-gradient(180deg, rgba(246, 248, 255, 0.92) 0%, rgba(255, 255, 255, 0.96) 100%);
  border: 1px solid rgba(223, 230, 251, 0.9);
}

.chart-card__chart {
  width: 100%;
  height: min(52vw, 520px);
  min-height: 340px;
  display: block;
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

.panel__footnote {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 24px;
  color: #7c87ab;
  font-size: 0.95rem;
  line-height: 1.5;
}

@media (max-width: 1200px) {
  .dashboard__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
  .panel__controls {
    justify-content: flex-start;
  }

  .chart-card__chart {
    height: 360px;
  }
}

@media (max-width: 680px) {
  .dashboard__main {
    padding: 18px 14px 28px;
  }

  .dashboard__header {
    padding: 10px 0;
  }

  .dashboard__stats,
  .panel__summary {
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

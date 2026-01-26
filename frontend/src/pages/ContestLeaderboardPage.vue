<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Loading leaderboard...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else>
          <div class="leaderboard-card">
            <div class="leaderboard-head">
              <div>
                <h2 class="leaderboard-title">{{ contestTitle }}</h2>
                <p v-if="scoringLabel" class="leaderboard-meta">{{ scoringLabel }}</p>
              </div>
              <router-link
                :to="contestRoute"
                class="button button--secondary leaderboard-link"
              >
                Назад
              </router-link>
            </div>

            <p v-if="!entries.length" class="note">No participants yet.</p>
            <div v-else class="leaderboard-table-wrap">
              <table class="leaderboard-table">
                <thead>
                  <tr>
                    <th class="leaderboard-cell leaderboard-cell--head leaderboard-cell--name">
                      Участник
                    </th>
                    <th class="leaderboard-cell leaderboard-cell--head leaderboard-cell--score">
                      {{ scoreLabel }}
                    </th>
                    <th
                      v-for="column in problemColumns"
                      :key="column.id"
                      class="leaderboard-cell leaderboard-cell--head leaderboard-cell--problem"
                      :title="column.title"
                    >
                      <span class="leaderboard-cell__title">{{ column.shortTitle }}</span>
                      <span v-if="column.metric" class="leaderboard-cell__meta">{{ column.metric }}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entry in entries" :key="entry.user_id">
                    <td class="leaderboard-cell leaderboard-cell--name">
                      {{ entry.username }}
                    </td>
                    <td class="leaderboard-cell leaderboard-cell--score">
                      {{ formatScore(entry) }}
                    </td>
                    <td
                      v-for="column in problemColumns"
                      :key="column.id"
                      class="leaderboard-cell leaderboard-cell--problem"
                    >
                      {{ formatMetric(problemResults[entry.user_id]?.[column.id]) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contestApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'

const route = useRoute()
const contestId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(contestId.value) && contestId.value > 0)
const queryTitle = computed(() => {
  const title = route.query.title
  return Array.isArray(title) ? title[0] : title
})

const contest = ref(null)
const overallLeaderboard = ref(null)
const problemLeaderboards = ref([])
const isLoading = ref(false)
const error = ref('')

const contestTitle = computed(() => {
  if (contest.value?.title) return contest.value.title
  if (queryTitle.value) return queryTitle.value
  return hasValidId.value ? `Contest ${contestId.value}` : 'Contest'
})

const scoringType = computed(() => overallLeaderboard.value?.scoring || contest.value?.scoring || '')
const scoringLabel = computed(() => {
  if (!scoringType.value) return ''
  const labelMap = {
    icpc: 'ICPC',
    ioi: 'IOI',
    partial: 'Partial',
  }
  const label = labelMap[scoringType.value] || scoringType.value
  const count = overallLeaderboard.value?.problems_count
  if (count != null) {
    return `Scoring: ${label} | Problems: ${count}`
  }
  return `Scoring: ${label}`
})

const showPenalty = computed(() => scoringType.value === 'icpc')
const scoreLabel = computed(() => 'Итог')

const problemColumns = computed(() => {
  const list = Array.isArray(problemLeaderboards.value)
    ? problemLeaderboards.value
    : []
  return list.map((board) => {
    const title = board.problem_title || `Problem ${board.problem_id}`
    const trimmed = title.length > 16 ? `${title.slice(0, 16)}…` : title
    return {
      id: board.problem_id,
      title,
      shortTitle: trimmed,
      metric: board.metric || '',
    }
  })
})

const problemResults = computed(() => {
  const map = {}
  for (const board of problemLeaderboards.value || []) {
    const entries = Array.isArray(board.entries) ? board.entries : []
    for (const entry of entries) {
      if (entry?.user_id == null) continue
      if (!map[entry.user_id]) map[entry.user_id] = {}
      map[entry.user_id][board.problem_id] = entry.best_metric
    }
  }
  return map
})

const entries = computed(() => {
  const list = Array.isArray(overallLeaderboard.value?.entries)
    ? overallLeaderboard.value.entries
    : []
  return [...list].sort((a, b) => {
    const rankA = a?.rank ?? Number.MAX_SAFE_INTEGER
    const rankB = b?.rank ?? Number.MAX_SAFE_INTEGER
    if (rankA !== rankB) return rankA - rankB
    return String(a?.username ?? '').localeCompare(String(b?.username ?? ''))
  })
})

const contestRoute = computed(() => {
  if (!hasValidId.value) return { name: 'home' }
  const title = contest.value?.title || queryTitle.value
  const query = title ? { title } : {}
  return { name: 'contest', params: { id: contestId.value }, query }
})

const formatScore = (entry) => {
  if (!entry) return '-'
  if (showPenalty.value) {
    const solved = entry.solved_count
    return solved == null ? '-' : solved
  }
  const score = entry.total_score
  if (score == null) return '-'
  return Number(score).toFixed(4)
}

const formatMetric = (value) => {
  if (value == null) return '-'
  const numeric = Number(value)
  if (Number.isFinite(numeric)) {
    return numeric.toFixed(4)
  }
  return String(value)
}

const loadLeaderboard = async () => {
  if (!hasValidId.value) {
    contest.value = null
    overallLeaderboard.value = null
    error.value = 'Invalid contest id.'
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    const [leaderboardData, contestData] = await Promise.all([
      contestApi.getContestLeaderboard(contestId.value),
      queryTitle.value ? Promise.resolve(null) : contestApi.getContest(contestId.value),
    ])
    contest.value = contestData
    overallLeaderboard.value = leaderboardData?.overall_leaderboard ?? null
    problemLeaderboards.value = Array.isArray(leaderboardData?.leaderboards)
      ? leaderboardData.leaderboards
      : []
    if (!overallLeaderboard.value) {
      error.value = 'Leaderboard data is unavailable.'
    }
  } catch (err) {
    console.error('Failed to load leaderboard.', err)
    error.value = err?.message || 'Failed to load leaderboard.'
  } finally {
    isLoading.value = false
  }
}

watch(contestId, () => {
  loadLeaderboard()
}, { immediate: true })
</script>

<style scoped>
.contest-page {
  min-height: 100vh;
  background: var(--color-bg-default);
  font-family: var(--font-default);
  color: var(--color-text-primary);
}

.contest-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px 40px;
}

.contest-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.leaderboard-card {
  background: var(--color-bg-card);
  border-radius: 16px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.leaderboard-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.leaderboard-title {
  margin: 0 0 6px;
  font-size: 24px;
}

.leaderboard-meta {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-primary);
}

.leaderboard-link {
  display: inline-flex;
  align-items: center;
  color: #1E264A;
  text-decoration: none;
}

.leaderboard-table-wrap {
  width: 100%;
  overflow-x: auto;
  padding-bottom: 4px;
}

.leaderboard-table {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 8px 10px;
}

.leaderboard-cell {
  height: 50px;
  padding: 0 12px;
  box-sizing: border-box;
  border-radius: 5px;
  background: #E4DAFF;
  color: #27346A;
  text-align: center;
  font-size: 14px;
  vertical-align: middle;
  white-space: nowrap;
}

.leaderboard-cell--head {
  background: #9480C9;
  color: #FFFFFF;
  font-weight: 400;
  border-top-left-radius: 20px;
  border-top-right-radius: 20px;
  border-bottom-left-radius: 5px;
  border-bottom-right-radius: 5px;
}

.leaderboard-cell--name {
  text-align: left;
  min-width: 200px;
  max-width: 260px;
}

.leaderboard-cell--score {
  min-width: 120px;
}

.leaderboard-cell--problem {
  min-width: 140px;
}

.leaderboard-cell__title {
  display: block;
  font-size: 13px;
  line-height: 1.2;
}

.leaderboard-cell__meta {
  display: block;
  font-size: 11px;
  opacity: 0.8;
}

.state {
  padding: 14px 16px;
  background: var(--color-bg-card);
  border: 1px dashed var(--color-border-default);
  border-radius: 12px;
  color: var(--color-text-muted);
  font-size: 15px;
}

.state--error {
  border-color: var(--color-border-danger);
  color: var(--color-text-danger);
}

.note {
  margin: 0;
  padding: 10px 12px;
  background: var(--color-bg-card);
  border-radius: 10px;
  border: 1px solid var(--color-border-light);
  font-size: 14px;
  color: var(--color-text-primary);
}

@media (min-width: 900px) {
  .contest-content {
    padding: 28px 24px 48px;
  }
}

@media (max-width: 640px) {
  .leaderboard-table {
    border-spacing: 6px 8px;
  }

  .leaderboard-cell {
    height: 44px;
    padding: 0 8px;
    font-size: 13px;
  }

  .leaderboard-cell__title {
    font-size: 12px;
  }

  .leaderboard-cell__meta {
    font-size: 10px;
  }

  .leaderboard-cell--name {
    min-width: 160px;
  }

  .leaderboard-cell--score {
    min-width: 96px;
  }

  .leaderboard-cell--problem {
    min-width: 120px;
  }
}
</style>

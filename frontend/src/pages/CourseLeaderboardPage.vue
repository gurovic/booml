<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <UiBreadcrumbs :course="course" />
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Загрузка...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else>
          <div class="leaderboard-card">
            <div class="leaderboard-head">
              <div>
                <h2 class="leaderboard-title">Таблица результатов курса "{{ courseTitle }}"</h2>
                <p v-if="hasParticipantsWithScores" class="leaderboard-meta">Участников: {{ filteredEntries.length }}</p>
              </div>
              <router-link
                :to="courseRoute"
                class="button button--secondary leaderboard-link"
              >
                Назад
              </router-link>
            </div>

            <p v-if="!contests.length" class="note">Пока нет контестов.</p>
            <p v-else-if="!hasParticipantsWithScores" class="note">Пока нет участников.</p>
            <div v-else class="leaderboard-table-wrap">
              <table class="leaderboard-table">
                <thead>
                  <tr>
                    <th class="leaderboard-cell leaderboard-cell--head leaderboard-cell--rank">
                      #
                    </th>
                    <th class="leaderboard-cell leaderboard-cell--head leaderboard-cell--name">
                      Участник
                    </th>
                    <th
                      v-for="contest in contestColumns"
                      :key="contest.id"
                      class="leaderboard-cell leaderboard-cell--head leaderboard-cell--contest"
                      :title="contest.title"
                    >
                      <span class="leaderboard-cell__title">{{ contest.shortTitle }}</span>
                    </th>
                    <th class="leaderboard-cell leaderboard-cell--head leaderboard-cell--score">
                      Итог
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entry in filteredEntries" :key="entry.user_id">
                    <td class="leaderboard-cell leaderboard-cell--rank">
                      {{ entry.rank }}
                    </td>
                    <td class="leaderboard-cell leaderboard-cell--name">
                      {{ entry.username }}
                    </td>
                    <td
                      v-for="contest in contestColumns"
                      :key="contest.id"
                      class="leaderboard-cell leaderboard-cell--contest"
                      :class="{ 'has-score': entry.contest_details?.[contest.index]?.score !== null }"
                    >
                      {{ formatScore(entry.contest_details?.[contest.index]?.score) }}
                    </td>
                    <td class="leaderboard-cell leaderboard-cell--score">
                      {{ formatScore(entry.total_score) }}
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
import { courseApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'

const route = useRoute()
const courseId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(courseId.value) && courseId.value > 0)
const queryTitle = computed(() => {
  const title = route.query.title
  return Array.isArray(title) ? title[0] : title
})

const course = ref(null)
const contests = ref([])
const entries = ref([])
const isLoading = ref(false)
const error = ref('')

const courseTitle = computed(() => {
  if (course.value?.title) return course.value.title
  if (queryTitle.value) return queryTitle.value
  return hasValidId.value ? `Курс ${courseId.value}` : 'Курс'
})

const contestColumns = computed(() => {
  const list = Array.isArray(contests.value) ? contests.value : []
  return list.map((contest, index) => {
    const title = contest.title || `Контест ${contest.id}`
    const trimmed = title.length > 14 ? `${title.slice(0, 14)}…` : title
    return {
      id: contest.id,
      index,
      title,
      shortTitle: trimmed,
    }
  })
})

const courseRoute = computed(() => {
  if (!hasValidId.value) return { name: 'home' }
  const title = course.value?.title || queryTitle.value
  const query = title ? { title } : {}
  return { name: 'course', params: { id: courseId.value }, query }
})

const formatScore = (score) => {
  if (score === null || score === undefined) return '-'
  const numeric = Number(score)
  if (Number.isFinite(numeric)) {
    return numeric.toFixed(2)
  }
  return String(score)
}

const hasParticipantsWithScores = computed(() => {
  return entries.value.some(e => (e.total_score ?? 0) > 0 || (e.problems_solved ?? 0) > 0)
})

const filteredEntries = computed(() => {
  return entries.value.filter(e => (e.total_score ?? 0) > 0 || (e.problems_solved ?? 0) > 0)
})

const loadLeaderboard = async () => {
  if (!hasValidId.value) {
    course.value = null
    contests.value = []
    entries.value = []
    error.value = 'Некорректный id курса.'
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    const [leaderboardData, courseData] = await Promise.all([
      courseApi.getCourseLeaderboard(courseId.value),
      queryTitle.value ? Promise.resolve(null) : courseApi.getCourse(courseId.value),
    ])
    course.value = courseData
    contests.value = Array.isArray(leaderboardData?.contests) ? leaderboardData.contests : []
    entries.value = Array.isArray(leaderboardData?.entries) ? leaderboardData.entries : []
    if (!contests.value.length && !entries.value.length && !leaderboardData) {
      error.value = 'Данные таблицы недоступны.'
    }
  } catch (err) {
    console.error('Failed to load leaderboard.', err)
    error.value = err?.message || 'Не удалось загрузить таблицу.'
  } finally {
    isLoading.value = false
  }
}

watch(courseId, () => {
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
  padding: 0 16px 40px;
}

.contest-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
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
  width: 100%;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 16px;
}

.leaderboard-cell {
  padding: 15px 20px;
  vertical-align: middle;
  white-space: nowrap;
  color: #333333;
}

.leaderboard-cell--head {
  color: #ffffff;
  font-weight: 500;
  text-align: left;
}

.leaderboard-table thead tr {
  background-color: #9480C9;
}

.leaderboard-table thead tr th:first-child {
  border-top-left-radius: 20px;
}

.leaderboard-table thead tr th:last-child {
  border-top-right-radius: 20px;
}

.leaderboard-table tbody tr {
  background-color: #E4DAFF;
  transition: opacity 0.2s ease;
}

.leaderboard-table tbody tr:nth-child(even) {
  background-color: #EDE6FF;
}

.leaderboard-table tbody tr:hover {
  opacity: 0.9;
}

.leaderboard-table tbody tr + tr {
  border-top: 2px solid var(--color-bg-default);
}

.leaderboard-table tbody tr:last-child td:first-child {
  border-bottom-left-radius: 20px;
}

.leaderboard-table tbody tr:last-child td:last-child {
  border-bottom-right-radius: 20px;
}

.leaderboard-cell--rank {
  min-width: 50px;
  text-align: center;
  font-weight: 600;
  color: var(--color-text-muted);
}

.leaderboard-cell--name {
  min-width: 180px;
  max-width: 240px;
}

.leaderboard-cell--contest {
  min-width: 120px;
  text-align: center;
}

.leaderboard-cell--score {
  min-width: 100px;
  text-align: right;
  font-weight: 600;
}

.leaderboard-cell--contest.has-score {
  color: var(--color-text-primary);
  font-family: var(--font-mono);
}

.leaderboard-cell__title {
  display: block;
  font-size: 13px;
  line-height: 1.2;
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
    padding: 0 24px 48px;
  }
}

@media (max-width: 640px) {
  .leaderboard-cell {
    padding: 12px 14px;
    font-size: 14px;
  }

  .leaderboard-cell__title {
    font-size: 12px;
  }

  .leaderboard-cell--name {
    min-width: 140px;
  }

  .leaderboard-cell--contest {
    min-width: 100px;
  }
}
</style>

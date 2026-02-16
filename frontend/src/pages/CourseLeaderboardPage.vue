<template>
  <div class="leaderboard-page">
    <UiHeader />

    <main class="leaderboard-content">
      <div class="page-header">
        <div class="breadcrumb">
          <router-link :to="{ name: 'home' }" class="breadcrumb-link">Главная</router-link>
          <span class="breadcrumb-separator">/</span>
          <span class="breadcrumb-current">{{ courseTitle }}</span>
          <span class="breadcrumb-separator">/</span>
          <span class="breadcrumb-current">Таблица результатов</span>
        </div>
        <h1 class="page-title">Таблица результатов курса</h1>
      </div>

      <div v-if="isLoading" class="state">Загрузка...</div>
      <div v-else-if="error" class="state state--error">{{ error }}</div>
      
      <template v-else>
        <section v-if="!contests.length" class="no-contests">
          В этом курсе пока нет контестов.
        </section>

        <section v-else class="leaderboard-table-wrapper">
          <table class="leaderboard-table">
            <thead>
              <tr>
                <th class="col-rank">#</th>
                <th class="col-user">Участник</th>
                <th 
                  v-for="contest in contests" 
                  :key="contest.id" 
                  class="col-contest"
                >
                  <router-link 
                    :to="{ name: 'contest', params: { id: contest.id }}"
                    class="contest-link"
                  >
                    {{ contest.title }}
                  </router-link>
                </th>
                <th class="col-total">Итог</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entry in entries" :key="entry.user_id">
                <td class="col-rank">{{ entry.rank }}</td>
                <td class="col-user">{{ entry.username }}</td>
                <td 
                  v-for="(detail, index) in entry.contest_details" 
                  :key="index" 
                  class="col-contest"
                  :class="{ 'has-score': detail.score !== null }"
                >
                  {{ formatScore(detail.score) }}
                </td>
                <td class="col-total">{{ formatScore(entry.total_score) }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { courseApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'

const route = useRoute()
const courseId = computed(() => Number(route.params.id))

const courseTitle = ref('')
const contests = ref([])
const entries = ref([])
const isLoading = ref(false)
const error = ref('')

const loadLeaderboard = async () => {
  if (!courseId.value || isNaN(courseId.value)) {
    error.value = 'Неверный ID курса.'
    return
  }

  isLoading.value = true
  error.value = ''

  try {
    const data = await courseApi.getCourseLeaderboard(courseId.value)
    if (!data) {
      error.value = 'Данные не получены.'
      return
    }
    courseTitle.value = data.course_title || ''
    contests.value = data.contests || []
    entries.value = data.entries || []
  } catch (err) {
    console.error('Failed to load leaderboard:', err)
    error.value = err?.message || 'Ошибка загрузки таблицы результатов.'
  } finally {
    isLoading.value = false
  }
}

const formatScore = (score) => {
  if (score === null || score === undefined) return '—'
  return typeof score === 'number' ? score.toFixed(4) : score
}

watch(courseId, () => {
  loadLeaderboard()
}, { immediate: true })
</script>

<style scoped>
.leaderboard-page {
  min-height: 100vh;
  background: var(--color-bg-default);
  font-family: var(--font-default);
  color: var(--color-text-primary);
}

.leaderboard-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px 40px;
}

.page-header {
  margin-bottom: 24px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--color-text-muted);
}

.breadcrumb-link {
  color: var(--color-primary);
  text-decoration: none;
}

.breadcrumb-link:hover {
  text-decoration: underline;
}

.breadcrumb-separator {
  color: var(--color-text-muted);
}

.breadcrumb-current {
  color: var(--color-text-secondary);
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: var(--color-text-primary);
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

.no-contests {
  padding: 24px;
  background: var(--color-bg-card);
  border-radius: 12px;
  text-align: center;
  color: var(--color-text-muted);
}

.leaderboard-table-wrapper {
  overflow-x: auto;
}

.leaderboard-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-bg-card);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.leaderboard-table th,
.leaderboard-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid var(--color-border-light);
  white-space: nowrap;
}

.leaderboard-table th {
  background: var(--color-bg-muted);
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.leaderboard-table tr:last-child td {
  border-bottom: none;
}

.leaderboard-table tr:hover {
  background: var(--color-bg-hover);
}

.col-rank {
  width: 50px;
  text-align: center !important;
  font-weight: 600;
  color: var(--color-text-muted);
}

.col-user {
  min-width: 150px;
  font-weight: 500;
}

.col-contest {
  text-align: center !important;
  font-family: var(--font-mono);
  font-size: 14px;
}

.contest-link {
  color: var(--color-text-primary);
  text-decoration: none;
  transition: color 0.2s;
}

.contest-link:hover {
  color: var(--color-primary);
  text-decoration: underline;
}

.col-contest.has-score {
  color: var(--color-text-primary);
}

.col-total {
  min-width: 100px;
  text-align: right !important;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--color-primary);
}

@media (min-width: 900px) {
  .leaderboard-content {
    padding: 28px 24px 48px;
  }

  .page-title {
    font-size: 32px;
  }
}
</style>

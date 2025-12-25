<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Loading contests...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else>
          <UiLinkList
            :title="courseTitle"
            :items="contestItems"
          />
          <p v-if="!contestItems.length" class="note">This course has no contests yet.</p>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contestApi, courseApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiLinkList from '@/components/ui/UiLinkList.vue'

const route = useRoute()
const courseId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(courseId.value) && courseId.value > 0)
const queryTitle = computed(() => {
  const title = route.query.title
  return Array.isArray(title) ? title[0] : title
})

const course = ref(null)
const contests = ref([])
const isLoading = ref(false)
const error = ref('')

const courseTitle = computed(() => course.value?.title || queryTitle.value || 'Course')

const contestItems = computed(() => {
  const list = Array.isArray(contests.value) ? contests.value : []
  return list
    .filter(contest => contest?.id != null)
    .map(contest => ({
      text: contest.title || `Contest ${contest.id}`,
      route: { name: 'contest', params: { id: contest.id }},
    }))
})

const loadContests = async () => {
  if (!hasValidId.value) {
    contests.value = []
    error.value = 'Invalid course id.'
    course.value = null
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    const [courseData, contestData] = await Promise.all([
      courseApi.getCourse(courseId.value),
      contestApi.getContestsByCourse(courseId.value),
    ])
    course.value = courseData
    contests.value = contestData
  } catch (err) {
    console.error('Failed to load contests.', err)
    error.value = err?.message || 'Failed to load contests.'
  } finally {
    isLoading.value = false
  }
}

watch(courseId, () => {
  loadContests()
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
  background: var(--color-bg-muted);
  border-radius: 10px;
  border: 1px solid var(--color-border-light);
  font-size: 14px;
  color: var(--color-text-muted);
}

@media (min-width: 900px) {
  .contest-content {
    padding: 28px 24px 48px;
  }
}
</style>

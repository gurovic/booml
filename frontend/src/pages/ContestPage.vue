<template>
  <div class="contest-page">
    <UiHeader />

    <main class="contest-content">
      <section class="contest-panel">
        <div v-if="isLoading" class="state">Loading contest...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else-if="contest">
          <UiLinkList
            :title="listTitle"
            :items="problemItems"
          />
          <p v-if="!problemItems.length" class="note">This contest has no problems yet.</p>
        </template>
        <div v-else class="state">Contest not found.</div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contestApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiLinkList from '@/components/ui/UiLinkList.vue'

const route = useRoute()
const contestId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(contestId.value) && contestId.value > 0)

const contest = ref(null)
const isLoading = ref(false)
const error = ref('')

const listTitle = computed(() => {
  if (contest.value?.title) return contest.value.title
  return hasValidId.value ? `Contest ${contestId.value}` : 'Contest'
})

const problemItems = computed(() => {
  const problems = Array.isArray(contest.value?.problems) ? contest.value.problems : []
  return problems
    .filter(problem => problem?.id != null)
    .map(problem => ({
      text: problem.title || `Problem ${problem.id}`,
      route: { name: 'problem', params: { id: problem.id }, query: { title: problem.title } },
    }))
})

const loadContest = async () => {
  if (!hasValidId.value) {
    contest.value = null
    error.value = 'Invalid contest id.'
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    contest.value = await contestApi.getContest(contestId.value)
  } catch (err) {
    console.error('Failed to load contest.', err)
    error.value = err?.message || 'Failed to load contest.'
  } finally {
    isLoading.value = false
  }
}

watch(contestId, () => {
  loadContest()
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

.note {
  margin: 0;
  padding: 10px 12px;
  background: var(--color-bg-primary);
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

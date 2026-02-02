<template>
  <div class="section-page">
    <UiHeader />

    <main class="section-content">
      <section class="section-panel">
        <div v-if="isLoading" class="state">Loading section...</div>
        <div v-else-if="error" class="state state--error">{{ error }}</div>
        <template v-else>
          <div class="section-info">
            <h1 class="section-title">{{ sectionTitle }}</h1>
            <p v-if="sectionData?.description" class="section-description">{{ sectionData.description }}</p>
          </div>

          <!-- Child Sections -->
          <div v-if="childSections.length > 0" class="subsections">
            <h2 class="subsection-header">Подразделы</h2>
            <div class="item-grid">
              <button
                v-for="section in childSections"
                :key="section.id"
                type="button"
                class="item-card"
                @click="goToSection(section)"
              >
                <h3 class="item-title">{{ section.title }}</h3>
                <p v-if="section.description" class="item-description">{{ section.description }}</p>
              </button>
            </div>
          </div>

          <!-- Courses -->
          <div v-if="courses.length > 0" class="courses">
            <UiLinkList
              title="Курсы"
              :items="courseItems"
            />
          </div>

          <!-- Empty State -->
          <div v-if="!childSections.length && !courses.length" class="empty-state">
            <p class="empty-text">В этом разделе пока нет курсов и подразделов</p>
          </div>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { courseApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiLinkList from '@/components/ui/UiLinkList.vue'

const route = useRoute()
const router = useRouter()
const sectionId = computed(() => Number(route.params.id))
const hasValidId = computed(() => Number.isInteger(sectionId.value) && sectionId.value > 0)
const queryTitle = computed(() => {
  const title = route.query.title
  return Array.isArray(title) ? title[0] : title
})

const sectionData = ref(null)
const isLoading = ref(false)
const error = ref('')

const sectionTitle = computed(() => sectionData.value?.title || queryTitle.value || 'Section')

const childSections = computed(() => {
  if (!sectionData.value || !Array.isArray(sectionData.value.children)) {
    return []
  }
  return sectionData.value.children.filter(item => item.type === 'section')
})

const courses = computed(() => {
  if (!sectionData.value || !Array.isArray(sectionData.value.children)) {
    return []
  }
  return sectionData.value.children.filter(item => item.type === 'course')
})

const courseItems = computed(() => {
  return courses.value.map(course => ({
    text: course.title || `Course ${course.id}`,
    route: { name: 'course', params: { id: course.id }},
  }))
})

const goToSection = (section) => {
  router.push({ name: 'section', params: { id: section.id }, query: { title: section.title } })
}

const loadSection = async () => {
  if (!hasValidId.value) {
    sectionData.value = null
    error.value = 'Invalid section id.'
    return
  }

  isLoading.value = true
  error.value = ''
  try {
    const data = await courseApi.getSection(sectionId.value)
    if (!data) {
      error.value = 'Section not found.'
      sectionData.value = null
    } else {
      sectionData.value = data
    }
  } catch (err) {
    console.error('Failed to load section.', err)
    error.value = err?.message || 'Failed to load section.'
    sectionData.value = null
  } finally {
    isLoading.value = false
  }
}

watch(sectionId, () => {
  loadSection()
}, { immediate: true })
</script>

<style scoped>
.section-page {
  min-height: 100vh;
  background: var(--color-bg-default);
  font-family: var(--font-default);
  color: var(--color-text-primary);
}

.section-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 16px 40px;
}

.section-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
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

.section-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-title);
}

.section-description {
  margin: 0;
  font-size: 16px;
  color: var(--color-text-primary);
  line-height: 1.5;
}

.subsections,
.courses {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subsection-header {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
  color: var(--color-text-title);
}

.item-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.item-card {
  background: var(--color-surface);
  border: 1px solid var(--color-surface-border);
  border-radius: 12px;
  padding: 16px;
  text-align: left;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 2px 8px var(--color-surface-shadow);
}

.item-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px var(--color-surface-shadow);
}

.item-title {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.item-description {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.empty-state {
  padding: 32px 16px;
  text-align: center;
}

.empty-text {
  margin: 0;
  font-size: 15px;
  color: var(--color-text-muted);
}

@media (min-width: 900px) {
  .section-content {
    padding: 28px 24px 48px;
  }
  
  .item-grid {
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  }
}
</style>

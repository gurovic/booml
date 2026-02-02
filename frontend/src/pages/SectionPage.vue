<template>
  <div class="page">
    <UiHeader />
    <div class="page__content">
      <div v-if="section" class="section-card">
        <div class="section-header-block">
          <h1 class="section-title">{{ section.title }}</h1>
          <p v-if="section.description" class="section-description">{{ section.description }}</p>
        </div>

        <div v-if="hasChildren" class="section-content">
          <ul class="course-list">
            <li
              v-for="child in orderedChildren"
              :key="child.id"
              class="course-item"
            >
              <template v-if="hasChildrenItems(child)">
                <button type="button" class="section-header section-header--inline" @click="toggleNested(child.id)">
                  <span class="triangle triangle--nested" :class="{ 'triangle--open': isNestedOpen(child.id) }"></span>
                  <h2 class="course-title course-title--section">{{ child.title }}</h2>
                </button>
                <div v-if="isNestedOpen(child.id) && (child.children || []).length" class="badge-list">
                  <button
                    v-for="grand in child.children"
                    :key="grand.id"
                    type="button"
                    class="badge"
                    @click="navigateTo(grand)"
                  >
                    {{ grand.title }}
                  </button>
                </div>
              </template>
              <template v-else>
                <button type="button" class="course-link" @click="navigateTo(child)">
                  {{ child.title }}
                </button>
              </template>
            </li>
          </ul>
        </div>
        <div v-else class="empty-state">
          <p class="empty-state__text">В этом разделе пока нет курсов или подразделов</p>
        </div>
      </div>

      <div v-else-if="loading" class="section-card">
        <p>Загрузка...</p>
      </div>

      <div v-else class="section-card">
        <p>Раздел не найден</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { courseApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id)

const courses = ref([])
const section = ref(null)
const loading = ref(true)
const openNested = ref({})

const hasChildrenItems = item => Array.isArray(item?.children) && item.children.length > 0

const hasChildren = computed(() => {
  return section.value && hasChildrenItems(section.value)
})

const orderedChildren = computed(() => {
  if (!section.value?.children) return []
  const list = section.value.children
  return [
    ...list.filter(item => hasChildrenItems(item)),
    ...list.filter(item => !hasChildrenItems(item)),
  ]
})

const isNestedOpen = nestedId => !!openNested.value[String(nestedId)]
const toggleNested = nestedId => {
  const key = String(nestedId)
  openNested.value = { ...openNested.value, [key]: !openNested.value[key] }
}

const navigateTo = (item) => {
  // Navigate to course or section page based on item type
  if (item.type === 'course') {
    router.push({ name: 'course', params: { id: item.id }, query: { title: item.title } })
  } else if (item.type === 'section') {
    router.push({ name: 'section', params: { id: item.id }, query: { title: item.title } })
  } else {
    console.warn('Unknown item type:', item.type)
  }
}

const findSectionById = (items, targetId) => {
  // Convert targetId to number for comparison
  const numericId = Number(targetId)
  for (const item of items) {
    if (item.id === numericId && item.type === 'section') {
      return item
    }
    if (item.children) {
      const found = findSectionById(item.children, numericId)
      if (found) return found
    }
  }
  return null
}

const load = async () => {
  try {
    loading.value = true
    const data = await courseApi.getCourses()
    courses.value = Array.isArray(data) ? data : []
    section.value = findSectionById(courses.value, id.value)
  } catch (err) {
    console.error('Не удалось загрузить раздел', err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 0 0 24px;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

.page__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 14px 16px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e9f1;
}

.section-header-block {
  padding: 6px 4px 16px;
  border-bottom: 1px solid #e5e9f1;
  margin-bottom: 16px;
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-text-title);
  margin: 0 0 8px;
}

.section-description {
  font-size: 16px;
  line-height: 1.5;
  color: var(--color-text-primary);
  margin: 0;
}

.section-content {
  margin-top: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  background: none;
  padding: 6px 4px 10px;
  text-align: left;
  color: var(--color-text-title);
}

.section-header--inline {
  padding: 0;
  gap: 8px;
  color: var(--color-text-primary);
}

.course-title {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.4;
  color: var(--color-text-primary);
}

.course-title--section {
  font-weight: 500;
}

.triangle {
  width: 0;
  height: 0;
  border-left: 7px solid var(--color-text-primary);
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  transition: transform 0.2s ease;
}

.triangle--open { 
  transform: rotate(90deg); 
}

.triangle--nested { 
  border-left-width: 6px; 
  border-top-width: 4px; 
  border-bottom-width: 4px; 
}

.course-list {
  margin-left: 12px;
  padding-left: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.course-item {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  color: inherit;
}

.badge-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding-left: 16px;
  width: 100%;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 9px 10px;
  background: var(--color-button-secondary);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
}

.course-link {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.4;
  color: var(--color-text-primary);
  background: none;
  padding: 6px 0;
  text-align: left;
}

.course-link:hover,
.badge:hover {
  opacity: 0.9;
}

.empty-state {
  padding: 16px 0;
}

.empty-state__text {
  font-size: 16px;
  color: var(--color-text-primary);
  margin: 0;
  text-align: center;
}

@media (min-width: 900px) {
  .page__content { 
    padding: 28px 32px 0; 
  }
}
</style>

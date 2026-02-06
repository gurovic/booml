<template>
  <div class="home">
    <UiHeader />
    <div class="home__content">
      <div v-for="section in sections" :key="section.id" class="section-card">
        <button type="button" class="section-header" @click="toggleSection(section.id)">
          <span class="triangle" :class="{ 'triangle--open': isSectionOpen(section.id) }"></span>
          <h2 class="section-title">{{ section.title }}</h2>
        </button>

        <ul v-if="isSectionOpen(section.id)" class="course-list">
          <li
            v-for="child in orderedChildren(section)"
            :key="child.id"
            class="course-item"
          >
            <template v-if="hasChildren(child)">
              <button type="button" class="section-header section-header--inline" @click="toggleNested(child.id)">
                <span class="triangle triangle--nested" :class="{ 'triangle--open': isNestedOpen(child.id) }"></span>
                <h3 class="course-title course-title--section">{{ child.title }}</h3>
              </button>
              <div v-if="isNestedOpen(child.id) && (child.children || []).length" class="badge-list">
                <button
                  v-for="grand in child.children"
                  :key="grand.id"
                  type="button"
                  class="badge"
                  @click="goToCourse(grand)"
                >
                  {{ grand.title }}
                </button>
              </div>
            </template>
            <template v-else>
              <button type="button" class="course-link" @click="goToCourse(child)">
                {{ child.title }}
              </button>
            </template>
          </li>
        </ul>
      </div>

      <div v-if="standalone.length && isAuthorized" class="section-card">
        <button type="button" class="section-header" @click="standaloneOpen = !standaloneOpen">
          <span class="triangle" :class="{ 'triangle--open': standaloneOpen }"></span>
          <h2 class="section-title">Курсы без раздела</h2>
        </button>
        <ul v-if="standaloneOpen" class="course-list">
          <li v-for="course in standalone" :key="course.id" class="course-item">
            <button type="button" class="course-link" @click="goToCourse(course)">
              {{ course.title }}
            </button>
          </li>
        </ul>
      </div>

      <div v-if="(!sections.length && !standalone.length) || (!isAuthorized)" class="section-card empty-state">
        <div class="empty-state__content">
          <h2 class="empty-state__title">Нет доступных курсов</h2>
          <p class="empty-state__text">
            Войдите в систему, чтобы увидеть доступные курсы
          </p>
          <button
            class="button button--primary empty-state__button"
            @click="router.push('/login')"
          >
            Войти
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { courseApi } from '@/api'
import UiHeader from '@/components/ui/UiHeader.vue'
import { useUserStore } from '@/stores/UserStore'

const courses = ref([])
const openSections = ref({})
const openNested = ref({})
const standaloneOpen = ref(true)
const router = useRouter()
const userStore = useUserStore()

let user = userStore.getCurrentUser()
let isAuthorized = computed(() => user.value != null)

const hasChildren = item => Array.isArray(item?.children) && item.children.length > 0
const sections = computed(() => courses.value.filter(hasChildren))
const standalone = computed(() => courses.value.filter(item => !hasChildren(item)))

const orderedChildren = section => {
  const list = section.children || []
  return [
    ...list.filter(item => hasChildren(item)),
    ...list.filter(item => !hasChildren(item)),
  ]
}

const isSectionOpen = id => !!openSections.value[String(id)]
const toggleSection = id => {
  const key = String(id)
  openSections.value = { ...openSections.value, [key]: !openSections.value[key] }
}

const isNestedOpen = id => !!openNested.value[String(id)]
const toggleNested = id => {
  const key = String(id)
  openNested.value = { ...openNested.value, [key]: !openNested.value[key] }
}

const goToCourse = (item) => {
  // Use the type field from API to determine route, fallback to checking children
  const name = item.type === 'course' ? 'course' : 'section'
  router.push({ name, params: { id: item.id }, query: { title: item.title } })
}

const load = async () => {
  try {
    const data = await courseApi.getCourses()
    courses.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('Не удалось загрузить курсы', err)
  }
}

onMounted(load)
</script>

<style scoped>
.home {
  min-height: 100vh;
  padding: 0 0 24px;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

.home__content {
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

.section-title {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.4;
}

.course-title {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.4;
  color: var(--color-text-primary);
}

.triangle {
  width: 0;
  height: 0;
  border-left: 7px solid var(--color-text-primary);
  border-top: 5px solid transparent;
  border-bottom: 5px solid transparent;
  transition: transform 0.2s ease;
}

.triangle--open { transform: rotate(90deg); }
.triangle--nested { border-left-width: 6px; border-top-width: 4px; border-bottom-width: 4px; }

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
  text-align: center;
}

.empty-state__content {
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.empty-state__title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-title);
}

.empty-state__text {
  font-size: 16px;
  color: var(--color-text-primary);
  margin: 0;
}

.empty-state__button {
  margin-top: 8px;
  padding: 10px 24px;
}

@media (min-width: 900px) {
  .home__content { padding: 28px 32px 0; }
}
</style>

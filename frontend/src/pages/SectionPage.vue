<template>
  <div>
    <h1>{{ sectionTitle }}</h1>
    <p>ID раздела: {{ id }}</p>

    <h2>Курсы в разделе</h2>

    <p v-if="loading">Загрузка курсов...</p>
    <p v-else-if="error">{{ error }}</p>

    <ul v-else-if="courses.length">
      <li v-for="course in courses" :key="course.id">
        <div>
          <strong>{{ course.title }}</strong>
          <p v-if="course.description">{{ course.description }}</p>
        </div>
        <button type="button" @click="openCourse(course)">Открыть</button>
      </li>
    </ul>

    <p v-else>В этом разделе пока нет курсов.</p>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { courseApi } from '@/api'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id)
const title = computed(() => route.query.title)
const sectionTitle = computed(() => title.value || `Раздел #${id.value}`)

const courses = ref([])
const loading = ref(false)
const error = ref('')
const sectionNode = ref(null)

const hasChildren = (item) => Array.isArray(item?.children) && item.children.length > 0

const findById = (items, targetId) => {
  for (const item of items) {
    if (String(item.id) === String(targetId)) return item
    if (Array.isArray(item.children) && item.children.length) {
      const nested = findById(item.children, targetId)
      if (nested) return nested
    }
  }
  return null
}

const loadCourses = async () => {
  loading.value = true
  error.value = ''
  try {
    const tree = await courseApi.getCourses()
    sectionNode.value = findById(Array.isArray(tree) ? tree : [], id.value)
    courses.value = Array.isArray(sectionNode.value?.children) ? sectionNode.value.children : []
    if (!sectionNode.value) {
      error.value = 'Раздел не найден.'
    }
  } catch (err) {
    console.error('Не удалось загрузить курсы раздела', err)
    error.value = 'Не удалось получить список курсов.'
    courses.value = []
  } finally {
    loading.value = false
  }
}

const openCourse = (item) => {
  const name = hasChildren(item) ? 'section' : 'course'
  router.push({ name, params: { id: item.id }, query: { title: item.title } })
}

onMounted(loadCourses)
watch(id, () => loadCourses())
</script>

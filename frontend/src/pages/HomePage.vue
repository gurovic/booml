<template>
  <section>
    <h1>Разделы</h1>
    <p v-if="sections.length == 0">Нет разделов</p>
    <div v-for="section in sections" :key="section.id">
      <h2>{{ section.title }}</h2>
      <p>{{ section.description }}</p>
      <ul>
        <li v-for="course in section.children" :key="course.id">{{ course.title }}</li>
      </ul>
    </div>
  </section>

  <section>
    <h1>Курсы без разделов</h1>
    <p v-if="standalone.length == 0">Нет курсов</p>
    <ul>
      <li v-for="course in standalone" :key="course.id">
        <strong>{{ course.title }}</strong> — {{ course.description }}
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { courseApi } from '@/api'

const courses = ref([])
const isLoading = ref(false)
const error = ref('')

const sections = computed(() => courses.value.filter(c => (c.children || []).length))
const standalone = computed(() => courses.value.filter(c => !(c.children || []).length))

const load = async () => {
  isLoading.value = true
  error.value = ''
  try { 
    courses.value = await courseApi.getCourses() 
  } catch (error) { 
    error.value = 'Не удалось загрузить курсы'
    console.error(error) 
  } finally { 
    isLoading.value = false 
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>Раздел {{ title || id }}</h1>
    <p>Страница раздела</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const id = computed(() => route.params.id)
const title = computed(() => route.query.title)
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 24px 16px;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

h1 {
  margin-bottom: 12px;
}
</style>

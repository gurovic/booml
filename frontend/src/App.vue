<template>
  <div class="app">
    <main class="app-content">
      <router-view />
    </main>
    <UiFooter />
  </div>
</template>

<script setup>
import UiFooter from '@/components/ui/UiFooter.vue'
</script>

<style scoped>
</style>

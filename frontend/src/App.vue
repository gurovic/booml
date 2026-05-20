<template>
  <div class="app">
    <div class="app-content">
      <router-view />
    </div>
    <UiFooter />
  </div>
</template>

<script setup>
import UiFooter from '@/components/ui/UiFooter.vue'
</script>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-content {
  flex: 1;
}
</style>

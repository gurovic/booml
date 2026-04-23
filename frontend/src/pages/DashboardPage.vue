<template>
  <div class="dashboard">
    <UiHeader />
    <div class="dashboard__content">
      <h1 class="dashboard__title">Dashboard</h1>
      <p class="dashboard__description">Панель управления платформой. Доступна только администратору.</p>
    </div>
  </div>
</template>

<script setup>
import UiHeader from '@/components/ui/UiHeader.vue'
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  font-family: var(--font-default);
  color: var(--color-text-primary);
  background: var(--color-bg-default);
}

.dashboard__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 16px;
}

.dashboard__title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 12px;
}

.dashboard__description {
  font-size: 16px;
  color: var(--color-text-secondary, #555);
}
</style>

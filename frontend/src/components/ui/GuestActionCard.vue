<template>
  <div class="guest-action-card">
    <h2 class="guest-action-card__title">{{ title }}</h2>
    <p class="guest-action-card__description">{{ description }}</p>
    <div class="guest-action-card__actions">
      <button
        type="button"
        class="button button--primary"
        @click="$emit('register')"
      >
        {{ primaryLabel }}
      </button>
      <button
        type="button"
        class="button button--secondary"
        @click="$emit('login')"
      >
        {{ secondaryLabel }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
  primaryLabel: {
    type: String,
    default: 'Зарегистрироваться',
  },
  secondaryLabel: {
    type: String,
    default: 'Войти',
  },
})

defineEmits(['register', 'login'])
</script>

<style scoped>
.guest-action-card {
  border-radius: 12px;
  border: 1px solid var(--color-border-default);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(247, 250, 255, 0.96) 100%);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.guest-action-card__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-title-text);
}

.guest-action-card__description {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.guest-action-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>

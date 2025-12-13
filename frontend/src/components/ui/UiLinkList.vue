<template>
  <div class="menu-list">
    <h2>{{ title }}</h2>

    <ul class="menu-list__items">
      <li v-for="item in items" :key="item.text" class="menu-list__item">
        <router-link :to="item.route" class="menu-list__link">
          {{ item.text }}
        </router-link>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: "MenuList",
  props: {
    title: {
      type: String,
      required: true
    },
    items: {
      type: Array,
      required: true
    }
  }
}
</script>

<style scoped>
.menu-list {
  width: 100%;
  background: var(--color-surface);
  border-radius: 12px;
  padding: 14px 16px 16px;
  box-shadow: 0 3px 10px var(--color-surface-shadow);
  border: 1px solid var(--color-surface-border);
  color: var(--color-text-primary);
}

.menu-list__items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.menu-list__item {
  background: var(--color-button-secondary);
  border-radius: 8px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
  transition: filter 0.2s ease, transform 0.12s ease;
}

.menu-list__item:hover {
  filter: brightness(0.98);
  transform: translateY(-1px);
}

.menu-list__item:active {
  transform: translateY(0);
}

.menu-list__link {
  display: block;
  width: 100%;
  padding: 8px 10px;
  color: var(--color-text-primary);
  border-radius: 8px;
}
</style>

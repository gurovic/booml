<template>
  <span class="id-pill" :title="titleText">{{ prefix }}{{ id }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  id: { type: [Number, String], required: true },
  prefix: { type: String, default: '#' },
  title: { type: String, default: '' },
})

const titleText = computed(() => props.title || `ID: ${props.prefix}${props.id}`)
</script>

<style scoped>
.id-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.2px;
  font-variant-numeric: tabular-nums;
  background: rgba(22, 33, 89, 0.08);
  border: 1px solid rgba(22, 33, 89, 0.14);
  color: rgba(22, 33, 89, 0.9);
  white-space: nowrap;
}
</style>

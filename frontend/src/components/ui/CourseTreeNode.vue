<template>
  <li class="tree-node">
    <div
      class="tree-node__row"
      :class="isCourse ? 'tree-node__row--course' : 'tree-node__row--section'"
      :style="{ '--tree-level': level }"
    >
      <button
        v-if="hasChildren"
        type="button"
        class="tree-node__toggle"
        :aria-expanded="isOpen"
        aria-label="Раскрыть/свернуть"
        @click="$emit('toggle-section', node.id)"
      >
        <span class="tree-node__triangle" :class="{ 'tree-node__triangle--open': isOpen }"></span>
      </button>
      <span v-else class="tree-node__toggle tree-node__toggle--spacer" aria-hidden="true"></span>

      <button
        type="button"
        class="tree-node__main"
        :class="isCourse ? 'tree-node__main--course' : 'tree-node__main--section'"
        :title="node.title"
        @click="$emit('navigate', node)"
      >
        <span
          class="tree-node__icon"
          :class="isCourse ? 'tree-node__icon--course' : 'tree-node__icon--section'"
          aria-hidden="true"
        >
          <svg v-if="isCourse" viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M6 3h11a2 2 0 0 1 2 2v14.5a1.5 1.5 0 0 1-2.34 1.25L12 17.7l-4.66 3.05A1.5 1.5 0 0 1 5 19.5V5a2 2 0 0 1 1-2Z"
              stroke="currentColor"
              stroke-width="2"
              stroke-linejoin="round"
            />
          </svg>
          <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M3 7.5c0-1.1.9-2 2-2h5l2 2h7c1.1 0 2 .9 2 2v8.5c0 1.1-.9 2-2 2H5c-1.1 0-2-.9-2-2V7.5Z"
              stroke="currentColor"
              stroke-width="2"
              stroke-linejoin="round"
            />
          </svg>
        </span>
        <span class="tree-node__text">{{ node.title }}</span>
      </button>

      <button
        v-if="showFavorite && isCourse"
        type="button"
        class="tree-node__star"
        :class="{ 'tree-node__star--on': favoriteOn }"
        :title="favoriteOn ? 'Убрать из избранного' : 'Добавить в избранное'"
        @click.stop.prevent="$emit('toggle-favorite', node)"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21 12 17.27Z"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linejoin="round"
            :fill="favoriteOn ? 'currentColor' : 'transparent'"
          />
        </svg>
      </button>
    </div>

    <ul v-if="hasChildren && isOpen" class="tree-node__children">
      <CourseTreeNode
        v-for="child in orderedChildren"
        :key="child.id"
        :node="child"
        :level="level + 1"
        :open-state="openState"
        :show-favorite="showFavorite"
        :is-favorite="isFavorite"
        @toggle-section="$emit('toggle-section', $event)"
        @navigate="$emit('navigate', $event)"
        @toggle-favorite="$emit('toggle-favorite', $event)"
      />
    </ul>
  </li>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  node: {
    type: Object,
    required: true,
  },
  level: {
    type: Number,
    default: 0,
  },
  openState: {
    type: Object,
    default: () => ({}),
  },
  showFavorite: {
    type: Boolean,
    default: false,
  },
  isFavorite: {
    type: Function,
    default: () => false,
  },
})

defineEmits(['toggle-section', 'navigate', 'toggle-favorite'])

const children = computed(() => (Array.isArray(props.node?.children) ? props.node.children : []))
const hasChildren = computed(() => children.value.length > 0)
const isCourse = computed(() => props.node?.type === 'course')
const isOpen = computed(() => !!props.openState[String(props.node?.id)])
const favoriteOn = computed(() => {
  if (!props.showFavorite || !isCourse.value) return false
  return !!props.isFavorite(props.node)
})

const orderedChildren = computed(() => {
  return [...children.value].sort((a, b) => {
    const aHasChildren = Array.isArray(a?.children) && a.children.length > 0
    const bHasChildren = Array.isArray(b?.children) && b.children.length > 0
    if (aHasChildren === bHasChildren) return 0
    return aHasChildren ? -1 : 1
  })
})
</script>

<style scoped>
.tree-node {
  list-style: none;
}

.tree-node__row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  width: 100%;
  min-width: 0;
  border-radius: 10px;
  padding: 8px 10px;
  padding-left: calc(10px + (var(--tree-level, 0) * 18px));
}

.tree-node__row--section {
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.26);
}

.tree-node__row--course {
  background: var(--color-button-secondary);
  border: 1px solid var(--color-border-default, #e5e9f1);
}

.tree-node__toggle {
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border: 1px solid var(--color-border-default, #d5dce9);
  border-radius: 8px;
  background: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.tree-node__toggle--spacer {
  border-color: transparent;
  background: transparent;
  pointer-events: none;
}

.tree-node__triangle {
  width: 0;
  height: 0;
  border-left: 6px solid var(--color-text-primary);
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
  transition: transform 0.2s ease;
}

.tree-node__triangle--open {
  transform: rotate(90deg);
}

.tree-node__main {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 1 1 auto;
  min-width: 0;
  border: none;
  background: none;
  padding: 0;
  text-align: left;
  cursor: pointer;
  color: var(--color-text-primary);
}

.tree-node__main--section {
  font-size: 15px;
  font-weight: 600;
}

.tree-node__main--course {
  font-size: 14px;
  font-weight: 500;
}

.tree-node__icon {
  flex: 0 0 auto;
}

.tree-node__icon--section {
  color: rgba(37, 99, 235, 0.95);
}

.tree-node__icon--course {
  color: rgba(22, 33, 89, 0.8);
}

.tree-node__text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-node__main:hover {
  opacity: 0.9;
}

.tree-node__star {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid var(--color-border-default, #d5dce9);
  background: #fff;
  color: #64748b;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
}

.tree-node__star:hover {
  border-color: var(--color-primary, #3b82f6);
  color: var(--color-text-primary, #000);
}

.tree-node__star--on {
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.45);
  background: rgba(251, 191, 36, 0.12);
}

.tree-node__children {
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

@media (max-width: 720px) {
  .tree-node__row {
    padding: 7px 8px;
    padding-left: calc(8px + (var(--tree-level, 0) * 14px));
  }
}
</style>

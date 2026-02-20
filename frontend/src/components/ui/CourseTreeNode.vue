<template>
  <li
    class="tree-node"
    :class="{
      'tree-node--course': isCourse,
      'tree-node--section': !isCourse,
      'tree-node--branch': hasChildren,
    }"
  >
    <div
      class="tree-node__row"
      :class="[
        isCourse ? 'tree-node__row--course' : 'tree-node__row--section',
        { 'tree-node__row--open': hasChildren && isOpen },
      ]"
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
              d="M12 3 2.5 8 12 13l9.5-5L12 3Z"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linejoin="round"
            />
            <path
              d="M6.5 10.3V15c0 .4.23.76.59.93C8.32 16.49 10.1 17 12 17s3.68-.51 4.91-1.07c.36-.17.59-.53.59-.93v-4.7"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <path
              d="M21.5 9.2V14"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
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
  position: relative;
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
  padding-left: calc(10px + (var(--tree-level, 0) * 8px));
  position: relative;
  transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.tree-node__row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: 999px;
  background: transparent;
}

.tree-node__row--section {
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.11), rgba(59, 130, 246, 0.07));
  border: 1px solid rgba(59, 130, 246, 0.28);
}

.tree-node__row--section::before {
  background: rgba(37, 99, 235, 0.7);
}

.tree-node__row--course {
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.34);
}

.tree-node__row--course::before {
  background: rgba(100, 116, 139, 0.46);
}

.tree-node__row--section:hover {
  border-color: rgba(37, 99, 235, 0.45);
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.08);
}

.tree-node__row--course:hover {
  border-color: rgba(100, 116, 139, 0.45);
  box-shadow: 0 3px 8px rgba(15, 23, 42, 0.06);
}

.tree-node__row:hover {
  transform: translateX(1px);
}

.tree-node__row--open.tree-node__row--section {
  border-color: rgba(37, 99, 235, 0.5);
  box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.08) inset;
}

.tree-node__row--open.tree-node__row--course {
  border-color: rgba(100, 116, 139, 0.5);
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
  transition: border-color 0.2s ease, background-color 0.2s ease, transform 0.2s ease;
}

.tree-node__toggle:hover {
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(239, 246, 255, 0.85);
}

.tree-node__toggle:active {
  transform: translateY(1px);
}

.tree-node__toggle:focus-visible {
  outline: 2px solid rgba(59, 130, 246, 0.45);
  outline-offset: 1px;
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
  transition: opacity 0.2s ease;
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
  width: 24px;
  height: 24px;
  border-radius: 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.tree-node__icon--section {
  color: rgba(37, 99, 235, 0.95);
}

.tree-node__icon--course {
  color: rgba(22, 33, 89, 0.8);
}

.tree-node__text {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-node__main:hover {
  opacity: 0.9;
}

.tree-node__main:focus-visible {
  outline: 2px solid rgba(59, 130, 246, 0.45);
  outline-offset: 2px;
  border-radius: 8px;
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
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.tree-node__star:hover {
  border-color: var(--color-primary, #3b82f6);
  color: var(--color-text-primary, #000);
  transform: translateY(-1px);
}

.tree-node__star:focus-visible {
  outline: 2px solid rgba(59, 130, 246, 0.45);
  outline-offset: 1px;
}

.tree-node__star--on {
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.45);
  background: rgba(251, 191, 36, 0.12);
}

.tree-node__children {
  margin: 6px 0 0 14px;
  padding: 8px 0 0 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-left: 1px solid rgba(148, 163, 184, 0.44);
  border-radius: 0 0 0 10px;
  background: rgba(148, 163, 184, 0.06);
}

.tree-node__children > .tree-node::before {
  content: '';
  position: absolute;
  left: -12px;
  top: 22px;
  width: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.44);
}

.tree-node--section > .tree-node__children {
  border-left-color: rgba(59, 130, 246, 0.36);
  background: rgba(59, 130, 246, 0.06);
}

.tree-node--section > .tree-node__children > .tree-node::before {
  border-top-color: rgba(59, 130, 246, 0.36);
}

@media (max-width: 720px) {
  .tree-node__row {
    padding: 7px 8px;
    padding-left: calc(8px + (var(--tree-level, 0) * 5px));
  }

  .tree-node__children {
    margin-left: 10px;
    padding-left: 9px;
    padding-top: 7px;
  }

  .tree-node__children > .tree-node::before {
    left: -9px;
    width: 7px;
  }

}
</style>

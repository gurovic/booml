<template>
  <div class="menu-list">
    <h2>{{ title }}</h2>

    <ul class="menu-list__items">
      <li
        v-for="(item, idx) in items"
        :key="item.key || item.id || item.text"
        class="menu-list__item"
        :class="dragItemClass(idx)"
        @dragover="onDragOver(idx, $event)"
        @drop="onDrop(idx, $event)"
        @dragleave="onDragLeave(idx)"
      >
        <button
          v-if="showReorderHandle"
          class="menu-list__drag-handle"
          type="button"
          title="Перетащить"
          aria-label="Перетащить"
          draggable="true"
          @click.stop.prevent
          @dragstart="onDragStart(idx, $event)"
          @dragend="onDragEnd"
        >
          <span class="material-symbols-rounded" aria-hidden="true">drag_indicator</span>
        </button>
        <UiIdPill
          v-if="item.idPill != null"
          class="menu-list__id"
          :id="item.idPill"
          title="ID задачи"
        />
        <router-link :to="item.route" class="menu-list__link">
          {{ item.text }}
        </router-link>
        <div v-if="$slots.action" class="menu-list__action">
          <slot v-if="$slots.action" name="action" :item="item" />
        </div>
      </li>
    </ul>
  </div>
</template>

<script>
import UiIdPill from './UiIdPill.vue'

export default {
  name: "MenuList",
  components: { UiIdPill },
  emits: ['reorder'],
  props: {
    title: {
      type: String,
      required: true
    },
    items: {
      type: Array,
      required: true
    },
    reorderable: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      dragFromIndex: null,
      dragOverIndex: null,
      dragOverPosition: 'before', // 'before' | 'after'
    }
  },
  computed: {
    showReorderHandle() {
      return this.reorderable && Array.isArray(this.items) && this.items.length > 1
    }
  },
  methods: {
    dragItemClass(idx) {
      if (!this.showReorderHandle) return {}
      return {
        'menu-list__item--dragging': this.dragFromIndex === idx,
        'menu-list__item--drag-over-before': this.dragOverIndex === idx && this.dragOverPosition === 'before',
        'menu-list__item--drag-over-after': this.dragOverIndex === idx && this.dragOverPosition === 'after',
      }
    },
    onDragStart(idx, e) {
      if (!this.showReorderHandle) return
      this.dragFromIndex = idx
      this.dragOverIndex = idx
      this.dragOverPosition = 'before'

      // Safari requires some data to be set to start a drag.
      try {
        e.dataTransfer.effectAllowed = 'move'
        e.dataTransfer.setData('text/plain', String(idx))
      } catch (_) {
        // ignore
      }
    },
    onDragEnd() {
      this.dragFromIndex = null
      this.dragOverIndex = null
      this.dragOverPosition = 'before'
    },
    onDragOver(idx, e) {
      if (!this.showReorderHandle) return
      if (this.dragFromIndex == null) return
      e.preventDefault()

      this.dragOverIndex = idx
      const rect = e.currentTarget?.getBoundingClientRect?.()
      if (!rect) return
      const mid = rect.top + rect.height / 2
      this.dragOverPosition = e.clientY > mid ? 'after' : 'before'
    },
    onDragLeave(idx) {
      if (!this.showReorderHandle) return
      if (this.dragOverIndex === idx) this.dragOverIndex = null
    },
    onDrop(targetIdx, e) {
      if (!this.showReorderHandle) return
      e.preventDefault()
      const from = this.dragFromIndex
      if (from == null) return

      const pos = this.dragOverPosition
      const target = Number(targetIdx)
      const f = Number(from)

      let to
      if (pos === 'before') {
        to = f < target ? target - 1 : target
      } else {
        to = f < target ? target : target + 1
      }

      const max = (this.items?.length || 1) - 1
      to = Math.max(0, Math.min(to, max))

      if (Number.isInteger(f) && Number.isInteger(to) && f !== to) {
        this.$emit('reorder', { from: f, to })
      }
      this.onDragEnd()
    },
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
  display: flex;
  align-items: center;
  background: var(--color-button-secondary);
  border-radius: 8px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
  transition: filter 0.2s ease, transform 0.12s ease;
  position: relative;
}

.menu-list__drag-handle {
  flex: 0 0 auto;
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1px solid var(--color-surface-border);
  background: rgba(255, 255, 255, 0.55);
  color: var(--color-text-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: grab;
  margin-left: 10px;
}

.menu-list__drag-handle:active {
  cursor: grabbing;
}

.menu-list__drag-handle :deep(.material-symbols-rounded) {
  font-size: 18px;
  line-height: 1;
}

.menu-list__item--dragging {
  opacity: 0.65;
}

.menu-list__item--drag-over-before::before,
.menu-list__item--drag-over-after::after {
  content: '';
  position: absolute;
  left: 10px;
  right: 10px;
  height: 2px;
  background: var(--color-primary, #2f6fed);
  border-radius: 2px;
}

.menu-list__item--drag-over-before::before {
  top: -2px;
}

.menu-list__item--drag-over-after::after {
  bottom: -2px;
}

.menu-list__id {
  margin-left: 10px;
  flex: 0 0 auto;
}

.menu-list__drag-handle + .menu-list__id {
  margin-left: 6px;
}

.menu-list__item:hover {
  filter: brightness(0.98);
  transform: translateY(-1px);
}

/* Hide destructive actions until the user intentionally hovers the row (desktop).
   On touch devices (no hover), keep them visible. */
@media (hover: hover) and (pointer: fine) {
  .menu-list__item :deep([data-hover-only="true"]) {
    display: none;
  }

  .menu-list__item:hover :deep([data-hover-only="true"]),
  .menu-list__item:focus-within :deep([data-hover-only="true"]) {
    display: inline-flex;
  }
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
  flex: 1;
}

.menu-list__action {
  padding-right: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>

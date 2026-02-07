<template>
  <div ref="host" class="code-editor-host"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap } from '@codemirror/view'
import { indentWithTab } from '@codemirror/commands'
import { basicSetup } from 'codemirror'
import { python } from '@codemirror/lang-python'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  readOnly: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'blur', 'focus'])

const host = ref(null)
let view = null
let lastValue = props.modelValue ?? ''

const createState = (value) => {
  return EditorState.create({
    doc: value,
    extensions: [
      basicSetup,
      python(),
      keymap.of([indentWithTab]),
      EditorState.tabSize.of(4),
      EditorView.editable.of(!props.readOnly),
      EditorView.domEventHandlers({
        blur: () => emit('blur'),
        focus: () => emit('focus'),
      }),
      EditorView.updateListener.of((update) => {
        if (!update.docChanged) return
        const next = update.state.doc.toString()
        lastValue = next
        emit('update:modelValue', next)
      }),
    ],
  })
}

onMounted(() => {
  if (!host.value) return
  view = new EditorView({
    state: createState(lastValue),
    parent: host.value,
  })
})

onBeforeUnmount(() => {
  if (view) {
    view.destroy()
    view = null
  }
})

watch(
  () => props.modelValue,
  (value) => {
    if (!view) return
    const next = value ?? ''
    if (next === lastValue) return
    lastValue = next
    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: next },
    })
  },
)
</script>

<style scoped>
.code-editor-host :deep(.cm-editor) {
  height: auto;
  background: transparent;
  outline: none;
}

.code-editor-host :deep(.cm-scroller) {
  overflow: hidden;
}

.code-editor-host :deep(.cm-content) {
  padding: 0;
}

.code-editor-host :deep(.cm-gutters) {
  background: transparent;
  border-right: none;
  color: #9aa3c7;
  font-family: 'Courier New', monospace;
  font-size: 15px;
  line-height: 1.6;
}

.code-editor-host :deep(.cm-lineNumbers .cm-gutterElement) {
  padding: 0 10px 0 0;
}

.code-editor-host :deep(.cm-content) {
  font-family: 'Courier New', monospace;
  font-size: 15px;
  line-height: 1.6;
  color: #1f2a5a;
}

.code-editor-host :deep(.cm-activeLine),
.code-editor-host :deep(.cm-activeLineGutter) {
  background: transparent;
}

.code-editor-host :deep(.cm-editor.cm-focused) {
  outline: none;
}
</style>

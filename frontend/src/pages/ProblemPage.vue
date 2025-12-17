<template>
  <UiHeader />
  <div class="problem">
    <div class="container">
      <div v-if="problem != null" class="problem__inner">
        <div class="problem__content">
          <h1 class="problem__name">{{ problem.title }}</h1>
          <div class="problem__text" v-html="problem.rendered_statement"></div>
        </div>
        <div class="problem__menu">
          <div class="problem__files" v-if="availableFiles.length > 0">
            <h2 class="problem__files-title">Файлы</h2>
            <ul class="problem__files-list">
              <li
                class="problem__file"
                v-for="file in availableFiles"
                :key="file.name"
              >
                <a class="problem__file-href button button--secondary" :href="file.url" :download="file.name">{{ file.name }}</a>
            </li>
            </ul>
          </div>
        </div>
      </div>
      <div v-else>
        <h1>Задача не найдена</h1>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { getProblem } from '@/api/problem'
import MarkdownIt from 'markdown-it'
import mkKatex from 'markdown-it-katex'
import UiHeader from '@/components/ui/UiHeader.vue'

const md = new MarkdownIt({
  html: false,
  breaks: true,
}).use(mkKatex)

const route = useRoute()

let problem = ref(null)

onMounted(async () => {
  try {
    const res = await getProblem(route.params.id)
    problem.value = res
  } catch (err) {
    console.log(err)
  } finally {
    if (problem.value != null) {
      problem.value.rendered_statement = md.render(problem.value.statement)
    }
  }
})

const availableFiles = computed(() => {
  if (!problem.value.files) return []
  return Object.entries(problem.value.files)
    .filter(([, url]) => url)
    .map(([name, url]) => ({ name, url }))
})
</script>

<style scoped>
.problem {
  width: 100%;
  height: 100%;
  padding: 20px 0;
}

.problem__inner {
  width: 100%;
  height: 100%;
  display: flex;
  gap: 20px;
}

.problem__content {
  position: relative;
  z-index: 1;
  flex-grow: 1;

  display: flex;
  flex-direction: column;

  padding: 32px 40px;

  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);

  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.problem__name {
  margin-bottom: 20px;

  font-family: var(--font-title);
  font-size: 48px;
  font-weight: 400;
  line-height: 1.2;

  color: var(--color-title-text);

  padding-left: 16px;
  border-left: 6px solid var(--color-primary);
}

.problem__menu {
  max-width: 350px;
  width: 100%;
  flex-grow: 1;
  display: flex;
  align-items: center;
  flex-direction: column;
}

.problem__files {
  width: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
  border: 1px solid #e5e9f1;
  border-radius: 30px;
}

.problem__files-list {
  margin-top: 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.problem__file {
  width: 100%;
}

.problem__file-href {
  display: inline-block;
  width: 100%;
  text-align: start;
}

.problem__text {
  font-family: var(--font-default);
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.problem__text :deep(p) {
  margin-bottom: 16px;
}

.problem__text :deep(h2) {
  font-size: 24px;
  font-weight: 500;
  margin: 32px 0 12px;
}

.problem__text :deep(h3) {
  font-size: 20px;
  font-weight: 500;
  margin: 24px 0 10px;
}

</style>
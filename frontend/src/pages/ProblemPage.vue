<template>
  <UiHeader />

  <main class="problem">
    <div class="container">
      <div v-if="problem" class="problem__layout">

        <!-- ===== CONTENT ===== -->
        <section class="problem-card">
          <h1 class="problem-title">
            {{ problem.title }}
          </h1>

          <div
            class="problem-statement"
            v-html="problem.rendered_statement"
          />
        </section>

        <!-- ===== FILES ===== -->
        <aside
          v-if="availableFiles.length"
          class="problem-files"
        >
          <h2 class="problem-files__title">Файлы</h2>

          <ul class="problem-files__list">
            <li
              v-for="file in availableFiles"
              :key="file.name"
            >
              <a
                class="button button--secondary problem-files__link"
                :href="file.url"
                :download="file.name"
              >
                {{ file.name }}
              </a>
            </li>
          </ul>
        </aside>

      </div>

      <div v-else class="problem-empty">
        <h2>Задача не найдена</h2>
      </div>
    </div>
  </main>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import MarkdownIt from 'markdown-it'
import mkKatex from 'markdown-it-katex'

import { getProblem } from '@/api/problem'
import UiHeader from '@/components/ui/UiHeader.vue'

const route = useRoute()
const problem = ref(null)

const md = new MarkdownIt({
  html: false,
  breaks: true,
}).use(mkKatex)

onMounted(async () => {
  try {
    const res = await getProblem(route.params.id)
    problem.value = {
      ...res,
      rendered_statement: md.render(res.statement),
    }
  } catch (e) {
    console.error(e)
  }
})

const availableFiles = computed(() => {
  if (!problem.value?.files) return []
  return Object.entries(problem.value.files)
    .filter(([, url]) => url)
    .map(([name, url]) => ({ name, url }))
})
</script>

<style scoped>
.problem {
  min-height: calc(100vh - 64px);
  padding: 24px 0;
  background: var(--color-bg-default);
}

.problem__layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

/* ===== CARD ===== */
.problem-card {
  background: var(--color-bg-card);
  border-radius: 20px;
  padding: 32px 40px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--color-border-light);
}

/* ===== TITLE ===== */
.problem-title {
  font-family: var(--font-title); /* Dela Gothic One */
  font-size: 48px;
  font-weight: 400;
  line-height: 1.2;
  color: var(--color-title-text);
  margin-bottom: 24px;
  padding-left: 16px;
  border-left: 6px solid var(--color-primary);
}

/* ===== STATEMENT ===== */
.problem-statement {
  font-family: var(--font-default);
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text-primary);
}

.problem-statement :deep(p) {
  margin-bottom: 16px;
}

.problem-statement :deep(h2) {
  font-size: 24px;
  font-weight: 500;
  margin: 32px 0 12px;
}

.problem-statement :deep(h3) {
  font-size: 20px;
  font-weight: 500;
  margin: 24px 0 10px;
}

/* ===== FILES ===== */
.problem-files {
  background: var(--color-bg-card);
  border-radius: 20px;
  padding: 24px;
  border: 1px solid var(--color-border-light);
  height: fit-content;
}

.problem-files__title {
  font-size: 20px;
  font-weight: 500;
  color: var(--color-title-text);
  margin-bottom: 16px;
}

.problem-files__list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.problem-files__link {
  width: 100%;
  justify-content: flex-start;
}

/* ===== EMPTY ===== */
.problem-empty {
  text-align: center;
  padding: 80px 0;
  color: var(--color-text-secondary);
}

/* ===== RESPONSIVE ===== */
@media (max-width: 900px) {
  .problem__layout {
    grid-template-columns: 1fr;
  }
}
</style>

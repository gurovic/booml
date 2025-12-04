<template>
  <UiHeader />
  <div class="problem">
    <div class="container">
      <div v-if="problem != null" class="problem__inner">
        <div class="problem__content">
          <h1 class="problem__name">{{ problem.title }}</h1>
          <div class="problem__text" v-html="problem.rendered_statement"></div>
        </div>
      </div>
      <div v-else>
        <h1>Задача не найдена</h1>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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
    problem.value.rendered_statement = md.render(problem.value.statement)
  }
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
  flex-direction: column;
}

.problem__content {
  position: relative;
  z-index: 1;
  max-width: 980px;
  display: flex;
  flex-direction: column;
  padding: 30px 50px;
  box-shadow: 0px 0px 5px 0px rgba(0, 0, 0, 0.25) inset;
  border-radius: 10px;
}

.problem__name {
  margin-bottom: 20px;
}

.problem__statement {

}
</style>
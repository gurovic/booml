import { createRouter, createWebHistory } from 'vue-router'
import StartPage from '@/pages/StartPage.vue'
import ProblemPage from '@/pages/ProblemPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'start',
      component: StartPage,
    },
    {
      path: '/problem/:id',
      name: 'problem',
      component: ProblemPage,
    },
  ],
})

export default router

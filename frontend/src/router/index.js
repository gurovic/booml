import { createRouter, createWebHistory } from 'vue-router'
import StartPage from '@/pages/StartPage.vue'
import ProblemPage from '@/pages/ProblemPage.vue'
import HomePage from '@/pages/HomePage.vue'
import SectionPage from '@/pages/SectionPage.vue'
import CoursePage from '@/pages/CoursePage.vue'
import LoginPage from '@/pages/LoginPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
    },
    {
      path: '/start-page',
      name: 'start',
      component: StartPage,
    },
    {
      path: '/problem/:id',
      name: 'problem',
      component: ProblemPage,
    },
    {
      path: '/section/:id',
      name: 'section',
      component: SectionPage,
    },
    {
      path: '/course/:id',
      name: 'course',
      component: CoursePage,
    },{
      path: '/login',
      name: 'login',
      component: LoginPage,
    }
  ],
})

export default router

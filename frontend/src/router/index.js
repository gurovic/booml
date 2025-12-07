import { createRouter, createWebHistory } from 'vue-router'
import StartPage from '@/pages/StartPage.vue'
import HomePage from '@/pages/HomePage.vue'
import SectionPage from '@/pages/SectionPage.vue'
import CoursePage from '@/pages/CoursePage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import RegisterPage from '@/pages/RegisterPage.vue'

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
    },{
      path: '/register',
      name: 'register',
      component: RegisterPage,
    }
  ],
})

export default router

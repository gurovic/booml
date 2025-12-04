import { createRouter, createWebHistory } from 'vue-router'
import StartPage from '@/pages/StartPage.vue'
import LoginPage from '@/pages/LoginPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
        {
            path: '/',
            name: 'start',
            component: StartPage,
        }, {
            path: '/login',
            name: 'login',
            component: LoginPage,
        }
    ],
})

export default router

import { createRouter, createWebHistory } from 'vue-router'
import StartPage from '@/pages/StartPage.vue'
import RegistrationPage from '@/pages/RegistrationPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
        {
        path: '/',
        name: 'start',
        component: StartPage,
        }, {
            path: '/registration',
            name: 'registration',
            component: RegistrationPage,
        },
    ],
})

export default router

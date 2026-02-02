import { createRouter, createWebHistory } from 'vue-router'
import StartPage from '@/pages/StartPage.vue'
import ProblemPage from '@/pages/ProblemPage.vue'
import SubmissionPage from '@/pages/SubmissionPage.vue'
import HomePage from '@/pages/HomePage.vue'
import SectionPage from '@/pages/SectionPage.vue'
import CoursePage from '@/pages/CoursePage.vue'
import ContestPage from '@/pages/ContestPage.vue'
import ContestLeaderboardPage from '@/pages/ContestLeaderboardPage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import RegisterPage from '@/pages/RegisterPage.vue'
import PolygonPage from '@/pages/PolygonPage.vue'
import PolygonProblemEditPage from '@/pages/PolygonProblemEditPage.vue'

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
      path: '/submission/:id',
      name: 'submission',
      component: SubmissionPage,
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
    },
    {
      path: '/contest/:id',
      name: 'contest',
      component: ContestPage,
    },
    {
      path: '/contest/:id/leaderboard',
      name: 'contest-leaderboard',
      component: ContestLeaderboardPage,
    },{
      path: '/login',
      name: 'login',
      component: LoginPage,
    },{
      path: '/register',
      name: 'register',
      component: RegisterPage,
    },{
      path: '/polygon',
      name: 'polygon',
      component: PolygonPage,
    },{
      path: '/polygon/problem/:id',
      name: 'polygon-problem-edit',
      component: PolygonProblemEditPage,
    }
  ],
})

export default router

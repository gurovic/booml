import { createRouter, createWebHistory } from 'vue-router'
import StartPage from '@/pages/StartPage.vue'
import ProblemPage from '@/pages/ProblemPage.vue'
import SubmissionPage from '@/pages/SubmissionPage.vue'
import HomePage from '@/pages/HomePage.vue'
import SectionPage from '@/pages/SectionPage.vue'
import CoursePage from '@/pages/CoursePage.vue'
import CourseLeaderboardPage from '@/pages/CourseLeaderboardPage.vue'
import ContestPage from '@/pages/ContestPage.vue'
import CoursesPage from '@/pages/CoursesPage.vue'
import ContestLeaderboardPage from '@/pages/ContestLeaderboardPage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import RegisterPage from '@/pages/RegisterPage.vue'
import PolygonPage from '@/pages/PolygonPage.vue'
import PolygonProblemEditPage from '@/pages/PolygonProblemEditPage.vue'
import SubmissionListPage from '@/pages/SubmissionListPage.vue'
import NotebookPage from '@/pages/NotebookPage.vue'
import ProfilePage from '@/pages/ProfilePage.vue'
import AuthRequiredPage from '@/pages/AuthRequiredPage.vue'
import { useUserStore } from '@/stores/UserStore'

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
      path: '/courses',
      name: 'courses',
      component: CoursesPage,
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
      meta: { requiresAuth: true },
    },
    {
      path: '/problem/:id/submissions',
      name: 'problem-submissions',
      component: SubmissionListPage,
      meta: { requiresAuth: true },
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
      path: '/course/:id/leaderboard/',
      name: 'course-leaderboard',
      component: CourseLeaderboardPage,
      meta: { requiresAuth: true },
    },
    {
      path: '/demo/leaderboard/',
      name: 'demo-leaderboard',
      component: CourseLeaderboardPage,
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
      meta: { requiresAuth: true },
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
      meta: { requiresAuth: true },
    },{
      path: '/polygon/problem/:id',
      name: 'polygon-problem-edit',
      component: PolygonProblemEditPage,
      meta: { requiresAuth: true },
    },{
      path: '/notebook/:id',
      name: 'notebook',
      component: NotebookPage,
      meta: { requiresAuth: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfilePage,
      meta: { requiresAuth: true },
    },
    {
      path: '/auth-required',
      name: 'auth-required',
      component: AuthRequiredPage,
    }
  ],
})

const sanitizeRedirect = (value) => {
  const raw = Array.isArray(value) ? value[0] : value
  if (typeof raw !== 'string' || !raw.startsWith('/')) return '/'
  if (raw.startsWith('/auth-required')) return '/'
  return raw
}

router.beforeEach((to) => {
  const userStore = useUserStore()
  const isAuthorized = !!userStore.currentUser
  const requiresAuth = to.matched.some(record => record.meta?.requiresAuth)

  if (!isAuthorized && requiresAuth) {
    return {
      name: 'auth-required',
      query: { redirect: to.fullPath },
    }
  }

  if (isAuthorized && (to.name === 'login' || to.name === 'register')) {
    return { name: 'home' }
  }

  if (isAuthorized && to.name === 'auth-required') {
    return sanitizeRedirect(to.query?.redirect)
  }

  return true
})

export default router

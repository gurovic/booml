import { createRouter, createWebHistory } from 'vue-router'
import StartPage from '@/pages/StartPage.vue'
import ProblemPage from '@/pages/ProblemPage.vue'
import SubmissionPage from '@/pages/SubmissionPage.vue'
import HomePage from '@/pages/HomePage.vue'
import SectionPage from '@/pages/SectionPage.vue'
import CoursePage from '@/pages/CoursePage.vue'
import CourseLeaderboardPage from '@/pages/CourseLeaderboardPage.vue'
import ContestPage from '@/pages/ContestPage.vue'
import ContestSubmissionsPage from '@/pages/ContestSubmissionsPage.vue'
import CoursesPage from '@/pages/CoursesPage.vue'
import ContestLeaderboardPage from '@/pages/ContestLeaderboardPage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import RegisterPage from '@/pages/RegisterPage.vue'
import TermsPage from '@/pages/TermsPage.vue'
import PrivacyPage from '@/pages/PrivacyPage.vue'
import PolygonPage from '@/pages/PolygonPage.vue'
import PolygonProblemEditPage from '@/pages/PolygonProblemEditPage.vue'
import SubmissionListPage from '@/pages/SubmissionListPage.vue'
import DashboardPage from '@/pages/DashboardPage.vue'
import NotebookPage from '@/pages/NotebookPage.vue'
import NotebookListPage from '@/pages/NotebookListPage.vue'
import ProfilePage from '@/pages/ProfilePage.vue'
import AuthRequiredPage from '@/pages/AuthRequiredPage.vue'
import { useUserStore } from '@/stores/UserStore'
import { buildAuthRedirect, sanitizeRedirectPath } from '@/utils/redirect'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0, left: 0 }
  },
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
      meta: { requiresAuth: true, authReason: 'submissions' },
    },
    {
      path: '/problem/:id/submissions',
      name: 'problem-submissions',
      component: SubmissionListPage,
      meta: { requiresAuth: true, authReason: 'submissions' },
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
      meta: { requiresAuth: true, authReason: 'leaderboard' },
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
      path: '/contest/:id/submissions',
      name: 'contest-submissions',
      component: ContestSubmissionsPage,
    },
    {
      path: '/contest/:id/leaderboard',
      name: 'contest-leaderboard',
      component: ContestLeaderboardPage,
      meta: { requiresAuth: true, authReason: 'leaderboard' },
    },{
      path: '/login',
      name: 'login',
      component: LoginPage,
    },{
      path: '/register',
      name: 'register',
      component: RegisterPage,
    },{
      path: '/terms',
      name: 'terms',
      component: TermsPage,
    },{
      path: '/privacy',
      name: 'privacy',
      component: PrivacyPage,
    },{
      path: '/polygon',
      name: 'polygon',
      component: PolygonPage,
      meta: { requiresAuth: true, authReason: 'generic' },
    },{
      path: '/polygon/problem/:id',
      name: 'polygon-problem-edit',
      component: PolygonProblemEditPage,
      meta: { requiresAuth: true, authReason: 'generic' },
    },
    
    {
      path: '/notebook/:id',
      name: 'notebook',
      component: NotebookPage,
      meta: { requiresAuth: true, authReason: 'notebook' },
    },
    {
      path: '/notebooks',
      name: 'notebooks',
      component: NotebookListPage,
      meta: { requiresAuth: true, authReason: 'notebook' },
    },

    {
      path: '/profile',
      name: 'profile',
      component: ProfilePage,
      meta: { requiresAuth: true, authReason: 'generic' },
    },
    {
      path: '/auth-required',
      name: 'auth-required',
      component: AuthRequiredPage,
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardPage,
      meta: { requiresAuth: true, requiresAdmin: true, authReason: 'generic' },
    }
  ],
})

const resolveAuthReason = (to) => {
  for (let idx = to.matched.length - 1; idx >= 0; idx -= 1) {
    const candidate = to.matched[idx]?.meta?.authReason
    if (typeof candidate === 'string' && candidate.trim()) {
      return candidate.trim()
    }
  }
  return 'generic'
}

router.beforeEach((to) => {
  const userStore = useUserStore()
  const isAuthorized = !!userStore.currentUser
  const requiresAuth = to.matched.some(record => record.meta?.requiresAuth)
  const requiresAdmin = to.matched.some(record => record.meta?.requiresAdmin)

  if (!isAuthorized && requiresAuth) {
    return {
      name: 'auth-required',
      query: buildAuthRedirect({
        redirect: to.fullPath,
        reason: resolveAuthReason(to),
      }),
    }
  }

  if (requiresAdmin) {
    const username = userStore.currentUser?.username?.toLowerCase()
    if (username !== 'admin') {
      return { name: 'home' }
    }
  }

  if (isAuthorized && (to.name === 'login' || to.name === 'register')) {
    return { name: 'home' }
  }

  if (isAuthorized && to.name === 'auth-required') {
    return sanitizeRedirectPath(to.query?.redirect)
  }

  return true
})

export default router

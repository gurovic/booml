import { buildAuthRedirect } from '@/utils/redirect'

const resolveAuthTarget = (mode = 'register') => {
  return mode === 'login' ? 'login' : 'register'
}

export const pushToAuthRoute = ({
  router,
  route,
  mode = 'register',
  reason = 'generic',
} = {}) => {
  if (!router) return Promise.resolve()

  return router.push({
    name: resolveAuthTarget(mode),
    query: buildAuthRedirect({
      redirect: route?.fullPath,
      reason,
    }),
  })
}

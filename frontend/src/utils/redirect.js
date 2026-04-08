const AUTH_REQUIRED_PATH = '/auth-required'
const AUTH_REASON_FALLBACK = 'generic'
const AUTH_REASON_SET = new Set([
  'submit',
  'notebook',
  'submissions',
  'leaderboard',
  'generic',
])

export const sanitizeRedirectPath = (raw, fallback = '/') => {
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string' || !value.startsWith('/')) return fallback
  if (value.startsWith(AUTH_REQUIRED_PATH)) return fallback
  return value
}

export const sanitizeAuthReason = (raw, fallback = AUTH_REASON_FALLBACK) => {
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string') return fallback
  return AUTH_REASON_SET.has(value) ? value : fallback
}

export const resolveRedirectFromQuery = (query, key = 'redirect', fallback = '/') => {
  return sanitizeRedirectPath(query?.[key], fallback)
}

export const resolveAuthReasonFromQuery = (query, key = 'reason', fallback = AUTH_REASON_FALLBACK) => {
  return sanitizeAuthReason(query?.[key], fallback)
}

export const buildAuthRedirect = ({
  redirect,
  reason = AUTH_REASON_FALLBACK,
  fallback = '/',
} = {}) => {
  return {
    redirect: sanitizeRedirectPath(redirect, fallback),
    reason: sanitizeAuthReason(reason),
  }
}

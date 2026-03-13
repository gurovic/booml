const AUTH_REQUIRED_PATH = '/auth-required'

export const sanitizeRedirectPath = (raw, fallback = '/') => {
  const value = Array.isArray(raw) ? raw[0] : raw
  if (typeof value !== 'string' || !value.startsWith('/')) return fallback
  if (value.startsWith(AUTH_REQUIRED_PATH)) return fallback
  return value
}

export const resolveRedirectFromQuery = (query, key = 'redirect', fallback = '/') => {
  return sanitizeRedirectPath(query?.[key], fallback)
}


import { apiGet } from './http'

export function checkAuth() {
  return apiGet('backend/check-auth/')
}

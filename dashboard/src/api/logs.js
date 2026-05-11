import { apiGet } from './http'

export function getLogs() {
  return apiGet('backend/logs/')
}

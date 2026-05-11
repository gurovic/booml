import { apiGet } from './http'

export function getRequestMetrics() {
  return apiGet('backend/dashboard/request-metrics/')
}

export function pingServer() {
  return apiGet('backend/ping/')
}

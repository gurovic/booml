import { apiGet } from './http'

export function getStartMessage() {
  return apiGet('/start')
}

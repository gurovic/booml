import * as courseMock from './mock/course'
import * as courseReal from './real/course'
import { apiGet } from './http'

const useMock = (process.env.VUE_APP_USE_MOCK ?? 'false') == 'true'

export const courseApi = useMock ? courseMock : courseReal

export async function getStartMessage() {
  return apiGet('api/start/')
}

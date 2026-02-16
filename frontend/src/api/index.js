import * as courseMock from './mock/course'
import * as courseReal from './real/course'
import * as contestMock from './mock/contest'
import * as contestReal from './real/contest'
import * as homeMock from './mock/home'
import * as homeReal from './real/home'
import { apiGet } from './http'

const useMock = (process.env.VUE_APP_USE_MOCK ?? 'false') == 'true'

export const courseApi = useMock ? courseMock : courseReal
export const contestApi = useMock ? contestMock : contestReal
export const homeApi = useMock ? homeMock : homeReal

export async function getStartMessage() {
  // Django exposes this under /backend/start/ (proxied in vue.config.js).
  return apiGet('backend/start/')
}

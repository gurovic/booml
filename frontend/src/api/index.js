import * as courseReal from './real/course'
import * as contestReal from './real/contest'
import * as homeReal from './real/home'
import { apiGet } from './http'


export const courseApi = courseReal
export const contestApi = contestReal
export const homeApi = homeReal

export async function getStartMessage() {
  // Django exposes this under /backend/start/ (proxied in vue.config.js).
  return apiGet('backend/start/')
}

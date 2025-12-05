import { apiGet } from '../http'

export async function getCourses() {
  const data = await apiGet('courses/tree/')
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  return []
}

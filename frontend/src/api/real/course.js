import { apiGet } from '../http'

export async function getCourses() {
  const data = await apiGet('api/courses/tree/')
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.items)) return data.items
  return []
}

export async function getCourse(courseId) {
  if (courseId == null || courseId === '') {
    return null
  }
  return await apiGet(`backend/course/${courseId}/`)
}

export async function getSection(sectionId) {
  if (sectionId == null || sectionId === '') {
    return null
  }
  // Get the full tree and find the section
  const tree = await getCourses()
  
  const findSection = (items, id) => {
    for (const item of items) {
      if (item.type === 'section' && item.id === id) {
        return item
      }
      if (item.children && item.children.length > 0) {
        const found = findSection(item.children, id)
        if (found) return found
      }
    }
    return null
  }
  
  return findSection(tree, Number(sectionId))
}

import { courseApi } from '@/api'

let _loadPromise = null
let _loadedAt = 0
let _sectionsById = new Map()
let _coursesById = new Map()
let _userCacheKey = null

function _toIntOrNull(v) {
  if (v == null || v === '') return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

function _buildMaps(tree) {
  _sectionsById = new Map()
  _coursesById = new Map()

  const walk = (nodes, parentSectionId = null) => {
    const list = Array.isArray(nodes) ? nodes : []
    for (const node of list) {
      if (!node || node.id == null) continue
      const id = Number(node.id)
      if (!Number.isFinite(id)) continue

      if (node.type === 'section') {
        _sectionsById.set(id, {
          id,
          title: node.title || `Раздел ${id}`,
          parent_id: _toIntOrNull(node.parent_id),
        })
        walk(node.children, id)
        continue
      }

      if (node.type === 'course') {
        _coursesById.set(id, {
          id,
          title: node.title || `Курс ${id}`,
          section_id: parentSectionId,
        })
      }
    }
  }

  walk(tree, null)
}

export async function ensureCourseTreeLoaded({ force = false } = {}) {
  if (!force && _sectionsById.size && _coursesById.size) return
  if (!force && _loadPromise) return _loadPromise

  _loadPromise = (async () => {
    try {
      const tree = await courseApi.getCourses()
      _buildMaps(tree)
      _loadedAt = Date.now()
    } finally {
      _loadPromise = null
    }
  })()

  return _loadPromise
}

export function resetCourseTreeCache({ userCacheKey = null } = {}) {
  _loadPromise = null
  _loadedAt = 0
  _sectionsById = new Map()
  _coursesById = new Map()
  _userCacheKey = userCacheKey
}

export function getCourseTreeCacheKey() {
  return _userCacheKey
}

export function getCourseTreeLoadedAt() {
  return _loadedAt
}

export function getSectionById(sectionId) {
  const id = Number(sectionId)
  if (!Number.isFinite(id)) return null
  return _sectionsById.get(id) || null
}

export function getCourseById(courseId) {
  const id = Number(courseId)
  if (!Number.isFinite(id)) return null
  return _coursesById.get(id) || null
}

export function getSectionChain(sectionId, { maxDepth = 32 } = {}) {
  const chain = []
  let current = getSectionById(sectionId)
  let depth = 0

  while (current && depth < maxDepth) {
    chain.push(current)
    depth += 1
    if (current.parent_id == null) break
    current = getSectionById(current.parent_id)
  }

  // Root -> leaf
  return chain.reverse()
}

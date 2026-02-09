<template>
  <nav v-if="items.length" class="crumbs" aria-label="Навигация">
    <div class="crumbs__inner">
      <template v-for="(item, idx) in items" :key="item.key">
        <span v-if="idx !== 0" class="crumbs__sep" aria-hidden="true">/</span>

        <router-link
          v-if="item.to && idx !== items.length - 1"
          :to="item.to"
          class="crumbs__link"
          :title="item.title"
        >
          <span class="crumbs__label">{{ item.label }}</span>
        </router-link>

        <span v-else class="crumbs__current" :title="item.title">
          <span class="crumbs__label">{{ item.label }}</span>
        </span>
      </template>
    </div>
  </nav>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { contestApi } from '@/api'
import { ensureCourseTreeLoaded, getCourseById, getSectionChain } from '@/utils/courseTreeCache'

const props = defineProps({
  section: { type: Object, default: null },
  course: { type: Object, default: null },
  contest: { type: Object, default: null },
  problem: { type: Object, default: null },
})

const route = useRoute()
const items = ref([])
const fetchedContest = ref(null)

const routeName = computed(() => String(route.name || ''))
const routeId = computed(() => Number(route.params.id))

const contestFromQuery = computed(() => {
  const v = route.query.contest
  const raw = Array.isArray(v) ? v[0] : v
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
})

const _titleFromQuery = (key) => {
  const v = route.query[key]
  const raw = Array.isArray(v) ? v[0] : v
  return raw ? String(raw) : ''
}

const _pushHome = (list) => {
  list.push({
    key: 'home',
    label: 'Главная',
    title: 'Главная',
    to: { name: 'home' },
  })
}

const _pushSectionChain = (list, sectionId) => {
  const chain = getSectionChain(sectionId)
  for (const sec of chain) {
    list.push({
      key: `section:${sec.id}`,
      label: sec.title,
      title: sec.title,
      to: { name: 'section', params: { id: sec.id }, query: { title: sec.title } },
    })
  }
}

const _courseTitle = (courseId) => {
  const fromProp = props.course?.title
  if (fromProp) return String(fromProp)
  const fromTree = getCourseById(courseId)?.title
  if (fromTree) return String(fromTree)
  const fromQuery = _titleFromQuery('course_title') || _titleFromQuery('title')
  if (fromQuery) return fromQuery
  return `Курс ${courseId}`
}

const _contestTitle = (contestId) => {
  const fromProp = props.contest?.title || fetchedContest.value?.title
  if (fromProp) return String(fromProp)
  const fromQuery = _titleFromQuery('title')
  if (fromQuery) return fromQuery
  return `Контест ${contestId}`
}

const _problemTitle = (problemId) => {
  const fromProp = props.problem?.title
  if (fromProp) return String(fromProp)
  return `Задача ${problemId}`
}

const refresh = async () => {
  const name = routeName.value
  if (name === 'home' || name === 'start') {
    items.value = []
    return
  }

  // Best-effort: build path from cached tree + optional context.
  try {
    await ensureCourseTreeLoaded()
  } catch (e) {
    // Ignore; breadcrumbs will be partial.
  }

  const list = []
  _pushHome(list)

  let sectionId = null
  let courseId = null
  let contestId = null

  fetchedContest.value = null

  if (name === 'section') {
    sectionId = Number(props.section?.id || routeId.value)
  }

  if (name === 'course') {
    courseId = Number(props.course?.id || routeId.value)
    sectionId = Number(props.course?.section || getCourseById(courseId)?.section_id || props.section?.id || null)
  }

  if (name === 'contest' || name === 'contest-leaderboard') {
    contestId = Number(props.contest?.id || routeId.value)
    courseId = Number(props.contest?.course || props.contest?.course_id || null)
    if (!courseId && props.contest?.course_id) courseId = Number(props.contest.course_id)
    if (contestId && !courseId) {
      try {
        const c = await contestApi.getContest(contestId)
        fetchedContest.value = c
        courseId = Number(c?.course || null)
      } catch (e) {
        // ignore
      }
    }
  }

  if (name === 'problem') {
    contestId = contestFromQuery.value

    // When opened from a contest page we pass ?contest=<id> so we can reconstruct the full path.
    if (contestId) {
      try {
        const c = await contestApi.getContest(contestId)
        fetchedContest.value = c
        courseId = Number(c?.course || null)
      } catch (e) {
        // ignore, show partial crumbs
      }
    }
  }

  if (courseId && !sectionId) {
    sectionId = Number(getCourseById(courseId)?.section_id || null)
  }

  if (sectionId) {
    _pushSectionChain(list, sectionId)
    // Fallback if the section is not present in cached tree (e.g., limited permissions).
    const hasCurrentSection = list.some((x) => x.key === `section:${Number(sectionId)}`)
    if (!hasCurrentSection) {
      const title =
        String(props.section?.title || _titleFromQuery('title') || `Раздел ${sectionId}`)
      list.push({
        key: `section:${Number(sectionId)}`,
        label: title,
        title,
        to: { name: 'section', params: { id: Number(sectionId) }, query: { title } },
      })
    }
  }

  if (courseId) {
    const title = _courseTitle(courseId)
    list.push({
      key: `course:${courseId}`,
      label: title,
      title,
      to: { name: 'course', params: { id: courseId }, query: { title } },
    })
  }

  if (contestId) {
    const title = _contestTitle(contestId)
    list.push({
      key: `contest:${contestId}`,
      label: title,
      title,
      to: { name: 'contest', params: { id: contestId }, query: { title } },
    })
  }

  // If we're on problem page, ensure the "problem" crumb is last and non-clickable.
  if (name === 'problem') {
    const pid = Number(props.problem?.id || routeId.value)
    const title = _problemTitle(pid)
    list.push({
      key: `problem:${pid}`,
      label: title,
      title,
      to: null,
    })
  } else {
    // Mark current page crumb as last (no to) by wiping to on last item.
    if (list.length) {
      const last = list[list.length - 1]
      list[list.length - 1] = { ...last, to: null }
    }
  }

  // Drop duplicates (can happen with problem logic).
  const seen = new Set()
  const uniq = []
  for (const it of list) {
    if (seen.has(it.key)) continue
    seen.add(it.key)
    uniq.push(it)
  }
  items.value = uniq
}

onMounted(refresh)
watch(
  () => [routeName.value, route.fullPath, props.section?.id, props.course?.id, props.contest?.id, props.problem?.id],
  refresh
)
</script>

<style scoped>
.crumbs {
  width: 100%;
  padding: 10px 0 0;
}

.crumbs__inner {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 6px 12px;
  border-radius: 12px;
  background: rgba(22, 33, 89, 0.06);
  border: 1px solid rgba(22, 33, 89, 0.10);
}

.crumbs__sep {
  color: rgba(22, 33, 89, 0.45);
  flex: 0 0 auto;
}

.crumbs__link,
.crumbs__current {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: clamp(110px, 18vw, 240px);
  color: rgba(22, 33, 89, 0.92);
}

.crumbs__link {
  text-decoration: none;
  border-radius: 8px;
  padding: 4px 6px;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.crumbs__link:hover {
  background: rgba(22, 33, 89, 0.08);
}

.crumbs__current {
  font-weight: 600;
}

.crumbs__label {
  display: inline-block;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

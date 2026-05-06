<template>
  <div class="ui-search" ref="root">
    <div class="ui-search__controls">
      <div class="ui-search__select-wrapper" @click="toggleTypeDropdown">
        <div class="ui-search__select">
          {{ selectedTypeLabel }}
        </div>
        <span class="material-symbols-rounded ui-search__select-arrow" :class="{ 'ui-search__select-arrow--open': showTypeDropdown }">expand_more</span>
      </div>

      <div class="ui-search__input-wrapper">
        <span class="material-symbols-rounded ui-search__icon">search</span>
        <input
          v-model="query"
          type="search"
          class="ui-search__input"
          placeholder="Поиск..."
          autocomplete="off"
          @input="onInput"
          @focus="showResults = true"
        />
      </div>
    </div>

    <div v-if="showTypeDropdown" class="ui-search-type-dropdown">
      <div
        class="ui-search-type-item"
        :class="{ 'ui-search-type-item--selected': selectedType === 'all' }"
        @click="selectType('all')"
      >
        <span class="material-symbols-rounded ui-search-type-item__icon">search</span>
        Везде
      </div>
      <div
        class="ui-search-type-item"
        :class="{ 'ui-search-type-item--selected': selectedType === 'course' }"
        @click="selectType('course')"
      >
        <span class="material-symbols-rounded ui-search-type-item__icon">school</span>
        Курсы
      </div>
      <div
        class="ui-search-type-item"
        :class="{ 'ui-search-type-item--selected': selectedType === 'problem' }"
        @click="selectType('problem')"
      >
        <span class="material-symbols-rounded ui-search-type-item__icon">extension</span>
        Задачи
      </div>
      <div
        class="ui-search-type-item"
        :class="{ 'ui-search-type-item--selected': selectedType === 'contest' }"
        @click="selectType('contest')"
      >
        <span class="material-symbols-rounded ui-search-type-item__icon">emoji_events</span>
        Контесты
      </div>
    </div>

    <div v-if="showResults && hasResults" class="ui-search-dropdown">
      <template v-if="results.courses?.length">
        <div class="ui-search-group">
          <div class="ui-search-group__title">
            <span class="material-symbols-rounded ui-search-group__icon">school</span>
            Курсы
          </div>
          <div
            v-for="c in results.courses"
            :key="'course'+c.id"
            class="ui-search-item"
            @click="openCourse(c)"
          >
            <span class="material-symbols-rounded ui-search-item__icon">menu_book</span>
            <span class="ui-search-item__title">{{ c.title }}</span>
          </div>
        </div>
      </template>

      <template v-if="results.problems?.length">
        <div class="ui-search-group">
          <div class="ui-search-group__title">
            <span class="material-symbols-rounded ui-search-group__icon">code</span>
            Задачи
          </div>
          <div
            v-for="p in results.problems"
            :key="'problem'+p.id"
            class="ui-search-item"
            @click="openProblem(p)"
          >
            <span class="material-symbols-rounded ui-search-item__icon">extension</span>
            <span class="ui-search-item__title">{{ p.title }}</span>
            <span class="ui-search-item__meta">{{ p.rating }}</span>
          </div>
        </div>
      </template>

      <template v-if="results.contests?.length">
        <div class="ui-search-group">
          <div class="ui-search-group__title">
            <span class="material-symbols-rounded ui-search-group__icon">emoji_events</span>
            Контесты
          </div>
          <div
            v-for="c in results.contests"
            :key="'contest'+c.id"
            class="ui-search-item"
            @click="openContest(c)"
          >
            <span class="material-symbols-rounded ui-search-item__icon">workspace_premium</span>
            <span class="ui-search-item__title">{{ c.title }}</span>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { search } from '@/api/search'

const router = useRouter()
const root = ref(null)
const query = ref('')
const selectedType = ref('all')
const showTypeDropdown = ref(false)
const results = reactive({
  courses: [],
  problems: [],
  contests: []
})
const showResults = ref(false)
let timer = null

const selectedTypeLabel = computed(() => {
  const map = {
    all: 'Везде',
    course: 'Курсы',
    problem: 'Задачи',
    contest: 'Контесты'
  }
  return map[selectedType.value]
})

const hasResults = computed(() =>
  (results.courses?.length ?? 0) +
  (results.problems?.length ?? 0) +
  (results.contests?.length ?? 0) > 0
)

watch(selectedType, () => {
  onInput(true)
  showTypeDropdown.value = false
})

const toggleTypeDropdown = () => {
  showTypeDropdown.value = !showTypeDropdown.value
}

const selectType = (type) => {
  selectedType.value = type
}

const onInput = (force = false) => {
  if (timer) clearTimeout(timer)

  const exec = async () => {
    const q = query.value.trim()
    if (!q) {
      results.courses = []
      results.problems = []
      results.contests = []
      showResults.value = false
      return
    }

    try {
      const res = await search({
        q,
        type: selectedType.value
      })

      results.courses = res.courses ?? []
      results.problems = res.problems ?? []
      results.contests = res.contests ?? []
      showResults.value = true
    } catch (err) {
      console.error(err)
    }
  }

  if (force) {
    exec()
  } else {
    timer = setTimeout(exec, 250)
  }
}

const openCourse = (course) => {
  showResults.value = false
  router.push({ name: 'course', params: { id: course.id } })
}

const openProblem = (problem) => {
  showResults.value = false
  router.push({ name: 'problem', params: { id: problem.id } })
}

const openContest = (contest) => {
  showResults.value = false
  router.push({ name: 'contest', params: { id: contest.id } })
}

const handleClickOutside = (event) => {
  if (!root.value) return
  if (!root.value.contains(event.target)) {
    showResults.value = false
    showTypeDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.ui-search {
  position: relative;
  width: 480px;
}

.ui-search__controls {
  display: flex;
  align-items: center;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-default);
  border-radius: 12px;
  transition: all 0.2s ease;
}

.ui-search__controls:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(39, 52, 106, 0.1);
}

.ui-search__select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  height: 48px;
  min-width: 130px;
  background: var(--color-bg-muted);
  border-right: 1px solid var(--color-border-light);
  border-radius: 12px 0 0 12px;
  cursor: pointer;
  padding: 0 36px 0 16px;
}

.ui-search__select-wrapper:hover {
  background: var(--color-bg-primary);
}

.ui-search__select {
  font-family: var(--font-default);
  font-size: 15px;
  color: var(--color-text-primary);
  white-space: nowrap;
}

.ui-search__select-arrow {
  position: absolute;
  right: 12px;
  color: var(--color-text-muted);
  font-size: 20px;
  transition: transform 0.2s ease;
}

.ui-search__select-arrow--open {
  transform: rotate(180deg);
}

.ui-search-type-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  width: 180px;
  background: var(--color-bg-card);
  border-radius: 12px;
  border: 1px solid var(--color-border-default);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 1001;
  padding: 6px;
}

.ui-search-type-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  font-family: var(--font-default);
  font-size: 14px;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.ui-search-type-item:hover {
  background: var(--color-bg-primary);
}

.ui-search-type-item--selected {
  background: var(--color-bg-primary);
  color: var(--color-primary);
  font-weight: 500;
}

.ui-search-type-item__icon {
  font-size: 18px;
  color: var(--color-text-muted);
}

.ui-search-type-item--selected .ui-search-type-item__icon {
  color: var(--color-primary);
}

.ui-search__input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 12px;
  background: var(--color-bg-card);
  border-radius: 0 12px 12px 0;
}

.ui-search__icon {
  font-size: 20px;
  color: var(--color-text-muted);
  margin-right: 8px;
}

.ui-search__input {
  flex: 1;
  height: 48px;
  border: none;
  background: transparent;
  font-family: var(--font-default);
  font-size: 15px;
  color: var(--color-text-primary);
  outline: none;
}

.ui-search__input::placeholder {
  color: var(--color-text-muted);
  opacity: 0.5;
}

.ui-search__input::-webkit-search-cancel-button {
  -webkit-appearance: none;
  height: 18px;
  width: 18px;
  background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%235C6280"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>');
  cursor: pointer;
  opacity: 0.5;
}

.ui-search__input::-webkit-search-cancel-button:hover {
  opacity: 0.8;
}

.ui-search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  max-height: 480px;
  overflow-y: auto;
  background: var(--color-bg-card);
  border-radius: 16px;
  border: 1px solid var(--color-border-default);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
  z-index: 1000;
  padding: 8px 0;
}

.ui-search-group {
  padding: 8px 0;
}

.ui-search-group:not(:last-child) {
  border-bottom: 1px solid var(--color-border-light);
}

.ui-search-group__title {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-muted);
}

.ui-search-group__icon {
  font-size: 16px;
  margin-right: 8px;
  color: var(--color-text-muted);
}

.ui-search-item {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  transition: background-color 0.15s ease;
  gap: 12px;
}

.ui-search-item:hover {
  background: var(--color-bg-primary);
}

.ui-search-item__icon {
  font-size: 20px;
  color: var(--color-primary);
  opacity: 0.7;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 20;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.ui-search-item__title {
  flex: 1;
  font-size: 14px;
  font-weight: 400;
  color: var(--color-text-primary);
  line-height: 1.4;
}

.ui-search-item__meta {
  font-size: 12px;
  color: var(--color-text-muted);
  background: var(--color-bg-muted);
  padding: 4px 8px;
  border-radius: 20px;
  font-weight: 500;
  white-space: nowrap;
}

.ui-search-dropdown::-webkit-scrollbar {
  width: 6px;
}

.ui-search-dropdown::-webkit-scrollbar-track {
  background: var(--color-bg-muted);
  border-radius: 0 16px 16px 0;
}

.ui-search-dropdown::-webkit-scrollbar-thumb {
  background: var(--color-border-default);
  border-radius: 6px;
}

.ui-search-dropdown::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-muted);
}
</style>
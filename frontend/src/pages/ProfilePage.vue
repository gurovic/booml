<template>
  <div class="page">
    <UiHeader />
    <div class="container">
      <UiBreadcrumbs :profile="profile" />
    </div>

    <div class="profile">
      <div class="container">

        <div class="profile__inner">
          <div class="profile__header">
            <h1 class="profile__title">Профиль</h1>
          </div>

          <div v-if="loading" class="profile__loading">
            Загрузка профиля...
          </div>

          <div v-else-if="error" class="profile__error">
            {{ error }}
          </div>

          <template v-else-if="profile">
            <div class="profile__user-card user-card">
              <div class="user-card__avatar-wrapper">
                <div class="user-card__avatar" @click="triggerFileUpload">
                  <img
                    v-if="profile.avatar_url"
                    :src="profile.avatar_url"
                    :alt="fullName"
                    class="user-card__avatar-image"
                  >
                  <div v-else class="user-card__avatar-placeholder">
                    {{ userInitials }}
                  </div>
                  <div class="user-card__avatar-overlay">
                    <span>Изменить</span>
                  </div>
                </div>

                <input
                  type="file"
                  ref="fileInput"
                  @change="uploadAvatar"
                  accept="image/jpeg,image/png,image/gif"
                  class="user-card__avatar-input"
                >
              </div>

              <div class="user-card__info">
                <div class="user-card__name-section">
                  <div v-if="!isEditingName" class="user-card__name-display">
                    <h2 class="user-card__name">{{ fullName }}</h2>
                    <button
                      @click="startEditName"
                      class="user-card__edit-button"
                      title="Редактировать имя"
                    >
                      ✏️
                    </button>
                  </div>

                  <div v-else class="user-card__name-edit">
                    <input
                      v-model="editFirstName"
                      placeholder="Имя"
                      class="user-card__name-input"
                    >
                    <input
                      v-model="editLastName"
                      placeholder="Фамилия"
                      class="user-card__name-input"
                    >
                    <div class="user-card__edit-actions">
                      <button @click="saveName" class="button button--primary">
                        Сохранить
                      </button>
                      <button @click="cancelEditName" class="button button--secondary">
                        Отмена
                      </button>
                    </div>
                  </div>
                </div>

                <p class="user-card__email">{{ profile.email }}</p>
                <span class="user-card__role">{{ userRole }}</span>
              </div>
            </div>

            <section class="profile__activity activity-section">
              <div class="activity-section__header">
                <h3 class="activity-section__title">Календарь активности</h3>
                <div class="activity-section__controls">
                  <button
                    class="activity-section__mode-button"
                    :class="{ 'activity-section__mode-button--active': isRollingHeatmapMode }"
                    :disabled="activityYearLoading"
                    @click="selectRollingWindow"
                  >
                    Последние 365 дней
                  </button>

                  <label
                    v-if="availableActivityYears.length > 0"
                    class="activity-section__year-picker"
                    :class="{ 'activity-section__year-picker--active': !isRollingHeatmapMode }"
                  >
                    <span class="activity-section__year-label">Год</span>
                    <select
                      class="activity-section__year-select"
                      :class="{ 'activity-section__year-select--active': !isRollingHeatmapMode }"
                      :value="selectedHeatmapYear ?? ''"
                      :disabled="activityYearLoading"
                      @change="handleActivityYearChange"
                    >
                      <option value="">Выбрать</option>
                      <option
                        v-for="year in availableActivityYears"
                        :key="`activity-year-option-${year}`"
                        :value="year"
                      >
                        {{ year }}
                      </option>
                    </select>
                  </label>
                </div>
              </div>

              <div v-if="activityHeatmap" class="activity-section__stats">
                <div class="activity-stat">
                  <p class="activity-stat__value">{{ activityHeatmap.total_submissions || 0 }}</p>
                  <p class="activity-stat__label">всего посылок</p>
                </div>
                <div class="activity-stat">
                  <p class="activity-stat__value">{{ activityHeatmap.active_days || 0 }}</p>
                  <p class="activity-stat__label">активных {{ getDaysWord(activityHeatmap.active_days || 0) }}</p>
                </div>
                <div class="activity-stat">
                  <p class="activity-stat__value">{{ activityHeatmap.current_streak || 0 }}</p>
                  <p class="activity-stat__label">текущая серия дней</p>
                </div>
                <div class="activity-stat">
                  <p class="activity-stat__value">{{ activityHeatmap.best_streak || 0 }}</p>
                  <p class="activity-stat__label">лучшая серия дней</p>
                </div>
              </div>

              <div v-if="heatmapWeeks.length > 0" class="activity-heatmap">
                <div class="activity-heatmap__scroll">
                  <div
                    class="activity-heatmap__months"
                    :style="{ gridTemplateColumns: `repeat(${heatmapWeeks.length}, var(--heatmap-cell-size))` }"
                  >
                    <span
                      v-for="marker in heatmapMonthMarkers"
                      :key="`month-${marker.index}-${marker.label}`"
                      class="activity-heatmap__month"
                      :style="{ gridColumn: marker.index + 1 }"
                    >
                      {{ marker.label }}
                    </span>
                  </div>

                  <div class="activity-heatmap__content">
                    <div class="activity-heatmap__weekdays">
                      <span>Пн</span>
                      <span></span>
                      <span>Ср</span>
                      <span></span>
                      <span>Пт</span>
                      <span></span>
                      <span>Вс</span>
                    </div>

                    <div
                      class="activity-heatmap__weeks"
                      :style="{ gridTemplateColumns: `repeat(${heatmapWeeks.length}, var(--heatmap-cell-size))` }"
                    >
                      <div
                        v-for="(week, weekIndex) in heatmapWeeks"
                        :key="`week-${weekIndex}`"
                        class="activity-heatmap__week"
                      >
                        <div
                          v-for="(day, dayIndex) in week"
                          :key="day ? day.date : `empty-${weekIndex}-${dayIndex}`"
                          class="activity-heatmap__cell"
                          :class="day ? getHeatmapCellClass(day) : 'activity-heatmap__cell--empty'"
                          :title="day ? getHeatmapCellTitle(day) : ''"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="activity-heatmap__legend">
                  <span class="activity-heatmap__legend-text">Меньше</span>
                  <div class="activity-heatmap__legend-scale">
                    <span class="activity-heatmap__cell activity-heatmap__cell--level-0"></span>
                    <span class="activity-heatmap__cell activity-heatmap__cell--level-1"></span>
                    <span class="activity-heatmap__cell activity-heatmap__cell--level-2"></span>
                    <span class="activity-heatmap__cell activity-heatmap__cell--level-3"></span>
                    <span class="activity-heatmap__cell activity-heatmap__cell--level-4"></span>
                  </div>
                  <span class="activity-heatmap__legend-text">Больше</span>
                </div>
              </div>

              <div v-else class="submissions-section__empty">
                Пока нет активности
              </div>
            </section>

            <section class="profile__submissions submissions-section">
              <div class="submissions-section__header">
                <h3 class="submissions-section__title">Последние посылки</h3>
              </div>

              <div class="submissions-section__content">
                <ul v-if="submissions.length > 0" class="submissions-list">
                  <li class="submissions-list__head">
                    <p>ID</p>
                    <p>Задача</p>
                    <p>Время</p>
                    <p>Статус</p>
                    <p>Метрика</p>
                  </li>
                  <li
                    v-for="sub in submissions"
                    :key="sub.id"
                    class="submissions-list__item"
                  >
                    <router-link
                      :to="`/submission/${sub.id}/`"
                      class="submissions-list__link"
                    >
                      <p>{{ sub.id }}</p>
                      <p>{{ formatTaskTitle(sub.problem_title) }}</p>
                      <p>{{ formatDate(sub.submitted_at) }}</p>
                      <p>{{ getStatusLabel(sub.status) }}</p>
                      <p>{{ formatMetric(sub.metrics) }}</p>
                    </router-link>
                  </li>
                </ul>

                <div v-else class="submissions-section__empty">
                  Нет посылок
                </div>
              </div>
            </section>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { getCurrentProfile, updateProfileInfo, uploadProfileAvatar } from '@/api/profile'
import { getMySubmissions } from '@/api/submission'
import { useUserStore } from '@/stores/UserStore'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'

const RECENT_SUBMISSIONS_REFRESH_MS = 5000

export default {
  name: 'ProfilePage',
  components: {
    UiHeader,
    UiBreadcrumbs
  },
  data() {
    return {
      profile: null,
      submissions: [],
      loading: false,
      error: null,
      fileInput: null,
      isEditingName: false,
      editFirstName: '',
      editLastName: '',
      activityYearLoading: false,
      submissionsRefreshTimer: null,
      submissionsRefreshInFlight: false,
      userStore: null
    }
  },
  computed: {
    breadcrumbs() {
      return [
        { key: 'home', label: 'Главная', to: { name: 'home' } },
        { key: 'profile', label: 'Профиль', to: null }
      ]
    },

    userInitials() {
      if (this.profile?.first_name && this.profile?.last_name) {
        return `${this.profile.first_name[0]}${this.profile.last_name[0]}`.toUpperCase()
      }
      if (this.profile?.username) {
        return this.profile.username.slice(0, 2).toUpperCase()
      }
      return '??'
    },

    fullName() {
      if (this.profile?.first_name || this.profile?.last_name) {
        return `${this.profile.first_name || ''} ${this.profile.last_name || ''}`.trim()
      }
      return this.profile?.username || 'Пользователь'
    },

    userRole() {
      const roles = {
        'student': 'Ученик',
        'teacher': 'Учитель'
      }
      return roles[this.profile?.role] || 'Ученик'
    },

    isAuthenticated() {
      return this.userStore?.isAuthenticated || false
    },

    activityHeatmap() {
      return this.profile?.activity_heatmap || null
    },

    selectedHeatmapYear() {
      const fromApi = Number(this.activityHeatmap?.selected_year)
      return Number.isInteger(fromApi) ? fromApi : null
    },

    isRollingHeatmapMode() {
      return this.activityHeatmap?.period_type !== 'year'
    },

    availableActivityYears() {
      const years = this.activityHeatmap?.available_years
      if (!Array.isArray(years)) {
        return []
      }

      return years
        .map(value => Number(value))
        .filter(value => Number.isInteger(value))
        .sort((a, b) => b - a)
    },

    heatmapDays() {
      const days = this.activityHeatmap?.days
      return Array.isArray(days) ? days : []
    },

    heatmapWeeks() {
      if (!this.heatmapDays.length) {
        return []
      }

      const firstDate = this.parseIsoDate(this.heatmapDays[0].date)
      const leadingPadding = this.getWeekdayIndex(firstDate)
      const paddedDays = [
        ...Array.from({ length: leadingPadding }, () => null),
        ...this.heatmapDays
      ]
      const trailingPadding = (7 - (paddedDays.length % 7)) % 7
      paddedDays.push(...Array.from({ length: trailingPadding }, () => null))

      const weeks = []
      for (let i = 0; i < paddedDays.length; i += 7) {
        weeks.push(paddedDays.slice(i, i + 7))
      }
      return weeks
    },

    heatmapMonthMarkers() {
      const markers = []
      let previousMonth = null

      this.heatmapWeeks.forEach((week, index) => {
        const firstVisibleDay = week.find(day => !!day)
        if (!firstVisibleDay) {
          return
        }

        const date = this.parseIsoDate(firstVisibleDay.date)
        if (isNaN(date.getTime())) {
          return
        }

        const month = date.getMonth()
        if (month !== previousMonth) {
          markers.push({
            index,
            label: this.formatMonthLabel(date)
          })
          previousMonth = month
        }
      })

      return markers
    }
  },
  methods: {
    async selectRollingWindow() {
      if (this.isRollingHeatmapMode || this.activityYearLoading) {
        return
      }

      this.activityYearLoading = true
      try {
        await this.loadProfileData({ silent: true })
      } finally {
        this.activityYearLoading = false
      }
    },

    async selectActivityYear(year) {
      const parsedYear = Number(year)
      if (!Number.isInteger(parsedYear)) {
        return
      }
      if (
        !this.isRollingHeatmapMode &&
        parsedYear === this.selectedHeatmapYear
      ) {
        return
      }
      if (this.activityYearLoading) {
        return
      }

      this.activityYearLoading = true
      try {
        await this.loadProfileData({ year: parsedYear, silent: true })
      } finally {
        this.activityYearLoading = false
      }
    },

    async handleActivityYearChange(event) {
      const value = event?.target?.value ?? ''
      if (!value) {
        await this.selectRollingWindow()
        return
      }

      await this.selectActivityYear(Number(value))
    },

    parseIsoDate(value) {
      if (typeof value !== 'string') {
        return new Date(NaN)
      }
      const [year, month, day] = value.split('-').map(Number)
      return new Date(year, month - 1, day)
    },

    getWeekdayIndex(date) {
      if (!(date instanceof Date) || isNaN(date.getTime())) {
        return 0
      }
      return (date.getDay() + 6) % 7
    },

    formatMonthLabel(date) {
      return date.toLocaleDateString('ru-RU', { month: 'short' }).replace('.', '')
    },

    formatHeatmapDate(dateString) {
      const date = this.parseIsoDate(dateString)
      if (isNaN(date.getTime())) {
        return dateString
      }
      return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      })
    },

    getSubmissionsWord(count) {
      const value = Math.abs(Number(count) || 0)
      const lastTwo = value % 100
      const last = value % 10

      if (lastTwo >= 11 && lastTwo <= 14) {
        return 'посылок'
      }
      if (last === 1) {
        return 'посылка'
      }
      if (last >= 2 && last <= 4) {
        return 'посылки'
      }
      return 'посылок'
    },

    getDaysWord(count) {
      const value = Math.abs(Number(count) || 0)
      const lastTwo = value % 100
      const last = value % 10

      if (lastTwo >= 11 && lastTwo <= 14) {
        return 'дней'
      }
      if (last === 1) {
        return 'день'
      }
      if (last >= 2 && last <= 4) {
        return 'дня'
      }
      return 'дней'
    },

    getHeatmapCellLevel(day) {
      const rawLevel = Number(day?.level)
      if (!Number.isFinite(rawLevel)) {
        return 0
      }
      return Math.min(4, Math.max(0, Math.round(rawLevel)))
    },

    getHeatmapCellClass(day) {
      return `activity-heatmap__cell--level-${this.getHeatmapCellLevel(day)}`
    },

    getHeatmapCellTitle(day) {
      if (!day) {
        return ''
      }

      const count = Number(day.count) || 0
      return `${this.formatHeatmapDate(day.date)}: ${count} ${this.getSubmissionsWord(count)}`
    },

    formatDate(dateString) {
      if (!dateString) return '-'
      try {
        const date = new Date(dateString)
        if (isNaN(date.getTime())) return dateString

        const day = String(date.getDate()).padStart(2, '0')
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const year = date.getFullYear()
        const hours = String(date.getHours()).padStart(2, '0')
        const minutes = String(date.getMinutes()).padStart(2, '0')

        return `${day}.${month}.${year} ${hours}:${minutes}`
      } catch {
        return dateString
      }
    },

    getStatusLabel(status) {
      const statusMap = {
        'pending': '⏳ В очереди',
        'running': '🏃 Выполняется',
        'accepted': '✅ Протестировано',
        'failed': '❌ Ошибка',
        'validation_error': '⚠️ Ошибка валидации',
        'validated': '✅ Валидировано'
      }
      return statusMap[status] || status
    },

    getStatusClass(status) {
      const baseClass = 'status'
      const statusClasses = {
        'accepted': 'status--tested',
        'validated': 'status--tested',
        'failed': 'status--error',
        'validation_error': 'status--error',
        'pending': 'status--pending',
        'running': 'status--pending'
      }
      return `${baseClass} ${statusClasses[status] || ''}`
    },

    formatMetric(metrics) {
      if (!metrics) return '–'
      if (typeof metrics === 'number') return metrics.toFixed(5)
      if (metrics?.accuracy) return metrics.accuracy.toFixed(5)
      if (typeof metrics === 'object') {
        const numValue = Object.values(metrics).find(v => typeof v === 'number')
        if (numValue) return numValue.toFixed(5)
      }
      return '–'
    },

    formatTaskTitle(title) {
      if (!title) return 'Без названия'
      return title.length > 30 ? title.slice(0, 27) + '...' : title
    },

    navigateToSubmission(submissionId) {
      this.$router.push(`/submission/${submissionId}/`)
    },

    normalizeSubmissionList(payload) {
      if (Array.isArray(payload)) return payload
      if (Array.isArray(payload?.results)) return payload.results
      if (Array.isArray(payload?.submissions)) return payload.submissions
      return []
    },

    async refreshRecentSubmissions() {
      if (!this.isAuthenticated || this.submissionsRefreshInFlight) return
      if (typeof document !== 'undefined' && document.hidden) return

      this.submissionsRefreshInFlight = true
      try {
        const data = await getMySubmissions()
        this.submissions = this.normalizeSubmissionList(data).slice(0, 4)
      } catch (_) {
        // Keep the current list on transient refresh errors.
      } finally {
        this.submissionsRefreshInFlight = false
      }
    },

    startSubmissionsPolling() {
      if (this.submissionsRefreshTimer != null) return
      this.submissionsRefreshTimer = window.setInterval(() => {
        this.refreshRecentSubmissions()
      }, RECENT_SUBMISSIONS_REFRESH_MS)
    },

    stopSubmissionsPolling() {
      if (this.submissionsRefreshTimer == null) return
      window.clearInterval(this.submissionsRefreshTimer)
      this.submissionsRefreshTimer = null
    },

    triggerFileUpload() {
      this.$refs.fileInput.click()
    },

    async uploadAvatar(event) {
      const file = event.target.files[0]
      if (!file) return

      if (file.size > 5 * 1024 * 1024) {
        alert('Файл слишком большой. Максимальный размер 5MB')
        return
      }

      if (!file.type.startsWith('image/')) {
        alert('Пожалуйста, выберите изображение')
        return
      }

      try {
        this.profile = await uploadProfileAvatar(file)
      } catch (error) {
        console.error('Upload error:', error)
        alert('Ошибка при загрузке аватара')
      } finally {
        event.target.value = ''
      }
    },

    startEditName() {
      this.editFirstName = this.profile?.first_name || ''
      this.editLastName = this.profile?.last_name || ''
      this.isEditingName = true
    },

    cancelEditName() {
      this.isEditingName = false
    },

    async saveName() {
      if (!this.editFirstName && !this.editLastName) {
        alert('Заполните хотя бы одно поле')
        return
      }

      try {
        this.profile = await updateProfileInfo({
          first_name: this.editFirstName,
          last_name: this.editLastName
        })
        this.isEditingName = false
      } catch {
        alert('Ошибка при обновлении имени')
      }
    },

    async loadProfileData(options = {}) {
      const { year = null, silent = false } = options

      if (!silent) {
        this.loading = true
        this.error = null
      }

      try {
        if (!this.isAuthenticated) {
          await this.userStore.checkAuth()
        }

        const params = {}
        const parsedYear = Number(year)
        if (Number.isInteger(parsedYear)) {
          params.year = parsedYear
        }

        this.profile = await getCurrentProfile(params)

        if (!this.profile) {
          throw new Error('Профиль не найден')
        }

        this.submissions = this.profile.recent_submissions || []
      } catch (err) {
        console.error('Failed to load profile:', err)
        if (silent) {
          alert('Не удалось загрузить активность за выбранный год')
          return
        }

        this.error = 'Не удалось загрузить профиль'
        this.submissions = []
      } finally {
        if (!silent) {
          this.loading = false
        }
      }
    }
  },
  async created() {
    this.userStore = useUserStore()
  },
  mounted() {
    this.loadProfileData()
    this.startSubmissionsPolling()
  },
  beforeUnmount() {
    this.stopSubmissionsPolling()
  }
}
</script>

<style scoped>
.profile {
  width: 100%;
  min-height: 100vh;
  padding: 20px 0;
  background: var(--color-bg);
}

.profile__inner {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile__header {
  padding: 32px 40px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.profile__title {
  font-size: 48px;
  font-weight: 400;
  line-height: 1.2;
  color: var(--color-title-text);
  padding-left: 16px;
  border-left: 6px solid var(--color-primary);
}

.profile__loading,
.profile__error {
  padding: 40px;
  text-align: center;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  font-size: 18px;
}

.profile__error {
  color: var(--color-error-text);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 30px;
  padding: 32px 40px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.user-card__avatar-wrapper {
  flex-shrink: 0;
}

.user-card__avatar {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: var(--color-bg-light);
  overflow: hidden;
  position: relative;
  cursor: pointer;
}

.user-card__avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-card__avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  color: white;
  font-size: 36px;
  font-weight: 600;
}

.user-card__avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  opacity: 0;
  transition: opacity 0.3s;
  border-radius: 50%;
}

.user-card__avatar:hover .user-card__avatar-overlay {
  opacity: 1;
}

.user-card__avatar-input {
  display: none;
}

.user-card__info {
  flex: 1;
}

.user-card__name-section {
  margin-bottom: 8px;
}

.user-card__name-display {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-card__name {
  margin: 0;
  font-size: 28px;
  font-weight: 600;
  color: var(--color-title-text);
}

.user-card__edit-button {
  background: none;
  border: none;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 18px;
  opacity: 0.5;
  transition: opacity 0.3s;
}

.user-card__edit-button:hover {
  opacity: 1;
}

.user-card__name-edit {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 300px;
}

.user-card__name-input {
  padding: 8px 12px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  font-size: 16px;
  background: var(--color-bg-light);
  color: var(--color-text-primary);
}

.user-card__name-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.user-card__edit-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.user-card__email {
  margin: 0 0 8px 0;
  color: var(--color-text-secondary);
  font-size: 16px;
}

.user-card__role {
  display: inline-block;
  padding: 6px 16px;
  background: var(--color-bg-light);
  color: var(--color-text-secondary);
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

.activity-section {
  padding: 32px 40px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.activity-section__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.activity-section__controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.activity-section__mode-button {
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 13px;
  line-height: 1;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.activity-section__mode-button:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: #eef2ff;
  color: var(--color-primary);
}

.activity-section__mode-button--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.activity-section__mode-button--active:hover:not(:disabled) {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.activity-section__mode-button:disabled {
  opacity: 0.65;
  cursor: default;
}

.activity-section__year-picker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.activity-section__year-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-muted);
}

.activity-section__year-select {
  border: 1px solid var(--color-border-default);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  border-radius: 10px;
  padding: 6px 10px;
  font-size: 13px;
  line-height: 1;
  font-weight: 500;
  min-width: 96px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.activity-section__year-select:hover:not(:disabled),
.activity-section__year-select:focus-visible {
  border-color: var(--color-primary);
  outline: none;
}

.activity-section__year-select:disabled {
  opacity: 0.65;
  cursor: default;
}

.activity-section__year-picker--active .activity-section__year-label {
  color: var(--color-primary);
}

.activity-section__year-select--active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.activity-section__year-select--active:hover:not(:disabled),
.activity-section__year-select--active:focus-visible {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.activity-section__title {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
  color: var(--color-title-text);
}

.activity-section__stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.activity-stat {
  padding: 12px 14px;
  border-radius: 12px;
  background: linear-gradient(140deg, #f5f7ff, #f9f7ff);
  border: 1px solid var(--color-border-light);
}

.activity-stat__value {
  margin: 0;
  font-size: 24px;
  line-height: 1.1;
  font-weight: 700;
  color: var(--color-primary);
}

.activity-stat__label {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.activity-heatmap {
  --heatmap-cell-size: 14px;
  --heatmap-cell-gap: 4px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.activity-heatmap__scroll {
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 4px;
}

.activity-heatmap__months {
  display: grid;
  column-gap: var(--heatmap-cell-gap);
  margin-left: 34px;
  margin-bottom: 8px;
  min-width: max-content;
}

.activity-heatmap__month {
  font-size: 12px;
  line-height: 1;
  color: var(--color-text-muted);
  text-transform: capitalize;
  white-space: nowrap;
}

.activity-heatmap__content {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  min-width: max-content;
}

.activity-heatmap__weekdays {
  width: 26px;
  display: grid;
  grid-template-rows: repeat(7, var(--heatmap-cell-size));
  row-gap: var(--heatmap-cell-gap);
}

.activity-heatmap__weekdays span {
  height: var(--heatmap-cell-size);
  font-size: 11px;
  line-height: var(--heatmap-cell-size);
  color: var(--color-text-muted);
}

.activity-heatmap__weeks {
  display: grid;
  column-gap: var(--heatmap-cell-gap);
}

.activity-heatmap__week {
  display: grid;
  grid-template-rows: repeat(7, var(--heatmap-cell-size));
  row-gap: var(--heatmap-cell-gap);
}

.activity-heatmap__cell {
  display: block;
  width: var(--heatmap-cell-size);
  height: var(--heatmap-cell-size);
  border-radius: 4px;
  transition: transform 0.15s ease, filter 0.15s ease;
}

.activity-heatmap__cell:not(.activity-heatmap__cell--empty):hover {
  transform: scale(1.12);
  filter: brightness(0.92);
}

.activity-heatmap__cell--empty {
  background: transparent;
  pointer-events: none;
}

.activity-heatmap__cell--level-0 {
  background: #edf1fb;
}

.activity-heatmap__cell--level-1 {
  background: #d8e1f7;
}

.activity-heatmap__cell--level-2 {
  background: #b4c5ee;
}

.activity-heatmap__cell--level-3 {
  background: #778fdc;
}

.activity-heatmap__cell--level-4 {
  background: #27346a;
}

.activity-heatmap__legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.activity-heatmap__legend-text {
  font-size: 12px;
  color: var(--color-text-muted);
}

.activity-heatmap__legend-scale {
  display: flex;
  gap: 4px;
}

.submissions-section {
  padding: 32px 40px;
  background: var(--color-bg-card);
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.submissions-section__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.submissions-section__title {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
  color: var(--color-title-text);
}

.submissions-section__view-all {
  text-decoration: none;
  padding: 10px 20px;
}

.submissions-section__empty {
  padding: 40px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 16px;
  background: var(--color-bg-light);
  border-radius: 12px;
}

.submissions-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.submissions-list__head,
.submissions-list__link {
  border-radius: 10px;
  padding: 15px 20px;
  width: 100%;
  display: grid;
  grid-template-columns: 0.5fr 1.5fr 1.2fr 1.2fr 0.8fr;
  align-items: center;
  gap: 10px;
}

.submissions-list__head {
  background-color: var(--color-button-primary);
  margin-bottom: 5px;
}

.submissions-list__head p {
  margin: 0;
  text-align: center;
  color: var(--color-button-text-primary);
  font-weight: 500;
  font-size: 15px;
}

.submissions-list__item {
  width: 100%;
  list-style: none;
}

.submissions-list__link {
  background-color: var(--color-button-secondary);
  text-decoration: none;
  transition: opacity 0.2s ease;
  display: grid;
}

.submissions-list__link:hover {
  opacity: 0.85;
}

.submissions-list__link p {
  margin: 0;
  text-align: center;
  color: #9480C9;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submissions-list__link p:first-child {
  font-weight: 500;
}

.submissions-list__link p:last-child {
  font-family: monospace;
  font-weight: 500;
}

.status {
  font-size: 14px;
  font-weight: 500;
  display: inline-block;
  color: #333333;
}

.status--tested {
  color: #059669;
}

.status--error {
  color: #dc2626;
}

.status--pending {
  color: #d97706;
}

@media (max-width: 960px) {
  .profile__header,
  .user-card,
  .activity-section,
  .submissions-section {
    padding: 24px 20px;
  }

  .user-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 20px;
  }

  .activity-section__stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .profile__title {
    font-size: 36px;
  }

  .activity-section__stats {
    grid-template-columns: 1fr;
  }

  .submissions-section__content {
    overflow-x: auto;
  }

  .submissions-list {
    min-width: 680px;
  }
}
</style>

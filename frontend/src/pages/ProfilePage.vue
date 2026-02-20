<!-- frontend/src/pages/ProfilePage.vue -->
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
import { useUserStore } from '@/stores/UserStore'
import UiHeader from '@/components/ui/UiHeader.vue'
import UiBreadcrumbs from '@/components/ui/UiBreadcrumbs.vue'

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
    }
  },
  methods: {
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

    async loadProfileData() {
        this.loading = true
        this.error = null

        try {
            if (!this.isAuthenticated) {
                await this.userStore.checkAuth()
            }

            this.profile = await getCurrentProfile()

            if (!this.profile) {
                throw new Error('Профиль не найден')
            }

            this.submissions = this.profile.recent_submissions || []

        } catch (err) {
            console.error('Failed to load profile:', err)
            this.error = 'Не удалось загрузить профиль'
            this.submissions = []
        } finally {
            this.loading = false
        }
    }
  },
  async created() {
    this.userStore = useUserStore()
  },
  mounted() {
    this.loadProfileData()
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
</style>
import { apiPost } from '@/api/http'
import { ref } from 'vue'

const currentUser = ref(null)

export const authService = {
    async login(credentials) {
        try {
            const response = await apiPost('backend/login/', credentials)

            if (response.success) {
                const { user, tokens } = response

                localStorage.setItem('access_token', tokens.access)
                localStorage.setItem('refresh_token', tokens.refresh)
                localStorage.setItem('user', JSON.stringify(user))

                currentUser.value = user

                return {
                    success: true,
                    user,
                    message: response.message
                }
            }

            return {
                success: false,
                error: response.message || 'Ошибка авторизации'
            }
        } catch (error) {
            return this.handleError(error, 'Ошибка авторизации')
        }
    },

    async register(userData) {
        try {
            const response = await apiPost('backend/register/', userData)

            if (response.success) {
                const { user, tokens } = response

                localStorage.setItem('access_token', tokens.access)
                localStorage.setItem('refresh_token', tokens.refresh)
                localStorage.setItem('user', JSON.stringify(user))

                return {
                    success: true,
                    user,
                    message: response.message
                }
            }

            return {
                success: false,
                error: response.message || 'Ошибка регистрации'
            }
        } catch (error) {
            return this.handleError(error, 'Ошибка регистрации')
        }
    },

    async logout() {
        try {
            await apiPost('backend/logout/')
            currentUser.value = null
        } catch (error) {
            console.error('Logout error:', error)
        } finally {
            this.clearStorage()
        }
    },

    getCurrentUser() {
        return currentUser
    },

    async checkAuth() {
        try {
            const response = await apiPost('backend/check-auth/')
            return response
        } catch (error) {
            return { is_authenticated: false }
        }
    },

    handleError(error, defaultMessage) {
        console.error('Auth error:', error)

        let errorMessage = defaultMessage

        if (error.response) {
            if (error.response.errors) {
                const errors = error.response.errors
                const errorList = []

                for (const [field, messages] of Object.entries(errors)) {
                    if (Array.isArray(messages)) {
                        errorList.push(`${field}: ${messages.join(', ')}`)
                    } else {
                        errorList.push(`${field}: ${messages}`)
                    }
                }

                errorMessage = errorList.join('; ')
            } else if (error.response.detail) {
                errorMessage = error.response.detail
            } else if (error.response.message) {
                errorMessage = error.response.message
            }
        }

        return {
            success: false,
            error: errorMessage
        }
    },

    clearStorage() {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
    },

    isAuthenticated() {
        return !!localStorage.getItem('access_token')
    },

    getStoredUser() {
        const userStr = localStorage.getItem('user')
        return userStr ? JSON.parse(userStr) : null
    }
}
import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'

import * as user from '@/api/user'
import { resetCourseTreeCache } from '@/utils/courseTreeCache'

export const useUserStore = defineStore('user', () => {
    const currentUser = ref(null)

    currentUser.value = JSON.parse(localStorage.getItem('currentUser')) || null

    watch(
        currentUser,
        (newCurrentUser, oldCurrentUser) => {
            localStorage.setItem('currentUser', JSON.stringify(newCurrentUser))

            const newId = newCurrentUser?.id ?? null
            const oldId = oldCurrentUser?.id ?? null
            if (newId !== oldId) {
                resetCourseTreeCache({ userCacheKey: newId })
            }
        },
        { deep: true }
    )

    const isAuthenticated = computed(() => {
        return !!(currentUser.value && currentUser.value.accessToken)
    })

    function formatFieldErrors(errors) {
        if (!errors || typeof errors !== 'object') {
            return ''
        }

        return Object.entries(errors)
            .map(([field, messages]) => {
                const list = Array.isArray(messages) ? messages : [messages]
                const message = list
                    .map(item => (typeof item === 'string' ? item : String(item)))
                    .filter(Boolean)
                    .join(', ')
                return message ? `${field}: ${message}` : ''
            })
            .filter(Boolean)
            .join('; ')
    }

    async function loginUser(username, password) {
        try {
            const res = await user.login({
                username,
                password,
            })

            if (res.success) {
                const accessToken = res?.tokens?.access || res?.user?.access || null
                const refreshToken = res?.tokens?.refresh || res?.user?.refresh || null
                currentUser.value = {
                    id: res.user.id,
                    username: res.user.username,
                    email: res.user.email,
                    role: res.user.role,
                    accessToken,
                    refreshToken,
                }

                resetCourseTreeCache({ userCacheKey: res.user.id })
                return {
                    success: true,
                    message: res.message,
                }
            }

            return {
                success: false,
                error: res.message || 'Ошибка авторизации'
            }
        } catch (err) {
            console.error('Failed to login user:', err)
            return {
                success: false,
                error: err?.message || 'Ошибка при входе'
            }
        }
    }

    async function registerUser(username, email, password1, password2, role, captchaToken = '', teacherProof = null, teacherComment = '') {
        try {
            const res = await user.register({
                username,
                email,
                password1,
                password2,
                role,
                captcha_token: captchaToken,
                teacher_proof: teacherProof,
                teacher_comment: teacherComment,
            })

            if (res.success) {
                const accessToken = res?.tokens?.access || null
                const refreshToken = res?.tokens?.refresh || null
                currentUser.value = {
                    id: res.user.id,
                    username: res.user.username,
                    email: res.user.email,
                    role: res.user.role,
                    accessToken,
                    refreshToken,
                }

                resetCourseTreeCache({ userCacheKey: res.user.id })
                return {
                    success: true,
                    message: res.message,
                }
            }

            return {
                success: false,
                error: formatFieldErrors(res.errors) || res.message || 'Ошибка регистрации'
            }
        } catch (err) {
            console.error('Failed to register user:', err)
            return {
                success: false,
                error: formatFieldErrors(err?.data?.errors) || err?.message || 'Ошибка при регистрации'
            }
        }
    }

    async function logoutUser() {
        try {
            await user.logout()
            clearStorage()
            resetCourseTreeCache({ userCacheKey: null })
            return { success: true }
        } catch (err) {
            console.error('Failed to logout user:', err)
            return { success: false, error: 'Ошибка при выходе' }
        }
    }

    function getCurrentUser() {
        return currentUser
    }

    async function checkAuth() {
        try {
            const res = await user.checkAuth()
            if (res?.is_authenticated) {
                currentUser.value = {
                    id: res?.user?.id || null,
                    username: res?.user?.username || null,
                    email: res?.user?.email || null,
                    role: res?.user?.role || null,
                    accessToken: res?.tokens?.access || res?.user?.accessToken || null,
                    refreshToken: res?.tokens?.refresh || res?.user?.refreshToken || null,
                }
            } else {
                currentUser.value = null
                resetCourseTreeCache({ userCacheKey: null })
            }
            return res
        } catch (err) {
            console.error('Failed to check authorisation user:', err)
            currentUser.value = null
            resetCourseTreeCache({ userCacheKey: null })
            return { is_authenticated: false }
        }
    }

    function clearStorage() {
        currentUser.value = null
        resetCourseTreeCache({ userCacheKey: null })
    }

    return {
        currentUser,
        isAuthenticated,
        loginUser,
        registerUser,
        logoutUser,
        getCurrentUser,
        checkAuth,
        clearStorage
    }
})

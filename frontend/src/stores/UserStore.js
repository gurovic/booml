import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import * as user from '@/api/user'

export const useUserStore = defineStore('user', () => {
    const currentUser = ref(null)

    currentUser.value = JSON.parse(localStorage.getItem('currentUser')) || null;


    watch(
        currentUser,
        (newCurrentUser) => {
            localStorage.setItem('currentUser', JSON.stringify(newCurrentUser));
        },
        { deep: true }
    );


    const isAuthenticated = computed(() => {
        return !!currentUser.value
    })

    async function loginUser(username, password) {
        try {
            const res = await user.login({
                username: username,
                password: password,
            })

            if (res.success) {
                const accessToken = res?.tokens?.access || res?.user?.access || null
                const refreshToken = res?.tokens?.refresh || res?.user?.refresh || null
                currentUser.value = {
                    'id': res.user.id,
                    'username': res.user.username,
                    'email': res.user.email,
                    'role': res.user.role,
                    'accessToken': accessToken,
                    'refreshToken': refreshToken,
                }

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
                error: 'Ошибка при входе'
            }
        }
    }

    async function registerUser(username, email, password1, password2, role) {
        try {
            const res = await user.register({
                username: username,
                email: email,
                password1: password1,
                password2: password2,
                role: role,
            })

            if (res.success) {
                const accessToken = res?.tokens?.access || res?.user?.access || null
                const refreshToken = res?.tokens?.refresh || res?.user?.refresh || null
                currentUser.value = {
                    'id': res.user.id,
                    'username': res.user.username,
                    'email': res.user.email,
                    'role': res.user.role,
                    'accessToken': accessToken,
                    'refreshToken': refreshToken,
                }

                return {
                    success: true,
                    message: res.message,
                }
            }

            return {
                success: false,
                error: res.message || 'Ошибка регистрации'
            }
        } catch (err) {
            console.error('Failed to register user:', err)
            return {
                success: false,
                error: 'Ошибка при регистрации'
            }
        }
    }

    async function logoutUser() {
        try {
            await user.logout()
            clearStorage()
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
                if (currentUser.value == null) {
                    currentUser.value = {
                        username: res?.user?.username || null,
                        email: res?.user?.email || null,
                    }
                } else {
                    currentUser.value = {
                        ...currentUser.value,
                        username: res?.user?.username ?? currentUser.value.username,
                        email: res?.user?.email ?? currentUser.value.email,
                    }
                }
            } else {
                currentUser.value = null
            }
            return res
        } catch (err) {
            console.error('Failed to check authorisation user:', err)
            return { is_authenticated: false }
        }
    }

    function clearStorage() {
        currentUser.value = null
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

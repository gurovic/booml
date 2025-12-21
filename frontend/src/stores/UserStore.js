import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import * as user from '@/api/user'

export const useUserStore = defineStore('user', () => {
    const id = ref(null)
    const username = ref(null)
    const email = ref(null)
    const role = ref("student")
    const currentUser = ref(null)

    const accessToken = ref(null)
    const refreshToken = ref(null)

    const password = ref(null)
    const password2 = ref(null)

    currentUser.value = JSON.parse(localStorage.getItem('currentUser')) || null;
    if (currentUser.value) {
        id.value = currentUser.value.id
        username.value = currentUser.value.username
        email.value = currentUser.value.email
        role.value = currentUser.value.role
        accessToken.value = currentUser.value.accessToken
        refreshToken.value = currentUser.value.refreshToken
    }


    watch(
        currentUser,
        (newCurrentUser) => {
            localStorage.setItem('currentUser', JSON.stringify(newCurrentUser));
        },
        { deep: true }
    );


    const isAuthenticated = computed(() => {
        return !!accessToken.value && !!id.value
    })

    async function loginUser() {
        try {
            const res = await user.login({
                username: username.value,
                password: password.value,
            })

            if (res.success) {
                id.value = res.user.id
                username.value = res.user.username
                email.value = res.user.email
                accessToken.value = res.tokens.access
                refreshToken.value = res.tokens.refresh
                currentUser.value = {
                    'id': id.value,
                    'username': username.value,
                    'email': email.value,
                    'role': role.value,
                    'accessToken': accessToken.value,
                    'refreshToken': refreshToken.value,
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

    async function registerUser() {
        try {
            const res = await user.register({
                username: username.value,
                email: email.value,
                password1: password.value,
                password2: password2.value,
                role: role.value,
            })

            if (res.success) {
                id.value = res.user.id
                username.value = res.user.username
                email.value = res.user.email
                role.value = res.user.role
                accessToken.value = res.tokens.access
                refreshToken.value = res.tokens.refresh
                currentUser.value = {
                    'id': id.value,
                    'username': username.value,
                    'email': email.value,
                    'role': role.value,
                    'accessToken': accessToken.value,
                    'refreshToken': refreshToken.value,
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
            return res
        } catch (err) {
            console.error('Failed to check authorisation user:', err)
            return { is_authenticated: false }
        }
    }

    function clearStorage() {
        id.value = null
        username.value = null
        email.value = null
        role.value = "student"
        currentUser.value = null
        accessToken.value = null
        refreshToken.value = null
        password.value = null
        password2.value = null
    }

    return {
        id,
        username,
        email,
        role,
        accessToken,
        refreshToken,
        password,
        password2,

        isAuthenticated,

        loginUser,
        registerUser,
        logoutUser,
        getCurrentUser,
        checkAuth,
        clearStorage
    }
})
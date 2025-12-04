<template>
    <div class="auth-page">
        <div class="auth-page__container">
            <div class="auth-card">
                <div class="auth-card__tabs">
                    <button
                        @click="switchToLogin"
                        :class="[
                            'auth-card__tab',
                            { 'auth-card__tab--active': activeTab === 'login' }
                        ]"
                    >
                        Вход
                    </button>
                    <button
                        @click="switchToRegister"
                        :class="[
                            'auth-card__tab',
                            { 'auth-card__tab--active': activeTab === 'register' }
                        ]"
                    >
                        Регистрация
                    </button>
                </div>

                <form @submit.prevent="handleSubmit" class="auth-card__form">
                    <h2 class="auth-card__title">
                        {{ activeTab === 'login' ? 'Вход в аккаунт' : 'Создание аккаунта' }}
                    </h2>

                    <div
                        v-if="formErrors.general"
                        class="auth-card__error auth-card__error--general"
                    >
                        {{ formErrors.general }}
                    </div>

                    <div class="form-group">
                        <label for="username" class="form-group__label">
                            Имя пользователя *
                        </label>
                        <input
                            type="text"
                            id="username"
                            v-model="formData.username"
                            :class="[
                                'form-group__input',
                                { 'form-group__input--error': formErrors.username }
                            ]"
                            placeholder="Ваше имя пользователя"
                            required
                        >
                        <div
                            v-if="formErrors.username"
                            class="form-group__error"
                        >
                            {{ formErrors.username }}
                        </div>
                    </div>

                    <div v-if="activeTab === 'register'" class="form-group">
                        <label for="email" class="form-group__label">
                            Email *
                        </label>
                        <input
                            type="email"
                            id="email"
                            v-model="formData.email"
                            :class="[
                                'form-group__input',
                                { 'form-group__input--error': formErrors.email }
                            ]"
                            placeholder="Ваш email"
                            required
                        >
                        <div
                            v-if="formErrors.email"
                            class="form-group__error"
                        >
                            {{ formErrors.email }}
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="password" class="form-group__label">
                            Пароль *
                        </label>
                        <input
                            type="password"
                            id="password"
                            v-model="formData.password"
                            :class="[
                                'form-group__input',
                                { 'form-group__input--error': formErrors.password }
                            ]"
                            :placeholder="activeTab === 'login' ? 'Введите пароль' : 'Придумайте пароль'"
                            required
                        >
                        <div
                            v-if="formErrors.password"
                            class="form-group__error"
                        >
                            {{ formErrors.password }}
                        </div>
                        <small
                            v-if="activeTab === 'register'"
                            class="form-group__hint"
                        >
                            Минимум 8 символов
                        </small>
                    </div>

                    <div v-if="activeTab === 'register'" class="form-group">
                        <label for="password2" class="form-group__label">
                            Подтверждение пароля *
                        </label>
                        <input
                            type="password"
                            id="password2"
                            v-model="formData.password2"
                            :class="[
                                'form-group__input',
                                { 'form-group__input--error': formErrors.password2 }
                            ]"
                            placeholder="Повторите пароль"
                            required
                        >
                        <div
                            v-if="formErrors.password2"
                            class="form-group__error"
                        >
                            {{ formErrors.password2 }}
                        </div>
                    </div>

                    <button
                        type="submit"
                        :class="[
                            'auth-card__submit',
                            { 'auth-card__submit--loading': loading }
                        ]"
                        :disabled="loading"
                    >
                        <span
                            v-if="loading"
                            class="auth-card__spinner"
                        ></span>
                        <span class="auth-card__submit-text">
                            {{ activeTab === 'login' ? 'Войти' : 'Зарегистрироваться' }}
                        </span>
                    </button>
                </form>

                <div class="auth-card__switch">
                    <p class="auth-card__switch-text">
                        <span v-if="activeTab === 'login'">
                            Нет аккаунта?
                        </span>
                        <span v-else>
                            Уже есть аккаунт?
                        </span>
                        <a
                            href="#"
                            @click.prevent="activeTab === 'login' ? switchToRegister() : switchToLogin()"
                            class="auth-card__switch-link"
                        >
                            {{ activeTab === 'login' ? 'Зарегистрируйтесь' : 'Войдите' }}
                        </a>
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '@/services/auth'

const router = useRouter()

const activeTab = ref('login')
const loading = ref(false)
const formData = reactive({
    username: '',
    email: '',
    password: '',
    password2: ''
})
const formErrors = reactive({})

const isLoginMode = computed(() => activeTab.value === 'login')

const switchToLogin = () => {
    activeTab.value = 'login'
    resetForm()
    clearErrors()
}

const switchToRegister = () => {
    activeTab.value = 'register'
    resetForm()
    clearErrors()
}

const resetForm = () => {
    Object.assign(formData, {
        username: '',
        email: '',
        password: '',
        password2: ''
    })
}

const clearErrors = () => {
    Object.keys(formErrors).forEach(key => {
        delete formErrors[key]
    })
}

const handleSubmit = async () => {
    loading.value = true
    clearErrors()

    try {
        let result

        if (isLoginMode.value) {
            result = await authService.login({
                username: formData.username,
                password: formData.password
            })
        } else {
            result = await authService.register({
                username: formData.username,
                email: formData.email,
                password1: formData.password,
                password2: formData.password2
            })
        }

        if (result.success) {
            await router.push('/')
        } else {
            handleErrors(result.error)
        }
    } catch (error) {
        console.error('Auth error:', error)
        formErrors.general = 'Произошла ошибка. Попробуйте позже.'
    } finally {
        loading.value = false
    }
}

const handleErrors = (error) => {
    if (error.includes(';')) {
        const errorParts = error.split(';')

        errorParts.forEach(part => {
            const [fieldWithLabel, message] = part.split(':')
            if (fieldWithLabel && message) {
                const field = fieldWithLabel.trim()
                const cleanMessage = message.trim()

                const fieldMap = {
                    'password1': 'password',
                    'password2': 'password2'
                }

                const vueField = fieldMap[field] || field
                formErrors[vueField] = cleanMessage
            }
        })
    } else {
        formErrors.general = error
    }
}
</script>

<style lang="scss" scoped>
</style>
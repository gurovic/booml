<template>
    <div class="auth-page">
        <div class="auth-page__container">
            <div class="auth-card">
                <div class="auth-card__header">
                    <h2 class="auth-card__title">Создание аккаунта</h2>
                    <p class="auth-card__subtitle">
                        Заполните форму для регистрации нового пользователя
                    </p>
                </div>

                <form @submit.prevent="handleSubmit" class="auth-card__form">
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
                            placeholder="Придумайте имя пользователя"
                            required
                            :disabled="loading"
                        >
                        <div
                            v-if="formErrors.username"
                            class="form-group__error"
                        >
                            {{ formErrors.username }}
                        </div>
                    </div>

                    <div class="form-group">
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
                            placeholder="Введите ваш email"
                            required
                            :disabled="loading"
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
                            placeholder="Придумайте пароль"
                            required
                            :disabled="loading"
                        >
                        <div
                            v-if="formErrors.password"
                            class="form-group__error"
                        >
                            {{ formErrors.password }}
                        </div>
                        <small class="form-group__hint">
                            Минимум 8 символов
                        </small>
                    </div>

                    <div class="form-group">
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
                            :disabled="loading"
                        >
                        <div
                            v-if="formErrors.password2"
                            class="form-group__error"
                        >
                            {{ formErrors.password2 }}
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="form-group__label">Роль *</label>
                        <div class="role-options">
                            <label
                                v-for="role in roles"
                                :key="role.value"
                                class="role-option"
                                :class="{ 'role-option--selected': formData.role === role.value }"
                            >
                                <input
                                    type="radio"
                                    :value="role.value"
                                    v-model="formData.role"
                                    :disabled="loading"
                                    class="role-option__input"
                                >
                                <span class="role-option__custom"></span>
                                <span class="role-option__label">{{ role.label }}</span>
                                <span class="role-option__description">{{ role.description }}</span>
                            </label>
                        </div>
                        <div
                            v-if="formErrors.role"
                            class="form-group__error"
                        >
                            {{ formErrors.role }}
                        </div>
                    </div>

                    <div class="form-group form-group--terms">
                        <label class="checkbox-label">
                            <input
                                type="checkbox"
                                v-model="acceptTerms"
                                :disabled="loading"
                                required
                            >
                            <span class="checkbox-custom"></span>
                            <span class="checkbox-text">
                                Я согласен с
                                <a href="#" class="terms-link">условиями использования</a>
                                и
                                <a href="#" class="terms-link">политикой конфиденциальности</a>
                            </span>
                        </label>
                    </div>

                    <button
                        type="submit"
                        :class="[
                            'auth-card__submit',
                            { 'auth-card__submit--loading': loading }
                        ]"
                        :disabled="loading || !acceptTerms"
                    >
                        <span
                            v-if="loading"
                            class="auth-card__spinner"
                        ></span>
                        <span class="auth-card__submit-text">
                            Зарегистрироваться
                        </span>
                    </button>
                </form>

                <div class="auth-card__footer">
                    <p class="auth-card__footer-text">
                        Уже есть аккаунт?
                        <router-link to="/login" class="auth-card__footer-link">
                            Войдите
                        </router-link>
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '@/services/auth'

const router = useRouter()

const loading = ref(false)
const acceptTerms = ref(false)
const formData = reactive({
    username: '',
    email: '',
    password: '',
    password2: '',
    role: 'student'
})
const formErrors = reactive({})

const roles = [
    {
        value: 'student',
        label: 'Студент/Ученик',
        description: 'Доступ к учебным материалам и заданиям'
    },
    {
        value: 'teacher',
        label: 'Учитель',
        description: 'Создание курсов и управление учебным процессом'
    }
]

const clearErrors = () => {
    Object.keys(formErrors).forEach(key => {
        delete formErrors[key]
    })
}

const handleSubmit = async () => {
    loading.value = true
    clearErrors()

    try {
        const result = await authService.register({
            username: formData.username,
            email: formData.email,
            password1: formData.password,
            password2: formData.password2,
            role: formData.role
        })

        if (result.success) {
            // Автоматически логиним после успешной регистрации
            const loginResult = await authService.login({
                username: formData.username,
                password: formData.password
            })

            if (loginResult.success) {
                await router.push('/')
            } else {
                formErrors.general = 'Регистрация прошла успешно, но не удалось войти автоматически. Пожалуйста, войдите вручную.'
            }
        } else {
            handleErrors(result.error)
        }
    } catch (error) {
        console.error('Register error:', error)
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

<style scoped>
</style>
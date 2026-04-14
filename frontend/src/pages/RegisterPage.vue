<template>
    <div class="auth-page">
        <div class="auth-page__container container">
            <div class="card">
                <div class="card__header">
                    <h2 class="card__title">Создание аккаунта</h2>
                    <p class="card__subtitle">
                        Заполните форму для регистрации нового пользователя
                    </p>
                </div>

                <form @submit.prevent="handleSubmit" class="card__form">
                    <div
                        v-if="formErrors.general"
                        class="card__error card__error--general"
                    >
                        {{ formErrors.general }}
                    </div>

                    <div class="form-group">
                        <label for="username" class="form-group__label">
                            Имя пользователя
                        </label>
                        <input
                            id="username"
                            v-model="formData.username"
                            type="text"
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
                            Email
                        </label>
                        <input
                            id="email"
                            v-model="formData.email"
                            type="email"
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
                            Пароль
                        </label>
                        <input
                            id="password"
                            v-model="formData.password"
                            type="password"
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
                            Подтверждение пароля
                        </label>
                        <input
                            id="password2"
                            v-model="formData.password2"
                            type="password"
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
                        <label class="form-group__label">Роль</label>
                        <div class="options">
                            <label
                                v-for="role in roles"
                                :key="role.value"
                                class="option"
                                :class="{ 'option--selected': formData.role === role.value }"
                            >
                                <input
                                    v-model="formData.role"
                                    type="radio"
                                    :value="role.value"
                                    :disabled="loading"
                                    class="option__input"
                                >
                                <span class="option__custom"></span>
                                <div class="option__content">
                                    <span class="option__label">{{ role.label }}</span>
                                    <span class="option__description">{{ role.description }}</span>
                                </div>
                            </label>
                        </div>
                        <div
                            v-if="formErrors.role"
                            class="form-group__error"
                        >
                            {{ formErrors.role }}
                        </div>
                    </div>

                    <div class="form-group form-group--checkbox">
                        <div class="checkbox-row">
                            <label class="checkbox-label" for="accept-terms">
                                <input
                                    id="accept-terms"
                                    v-model="acceptTerms"
                                    type="checkbox"
                                    :disabled="loading"
                                    required
                                >
                                <span class="checkbox-custom"></span>
                            </label>
                            <span class="checkbox-text">
                                Я согласен с
                                <router-link :to="{ name: 'terms' }" class="link">условиями использования</router-link>
                                и
                                <router-link :to="{ name: 'privacy' }" class="link">политикой конфиденциальности</router-link>
                            </span>
                        </div>
                    </div>

                    <div v-if="captchaEnabled" class="form-group">
                        <label class="form-group__label">
                            Подтверждение
                        </label>
                        <TurnstileCaptcha
                            ref="captchaRef"
                            v-model="captchaToken"
                            :site-key="captchaSiteKey"
                            @load-error="handleCaptchaLoadError"
                        />
                        <div
                            v-if="formErrors.captcha"
                            class="form-group__error"
                        >
                            {{ formErrors.captcha }}
                        </div>
                    </div>

                    <button
                        type="submit"
                        :class="[
                            'card__submit button button--primary',
                            { 'card__submit--loading': loading }
                        ]"
                        :disabled="loading || !acceptTerms || (captchaEnabled && !captchaToken)"
                    >
                        <span
                            v-if="loading"
                            class="card__spinner"
                        ></span>
                        <span class="card__submit-text">
                            Зарегистрироваться
                        </span>
                    </button>
                </form>

                <div class="card__footer">
                    <p class="card__footer-text">
                        Уже есть аккаунт?
                        <router-link :to="{ name: 'login', query: authLinkQuery }" class="card__footer-link">
                            Войдите
                        </router-link>
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import '@/assets/styles/form.css'
import TurnstileCaptcha from '@/components/ui/TurnstileCaptcha.vue'
import { useUserStore } from '@/stores/UserStore'
import {
    buildAuthRedirect,
    resolveAuthReasonFromQuery,
    resolveRedirectFromQuery,
} from '@/utils/redirect'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loading = ref(false)
const acceptTerms = ref(false)
const captchaRef = ref(null)
const captchaToken = ref('')
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

const redirectPath = computed(() => resolveRedirectFromQuery(route.query))
const authReason = computed(() => resolveAuthReasonFromQuery(route.query))
const authLinkQuery = computed(() => (
    buildAuthRedirect({
        redirect: redirectPath.value,
        reason: authReason.value,
    })
))
const captchaSiteKey = (process.env.VUE_APP_TURNSTILE_SITE_KEY || '').trim()
const captchaEnabled = Boolean(captchaSiteKey)

const resolveRedirect = () => redirectPath.value

const clearErrors = () => {
    Object.keys(formErrors).forEach(key => {
        delete formErrors[key]
    })
}

const handleSubmit = async () => {
    loading.value = true
    clearErrors()

    try {
        const result = await userStore.registerUser(
            formData.username,
            formData.email,
            formData.password,
            formData.password2,
            formData.role,
            captchaToken.value
        )

        if (result.success) {
            const loginResult = await userStore.loginUser(formData.username, formData.password)

            if (loginResult.success) {
                await router.push(resolveRedirect())
            } else {
                formErrors.general = 'Регистрация прошла успешно, но не удалось войти автоматически. Пожалуйста, войдите вручную.'
            }
        } else {
            handleErrors(result.error)
            captchaRef.value?.reset()
        }
    } catch (error) {
        console.error('Register error:', error)
        formErrors.general = 'Произошла ошибка. Попробуйте позже.'
        captchaRef.value?.reset()
    } finally {
        loading.value = false
    }
}

const handleCaptchaLoadError = () => {
    formErrors.captcha = 'Не удалось загрузить капчу. Обновите страницу и попробуйте снова.'
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
                    password1: 'password',
                    password2: 'password2',
                    captcha_token: 'captcha',
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
.auth-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--color-bg-default);
    padding: 20px;
}

.auth-page__container {
    max-width: 520px;
    margin: 0 auto;
}

@keyframes spin {
    to {
        transform: translate(-50%, -50%) rotate(360deg);
    }
}
</style>

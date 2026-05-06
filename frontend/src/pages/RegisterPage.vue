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

                    <div v-if="formData.role === 'teacher'" class="form-group">
                        <label for="teacher-proof" class="form-group__label">
                            Подтверждение статуса учителя
                        </label>
                        <div
                            class="teacher-proof-picker"
                            :class="{
                                'teacher-proof-picker--error': formErrors.teacher_proof,
                                'teacher-proof-picker--disabled': loading,
                                'teacher-proof-picker--selected': teacherProof
                            }"
                        >
                            <input
                                id="teacher-proof"
                                :key="teacherProofInputKey"
                                type="file"
                                accept="image/jpeg,image/png,image/webp"
                                class="teacher-proof-picker__input"
                                :disabled="loading"
                                required
                                @change="handleTeacherProofChange"
                            >
                            <label class="teacher-proof-picker__button" for="teacher-proof">
                                <span class="teacher-proof-picker__icon" aria-hidden="true">+</span>
                                <span>{{ teacherProof ? 'Заменить файл' : 'Выбрать файл' }}</span>
                            </label>
                            <div class="teacher-proof-picker__info">
                                <span class="teacher-proof-picker__name">
                                    {{ teacherProofName }}
                                </span>
                                <span class="teacher-proof-picker__meta">
                                    JPEG, PNG или WEBP до 10MB
                                </span>
                            </div>
                        </div>
                        <small class="form-group__hint">
                            Подойдёт скриншот из МЭШ. Форматы: JPEG, PNG или WEBP, до 10MB.
                        </small>
                        <div
                            v-if="formErrors.teacher_proof"
                            class="form-group__error"
                        >
                            {{ formErrors.teacher_proof }}
                        </div>
                    </div>

                    <div v-if="formData.role === 'teacher'" class="form-group">
                        <label for="teacher-comment" class="form-group__label">
                            Комментарий для модератора
                        </label>
                        <textarea
                            id="teacher-comment"
                            v-model="teacherComment"
                            :class="[
                                'form-group__input',
                                'form-group__textarea',
                                { 'form-group__input--error': formErrors.teacher_comment }
                            ]"
                            rows="3"
                            placeholder="Например: школа, предмет, ссылка на профиль МЭШ"
                            :disabled="loading"
                        ></textarea>
                        <div
                            v-if="formErrors.teacher_comment"
                            class="form-group__error"
                        >
                            {{ formErrors.teacher_comment }}
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
                        :disabled="loading || !acceptTerms || isTeacherProofMissing || (captchaEnabled && !captchaToken)"
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
import { computed, reactive, ref, watch } from 'vue'
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
const teacherProof = ref(null)
const teacherProofInputKey = ref(0)
const teacherComment = ref('')
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
const isTeacherProofMissing = computed(() => formData.role === 'teacher' && !teacherProof.value)
const teacherProofName = computed(() => teacherProof.value?.name || 'Файл не выбран')

const resolveRedirect = () => redirectPath.value

watch(
    () => formData.role,
    (role) => {
        if (role === 'teacher') {
            return
        }

        teacherProof.value = null
        teacherComment.value = ''
        teacherProofInputKey.value += 1
        delete formErrors.teacher_proof
        delete formErrors.teacher_comment
    }
)

const clearErrors = () => {
    Object.keys(formErrors).forEach(key => {
        delete formErrors[key]
    })
}

const handleTeacherProofChange = (event) => {
    const file = event.target.files?.[0]
    delete formErrors.teacher_proof

    if (!file) {
        teacherProof.value = null
        return
    }

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
    const allowedExtensions = ['.jpg', '.jpeg', '.png', '.webp']
    const fileName = file.name.toLowerCase()
    const hasAllowedType = allowedTypes.includes(file.type)
    const hasAllowedExtension = allowedExtensions.some(ext => fileName.endsWith(ext))

    if (file.size > 10 * 1024 * 1024) {
        teacherProof.value = null
        teacherProofInputKey.value += 1
        formErrors.teacher_proof = 'Файл слишком большой. Максимальный размер 10MB.'
        return
    }

    if (!hasAllowedType && !hasAllowedExtension) {
        teacherProof.value = null
        teacherProofInputKey.value += 1
        formErrors.teacher_proof = 'Загрузите скриншот в формате JPEG, PNG или WEBP.'
        return
    }

    teacherProof.value = file
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
            captchaToken.value,
            teacherProof.value,
            teacherComment.value
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

.form-group__textarea {
    min-height: 88px;
    resize: vertical;
}

.teacher-proof-picker {
    display: flex;
    align-items: stretch;
    gap: 10px;
    width: 100%;
    min-height: 52px;
}

.teacher-proof-picker__input {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
}

.teacher-proof-picker__button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-width: 150px;
    padding: 0 16px;
    border: 1px solid var(--color-button-primary);
    border-radius: 8px;
    background: var(--color-button-primary);
    color: var(--color-button-text-primary);
    font-size: 14px;
    font-weight: 600;
    line-height: 1;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.teacher-proof-picker__button:hover {
    transform: translateY(-1px);
}

.teacher-proof-picker__input:focus-visible + .teacher-proof-picker__button {
    outline: 2px solid rgba(20, 78, 236, 0.25);
    outline-offset: 2px;
}

.teacher-proof-picker__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.18);
    font-size: 16px;
    line-height: 1;
}

.teacher-proof-picker__info {
    display: flex;
    flex: 1;
    min-width: 0;
    flex-direction: column;
    justify-content: center;
    gap: 3px;
    padding: 8px 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
}

.teacher-proof-picker__name {
    overflow: hidden;
    color: var(--color-text-primary);
    font-size: 14px;
    font-weight: 600;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.teacher-proof-picker__meta {
    overflow: hidden;
    color: var(--color-text-secondary);
    font-size: 12px;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.teacher-proof-picker--selected .teacher-proof-picker__info {
    border-color: rgba(20, 78, 236, 0.35);
    background: rgba(20, 78, 236, 0.04);
}

.teacher-proof-picker--error .teacher-proof-picker__info,
.teacher-proof-picker--error .teacher-proof-picker__button {
    border-color: #ef4444;
}

.teacher-proof-picker--disabled {
    opacity: 0.7;
}

.teacher-proof-picker--disabled .teacher-proof-picker__button {
    cursor: not-allowed;
    transform: none;
}

@media (max-width: 520px) {
    .teacher-proof-picker {
        flex-direction: column;
    }

    .teacher-proof-picker__button {
        min-height: 46px;
        width: 100%;
    }
}
</style>

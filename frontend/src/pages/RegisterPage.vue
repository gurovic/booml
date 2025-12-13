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
                            Имя пользователя
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
                            Email
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
                            Пароль
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
                            Подтверждение пароля
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
                        <label class="form-group__label">Роль</label>
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
                                <div class="role-option__content">
                                    <span class="role-option__label">{{ role.label }}</span>
                                    <span class="role-option__description">{{ role.description }}</span>
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
.auth-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #f8f9fa;
    padding: 20px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.auth-page__container {
    width: 100%;
    max-width: 520px;
    margin: 0 auto;
}

.auth-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    padding: 40px;
}

.auth-card__header {
    text-align: center;
    margin-bottom: 32px;
}

.auth-card__title {
    color: #2c3e50;
    font-size: 26px;
    font-weight: 600;
    margin: 0 0 10px 0;
    line-height: 1.2;
}

.auth-card__subtitle {
    color: #7f8c8d;
    font-size: 15px;
    margin: 0;
    line-height: 1.5;
}

.auth-card__form {
    margin-bottom: 24px;
}

.auth-card__error--general {
    background-color: #fef2f2;
    border: 1px solid #fee2e2;
    color: #dc2626;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 20px;
    font-size: 14px;
    text-align: center;
}

.form-group {
    margin-bottom: 24px;
}

.form-group__label {
    display: block;
    color: #374151;
    font-weight: 500;
    font-size: 14px;
    margin-bottom: 8px;
}

.form-group__label::after {
    content: " *";
    color: #ef4444;
}

.form-group__input {
    width: 100%;
    padding: 14px 16px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-size: 16px;
    color: #111827;
    background-color: #fff;
    transition: border-color 0.15s ease;
    box-sizing: border-box;
}

.form-group__input:focus {
    outline: none;
    border-color: #144EEC;
    box-shadow: 0 0 0 3px rgba(20, 78, 236, 0.1);
}

.form-group__input--error {
    border-color: #ef4444;
    background-color: #fffafa;
}

.form-group__input--error:focus {
    border-color: #ef4444;
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.form-group__input:disabled {
    background-color: #f9fafb;
    cursor: not-allowed;
    opacity: 0.7;
}

.form-group__error {
    color: #ef4444;
    font-size: 13px;
    margin-top: 6px;
}

.form-group__hint {
    display: block;
    color: #6b7280;
    font-size: 12px;
    margin-top: 6px;
}

.role-options {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.role-option {
    display: flex;
    align-items: flex-start;
    padding: 16px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.15s ease;
    position: relative;
}

.role-option:hover {
    border-color: #9ca3af;
    background-color: #f9fafb;
}

.role-option--selected {
    border-color: #144EEC;
    background-color: rgba(20, 78, 236, 0.05);
}

.role-option--selected:hover {
    border-color: #144EEC;
    background-color: rgba(20, 78, 236, 0.08);
}

.role-option__input {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
}

.role-option__custom {
    display: inline-block;
    width: 18px;
    height: 18px;
    border: 2px solid #9ca3af;
    border-radius: 50%;
    margin-right: 16px;
    margin-top: 2px;
    position: relative;
    flex-shrink: 0;
    transition: all 0.15s ease;
}

.role-option--selected .role-option__custom {
    border-color: #144EEC;
}

.role-option--selected .role-option__custom::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 8px;
    height: 8px;
    background-color: #144EEC;
    border-radius: 50%;
}

.role-option__content {
    flex: 1;
    margin-left: 2px;
}

.role-option__label {
    font-weight: 600;
    color: #374151;
    font-size: 15px;
    margin-bottom: 6px;
    display: block;
    line-height: 1.3;
}

.role-option__description {
    color: #6b7280;
    font-size: 14px;
    line-height: 1.4;
    display: block;
    padding-left: 0;
    margin-left: 0;
}

.form-group--terms {
    padding-top: 8px;
}

.checkbox-label {
    display: flex;
    align-items: flex-start;
    cursor: pointer;
    position: relative;
}

.checkbox-label input[type="checkbox"] {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
}

.checkbox-custom {
    display: inline-block;
    width: 18px;
    height: 18px;
    border: 2px solid #d1d5db;
    border-radius: 4px;
    margin-right: 12px;
    margin-top: 2px;
    flex-shrink: 0;
    transition: all 0.15s ease;
    position: relative;
}

.checkbox-label:hover .checkbox-custom {
    border-color: #9ca3af;
}

.checkbox-label input[type="checkbox"]:checked + .checkbox-custom {
    border-color: #144EEC;
    background-color: #144EEC;
}

.checkbox-label input[type="checkbox"]:checked + .checkbox-custom::after {
    content: '✓';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: white;
    font-size: 12px;
    font-weight: bold;
}

.checkbox-text {
    color: #374151;
    font-size: 14px;
    line-height: 1.5;
}

.terms-link {
    color: #144EEC;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.15s ease;
}

.terms-link:hover {
    color: #0d3ec8;
    text-decoration: underline;
}

.auth-card__submit {
    width: 100%;
    background-color: #144EEC;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 16px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.15s ease;
    height: 52px;
    margin-top: 8px;
}

.auth-card__submit:hover:not(:disabled) {
    background-color: #0d3ec8;
}

.auth-card__submit:active:not(:disabled) {
    background-color: #0a32a8;
}

.auth-card__submit:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    background-color: #9ca3af;
}

.auth-card__submit--loading {
    opacity: 0.8;
}

.auth-card__spinner {
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    border-top-color: white;
    animation: spin 0.8s linear infinite;
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
}

.auth-card__submit-text {
    opacity: 1;
    transition: opacity 0.15s ease;
}

.auth-card__submit--loading .auth-card__submit-text {
    opacity: 0;
}

@keyframes spin {
    to {
        transform: translate(-50%, -50%) rotate(360deg);
    }
}

.auth-card__footer {
    text-align: center;
    padding-top: 24px;
    border-top: 1px solid #e5e7eb;
}

.auth-card__footer-text {
    color: #6b7280;
    font-size: 15px;
    margin: 0;
}

.auth-card__footer-link {
    color: #144EEC;
    text-decoration: none;
    font-weight: 600;
    margin-left: 4px;
    transition: color 0.15s ease;
}

.auth-card__footer-link:hover {
    color: #0d3ec8;
    text-decoration: underline;
}

@media (max-width: 480px) {
    .auth-card {
        padding: 32px 24px;
    }

    .auth-card__title {
        font-size: 24px;
    }

    .auth-card__subtitle {
        font-size: 14px;
    }

    .form-group__input {
        padding: 12px 14px;
        font-size: 15px;
    }

    .role-option {
        padding: 14px;
    }

    .role-option__custom {
        margin-right: 14px;
        margin-top: 1px;
    }

    .role-option__label {
        font-size: 14px;
        margin-bottom: 5px;
    }

    .role-option__description {
        font-size: 13px;
    }
}
</style>
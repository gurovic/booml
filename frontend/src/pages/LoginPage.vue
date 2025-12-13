<template>
    <div class="auth-page">
        <div class="auth-page__container">
            <div class="auth-card">
                <div class="auth-card__header">
                    <h2 class="auth-card__title">Вход в аккаунт</h2>
                    <p class="auth-card__subtitle">
                        Введите свои данные для входа в систему
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
                            placeholder="Введите имя пользователя"
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
                            placeholder="Введите пароль"
                            required
                            :disabled="loading"
                        >
                        <div
                            v-if="formErrors.password"
                            class="form-group__error"
                        >
                            {{ formErrors.password }}
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
                            Войти
                        </span>
                    </button>
                </form>

                <div class="auth-card__footer">
                    <p class="auth-card__footer-text">
                        Нет аккаунта?
                        <router-link to="/register" class="auth-card__footer-link">
                            Зарегистрируйтесь
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
const formData = reactive({
    username: '',
    password: ''
})
const formErrors = reactive({})

const clearErrors = () => {
    Object.keys(formErrors).forEach(key => {
        delete formErrors[key]
    })
}

const handleSubmit = async () => {
    loading.value = true
    clearErrors()

    try {
        const result = await authService.login({
            username: formData.username,
            password: formData.password
        })

        if (result.success) {
            await router.push('/')
        } else {
            handleErrors(result.error)
        }
    } catch (error) {
        console.error('Login error:', error)
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
                formErrors[field] = cleanMessage
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
    max-width: 440px;
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
}
</style>
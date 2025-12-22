<template>
    <div class="auth-page">
        <div class="auth-page__container container">
            <div class="card">
                <div class="card__header">
                    <h2 class="card__title">Вход в аккаунт</h2>
                    <p class="card__subtitle">
                        Введите свои данные для входа в систему
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
                            'card__submit button button--primary',
                            { 'card__submit--loading': loading }
                        ]"
                        :disabled="loading"
                    >
                        <span
                            v-if="loading"
                            class="card__spinner"
                        ></span>
                        <span class="card__submit-text">
                            Войти
                        </span>
                    </button>
                </form>

                <div class="card__footer">
                    <p class="card__footer-text">
                        Нет аккаунта?
                        <router-link to="/register" class="card__footer-link">
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
import { useUserStore } from '@/stores/UserStore'

const router = useRouter()
const userStore = useUserStore()

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
        const result = await userStore.loginUser(formData.username, formData.password)

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
    background-color: var(--color-bg-default);
    padding: 20px;
}

.auth-page__container {
    max-width: 440px;
    margin: 0 auto;
}

@keyframes spin {
    to {
        transform: translate(-50%, -50%) rotate(360deg);
    }
}
</style>
<template>
    <h1>Стартовая страница</h1>
    <h2>Фронтенд</h2>
    <h3>Сообщение от бэкенда: {{ message }}</h3>

    <h1>Заголовок 1</h1>
    <h2>Заголовок 2</h2>
    <h3>Заголовок 3</h3>
    <p>Текст</p>
    <button class="button button--primary">Основная кнопка</button>
    <button class="button button--secondary">Вторичная кнопка</button>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getStartMessage } from '@/api'

let message = ref('')

onMounted(async () => {
    try {
        const data = await getStartMessage()
        message.value = data.message
    } catch(err) {
        message.value = 'Не удалось получить сообщение'
        console.error(err)
    }
})
</script>

<style scoped>
</style>

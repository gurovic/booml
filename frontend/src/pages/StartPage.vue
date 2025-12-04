<template>
    <h1>Start Page</h1>
    <h2>Frontend</h2>
    <h3>Message from backend: {{ message }}</h3>

    <h1>Title 1</h1>
    <h2>Title 2</h2>
    <h3>Title 3</h3>
    <p>Body text</p>
    <button class="button button--primary">Primary button</button>
    <button class="button button--secondary">Secondary button</button>
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
        message.value = 'Error getting message'
        console.error(err)
    }
})
</script>

<style scoped>
</style>
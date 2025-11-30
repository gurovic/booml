<template>
    <h1>Start Page</h1>
    <h2>Frontend</h2>
    <h3>Message from backend: {{ message }}</h3>
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
        message = 'Error getting message'
        console.error(err)
    }
})
</script>

<style scoped>
</style>
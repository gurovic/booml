<template>
  <form>
  <div class="container">
    <h1>Register</h1>
    <p>Пожалуйста, заполните эту форму для создания нового аккаунта.</p>

    <label for="username">Username</label>
    <input type="text" placeholder="Enter Username" name="username" v-model="data.username" required>

    <label for="email">Email</label>
    <input type="text" placeholder="Enter Email" name="email" v-model="data.email" required>

    <label for="password1">Password</label>
    <input type="password" placeholder="Enter Password" name="password1" v-model="data.password1" required>

    <label for="password2">Repeat Password</label>
    <input type="password" placeholder="Repeat Password" name="password2" v-model="data.password2" required>

    <button type="submit" class="registerbtn" @click="handleClick">Register</button>
  </div>

  <div class="container signin">
    <p>Уже есть аккаунт? <a href="/login/">Sign in</a>.</p>
  </div>
</form>

</template>

<script setup>

import { ref } from 'vue';
import { apiPost } from '@/api/http';

const data = ref({
  username: '',
  email: '',
  password1: '',
  password2: ''
});

const handleClick = () => {
    try {
        apiPost('register', data.value);
    } catch (err) {
        console.log(err);
    }
}

</script>

<style scoped>
</style>
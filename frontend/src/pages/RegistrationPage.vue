<template>
  <form>
  <div class="container">
    <h1>Register</h1>
    <p>Please fill in this form to create an account.</p>
    <hr>

    <label for="username"><b>Username</b></label>
    <input type="text" placeholder="Enter Username" name="username" id="username" v-model="data.username" required>

    <label for="email"><b>Email</b></label>
    <input type="text" placeholder="Enter Email" name="email" id="email" v-model="data.email" required>

    <label for="password1"><b>Password</b></label>
    <input type="password" placeholder="Enter Password" name="password1" id="password1" v-model="data.password1" required>

    <label for="password2"><b>Repeat Password</b></label>
    <input type="password" placeholder="Repeat Password" name="password2" id="password2" v-model="data.password2" required>
    <hr>

    <button type="submit" class="registerbtn" @click="handleClick">Register</button>
  </div>

  <div class="container signin">
    <p>Already have an account? <a href="/login/">Sign in</a>.</p>
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
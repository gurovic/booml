<template>
  <header class="header">
    <div class="container">
      <div class="header__inner">
        <a href="/" class="header__title">
          Booml
        </a>

        <button
          class="button button--secondary header__button"
          @click="handleButton"
        >
          {{ isAuthorized ? 'Выйти' : 'Войти' }}
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const user = ref(null) // позже подключите auth
const isAuthorized = computed(() => user.value !== null)

const handleButton = () => {
  if (isAuthorized.value) {
    router.push('/logout')
  } else {
    router.push('/login')
  }
}
</script>

<style scoped>
.header {
  height: 64px;
  background-color: var(--color-primary);
}

.container {
  height: 100%;
}

.header__inner {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header__title {
  font-family: 'Dela Gothic One', sans-serif;
  font-size: 20px;
  line-height: 1;
  color: #ffffff;
  text-decoration: none;
}

.header__button {
  height: 40px;
  display: flex;
  align-items: center;
}
</style>
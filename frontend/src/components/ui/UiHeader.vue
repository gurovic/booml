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
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/UserStore'

const router = useRouter()
const userStore = useUserStore()
let user = userStore.getCurrentUser()

let isAuthorized = computed(() => user.value != null)

const handleButton = async () => {
  if (isAuthorized.value) {
    await userStore.logoutUser()
    router.push('/')
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
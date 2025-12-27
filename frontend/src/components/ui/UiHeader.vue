<template>
  <header class="header">
    <div class="container">
      <div class="header__inner">
        <button type="button" class="header__title" @click="handleHomeClick">
          Booml
        </button>

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
    if (router.currentRoute.value.path !== '/') {
      router.push('/')
    }
  } else {
    router.push('/login')
  }
}

const handleHomeClick = () => {
  if (router.currentRoute.value.path !== '/') {
    router.push('/')
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
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}

.header__title:hover {
  opacity: 0.9;
}

.header__title:focus {
  outline: 2px solid #ffffff;
  outline-offset: 2px;
}

.header__button {
  height: 40px;
  display: flex;
  align-items: center;
}
</style>
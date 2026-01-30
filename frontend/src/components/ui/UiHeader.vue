<template>
  <header class="header">
    <div class="container">
      <div class="header__inner">
        <button type="button" class="header__title" @click="handleHomeClick">
          Booml
        </button>

        <nav v-if="isAuthorized" class="header__nav">
          <button 
            type="button" 
            class="header__nav-link"
            @click="router.push('/polygon')"
          >
            Полигон
          </button>
        </nav>

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

.header__nav {
  display: flex;
  gap: 16px;
  align-items: center;
}

.header__nav-link {
  background: none;
  border: none;
  color: #ffffff;
  font-family: var(--font-default);
  font-size: 16px;
  font-weight: 500;
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.header__nav-link:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.header__nav-link:focus {
  outline: 2px solid #ffffff;
  outline-offset: 2px;
}
</style>
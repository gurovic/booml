<template>
  <header class="header">
    <div class="container">
      <div class="header__inner">
        <button type="button" class="header__title" @click="handleHomeClick">
          <img :src="logo" alt="Booml logo" class="header__logo" />
          <span class="header__title-text">BOOML</span>
        </button>

        <nav v-if="isAuthorized" class="header__nav">
          <button
            type="button"
            class="header__nav-link"
            @click="handleCoursesClick"
          >
            Мои курсы
          </button>
          <button
            type="button"
            class="header__nav-link"
            @click="handlePolygonClick"
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
import logo from '@/assets/logo.png'

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

const handlePolygonClick = () => {
  if (router.currentRoute.value.path !== '/polygon') {
    router.push('/polygon')
  }
}

const handleCoursesClick = () => {
  if (router.currentRoute.value.path !== '/courses') {
    router.push('/courses')
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
  font-size: 40px;
  line-height: 1;
  color: #ffffff;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}

.header__logo {
  width: 72px;
  height: 72px;
  margin-left: 24px;
  object-fit: contain;
  margin-right: 5px
}

.header__title:hover {
  opacity: 0.9;
}

.header__title:focus {
  outline: 2px solid #ffffff;
  outline-offset: 2px;
}

.header__nav {
  display: flex;
  align-items: center;
  margin-left: auto;
  margin-right: 16px;
}

.header__nav-link {
  font-family: var(--font-default);
  font-size: 16px;
  font-weight: 500;
  line-height: 1;
  color: #ffffff;
  text-decoration: none;
  background: none;
  border: none;
  padding: 8px 16px;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.header__nav-link:hover {
  opacity: 0.8;
}

.header__nav-link:focus {
  outline: 2px solid #ffffff;
  outline-offset: 2px;
}

.header__button {
  height: 40px;
  display: flex;
  align-items: center;
}
</style>

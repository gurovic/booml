<template>
  <div class="header">
    <div class="container">
      <div class="header__inner">
        <a class="header__title" href="/"><h1>Booml</h1></a>
        <button 
          class="header__button button button--secondary"
          @click="handleButton"
        >
          {{ isAuthorized ? "Выйти" : "Войти" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/UserStore'

const router = useRouter()
const userStore = useUserStore()
let user = userStore.getCurrentUser()

let isAuthorized = computed(() => user.value != null)

onMounted(async () => {
  // getting user from storage
})

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
  background-color: #144EEC;
  width: 100%;
  height: 60px;
}

.header__inner {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header__title {
  color: white;
}
</style>
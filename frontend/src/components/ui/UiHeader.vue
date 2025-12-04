<template>
  <div class="header">
    <div class="container">
      <div class="header__inner">
        <h1 class="header__title">Booml</h1>
        <button 
          class="header__button button button--secondary"
          @click=handle_button
        >
          {{ is_authorized ? "Выйти" : "Войти" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
let user = ref(null)

let is_authorized = computed(() => user.value != null)

onMounted(async () => {
  // getting user from storage
})

const handle_button = () => {
  if (is_authorized.value) {
    router.push('logout')
  } else {
    router.push('login')
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
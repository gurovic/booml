import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import router from '@/router/index.js'
import '@/assets/styles/main.css'
import { useUserStore } from '@/stores/UserStore'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
const userStore = useUserStore(pinia)
userStore.checkAuth()

app.use(router)

app.mount('#app')

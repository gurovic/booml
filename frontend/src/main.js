import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from '@/App.vue'
import router from '@/router/index.js'
import '@/assets/styles/main.css'
import 'katex/dist/katex.min.css'
import { useUserStore } from '@/stores/UserStore'

const app = createApp(App)
const pinia = createPinia()

;(async () => {
  app.use(pinia)
  const userStore = useUserStore(pinia)
  await userStore.checkAuth()

  app.use(router)

  app.mount('#app')
})()

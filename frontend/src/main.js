import './styles/fonts.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './shadcn.css'
import './tailwind.css'
import './styles/modal-compat.css'
import './styles/page-compat.css'
import './styles/pipeline-detail.css'
import '@fortawesome/fontawesome-free/css/all.min.css'
import './style.css'
import router from './router'
import { setupAxiosInterceptors } from './utils/axios-interceptor'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()
const app = createApp(App)
app.use(pinia)
app.use(router)

setupAxiosInterceptors()

const authStore = useAuthStore()
authStore.syncFromStorage()

app.mount('#app')
const appLoading = document.getElementById('app-loading')
if (appLoading) appLoading.style.display = 'none'

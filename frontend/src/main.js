import './styles/fonts.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import AppIcon from './components/ui/icon/AppIcon.vue'
import './shadcn.css'
import './tailwind.css'
import './styles/host-manager.css'
import './styles/pipeline-detail.css'
import './style.css'
import router from './router'
import { setupAxiosInterceptors } from './utils/axios-interceptor'
import { useAuthStore } from './stores/auth'

const pinia = createPinia()
const app = createApp(App)
app.component('AppIcon', AppIcon)
app.use(pinia)
app.use(router)

setupAxiosInterceptors()

const authStore = useAuthStore()
authStore.syncFromStorage()

app.mount('#app')
const appLoading = document.getElementById('app-loading')
if (appLoading) appLoading.style.display = 'none'

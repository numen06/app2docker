import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

// 导入 Bootstrap JS
import 'bootstrap/dist/js/bootstrap.bundle.min.js'

// 配置 axios
import { setupAxiosInterceptors } from './utils/axios-interceptor'

// 不设置 baseURL，直接使用 /api 前缀，Vite 会代理
setupAxiosInterceptors()

createApp(App).mount('#app')

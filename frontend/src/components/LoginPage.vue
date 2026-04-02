<template>
  <div class="login-page d-flex align-items-center justify-content-center min-vh-100 bg-light">
    <div class="login-container">
      <div class="card shadow-lg" style="width: 400px;">
        <div class="card-body p-4">
          <!-- Logo -->
          <div class="text-center mb-4">
            <i class="fas fa-box-open fa-3x text-primary mb-3"></i>
            <h3 class="fw-bold">App2Docker</h3>
            <p class="text-muted small">Docker 镜像构建平台</p>
          </div>

          <!-- 登录表单 -->
          <form @submit.prevent="handleLogin">
            <div class="mb-3">
              <label class="form-label">
                <i class="fas fa-user"></i> 用户名
              </label>
              <input 
                v-model="username" 
                type="text" 
                class="form-control" 
                placeholder="请输入用户名"
                required
                autocomplete="username"
              />
            </div>

            <div class="mb-3">
              <label class="form-label">
                <i class="fas fa-lock"></i> 密码
              </label>
              <input 
                v-model="password" 
                type="password" 
                class="form-control" 
                placeholder="请输入密码"
                required
                autocomplete="current-password"
              />
            </div>

            <div class="mb-3 form-check">
              <input 
                v-model="rememberMe" 
                type="checkbox" 
                class="form-check-input" 
                id="rememberMe"
              />
              <label class="form-check-label" for="rememberMe">
                记住我
              </label>
            </div>

            <button 
              type="submit" 
              class="btn btn-primary w-100" 
              :disabled="loading"
            >
              <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
              {{ loading ? '登录中...' : '登录' }}
            </button>
          </form>

          <!-- 错误提示 -->
          <div v-if="error" class="alert alert-danger mt-3 mb-0" role="alert">
            <i class="fas fa-exclamation-triangle"></i>
            {{ error }}
          </div>
        </div>

        <!-- 版本信息 -->
        <div class="card-footer text-center text-muted small bg-light">
          <div>
            <i class="fas fa-shield-alt"></i> 安全认证登录
          </div>
          <div v-if="appVersion" class="mt-1">
            <i class="fas fa-code-branch"></i>
            当前版本 <strong class="text-secondary">v{{ appVersion }}</strong>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 修改密码模态框（使用用户中心组件） -->
    <UserCenterModal 
      v-if="showChangePassword"
      v-model:show="showChangePassword" 
      :username="loginUsername || ''"
      :require-password-change="true"
      @password-changed="handlePasswordChangeSuccess"
    />
  </div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, ref } from 'vue'
import UserCenterModal from './UserCenterModal.vue'

const emit = defineEmits(['login-success'])

const appVersion = ref('')

onMounted(async () => {
  try {
    const res = await axios.get('/api/public/version')
    if (res.data?.success && res.data.version) {
      appVersion.value = res.data.version
    }
  } catch {
    // 版本展示非关键
  }
})

const username = ref('')
const password = ref('')
const rememberMe = ref(true)
const loading = ref(false)
const error = ref('')
const showChangePassword = ref(false)
const loginToken = ref(null)
const loginUsername = ref(null)

async function handleLogin() {
  // 如果正在加载，直接返回，避免重复提交
  if (loading.value) {
    return
  }
  
  error.value = ''
  loading.value = true
  
  try {
    const res = await axios.post('/api/login', {
      username: username.value.trim(),
      password: password.value
    })
    
    if (res.data.success) {
      // 检查是否需要修改密码
      if (res.data.require_password_change) {
        // 保存token和用户名，但先不触发登录成功事件
        loginToken.value = res.data.token
        loginUsername.value = res.data.username
        
        // 设置 axios 默认 header（修改密码时需要）
        axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`
        
        showChangePassword.value = true
        loading.value = false
        return
      }
      
      // 正常登录流程
      const storage = rememberMe.value ? localStorage : sessionStorage
      storage.setItem('auth_token', res.data.token)
      storage.setItem('username', res.data.username)
      
      // 设置 axios 默认 header
      axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.token}`
      
      emit('login-success', {
        username: res.data.username,
        token: res.data.token
      })
    } else {
      // 登录失败，显示错误信息，不闪退
      error.value = res.data.error || '登录失败'
      loading.value = false
    }
  } catch (err) {
    // 捕获所有错误，确保不会闪退
    console.error('登录错误:', err)
    if (err.response) {
      // 服务器返回了错误响应
      const status = err.response.status
      if (status === 401) {
        error.value = '用户名或密码错误'
      } else {
        error.value = err.response.data?.error || err.response.data?.detail || '登录失败，请检查用户名和密码'
      }
    } else if (err.request) {
      // 请求已发出但没有收到响应
      error.value = '网络连接失败，请检查网络设置'
    } else {
      // 其他错误
      error.value = '登录失败，请稍后重试'
    }
    loading.value = false
  }
}

function handlePasswordChangeSuccess() {
  // 密码修改成功后，完成登录流程
  const storage = rememberMe.value ? localStorage : sessionStorage
  storage.setItem('auth_token', loginToken.value)
  storage.setItem('username', loginUsername.value)
  
  axios.defaults.headers.common['Authorization'] = `Bearer ${loginToken.value}`
  
  emit('login-success', {
    username: loginUsername.value,
    token: loginToken.value
  })
  
  showChangePassword.value = false
}
</script>

<style scoped>
.login-page {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  animation: slideIn 0.4s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card {
  border: none;
  border-radius: 1rem;
}

.card-footer {
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 0 0 1rem 1rem;
}

code {
  background-color: #f8f9fa;
  padding: 2px 6px;
  border-radius: 3px;
  color: #d63384;
}
</style>


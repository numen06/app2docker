<template>
  <div id="app">
    <!-- 登录页面 -->
    <LoginPage v-if="!authenticated" @login-success="handleLoginSuccess" />

    <!-- 主应用 -->
    <div v-else class="min-vh-100 bg-light">
      <div class="container-fluid px-3 py-3" style="max-width: 1400px;">
        <!-- 标题 -->
        <div class="text-center mb-4">
          <h1 class="mb-2">
            <i class="fas fa-box-open text-primary"></i> App2Docker
          </h1>
          <p class="lead text-muted mb-0">上传 Java/Node.js 应用，一键构建并推送 Docker 镜像</p>
        </div>

        <!-- 操作面板 -->
        <div class="card shadow-sm">
          <div class="card-body p-4">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h5 class="mb-0">
                <i class="fas fa-tools"></i> 操作面板
              </h5>
              <div class="d-flex gap-2 align-items-center">
                <!-- 用户信息 -->
                <span class="text-muted small me-2">
                  <i class="fas fa-user-circle"></i> {{ username }}
                </span>
                <button class="btn btn-outline-secondary btn-sm" @click="showBuildLog = true">
                  <i class="fas fa-terminal"></i> 查看日志
                </button>
                <button class="btn btn-outline-primary btn-sm" @click="showConfig = true">
                  <i class="fas fa-cog"></i> 配置
                </button>
                <button class="btn btn-outline-danger btn-sm" @click="handleLogout">
                  <i class="fas fa-sign-out-alt"></i> 登出
                </button>
              </div>
            </div>

            <!-- 标签页 -->
            <ul class="nav nav-tabs mb-3">
              <li class="nav-item">
                <button 
                  type="button"
                  class="nav-link" 
                  :class="{ active: activeTab === 'build' }"
                  @click="activeTab = 'build'"
                >
                  <i class="fas fa-cloud-upload-alt"></i> 构建镜像
                </button>
              </li>
              <li class="nav-item">
                <button 
                  type="button"
                  class="nav-link" 
                  :class="{ active: activeTab === 'export' }"
                  @click="activeTab = 'export'"
                >
                  <i class="fas fa-file-export"></i> 导出镜像
                </button>
              </li>
              <li class="nav-item">
                <button 
                  type="button"
                  class="nav-link" 
                  :class="{ active: activeTab === 'export-tasks' }"
                  @click="activeTab = 'export-tasks'"
                >
                  <i class="fas fa-list-check"></i> 导出任务
                </button>
              </li>
              <li class="nav-item">
                <button 
                  type="button"
                  class="nav-link" 
                  :class="{ active: activeTab === 'compose' }"
                  @click="activeTab = 'compose'"
                >
                  <i class="fas fa-diagram-project"></i> Compose
                </button>
              </li>
              <li class="nav-item">
                <button 
                  type="button"
                  class="nav-link" 
                  :class="{ active: activeTab === 'template' }"
                  @click="activeTab = 'template'"
                >
                  <i class="fas fa-layer-group"></i> 模板管理
                </button>
              </li>
            </ul>

            <!-- 标签页内容 -->
            <div class="tab-content">
              <BuildPanel v-if="activeTab === 'build'" />
              <ExportPanel v-if="activeTab === 'export'" />
              <ExportTaskList v-if="activeTab === 'export-tasks'" />
              <ComposePanel v-if="activeTab === 'compose'" />
              <TemplatePanel v-if="activeTab === 'template'" />
            </div>
          </div>
        </div>
      </div>
      
      <!-- 构建日志模态框 - 始终挂载以便监听事件 -->
      <BuildLogModal v-model="showBuildLog" ref="buildLogModal" />
      
      <!-- 配置模态框 -->
      <ConfigModal v-if="showConfig" v-model="showConfig" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { isAuthenticated, getUsername, getToken, logout } from './utils/auth'
import axios from 'axios'

// 懒加载组件
import LoginPage from './components/LoginPage.vue'
import BuildPanel from './components/BuildPanel.vue'
import ExportPanel from './components/ExportPanel.vue'
import ExportTaskList from './components/ExportTaskList.vue'
import ComposePanel from './components/ComposePanel.vue'
import TemplatePanel from './components/TemplatePanel.vue'
import BuildLogModal from './components/BuildLogModal.vue'
import ConfigModal from './components/ConfigModal.vue'

const authenticated = ref(false)
const username = ref('')
const activeTab = ref('build')
const showBuildLog = ref(false)
const showConfig = ref(false)

function handleLoginSuccess(data) {
  authenticated.value = true
  username.value = data.username
  console.log('✅ 登录成功:', data.username)
}

async function handleLogout() {
  if (confirm('确定要退出登录吗？')) {
    await logout()
    authenticated.value = false
    username.value = ''
    console.log('👋 已登出')
  }
}

onMounted(() => {
  console.log('🚀 App 组件挂载')
  
  // 检查是否已登录
  if (isAuthenticated()) {
    authenticated.value = true
    username.value = getUsername() || 'User'
    
    // 设置 axios 默认 Authorization header
    const token = getToken()
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
    }
    
    console.log('✅ 已登录用户:', username.value)
  } else {
    console.log('🔒 未登录，显示登录页面')
  }
})
</script>

<style>
/* 导入 Bootstrap 和 FontAwesome */
@import 'bootstrap/dist/css/bootstrap.min.css';
@import '@fortawesome/fontawesome-free/css/all.min.css';

.nav-tabs .nav-link {
  padding: 0.75rem 1.25rem;
  font-size: 0.95rem;
  cursor: pointer;
  border: none;
  border-bottom: 2px solid transparent;
  background: none;
}

.nav-tabs .nav-link:hover {
  border-bottom-color: #dee2e6;
}

.nav-tabs .nav-link.active {
  color: #0d6efd;
  background-color: transparent;
  border-bottom-color: #0d6efd;
}

.form-label {
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
  font-weight: 500;
}

.form-control, .form-select {
  font-size: 0.95rem;
}
</style>

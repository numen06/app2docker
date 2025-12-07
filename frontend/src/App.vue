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
                <button class="btn btn-outline-primary btn-sm" @click="showUserCenter = true">
                  <i class="fas fa-user-circle"></i> 用户中心
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
                  :class="{ active: activeTab === 'source-build' }"
                  @click="activeTab = 'source-build'"
                >
                  <i class="fas fa-code-branch"></i> 源码构建
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
                  :class="{ active: activeTab === 'tasks' }"
                  @click="activeTab = 'tasks'"
                >
                  <i class="fas fa-list-check"></i> 任务管理
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
              <li class="nav-item">
                <button 
                  type="button"
                  class="nav-link" 
                  :class="{ active: activeTab === 'logs' }"
                  @click="activeTab = 'logs'"
                >
                  <i class="fas fa-history"></i> 操作日志
                </button>
              </li>
              <li class="nav-item">
                <button 
                  type="button"
                  class="nav-link" 
                  :class="{ active: activeTab === 'docker' }"
                  @click="activeTab = 'docker'"
                >
                  <i class="fas fa-server"></i> Docker 管理
                </button>
              </li>
            </ul>

            <!-- 标签页内容 -->
            <div class="tab-content">
              <BuildPanel v-if="activeTab === 'build'" />
              <SourceBuildPanel v-if="activeTab === 'source-build'" />
              <ExportPanel v-if="activeTab === 'export'" />
              <TaskManager v-if="activeTab === 'tasks'" />
              <ComposePanel v-if="activeTab === 'compose'" />
              <TemplatePanel v-if="activeTab === 'template'" />
              <OperationLogs v-if="activeTab === 'logs'" />
              <DockerManager v-if="activeTab === 'docker'" />
            </div>
          </div>
        </div>
      </div>
      
      <!-- 配置模态框 -->
      <ConfigModal v-if="showConfig" v-model="showConfig" />
      
      <!-- 用户中心模态框 -->
      <UserCenterModal v-if="showUserCenter" v-model:show="showUserCenter" :username="username" />
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, ref } from 'vue'
import { getToken, getUsername, isAuthenticated, logout } from './utils/auth'

// 懒加载组件
import BuildPanel from './components/BuildPanel.vue'
import ComposePanel from './components/ComposePanel.vue'
import ConfigModal from './components/ConfigModal.vue'
import DockerManager from './components/DockerManager.vue'
import ExportPanel from './components/ExportPanel.vue'
import LoginPage from './components/LoginPage.vue'
import OperationLogs from './components/OperationLogs.vue'
import SourceBuildPanel from './components/SourceBuildPanel.vue'
import TaskManager from './components/TaskManager.vue'
import TemplatePanel from './components/TemplatePanel.vue'
import UserCenterModal from './components/UserCenterModal.vue'

const authenticated = ref(false)
const username = ref('')
const activeTab = ref('build')
const showConfig = ref(false)
const showUserCenter = ref(false)

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

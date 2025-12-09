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
          <p class="lead text-muted mb-0">上传 Java/Node.js/Python/Go 应用，一键构建并推送 Docker 镜像</p>
        </div>

        <!-- 操作面板 -->
        <div class="card shadow-sm">
          <!-- 卡片头部：标题+操作按钮 -->
          <div class="card-header bg-white d-flex justify-content-between align-items-center py-2">
            <h5 class="mb-0">
              <i class="fas fa-tools text-primary"></i> 操作面板
            </h5>
            <div class="d-flex gap-2">
              <button class="btn btn-outline-primary btn-sm" @click="showUserCenter = true">
                <i class="fas fa-user-circle"></i> 用户中心
              </button>
              <button class="btn btn-outline-primary btn-sm" @click="activeTab = 'logs'">
                <i class="fas fa-history"></i> 操作日志
              </button>
              <button class="btn btn-outline-primary btn-sm" @click="showConfig = true">
                <i class="fas fa-cog"></i> 配置
              </button>
              <button class="btn btn-outline-danger btn-sm" @click="handleLogout">
                <i class="fas fa-sign-out-alt"></i> 登出
              </button>
            </div>
          </div>

          <!-- Tab 导航 -->
          <div class="card-header bg-white py-0 border-top-0">
            <ul class="nav nav-tabs border-0">
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'step-build' }" @click="activeTab = 'step-build'">
                  <i class="fas fa-list-ol"></i> 镜像构建
                </button>
              </li>
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'export' }" @click="activeTab = 'export'">
                  <i class="fas fa-file-export"></i> 导出镜像
                </button>
              </li>
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'tasks' }" @click="activeTab = 'tasks'">
                  <i class="fas fa-list-check"></i> 任务管理
                </button>
              </li>
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'pipeline' }" @click="activeTab = 'pipeline'">
                  <i class="fas fa-project-diagram"></i> 流水线
                </button>
              </li>
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'datasource' }" @click="activeTab = 'datasource'">
                  <i class="fas fa-database"></i> 数据源
                </button>
              </li>
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'template' }" @click="activeTab = 'template'">
                  <i class="fas fa-layer-group"></i> 模板管理
                </button>
              </li>
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'docker' }" @click="activeTab = 'docker'">
                  <i class="fas fa-server"></i> Docker 管理
                </button>
              </li>
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'resource-package' }" @click="activeTab = 'resource-package'">
                  <i class="fas fa-archive"></i> 资源包
                </button>
              </li>
              <li class="nav-item">
                <button type="button" class="nav-link" :class="{ active: activeTab === 'host' }" @click="activeTab = 'host'">
                  <i class="fas fa-server"></i> 主机管理
                </button>
              </li>
            </ul>
          </div>

          <!-- 标签页内容 -->
          <div class="card-body p-3">
            <StepBuildPanel v-if="activeTab === 'step-build'" />
            <ExportPanel v-if="activeTab === 'export'" />
            <TemplatePanel v-if="activeTab === 'template'" />
            <OperationLogs v-if="activeTab === 'logs'" />
            <DockerManager v-if="activeTab === 'docker'" />
            <PipelinePanel v-if="activeTab === 'pipeline'" />
            <DataSourcePanel v-if="activeTab === 'datasource'" />
            <TaskManager v-if="activeTab === 'tasks'" />
            <ResourcePackagePanel v-if="activeTab === 'resource-package'" />
            <HostManager v-if="activeTab === 'host'" />
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
import { useModalEscape } from './composables/useModalEscape'

// 懒加载组件
import ConfigModal from './components/ConfigModal.vue'
import DataSourcePanel from './components/DataSourcePanel.vue'
import DockerManager from './components/DockerManager.vue'
import ResourcePackagePanel from './components/ResourcePackagePanel.vue'
import ExportPanel from './components/ExportPanel.vue'
import HostManager from './components/HostManager.vue'
import LoginPage from './components/LoginPage.vue'
import OperationLogs from './components/OperationLogs.vue'
import PipelinePanel from './components/PipelinePanel.vue'
import StepBuildPanel from './components/StepBuildPanel.vue'
import TaskManager from './components/TaskManager.vue'
import TemplatePanel from './components/TemplatePanel.vue'
import UserCenterModal from './components/UserCenterModal.vue'

const authenticated = ref(false)
const username = ref('')
const activeTab = ref('step-build')
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

// 统一处理所有模态框的 ESC 键
useModalEscape()

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

/* === 全局统一样式 === */

/* Tab 样式统一 */
.nav-tabs {
  border-bottom: 1px solid #dee2e6;
}

.nav-tabs .nav-link {
  padding: 0.75rem 1.25rem;
  font-size: 0.95rem;
  cursor: pointer;
  border: none;
  border-bottom: 2px solid transparent;
  background: none;
  color: #6c757d;
  transition: color 0.15s, border-color 0.15s;
}

.nav-tabs .nav-link:hover {
  color: #0d6efd;
  border-bottom-color: #dee2e6;
}

.nav-tabs .nav-link.active {
  color: #0d6efd;
  background-color: transparent;
  border-bottom-color: #0d6efd;
  font-weight: 500;
}

/* 表单样式统一 */
.form-label {
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
  font-weight: 500;
}

.form-control, .form-select {
  font-size: 0.95rem;
}

/* 卡片样式统一 */
.card {
  border: 1px solid rgba(0,0,0,0.1);
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.card-header {
  background-color: #f8f9fa;
  border-bottom: 1px solid rgba(0,0,0,0.1);
  padding: 0.75rem 1rem;
}

.card-header.bg-white {
  background-color: #fff !important;
}

/* 按钮样式统一 */
.btn {
  font-size: 0.9rem;
  border-radius: 0.375rem;
}

.btn-sm {
  font-size: 0.8rem;
  padding: 0.35rem 0.65rem;
}

/* 表格样式统一 */
.table {
  margin-bottom: 0;
}

.table th {
  font-weight: 600;
  font-size: 0.85rem;
  background-color: #f8f9fa;
  border-bottom-width: 1px;
}

.table td {
  vertical-align: middle;
  font-size: 0.9rem;
}

.table-hover tbody tr:hover {
  background-color: rgba(13, 110, 253, 0.04);
}

/* Badge 样式统一 */
.badge {
  font-weight: 500;
  font-size: 0.75rem;
}

/* 搜索栏样式 */
.input-group-text {
  background-color: #f8f9fa;
  border-color: #dee2e6;
}

/* 分页样式 */
.pagination {
  margin-bottom: 0;
}

.page-link {
  font-size: 0.85rem;
  padding: 0.35rem 0.65rem;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}
</style>

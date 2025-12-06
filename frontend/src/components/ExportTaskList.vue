<template>
  <div class="export-task-list">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-list-check"></i> 导出任务清单
      </h5>
      <div class="d-flex gap-2 align-items-center">
        <select v-model="statusFilter" class="form-select form-select-sm" style="width: auto;">
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="running">进行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
        <button class="btn btn-sm btn-outline-primary" @click="loadTasks">
          <i class="fas fa-sync-alt"></i> 刷新
        </button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">加载中...</span>
      </div>
    </div>

    <div v-else-if="filteredTasks.length === 0" class="text-center py-4 text-muted">
      <i class="fas fa-inbox fa-2x mb-2"></i>
      <p class="mb-0">暂无导出任务</p>
    </div>

    <div v-else class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th style="width: 200px;">镜像</th>
            <th style="width: 100px;">标签</th>
            <th style="width: 100px;">压缩</th>
            <th style="width: 120px;">状态</th>
            <th style="width: 150px;">创建时间</th>
            <th style="width: 100px;">文件大小</th>
            <th style="width: 150px;" class="text-end">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in filteredTasks" :key="task.task_id">
            <td>
              <code class="small">{{ task.image }}</code>
            </td>
            <td>{{ task.tag }}</td>
            <td>
              <span v-if="task.compress === 'gzip'" class="badge bg-secondary">GZIP</span>
              <span v-else class="badge bg-light text-dark">TAR</span>
            </td>
            <td>
              <span v-if="task.status === 'pending'" class="badge bg-secondary">
                <i class="fas fa-clock"></i> 等待中
              </span>
              <span v-else-if="task.status === 'running'" class="badge bg-primary">
                <span class="spinner-border spinner-border-sm me-1"></span> 进行中
              </span>
              <span v-else-if="task.status === 'completed'" class="badge bg-success">
                <i class="fas fa-check-circle"></i> 已完成
              </span>
              <span v-else-if="task.status === 'failed'" class="badge bg-danger">
                <i class="fas fa-times-circle"></i> 失败
              </span>
            </td>
            <td class="small text-muted">
              {{ formatTime(task.created_at) }}
            </td>
            <td class="small">
              <span v-if="task.file_size">{{ formatFileSize(task.file_size) }}</span>
              <span v-else>-</span>
            </td>
            <td class="text-end">
              <div class="btn-group btn-group-sm">
                <button 
                  v-if="task.status === 'completed'"
                  class="btn btn-sm btn-success"
                  @click="downloadTask(task)"
                  :disabled="downloading === task.task_id"
                >
                  <i class="fas fa-download"></i>
                  <span v-if="downloading === task.task_id" class="spinner-border spinner-border-sm ms-1"></span>
                </button>
                <button 
                  class="btn btn-sm btn-outline-danger"
                  @click="deleteTask(task)"
                  :disabled="deleting === task.task_id"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="alert alert-danger mt-3 mb-0">
      <i class="fas fa-exclamation-circle"></i> {{ error }}
    </div>

    <!-- 失败任务详情 -->
    <div v-if="selectedFailedTask" class="alert alert-danger mt-3 mb-0">
      <div class="d-flex justify-content-between align-items-start">
        <div class="flex-grow-1">
          <strong>任务失败:</strong> {{ selectedFailedTask.image }}:{{ selectedFailedTask.tag }}
          <div class="small mt-1">
            <code>{{ selectedFailedTask.error }}</code>
          </div>
        </div>
        <button class="btn btn-sm btn-outline-danger" @click="selectedFailedTask = null">
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { ref, computed, onMounted, onUnmounted } from 'vue'

const tasks = ref([])
const loading = ref(false)
const error = ref(null)
const statusFilter = ref('')
const downloading = ref(null)
const deleting = ref(null)
const selectedFailedTask = ref(null)
let refreshInterval = null

const filteredTasks = computed(() => {
  if (!statusFilter.value) {
    return tasks.value
  }
  return tasks.value.filter(t => t.status === statusFilter.value)
})

function formatTime(isoString) {
  if (!isoString) return '-'
  const date = new Date(isoString)
  
  // 显示完整精确时间（包括年月日时分秒）
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

function formatFileSize(bytes) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

async function loadTasks() {
  loading.value = true
  error.value = null
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {}
    const res = await axios.get('/api/export-tasks', { params })
    tasks.value = res.data.tasks || []
  } catch (err) {
    error.value = err.response?.data?.error || err.message || '加载任务列表失败'
    console.error('加载任务列表失败:', err)
  } finally {
    loading.value = false
  }
}

async function downloadTask(task) {
  if (downloading.value) return
  
  downloading.value = task.task_id
  try {
    const res = await axios.get(`/api/export-tasks/${task.task_id}/download`, {
      responseType: 'blob'
    })
    
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    
    // 生成文件名
    const image = task.image.replace(/\//g, '_')
    const tag = task.tag
    const ext = task.compress === 'gzip' ? '.tar.gz' : '.tar'
    a.download = `${image}-${tag}${ext}`
    
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    alert(err.response?.data?.error || err.message || '下载失败')
  } finally {
    downloading.value = null
  }
}

async function deleteTask(task) {
  if (!confirm(`确定要删除任务 "${task.image}:${task.tag}" 吗？`)) {
    return
  }
  
  deleting.value = task.task_id
  try {
    await axios.delete(`/api/export-tasks/${task.task_id}`)
    await loadTasks()
  } catch (err) {
    alert(err.response?.data?.error || err.message || '删除失败')
  } finally {
    deleting.value = null
  }
}

onMounted(() => {
  loadTasks()
  // 每5秒自动刷新一次（只刷新进行中的任务）
  refreshInterval = setInterval(() => {
    const hasRunning = tasks.value.some(t => t.status === 'running' || t.status === 'pending')
    if (hasRunning) {
      loadTasks()
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.export-task-list {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.table {
  font-size: 0.9rem;
}

code {
  font-size: 0.85rem;
  background-color: #f8f9fa;
  padding: 2px 6px;
  border-radius: 3px;
}
</style>

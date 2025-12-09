<template>
  <div>
    <div 
      v-if="modelValue && task"
      class="modal fade show d-block" 
      style="z-index: 1070;"
      tabindex="-1"
      @click.self="close"
    >
      <div class="modal-dialog modal-xl" style="max-width: 90%;">
        <div class="modal-content">
          <div class="modal-header" :class="getStatusHeaderClass(task.status)">
            <h5 class="modal-title">
              <i :class="getStatusIcon(task.status)"></i>
              任务日志 - {{ task.image || '未知' }}:{{ task.tag || 'latest' }}
              <span v-if="isTaskRunning" class="badge bg-primary ms-2">
                <span class="spinner-border spinner-border-sm me-1" style="width: 0.7rem; height: 0.7rem;"></span> 运行中
              </span>
            </h5>
            <button type="button" class="btn-close" :class="task.status === 'failed' ? 'btn-close-white' : ''" @click="close"></button>
          </div>
          <div class="modal-body p-0" style="display: flex; flex-direction: column; max-height: 80vh;">
            <!-- 工具栏 -->
            <div class="d-flex justify-content-between align-items-center p-2 border-bottom bg-light">
              <div class="d-flex align-items-center gap-2">
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-primary"
                  @click="refreshLogs"
                  :disabled="refreshingLogs"
                >
                  <i class="fas fa-sync-alt" :class="{ 'fa-spin': refreshingLogs }"></i> 刷新
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-secondary"
                  @click="toggleAutoScroll"
                >
                  <i class="fas" :class="autoScroll ? 'fa-pause' : 'fa-play'"></i> {{ autoScroll ? '暂停滚动' : '自动滚动' }}
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-secondary"
                  @click="copyLogs"
                >
                  <i class="fas fa-copy"></i> 复制
                </button>
                <span v-if="isTaskRunning" class="text-muted small">
                  <i class="fas fa-info-circle"></i> 正在自动刷新日志...
                </span>
              </div>
              <div class="text-muted small">
                任务ID: <code>{{ task.task_id?.substring(0, 8) || '未知' }}</code>
              </div>
            </div>
            
            <!-- 任务概况（仅已完成/失败/停止时显示） -->
            <div 
              v-if="task.status === 'failed' || task.status === 'completed' || task.status === 'stopped'" 
              class="p-3 border-bottom" 
              :class="getStatusSummaryClass(task.status)"
            >
              <div class="d-flex align-items-center mb-2">
                <i :class="getStatusIcon(task.status)" class="me-2"></i>
                <strong>{{ getStatusText(task.status) }}</strong>
              </div>
              <div v-if="task.status === 'failed' && task.error" class="mt-2">
                <strong>错误信息：</strong>
                <pre class="mb-0 mt-1 p-2 bg-dark text-light rounded" style="font-size: 0.85rem; max-height: 150px; overflow-y: auto;">{{ task.error }}</pre>
              </div>
              <div v-if="task.status === 'completed'" class="mt-2 small">
                <div><strong>创建时间：</strong>{{ formatTime(task.created_at) }}</div>
                <div v-if="task.completed_at"><strong>完成时间：</strong>{{ formatTime(task.completed_at) }}</div>
                <div v-if="task.completed_at"><strong>耗时：</strong>{{ calculateDuration(task.created_at, task.completed_at) }}</div>
              </div>
              <div v-if="task.status === 'stopped'" class="mt-2 small">
                <div><strong>创建时间：</strong>{{ formatTime(task.created_at) }}</div>
                <div v-if="task.completed_at"><strong>停止时间：</strong>{{ formatTime(task.completed_at) }}</div>
              </div>
            </div>
            
            <!-- 日志内容 -->
            <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
              <pre 
                ref="logContainer"
                class="bg-dark text-light p-3 mb-0" 
                style="flex: 1; overflow-y: auto; overflow-x: hidden; font-size: 0.85rem; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', monospace; line-height: 1.5; min-height: 0;"
              >{{ logs || '暂无日志' }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="close">关闭</button>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="modelValue" class="modal-backdrop fade show" style="z-index: 1065;" @click="close"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import axios from 'axios'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  task: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const logs = ref('')
const logContainer = ref(null)
const logPollingInterval = ref(null)
const autoScroll = ref(true)
const refreshingLogs = ref(false)

// 计算任务是否正在运行
const isTaskRunning = computed(() => {
  if (!props.task) return false
  const status = props.task.status
  return status === 'running' || status === 'pending'
})

// 滚动日志到底部
function scrollToBottom() {
  if (logContainer.value && autoScroll.value) {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
}

// 获取任务日志
async function fetchTaskLogs(taskId, silent = false) {
  if (!silent) {
    refreshingLogs.value = true
  }
  
  try {
    const res = await axios.get(`/api/build-tasks/${taskId}/logs`)
    const oldLength = logs.value.length
    if (typeof res.data === 'string') {
      logs.value = res.data || '暂无日志'
    } else {
      logs.value = JSON.stringify(res.data, null, 2)
    }
    
    // 如果有新内容，自动滚动到底部
    if (logs.value.length > oldLength && autoScroll.value) {
      setTimeout(() => {
        scrollToBottom()
      }, 50)
    }
  } catch (err) {
    console.error('获取日志失败:', err)
    const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || '未知错误'
    logs.value = `加载日志失败: ${errorMsg}`
  } finally {
    refreshingLogs.value = false
  }
}

// 刷新日志
async function refreshLogs() {
  if (!props.task) return
  await fetchTaskLogs(props.task.task_id, false)
}

// 切换自动滚动
function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
  if (autoScroll.value) {
    scrollToBottom()
  }
}

// 复制日志
function copyLogs() {
  navigator.clipboard.writeText(logs.value).then(() => {
    alert('日志已复制到剪贴板')
  }).catch(err => {
    console.error('复制失败:', err)
    alert('复制失败，请手动选择文本复制')
  })
}

// 启动日志轮询
function startLogPolling(taskId) {
  // 清除旧的定时器
  if (logPollingInterval.value) {
    clearInterval(logPollingInterval.value)
  }
  
  // 如果任务正在运行，每2秒刷新一次日志
  if (isTaskRunning.value) {
    logPollingInterval.value = setInterval(async () => {
      if (props.modelValue && props.task) {
        // 静默刷新，不显示加载状态
        await fetchTaskLogs(taskId, true)
        
        // 检查任务状态是否已改变
        try {
          const res = await axios.get(`/api/build-tasks/${taskId}`)
          if (res.data && res.data.status) {
            // 通过 emit 更新任务状态
            emit('task-status-updated', res.data.status)
            // 如果任务已完成或失败，停止轮询
            if (res.data.status === 'completed' || res.data.status === 'failed') {
              stopLogPolling()
            }
          }
        } catch (err) {
          console.error('获取任务状态失败:', err)
        }
      } else {
        stopLogPolling()
      }
    }, 2000)  // 每2秒刷新一次
  }
}

// 停止日志轮询
function stopLogPolling() {
  if (logPollingInterval.value) {
    clearInterval(logPollingInterval.value)
    logPollingInterval.value = null
  }
}

// 关闭模态框
function close() {
  stopLogPolling()
  emit('update:modelValue', false)
}

// 状态相关函数
function getStatusHeaderClass(status) {
  if (status === 'failed') return 'bg-danger text-white'
  if (status === 'completed') return 'bg-success text-white'
  if (status === 'stopped') return 'bg-warning text-dark'
  return ''
}

function getStatusSummaryClass(status) {
  if (status === 'failed') return 'bg-danger bg-opacity-10 border border-danger'
  if (status === 'completed') return 'bg-success bg-opacity-10 border border-success'
  if (status === 'stopped') return 'bg-warning bg-opacity-10 border border-warning'
  return 'bg-secondary bg-opacity-10'
}

function getStatusIcon(status) {
  if (status === 'failed') return 'fas fa-times-circle'
  if (status === 'completed') return 'fas fa-check-circle'
  if (status === 'stopped') return 'fas fa-stop-circle'
  if (status === 'running') return 'fas fa-spinner fa-spin'
  if (status === 'pending') return 'fas fa-clock'
  return 'fas fa-info-circle'
}

function getStatusText(status) {
  if (status === 'failed') return '任务失败'
  if (status === 'completed') return '任务成功'
  if (status === 'stopped') return '任务已停止'
  if (status === 'running') return '任务进行中'
  if (status === 'pending') return '任务等待中'
  return '未知状态'
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit', 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  })
}

function calculateDuration(startTime, endTime) {
  if (!startTime || !endTime) return '-'
  const start = new Date(startTime)
  const end = new Date(endTime)
  const diff = Math.floor((end - start) / 1000)  // 秒
  const hours = Math.floor(diff / 3600)
  const minutes = Math.floor((diff % 3600) / 60)
  const seconds = diff % 60
  if (hours > 0) {
    return `${hours}小时${minutes}分钟${seconds}秒`
  } else if (minutes > 0) {
    return `${minutes}分钟${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}

// 监听 modelValue 和 task 变化
watch(() => [props.modelValue, props.task], ([newValue, newTask]) => {
  if (newValue && newTask) {
    const taskId = newTask.task_id
    if (taskId) {
      logs.value = '加载中...'
      fetchTaskLogs(taskId)
      startLogPolling(taskId)
    } else {
      logs.value = '任务ID不存在'
      stopLogPolling()
    }
  } else {
    stopLogPolling()
    logs.value = ''
  }
}, { immediate: true })

// 监听任务状态变化
watch(() => props.task?.status, (newStatus) => {
  if (newStatus === 'completed' || newStatus === 'failed') {
    stopLogPolling()
  } else if (newStatus === 'running' || newStatus === 'pending') {
    const taskId = props.task?.task_id
    if (taskId) {
      startLogPolling(taskId)
    }
  }
})

// 组件卸载时清理定时器
onUnmounted(() => {
  stopLogPolling()
})
</script>

<style scoped>
.modal.show {
  display: block !important;
}

.modal-backdrop.show {
  opacity: 0.5;
}
</style>


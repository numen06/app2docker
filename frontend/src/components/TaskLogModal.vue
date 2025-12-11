<template>
  <div>
    <div 
      v-if="modelValue"
      class="modal fade show d-block" 
      style="z-index: 1070;"
      tabindex="-1"
    >
      <div class="modal-dialog modal-xl" style="max-width: 90%;">
        <div class="modal-content">
          <div class="modal-header" :class="task ? getStatusHeaderClass(task.status) : ''">
            <h5 class="modal-title">
              <i :class="task ? getStatusIcon(task.status) : 'fas fa-info-circle'"></i>
              任务日志 - {{ task?.image || '未知' }}:{{ task?.tag || 'latest' }}
              <span v-if="task && isTaskRunning" class="badge bg-primary ms-2">
                <span class="spinner-border spinner-border-sm me-1" style="width: 0.7rem; height: 0.7rem;"></span> 运行中
              </span>
            </h5>
            <button type="button" class="btn-close" :class="task && task.status === 'failed' ? 'btn-close-white' : ''" @click="close"></button>
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
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-info"
                  @click="scrollToTop"
                  title="滚动到顶部"
                >
                  <i class="fas fa-arrow-up"></i> 到顶
                </button>
                <button 
                  type="button" 
                  class="btn btn-sm btn-outline-info"
                  @click="scrollToBottom"
                  title="滚动到底部"
                >
                  <i class="fas fa-arrow-down"></i> 到底
                </button>
                <span v-if="isTaskRunning" class="text-muted small">
                  <i class="fas fa-info-circle"></i> 正在自动刷新日志...
                </span>
              </div>
              <div class="text-muted small">
                任务ID: <code>{{ task?.task_id?.substring(0, 8) || '未知' }}</code>
              </div>
            </div>
            
            <!-- 任务概况按钮（仅已完成/失败/停止时显示） -->
            <div 
              v-if="task && (task.status === 'failed' || task.status === 'completed' || task.status === 'stopped')" 
              class="p-2 border-bottom bg-light"
            >
              <button 
                type="button" 
                class="btn btn-sm w-100 text-start"
                :class="showTaskSummary ? 'btn-outline-primary' : 'btn-outline-secondary'"
                @click="showTaskSummary = !showTaskSummary"
              >
                <i :class="getStatusIcon(task.status)" class="me-2"></i>
                <strong>{{ getStatusText(task.status) }}</strong>
                <i class="fas float-end mt-1" :class="showTaskSummary ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
              </button>
              <div v-if="showTaskSummary" class="mt-2 p-3 rounded" :class="getStatusSummaryClass(task.status)">
                <div v-if="task.status === 'failed' && task.error" class="mb-3">
                  <strong>错误信息：</strong>
                  <pre class="mb-0 mt-1 p-2 bg-dark text-light rounded" style="font-size: 0.85rem; max-height: 150px; overflow-y: auto;">{{ task.error }}</pre>
                </div>
                <div v-if="task.status === 'completed'" class="small">
                  <div class="mb-1"><strong>创建时间：</strong>{{ formatTime(task.created_at) }}</div>
                  <div v-if="task.completed_at" class="mb-1"><strong>完成时间：</strong>{{ formatTime(task.completed_at) }}</div>
                  <div v-if="task.completed_at"><strong>耗时：</strong>{{ calculateDuration(task.created_at, task.completed_at) }}</div>
                </div>
                <div v-if="task.status === 'stopped'" class="small">
                  <div class="mb-1"><strong>创建时间：</strong>{{ formatTime(task.created_at) }}</div>
                  <div v-if="task.completed_at"><strong>停止时间：</strong>{{ formatTime(task.completed_at) }}</div>
                </div>
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
    
    <div v-if="modelValue" class="modal-backdrop fade show" style="z-index: 1065;"></div>
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
const showTaskSummary = ref(false) // 任务概况是否展开

// 计算任务是否正在运行
const isTaskRunning = computed(() => {
  if (!props.task) return false
  const status = props.task.status
  return status === 'running' || status === 'pending'
})

// 滚动日志到顶部
function scrollToTop() {
  if (logContainer.value) {
    autoScroll.value = false  // 滚动到顶部时关闭自动滚动
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = 0
      }
    })
  }
}

// 滚动日志到底部
function scrollToBottom() {
  if (logContainer.value) {
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

// 禁用/启用 body 滚动
function lockBodyScroll() {
  document.body.style.overflow = 'hidden'
}

function unlockBodyScroll() {
  document.body.style.overflow = ''
}

// 关闭模态框
function close() {
  stopLogPolling()
  unlockBodyScroll()
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

// 加载日志的函数
function loadLogsIfNeeded() {
  if (props.modelValue && props.task && props.task.task_id) {
    const taskId = props.task.task_id
    console.log('TaskLogModal 加载日志', { taskId, task: props.task })
    logs.value = '加载中...'
    fetchTaskLogs(taskId)
    startLogPolling(taskId)
  } else {
    console.log('TaskLogModal 条件不满足', { modelValue: props.modelValue, task: props.task })
    stopLogPolling()
    if (!props.modelValue) {
      logs.value = ''
    } else if (!props.task) {
      logs.value = '任务信息不存在'
    } else if (!props.task.task_id) {
      logs.value = '任务ID不存在'
    }
  }
}

// 监听 modelValue 变化
watch(() => props.modelValue, (newValue) => {
  console.log('TaskLogModal modelValue 变化', { modelValue: newValue, task: props.task })
  if (newValue) {
    // 模态框打开时，加载日志并锁定 body 滚动
    lockBodyScroll()
    loadLogsIfNeeded()
  } else {
    // 模态框关闭时，清理并恢复 body 滚动
    console.log('关闭日志模态框')
    stopLogPolling()
    logs.value = ''
    unlockBodyScroll()
  }
})

// 监听 task 变化（当模态框已打开时）
watch(() => props.task, (newTask, oldTask) => {
  console.log('TaskLogModal task 变化', { modelValue: props.modelValue, newTask, oldTask })
  if (props.modelValue && newTask) {
    // 如果模态框已打开且 task 变化，重新加载日志
    // 使用 setTimeout 确保在下一个 tick 执行
    setTimeout(() => {
      loadLogsIfNeeded()
    }, 0)
  }
}, { deep: true, immediate: false })

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
  // 确保恢复 body 滚动
  unlockBodyScroll()
})
</script>

<style scoped>
.modal.show {
  display: block !important;
}

.modal-backdrop.show {
  opacity: 0.5;
}

/* 防止滚动穿透 */
.modal {
  overflow: hidden;
}
</style>


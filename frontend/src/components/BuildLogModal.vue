<template>
  <div>
    <div 
      v-if="modelValue"
      class="modal fade show d-block" 
      tabindex="-1"
    >
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header bg-dark text-white">
          <h5 class="modal-title">
            <i class="fas fa-terminal"></i> 构建日志
          </h5>
          <button type="button" class="btn-close btn-close-white" @click="close"></button>
          </div>
          <div class="modal-body p-0" style="height: 600px;">
          <!-- 工具栏 -->
          <div class="log-toolbar">
            <input 
              v-model="searchTerm" 
              type="text" 
              placeholder="🔍 搜索..." 
              class="form-control-sm"
              style="min-width: 150px;"
            />
            <select v-model="levelFilter" class="form-select-sm">
              <option value="all">全部</option>
              <option value="error">错误</option>
              <option value="warning">警告</option>
              <option value="success">成功</option>
              <option value="info">信息</option>
            </select>
            <div class="btn-group btn-group-sm">
              <button 
                class="btn btn-outline-secondary py-0" 
                :class="{ active: autoScroll }"
                @click="autoScroll = !autoScroll"
                title="自动滚动"
              >
                <i class="fas fa-arrow-down"></i>
              </button>
              <button 
                class="btn btn-outline-secondary py-0" 
                :class="{ active: showLineNumber }"
                @click="showLineNumber = !showLineNumber"
                title="行号"
              >
                <i class="fas fa-list-ol"></i>
              </button>
              <button 
                class="btn btn-outline-secondary py-0" 
                :class="{ active: showTimestamp }"
                @click="showTimestamp = !showTimestamp"
                title="时间戳"
              >
                <i class="fas fa-clock"></i>
              </button>
            </div>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-primary py-0" @click="copyLog" title="复制">
                <i class="fas fa-copy"></i>
              </button>
              <button class="btn btn-outline-success py-0" @click="downloadLog" title="下载">
                <i class="fas fa-download"></i>
              </button>
              <button class="btn btn-outline-danger py-0" @click="clearLog" title="清空">
                <i class="fas fa-trash"></i>
              </button>
              <button class="btn btn-outline-info py-0" @click="scrollToTop" title="滚动到顶部">
                <i class="fas fa-arrow-up"></i>
              </button>
              <button class="btn btn-outline-info py-0" @click="scrollToBottom" title="滚动到底部">
                <i class="fas fa-arrow-down"></i>
              </button>
            </div>
            <div class="log-stats">
              {{ logs.length }} 行 | {{ filteredLogs.length }} 显示
            </div>
          </div>

          <!-- 日志容器 -->
          <div ref="logContainer" class="log-container">
            <div 
              v-for="(log, index) in filteredLogs" 
              :key="index"
              class="log-line"
              :class="log.level"
            >
              <span v-if="showLineNumber" class="log-line-number">{{ log.number }}</span>
              <span v-if="showTimestamp" class="log-timestamp">[{{ log.timestamp }}]</span>
              <span class="log-content" v-html="highlightSearch(log.text)"></span>
            </div>
          </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="modelValue" class="modal-backdrop fade show"></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean
})

const emit = defineEmits(['update:modelValue'])

const logs = ref([])
const searchTerm = ref('')
const levelFilter = ref('all')
const autoScroll = ref(true)
const showLineNumber = ref(true)
const showTimestamp = ref(true)
const logContainer = ref(null)

const filteredLogs = computed(() => {
  return logs.value.filter(log => {
    if (levelFilter.value !== 'all' && log.level !== levelFilter.value) {
      return false
    }
    if (searchTerm.value && !log.text.toLowerCase().includes(searchTerm.value.toLowerCase())) {
      return false
    }
    return true
  })
})

function addLog(text, level = 'info') {
  const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  
  // 智能检测级别
  if (!level || level === 'info') {
    if (text.includes('❌') || text.includes('错误') || text.includes('失败') || text.includes('ERROR')) {
      level = 'error'
    } else if (text.includes('✅') || text.includes('成功') || text.includes('完成') || text.includes('SUCCESS')) {
      level = 'success'
    } else if (text.includes('⚠️') || text.includes('警告') || text.includes('WARNING')) {
      level = 'warning'
    }
  }
  
  logs.value.push({
    number: logs.value.length + 1,
    timestamp,
    text,
    level
  })
  
  if (autoScroll.value) {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
}

function highlightSearch(text) {
  if (!searchTerm.value) return text
  const regex = new RegExp(`(${searchTerm.value})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

function clearLog() {
  if (confirm('确定要清空所有日志吗？')) {
    logs.value = []
  }
}

function copyLog() {
  // 清理和格式化日志文本
  const text = logs.value
    .map(log => {
      // 移除可能的额外空白和特殊字符
      let cleanText = log.text.trim()
      // 确保每行都是独立的
      return cleanText
    })
    .filter(line => line.length > 0)  // 过滤空行
    .join('\n')  // 用换行符连接
  
  navigator.clipboard.writeText(text).then(() => {
    alert(`日志已复制到剪贴板 (${logs.value.length} 行)`)
  }).catch(err => {
    console.error('复制失败:', err)
    alert('复制失败，请手动选择文本复制')
  })
}

function downloadLog() {
  const text = logs.value
    .map(log => {
      let line = ''
      if (showLineNumber.value) line += `${log.number.toString().padStart(4, ' ')} `
      if (showTimestamp.value) line += `[${log.timestamp}] `
      line += log.text.trim()  // 清理文本
      return line
    })
    .filter(line => line.trim().length > 0)  // 过滤空行
    .join('\n')
  
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `app2docker-${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.log`
  a.click()
  URL.revokeObjectURL(url)
}

// 滚动到顶部
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

// 滚动到底部
function scrollToBottom() {
  if (logContainer.value) {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
}

function close() {
  unlockBodyScroll()
  emit('update:modelValue', false)
}

// 事件处理函数
const handleShowBuildLog = () => {
  console.log('📖 收到 show-build-log 事件')
  emit('update:modelValue', true)
}

const handleAddLog = (e) => {
  console.log('📝 收到 add-log 事件:', e.detail.text)
  addLog(e.detail.text, e.detail.level)
}

// 禁用/启用 body 滚动
function lockBodyScroll() {
  document.body.style.overflow = 'hidden'
}

function unlockBodyScroll() {
  document.body.style.overflow = ''
}

// 监听 modelValue 变化，控制 body 滚动
watch(() => props.modelValue, (newValue) => {
  if (newValue) {
    lockBodyScroll()
  } else {
    unlockBodyScroll()
  }
})

// 监听全局事件
onMounted(() => {
  window.addEventListener('show-build-log', handleShowBuildLog)
  window.addEventListener('add-log', handleAddLog)
  // 如果组件挂载时模态框已经打开，锁定滚动
  if (props.modelValue) {
    lockBodyScroll()
  }
})

onUnmounted(() => {
  window.removeEventListener('show-build-log', handleShowBuildLog)
  window.removeEventListener('add-log', handleAddLog)
  // 组件卸载时确保恢复滚动
  unlockBodyScroll()
})

defineExpose({
  addLog,
  clearLog
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

.log-toolbar {
  background: #252526;
  border-bottom: 1px solid #3e3e42;
  padding: 6px 10px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.log-toolbar input,
.log-toolbar select {
  background: #3c3c3c;
  border: 1px solid #555;
  color: #d4d4d4;
  padding: 3px 6px;
  border-radius: 3px;
  font-size: 11px;
}

.log-toolbar .btn-sm {
  padding: 2px 6px;
  font-size: 11px;
}

.log-stats {
  color: #858585;
  font-size: 10px;
  margin-left: auto;
}

.log-container {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  height: calc(100% - 42px);
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.5;
}

.log-line {
  padding: 4px 12px 4px 60px;
  border-left: 3px solid transparent;
  position: relative;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.log-line-number {
  position: absolute;
  left: 8px;
  top: 4px;
  color: #858585;
  font-size: 11px;
  width: 40px;
  text-align: right;
}

.log-timestamp {
  color: #858585;
  font-size: 11px;
  margin-right: 8px;
}

.log-line.error {
  border-left-color: #f48771;
  background: rgba(244, 135, 113, 0.05);
}

.log-line.error .log-content {
  color: #f48771;
}

.log-line.success {
  border-left-color: #89d185;
  background: rgba(137, 209, 133, 0.05);
}

.log-line.success .log-content {
  color: #89d185;
}

.log-line.warning {
  border-left-color: #e5c07b;
  background: rgba(229, 192, 123, 0.05);
}

.log-line.warning .log-content {
  color: #e5c07b;
}

.log-line.info {
  border-left-color: #61afef;
}

.log-line.info .log-content {
  color: #61afef;
}
</style>


<template>
  <div class="task-manager">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-tasks"></i> 任务管理
      </h5>
      <div class="d-flex gap-2 align-items-center">
        <select v-model="statusFilter" class="form-select form-select-sm" style="width: auto;" @change="resetPage">
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="running">进行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
        <select v-model="categoryFilter" class="form-select form-select-sm" style="width: auto;" @change="resetPage">
          <option value="">全部类型</option>
          <option value="build">构建任务</option>
          <option value="export">导出任务</option>
        </select>
        <button class="btn btn-sm btn-outline-primary" @click="loadTasks">
          <i class="fas fa-sync-alt"></i> 刷新
        </button>
        <button class="btn btn-sm btn-outline-danger" @click="showCleanupModal = true">
          <i class="fas fa-broom"></i> 清理
        </button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">加载中...</span>
      </div>
    </div>

    <div v-else-if="paginatedTasks.length === 0" class="text-center py-4 text-muted">
      <i class="fas fa-inbox fa-2x mb-2"></i>
      <p class="mb-0">暂无任务</p>
    </div>

    <div v-else class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th style="width: 100px;">类型</th>
            <th style="width: 200px;">镜像/任务</th>
            <th style="width: 100px;">标签</th>
            <th style="width: 120px;">状态</th>
            <th style="width: 150px;">创建时间</th>
            <th style="width: 100px;">时长</th>
            <th style="width: 100px;">文件大小</th>
            <th style="width: 200px;" class="text-end">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in paginatedTasks" :key="task.task_id">
            <td>
              <span v-if="task.task_category === 'build'" class="badge bg-info">
                <i class="fas fa-hammer"></i> 构建
              </span>
              <span v-else class="badge bg-secondary">
                <i class="fas fa-download"></i> 导出
              </span>
            </td>
            <td>
              <code class="small">{{ task.image || (task.task_type ? task.task_type : '未知') }}</code>
            </td>
            <td>{{ task.tag || '-' }}</td>
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
              <span v-if="task.status === 'running'" class="text-primary">
                <span class="spinner-border spinner-border-sm me-1" style="width: 0.7rem; height: 0.7rem;"></span>
                {{ calculateDuration(task.created_at, null) }}
              </span>
              <span v-else-if="task.completed_at" :class="{'text-success': task.status === 'completed', 'text-danger': task.status === 'failed'}">
                {{ calculateDuration(task.created_at, task.completed_at) }}
              </span>
              <span v-else class="text-muted">-</span>
            </td>
            <td class="small">
              <span v-if="task.file_size">{{ formatFileSize(task.file_size) }}</span>
              <span v-else>-</span>
            </td>
            <td class="text-end">
              <div class="btn-group btn-group-sm">
                <button 
                  v-if="task.task_category === 'build' && task.status === 'completed' && task.task_type === 'build_from_source'"
                  class="btn btn-sm btn-outline-success"
                  @click="addToPipeline(task)"
                  :title="'加入流水线'"
                >
                  <i class="fas fa-plus-circle"></i> 流水线
                </button>
                <button 
                  v-if="task.task_category === 'build'"
                  class="btn btn-sm btn-outline-info"
                  @click="viewLogs(task)"
                  :disabled="viewingLogs === task.task_id"
                  :title="'查看构建日志'"
                >
                  <i class="fas fa-terminal"></i> 日志
                </button>
                <button 
                  v-if="task.status === 'failed' && task.error"
                  class="btn btn-sm btn-outline-warning"
                  @click="showErrorDetails(task)"
                  :title="'查看错误详情'"
                >
                  <i class="fas fa-exclamation-triangle"></i> 错误
                </button>
                <button 
                  v-if="task.task_category === 'export' && task.status === 'completed'"
                  class="btn btn-sm btn-success"
                  @click="downloadTask(task)"
                  :disabled="downloading === task.task_id"
                  :title="'下载导出文件'"
                >
                  <i class="fas fa-download"></i>
                  <span v-if="downloading === task.task_id" class="spinner-border spinner-border-sm ms-1"></span>
                </button>
                <button 
                  class="btn btn-sm btn-outline-danger"
                  @click="deleteTask(task)"
                  :disabled="deleting === task.task_id"
                  :title="'删除任务'"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页控件 -->
    <div v-if="totalPages > 1" class="d-flex justify-content-between align-items-center mt-3">
      <div class="text-muted small">
        显示第 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, totalTasks) }} 条，共 {{ totalTasks }} 条
      </div>
      <nav>
        <ul class="pagination pagination-sm mb-0">
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <button class="page-link" @click="changePage(1)" :disabled="currentPage === 1">
              <i class="fas fa-angle-double-left"></i>
            </button>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <button class="page-link" @click="changePage(currentPage - 1)" :disabled="currentPage === 1">
              <i class="fas fa-angle-left"></i>
            </button>
          </li>
          <li 
            v-for="page in visiblePages" 
            :key="page" 
            class="page-item" 
            :class="{ active: currentPage === page }"
          >
            <button class="page-link" @click="changePage(page)">{{ page }}</button>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <button class="page-link" @click="changePage(currentPage + 1)" :disabled="currentPage === totalPages">
              <i class="fas fa-angle-right"></i>
            </button>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <button class="page-link" @click="changePage(totalPages)" :disabled="currentPage === totalPages">
              <i class="fas fa-angle-double-right"></i>
            </button>
          </li>
        </ul>
      </nav>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="alert alert-danger mt-3 mb-0">
      <i class="fas fa-exclamation-circle"></i> {{ error }}
    </div>

    <!-- 错误详情模态框 -->
    <div v-if="showErrorModal && selectedErrorTask" class="modal fade show" style="display: block;" tabindex="-1" @click.self="closeErrorModal">
      <div class="modal-dialog modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header bg-danger text-white">
            <h5 class="modal-title">
              <i class="fas fa-exclamation-triangle"></i> 任务错误详情
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="closeErrorModal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <strong>任务信息:</strong>
              <div class="mt-1">
                <code>{{ selectedErrorTask.image || selectedErrorTask.task_type }}:{{ selectedErrorTask.tag || 'latest' }}</code>
              </div>
            </div>
            <div class="mb-3">
              <strong>任务类型:</strong>
              <span class="badge" :class="selectedErrorTask.task_category === 'build' ? 'bg-info' : 'bg-secondary'">
                {{ selectedErrorTask.task_category === 'build' ? '构建任务' : '导出任务' }}
              </span>
            </div>
            <div class="mb-3">
              <strong>创建时间:</strong> {{ formatTime(selectedErrorTask.created_at) }}
            </div>
            <div class="mb-3" v-if="selectedErrorTask.completed_at">
              <strong>失败时间:</strong> {{ formatTime(selectedErrorTask.completed_at) }}
            </div>
            <div>
              <strong>错误信息:</strong>
              <pre class="bg-dark text-light p-3 rounded mt-2" style="max-height: 300px; overflow-y: auto; font-size: 0.85rem;">{{ selectedErrorTask.error }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeErrorModal">关闭</button>
            <button 
              v-if="selectedErrorTask.task_category === 'build'"
              type="button" 
              class="btn btn-info" 
              @click="viewLogsFromError(selectedErrorTask)"
            >
              <i class="fas fa-terminal"></i> 查看完整日志
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showErrorModal" class="modal-backdrop fade show" @click="closeErrorModal"></div>

    <!-- 日志模态框 -->
    <div v-if="showLogModal && selectedTask" class="modal fade show" style="display: block;" tabindex="-1" @click.self="closeLogModal">
      <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">任务日志 - {{ selectedTask.image }}:{{ selectedTask.tag }}</h5>
            <button type="button" class="btn-close" @click="closeLogModal"></button>
          </div>
          <div class="modal-body">
            <pre class="bg-dark text-light p-3 rounded" style="max-height: 500px; overflow-y: auto; font-size: 0.85rem;">{{ taskLogs }}</pre>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeLogModal">关闭</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showLogModal" class="modal-backdrop fade show" @click="closeLogModal"></div>

    <!-- 清理任务模态框 -->
    <div v-if="showCleanupModal" class="modal fade show" style="display: block;" tabindex="-1" @click.self="closeCleanupModal">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header bg-warning text-dark">
            <h5 class="modal-title">
              <i class="fas fa-broom"></i> 批量清理任务
            </h5>
            <button type="button" class="btn-close" @click="closeCleanupModal"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-warning">
              <i class="fas fa-exclamation-triangle"></i>
              清理后的任务无法恢复，请谨慎操作！
            </div>

            <div class="mb-3">
              <label class="form-label">清理类型</label>
              <select v-model="cleanupOptions.type" class="form-select">
                <option value="status">按状态清理</option>
                <option value="days">按时间清理</option>
              </select>
            </div>

            <div v-if="cleanupOptions.type === 'status'" class="mb-3">
              <label class="form-label">选择状态</label>
              <select v-model="cleanupOptions.status" class="form-select">
                <option value="">所有状态</option>
                <option value="completed">已完成</option>
                <option value="failed">失败</option>
              </select>
            </div>

            <div v-if="cleanupOptions.type === 'days'" class="mb-3">
              <label class="form-label">清理 N 天前的任务</label>
              <input 
                v-model.number="cleanupOptions.days" 
                type="number" 
                class="form-control" 
                min="1"
                placeholder="例如：7 表示清理7天前的任务"
              />
            </div>

            <div class="mb-3">
              <label class="form-label">任务类型</label>
              <select v-model="cleanupOptions.taskType" class="form-select">
                <option value="">所有类型</option>
                <option value="build">仅构建任务</option>
                <option value="export">仅导出任务</option>
              </select>
            </div>

            <div class="alert alert-info mb-0">
              <small>
                <i class="fas fa-info-circle"></i>
                <strong>预计清理：</strong>
                <span v-if="cleanupOptions.type === 'status'">
                  {{ cleanupOptions.status ? `${cleanupOptions.status === 'completed' ? '已完成' : '失败'}` : '所有状态' }}的
                </span>
                <span v-else>
                  {{ cleanupOptions.days || 'N' }} 天前的
                </span>
                {{ cleanupOptions.taskType === 'build' ? '构建任务' : cleanupOptions.taskType === 'export' ? '导出任务' : '所有任务' }}
              </small>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeCleanupModal">取消</button>
            <button 
              type="button" 
              class="btn btn-danger" 
              @click="executeCleanup"
              :disabled="cleaning || (cleanupOptions.type === 'days' && !cleanupOptions.days)"
            >
              <span v-if="cleaning" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="fas fa-broom"></i>
              {{ cleaning ? '清理中...' : '确认清理' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showCleanupModal" class="modal-backdrop fade show" @click="closeCleanupModal"></div>

    <!-- 加入流水线模态框 -->
    <div v-if="showPipelineModal && selectedPipelineTask" class="modal fade show" style="display: block;" tabindex="-1" @click.self="closePipelineModal">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header bg-success text-white">
            <h5 class="modal-title">
              <i class="fas fa-plus-circle"></i> 加入流水线
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="closePipelineModal"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-info mb-3">
              <i class="fas fa-info-circle"></i>
              将此成功的构建任务配置保存为流水线，可通过 Webhook 或定时任务自动触发构建。
            </div>

            <form @submit.prevent="savePipeline">
              <div class="mb-3">
                <label class="form-label">流水线名称 <span class="text-danger">*</span></label>
                <input 
                  v-model="pipelineForm.name" 
                  type="text" 
                  class="form-control" 
                  required
                  placeholder="例如：主分支自动构建"
                />
              </div>

              <div class="mb-3">
                <label class="form-label">描述</label>
                <input 
                  v-model="pipelineForm.description" 
                  type="text" 
                  class="form-control"
                  placeholder="流水线描述（可选）"
                />
              </div>

              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">Git 仓库</label>
                  <input 
                    v-model="pipelineForm.git_url" 
                    type="text" 
                    class="form-control" 
                    readonly
                  />
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">分支</label>
                  <input 
                    v-model="pipelineForm.branch" 
                    type="text" 
                    class="form-control"
                  />
                </div>
              </div>

              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">镜像名称</label>
                  <input 
                    v-model="pipelineForm.image_name" 
                    type="text" 
                    class="form-control"
                  />
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">镜像标签</label>
                  <input 
                    v-model="pipelineForm.tag" 
                    type="text" 
                    class="form-control"
                  />
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label">触发方式</label>
                <div class="form-check">
                  <input 
                    v-model="pipelineForm.trigger_webhook" 
                    class="form-check-input" 
                    type="checkbox" 
                    id="triggerWebhook"
                  />
                  <label class="form-check-label" for="triggerWebhook">
                    <i class="fas fa-link"></i> Webhook 触发
                  </label>
                </div>
                <div class="form-check mt-2">
                  <input 
                    v-model="pipelineForm.trigger_schedule" 
                    class="form-check-input" 
                    type="checkbox" 
                    id="triggerSchedule"
                  />
                  <label class="form-check-label" for="triggerSchedule">
                    <i class="fas fa-clock"></i> 定时触发
                  </label>
                </div>
              </div>

              <div v-if="pipelineForm.trigger_schedule" class="mb-3">
                <label class="form-label">Cron 表达式</label>
                <input 
                  v-model="pipelineForm.cron_expression" 
                  type="text" 
                  class="form-control"
                  placeholder="0 0 * * * (每天零点)"
                />
                <div class="form-text small">
                  示例：<code>0 0 * * *</code> 每天零点，<code>0 */6 * * *</code> 每6小时
                </div>
              </div>

              <div class="form-check mb-3">
                <input 
                  v-model="pipelineForm.enabled" 
                  class="form-check-input" 
                  type="checkbox" 
                  id="pipelineEnabled"
                />
                <label class="form-check-label" for="pipelineEnabled">
                  启用流水线
                </label>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closePipelineModal">取消</button>
            <button 
              type="button" 
              class="btn btn-success" 
              @click="savePipeline"
              :disabled="saving"
            >
              <i class="fas fa-save"></i> 保存
              <span v-if="saving" class="spinner-border spinner-border-sm ms-1"></span>
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showPipelineModal" class="modal-backdrop fade show" @click="closePipelineModal"></div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, onUnmounted, ref } from 'vue'

const tasks = ref([])
const loading = ref(false)
const error = ref(null)
const statusFilter = ref('')
const categoryFilter = ref('')
const downloading = ref(null)
const deleting = ref(null)
const viewingLogs = ref(null)
const showLogModal = ref(false)
const selectedTask = ref(null)
const taskLogs = ref('')
const showErrorModal = ref(false)
const selectedErrorTask = ref(null)
const currentPage = ref(1)  // 当前页码
const pageSize = ref(10)    // 每页显示数量
const showCleanupModal = ref(false)  // 清理模态框
const cleaning = ref(false)  // 清理中状态
const cleanupOptions = ref({
  type: 'status',  // status 或 days
  status: 'completed',  // completed, failed, 或 ''
  days: 7,  // 清理N天前的任务
  taskType: ''  // build, export, 或 ''
})
const showPipelineModal = ref(false)  // 流水线模态框
const selectedPipelineTask = ref(null)  // 选中的任务
const saving = ref(false)  // 保存中状态
const pipelineForm = ref({
  name: '',
  description: '',
  git_url: '',
  branch: '',
  image_name: '',
  tag: '',
  project_type: '',
  template: '',
  template_params: {},
  sub_path: '',
  use_project_dockerfile: true,
  push: false,
  push_registry: '',
  trigger_webhook: true,
  trigger_schedule: false,
  cron_expression: '',
  enabled: true
})
let refreshInterval = null

const filteredTasks = computed(() => {
  let result = tasks.value
  if (statusFilter.value) {
    result = result.filter(t => t.status === statusFilter.value)
  }
  if (categoryFilter.value) {
    result = result.filter(t => t.task_category === categoryFilter.value)
  }
  return result
})

// 总任务数
const totalTasks = computed(() => filteredTasks.value.length)

// 总页数
const totalPages = computed(() => Math.ceil(totalTasks.value / pageSize.value))

// 当前页的任务列表
const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredTasks.value.slice(start, end)
})

// 可见的页码列表
const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages = []
  
  if (total <= 7) {
    // 总页数小于7，显示所有页码
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    // 总页数大于7，智能显示
    if (current <= 4) {
      // 前部：1 2 3 4 5 ... 最后页
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 3) {
      // 后部：1 ... 倍数第5页 倍数第4页 倍数第3页 倍数第2页 最后页
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      // 中间：1 ... current-1 current current+1 ... 最后页
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    }
  }
  
  return pages.filter(p => p !== '...' || pages.indexOf(p) === pages.lastIndexOf(p))
})

// 切换页码
function changePage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  currentPage.value = page
}

// 重置到第1页（切换过滤条件时）
function resetPage() {
  currentPage.value = 1
}

function showErrorDetails(task) {
  selectedErrorTask.value = task
  showErrorModal.value = true
}

function closeErrorModal() {
  showErrorModal.value = false
  selectedErrorTask.value = null
}

function viewLogsFromError(task) {
  closeErrorModal()
  viewLogs(task)
}

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

function calculateDuration(startTime, endTime) {
  if (!startTime) return '-'
  
  const start = new Date(startTime)
  const end = endTime ? new Date(endTime) : new Date()
  
  const diffMs = end - start
  if (diffMs < 0) return '-'
  
  const seconds = Math.floor(diffMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0) {
    return `${hours}小时${minutes % 60}分`
  } else if (minutes > 0) {
    return `${minutes}分${seconds % 60}秒`
  } else {
    return `${seconds}秒`
  }
}

async function loadTasks() {
  loading.value = true
  error.value = null
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const res = await axios.get('/api/tasks', { params })
    tasks.value = res.data.tasks || []
  } catch (err) {
    error.value = err.response?.data?.error || err.message || '加载任务列表失败'
    console.error('加载任务列表失败:', err)
  } finally {
    loading.value = false
  }
}

async function viewLogs(task) {
  if (viewingLogs.value) return
  
  viewingLogs.value = task.task_id
  selectedTask.value = task
  showLogModal.value = true
  taskLogs.value = '加载中...'
  
  try {
    const res = await axios.get(`/api/build-tasks/${task.task_id}/logs`)
    // 直接使用 res.data,不设置 responseType
    if (typeof res.data === 'string') {
      taskLogs.value = res.data || '暂无日志'
    } else {
      // 如果返回的不是字符串,尝试转换
      taskLogs.value = JSON.stringify(res.data, null, 2)
    }
  } catch (err) {
    console.error('获取日志失败:', err)
    const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || '未知错误'
    taskLogs.value = `加载日志失败: ${errorMsg}`
  } finally {
    viewingLogs.value = null
  }
}

function closeLogModal() {
  showLogModal.value = false
  selectedTask.value = null
  taskLogs.value = ''
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
    const tag = task.tag || 'latest'
    // 检查 compress 字段，支持多种格式
    const isCompressed = task.compress && ['gzip', 'gz', 'tgz', '1', 'true', 'yes'].includes(task.compress.toLowerCase())
    const ext = isCompressed ? '.tar.gz' : '.tar'
    a.download = `${image}-${tag}${ext}`
    
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('下载失败:', err)
    const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || '下载失败'
    error.value = `下载失败: ${errorMsg}`
    // 3秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes('下载失败')) {
        error.value = null
      }
    }, 3000)
  } finally {
    downloading.value = null
  }
}

async function deleteTask(task) {
  const taskName = task.image || task.task_type || '未知任务'
  const taskTag = task.tag || '-'
  if (!confirm(`确定要删除任务 "${taskName}:${taskTag}" 吗？`)) {
    return
  }
  
  deleting.value = task.task_id
  try {
    if (task.task_category === 'build') {
      await axios.delete(`/api/build-tasks/${task.task_id}`)
    } else {
      await axios.delete(`/api/export-tasks/${task.task_id}`)
    }
    // 成功删除后刷新列表
    await loadTasks()
  } catch (err) {
    console.error('删除任务失败:', err)
    const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || '删除失败'
    error.value = `删除任务失败: ${errorMsg}`
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes('删除任务失败')) {
        error.value = null
      }
    }, 5000)
  } finally {
    deleting.value = null
  }
}

function closeCleanupModal() {
  showCleanupModal.value = false
  // 重置选项
  cleanupOptions.value = {
    type: 'status',
    status: 'completed',
    days: 7,
    taskType: ''
  }
}

async function executeCleanup() {
  if (cleaning.value) return
  
  // 二次确认
  let confirmMsg = ''
  if (cleanupOptions.value.type === 'status') {
    const statusText = cleanupOptions.value.status 
      ? (cleanupOptions.value.status === 'completed' ? '已完成' : '失败')
      : '所有状态'
    confirmMsg = `确定要清理${statusText}的任务吗？`
  } else {
    confirmMsg = `确定要清理${cleanupOptions.value.days}天前的任务吗？`
  }
  
  if (!confirm(confirmMsg)) {
    return
  }
  
  cleaning.value = true
  error.value = null
  
  try {
    const payload = {
      task_type: cleanupOptions.value.taskType || null
    }
    
    if (cleanupOptions.value.type === 'status') {
      payload.status = cleanupOptions.value.status || null
    } else {
      payload.days = cleanupOptions.value.days
    }
    
    const res = await axios.post('/api/tasks/cleanup', payload)
    
    // 显示成功消息
    alert(`成功清理 ${res.data.removed_count} 个任务`)
    
    // 关闭模态框
    closeCleanupModal()
    
    // 刷新任务列表
    await loadTasks()
  } catch (err) {
    console.error('清理任务失败:', err)
    const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || '清理失败'
    error.value = `清理任务失败: ${errorMsg}`
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes('清理任务失败')) {
        error.value = null
      }
    }, 5000)
  } finally {
    cleaning.value = false
  }
}

// 打开流水线模态框
function addToPipeline(task) {
  selectedPipelineTask.value = task
  
  // 从任务中提取配置信息
  const config = task.config || {}
  
  pipelineForm.value = {
    name: `${task.image || 'unnamed'}-pipeline`,
    description: `基于任务 ${task.task_id.substring(0, 8)} 创建`,
    git_url: config.git_url || '',
    branch: config.branch || 'main',
    image_name: task.image || '',
    tag: task.tag || 'latest',
    project_type: config.project_type || 'jar',
    template: config.template || '',
    template_params: config.template_params || {},
    sub_path: config.sub_path || '',
    use_project_dockerfile: config.use_project_dockerfile !== false,
    push: config.push || false,
    push_registry: config.push_registry || '',
    trigger_webhook: true,
    trigger_schedule: false,
    cron_expression: '',
    enabled: true
  }
  
  showPipelineModal.value = true
}

// 关闭流水线模态框
function closePipelineModal() {
  showPipelineModal.value = false
  selectedPipelineTask.value = null
}

// 保存流水线
async function savePipeline() {
  if (saving.value) return
  
  if (!pipelineForm.value.name) {
    alert('请输入流水线名称')
    return
  }
  
  if (!pipelineForm.value.git_url) {
    alert('Git 仓库地址不能为空')
    return
  }
  
  if (pipelineForm.value.trigger_schedule && !pipelineForm.value.cron_expression) {
    alert('启用定时触发时，必须填写 Cron 表达式')
    return
  }
  
  saving.value = true
  error.value = null
  
  try {
    const payload = {
      name: pipelineForm.value.name,
      description: pipelineForm.value.description,
      git_url: pipelineForm.value.git_url,
      branch: pipelineForm.value.branch,
      project_type: pipelineForm.value.project_type,
      template: pipelineForm.value.template,
      image_name: pipelineForm.value.image_name,
      tag: pipelineForm.value.tag,
      push: pipelineForm.value.push,
      push_registry: pipelineForm.value.push_registry,
      template_params: pipelineForm.value.template_params,
      sub_path: pipelineForm.value.sub_path,
      use_project_dockerfile: pipelineForm.value.use_project_dockerfile,
      enabled: pipelineForm.value.enabled,
      cron_expression: pipelineForm.value.trigger_schedule ? pipelineForm.value.cron_expression : null
    }
    
    await axios.post('/api/pipelines', payload)
    
    alert('流水线创建成功！')
    closePipelineModal()
  } catch (err) {
    console.error('创建流水线失败:', err)
    const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || '创建失败'
    error.value = `创建流水线失败: ${errorMsg}`
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes('创建流水线失败')) {
        error.value = null
      }
    }, 5000)
  } finally {
    saving.value = false
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
.task-manager {
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

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* 分页样式优化 */
.pagination .page-link {
  min-width: 38px;
  text-align: center;
}

.pagination .page-item.disabled .page-link {
  cursor: not-allowed;
}

.pagination .page-item.active .page-link {
  font-weight: 600;
}
</style>


<template>
  <div class="pipeline-panel">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-project-diagram"></i> 流水线管理
      </h5>
      <button class="btn btn-primary btn-sm" @click="showCreateModal">
        <i class="fas fa-plus"></i> 新建流水线
      </button>
    </div>

    <!-- 流水线列表 -->
    <div class="table-responsive">
      <table class="table table-sm table-hover">
        <thead>
          <tr>
            <th style="width: 15%;">名称</th>
            <th style="width: 18%;">Git 仓库</th>
            <th style="width: 8%;">分支</th>
            <th style="width: 12%;">镜像</th>
            <th style="width: 8%;">状态</th>
            <th style="width: 8%;">当前任务</th>
            <th style="width: 12%;">最后构建</th>
            <th style="width: 6%;">定时</th>
            <th style="width: 6%;">触发次数</th>
            <th style="width: 10%;">最后触发</th>
            <th style="width: 7%;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="11" class="text-center">
              <span class="spinner-border spinner-border-sm"></span> 加载中...
            </td>
          </tr>
          <tr v-else-if="pipelines.length === 0">
            <td colspan="11" class="text-center text-muted">
              暂无流水线配置
            </td>
          </tr>
          <tr v-for="pipeline in pipelines" :key="pipeline.pipeline_id">
            <td>
              <div class="text-truncate" :title="pipeline.name">
                <strong>{{ pipeline.name }}</strong>
              </div>
              <small class="text-muted text-truncate d-block" :title="pipeline.description">
                {{ pipeline.description || '-' }}
              </small>
            </td>
            <td>
              <small class="font-monospace text-truncate d-block" :title="pipeline.git_url">
                {{ formatGitUrl(pipeline.git_url) }}
              </small>
            </td>
            <td>
              <span class="badge bg-secondary">{{ pipeline.branch || '默认' }}</span>
            </td>
            <td>
              <small class="font-monospace text-truncate d-block" :title="`${pipeline.image_name}:${pipeline.tag}`">
                {{ pipeline.image_name }}:{{ pipeline.tag }}
              </small>
            </td>
            <td>
              <span v-if="pipeline.enabled" class="badge bg-success">
                <i class="fas fa-check-circle"></i> 已启用
              </span>
              <span v-else class="badge bg-secondary">
                <i class="fas fa-times-circle"></i> 已禁用
              </span>
            </td>
            <td>
              <span v-if="pipeline.current_task_info">
                <span v-if="pipeline.current_task_status === 'running'" class="badge bg-primary">
                  <span class="spinner-border spinner-border-sm me-1" style="width: 0.65rem; height: 0.65rem;"></span> 运行中
                </span>
                <span v-else-if="pipeline.current_task_status === 'pending'" class="badge bg-warning">
                  <i class="fas fa-clock"></i> 等待中
                </span>
                <span v-else class="text-muted small">-</span>
              </span>
              <span v-else class="text-muted small">-</span>
            </td>
            <td>
              <span v-if="pipeline.last_build">
                <div class="d-flex align-items-center gap-1 mb-1">
                  <span 
                    :class="{
                      'badge': true,
                      'bg-success': pipeline.last_build.status === 'completed',
                      'bg-danger': pipeline.last_build.status === 'failed',
                    }"
                  >
                    <i v-if="pipeline.last_build.status === 'completed'" class="fas fa-check-circle"></i>
                    <i v-else-if="pipeline.last_build.status === 'failed'" class="fas fa-times-circle"></i>
                    {{ pipeline.last_build.status === 'completed' ? '成功' : '失败' }}
                  </span>
                  <button 
                    v-if="pipeline.last_build.task_id && pipeline.last_build.status !== 'deleted'"
                    class="btn btn-sm btn-outline-info p-0" 
                    style="width: 20px; height: 20px; line-height: 1;"
                    @click="viewTaskLogs(pipeline.last_build.task_id, pipeline.last_build)"
                    title="查看日志"
                  >
                    <i class="fas fa-terminal" style="font-size: 0.7rem;"></i>
                  </button>
                </div>
                <small class="text-muted d-block" :title="formatDateTime(pipeline.last_build.completed_at || pipeline.last_build.created_at)">
                  {{ formatDateTime(pipeline.last_build.completed_at || pipeline.last_build.created_at) }}
                </small>
                <small class="text-muted d-block">
                  <code>{{ pipeline.last_build.task_id.substring(0, 8) }}</code>
                </small>
              </span>
              <span v-else class="text-muted small">-</span>
            </td>
            <td>
              <span v-if="pipeline.cron_expression" class="badge bg-info" :title="pipeline.cron_expression">
                <i class="fas fa-clock"></i> 已启用
              </span>
              <span v-else class="text-muted">
                -
              </span>
            </td>
            <td class="text-center">{{ pipeline.trigger_count || 0 }}</td>
            <td>
              <small v-if="pipeline.last_triggered_at" :title="formatDateTime(pipeline.last_triggered_at)">
                {{ formatDateTime(pipeline.last_triggered_at) }}
              </small>
              <small v-else class="text-muted">-</small>
            </td>
            <td>
              <div class="btn-group btn-group-sm">
                <button 
                  class="btn btn-outline-success" 
                  @click="runPipeline(pipeline)"
                  :disabled="running === pipeline.pipeline_id"
                  title="手动运行"
                >
                  <i class="fas fa-play"></i>
                  <span v-if="running === pipeline.pipeline_id" class="spinner-border spinner-border-sm ms-1"></span>
                </button>
                <button 
                  class="btn btn-outline-secondary" 
                  @click="showHistory(pipeline)"
                  title="查看历史构建"
                >
                  <i class="fas fa-history"></i>
                </button>
                <button 
                  class="btn btn-outline-info" 
                  @click="showWebhookUrl(pipeline)"
                  title="查看 Webhook URL"
                >
                  <i class="fas fa-link"></i>
                </button>
                <button 
                  class="btn btn-outline-primary" 
                  @click="editPipeline(pipeline)"
                  title="编辑"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button 
                  class="btn btn-outline-danger" 
                  @click="deletePipeline(pipeline)"
                  title="删除"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 创建/编辑流水线模态框 -->
    <div v-if="showModal" class="modal show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5)">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ editingPipeline ? '编辑流水线' : '新建流水线' }}
            </h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="savePipeline">
              <div class="mb-3">
                <label class="form-label">流水线名称 <span class="text-danger">*</span></label>
                <input 
                  v-model="formData.name" 
                  type="text" 
                  class="form-control form-control-sm" 
                  required
                  placeholder="例如：主分支自动构建"
                >
              </div>

              <div class="mb-3">
                <label class="form-label">描述</label>
                <input 
                  v-model="formData.description" 
                  type="text" 
                  class="form-control form-control-sm"
                  placeholder="流水线描述（可选）"
                >
              </div>

              <div class="mb-3">
                <label class="form-label">Git 仓库地址 <span class="text-danger">*</span></label>
                <input 
                  v-model="formData.git_url" 
                  type="text" 
                  class="form-control form-control-sm" 
                  required
                  placeholder="https://github.com/user/repo.git"
                >
              </div>

              <div class="row">
                <div class="col-md-4 mb-3">
                  <label class="form-label">分支名称</label>
                  <input 
                    v-model="formData.branch" 
                    type="text" 
                    class="form-control form-control-sm"
                    placeholder="main"
                  >
                </div>
                <div class="col-md-4 mb-3">
                  <label class="form-label">子路径</label>
                  <input 
                    v-model="formData.sub_path" 
                    type="text" 
                    class="form-control form-control-sm"
                    placeholder="留空表示根目录"
                  >
                </div>
                <div class="col-md-4 mb-3">
                  <label class="form-label">项目类型</label>
                  <select v-model="formData.project_type" class="form-select form-select-sm">
                    <option value="jar">Java (JAR)</option>
                    <option value="nodejs">Node.js</option>
                    <option value="python">Python</option>
                    <option value="go">Go</option>
                    <option value="web">静态网站</option>
                  </select>
                </div>
              </div>

              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">镜像名称 <span class="text-danger">*</span></label>
                  <input 
                    v-model="formData.image_name" 
                    type="text" 
                    class="form-control form-control-sm" 
                    required
                    placeholder="myapp/demo"
                  >
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">镜像标签</label>
                  <input 
                    v-model="formData.tag" 
                    type="text" 
                    class="form-control form-control-sm"
                    placeholder="latest"
                  >
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label">Dockerfile 模板</label>
                <select v-model="formData.template" class="form-select form-select-sm">
                  <option value="">使用项目中的 Dockerfile</option>
                  <option v-for="tpl in templates" :key="tpl.name" :value="tpl.name">
                    {{ tpl.name }} ({{ tpl.project_type }})
                  </option>
                </select>
              </div>

              <div class="mb-3">
                <label class="form-label">Webhook 密钥</label>
                <input 
                  v-model="formData.webhook_secret" 
                  type="text" 
                  class="form-control form-control-sm"
                  placeholder="留空自动生成"
                >
                <small class="text-muted">用于验证 Webhook 签名（可选）</small>
              </div>

              <div class="form-check mb-3">
                <input 
                  v-model="formData.push" 
                  class="form-check-input" 
                  type="checkbox" 
                  id="pushCheck"
                >
                <label class="form-check-label" for="pushCheck">
                  构建完成后推送镜像
                </label>
              </div>

              <div v-if="formData.push" class="mb-3">
                <label class="form-label">推送仓库</label>
                <select v-model="formData.push_registry" class="form-select form-select-sm">
                  <option value="">使用默认仓库</option>
                  <option v-for="reg in registries" :key="reg.name" :value="reg.name">
                    {{ reg.name }} ({{ reg.registry }})
                  </option>
                </select>
              </div>

              <div class="form-check mb-3">
                <input 
                  v-model="formData.enabled" 
                  class="form-check-input" 
                  type="checkbox" 
                  id="enabledCheck"
                >
                <label class="form-check-label" for="enabledCheck">
                  启用流水线
                </label>
              </div>

              <!-- 定时触发配置 -->
              <div class="mb-3">
                <div class="form-check mb-2">
                  <input 
                    v-model="formData.trigger_schedule" 
                    class="form-check-input" 
                    type="checkbox" 
                    id="triggerScheduleCheck"
                  >
                  <label class="form-check-label" for="triggerScheduleCheck">
                    启用定时触发
                  </label>
                </div>
                
                <div v-if="formData.trigger_schedule" class="ms-3">
                  <label class="form-label">Cron 表达式 <span class="text-danger">*</span></label>
                  <input 
                    v-model="formData.cron_expression" 
                    type="text" 
                    class="form-control form-control-sm font-monospace"
                    placeholder="0 0 * * * (每天零点)"
                    :required="formData.trigger_schedule"
                  >
                  <small class="text-muted">
                    示例：<br>
                    <code>0 0 * * *</code> - 每天零点<br>
                    <code>0 */2 * * *</code> - 每2小时<br>
                    <code>0 0 * * 1</code> - 每周一零点<br>
                    <code>*/30 * * * *</code> - 每30分钟
                  </small>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeModal">取消</button>
            <button type="button" class="btn btn-primary btn-sm" @click="savePipeline">
              <i class="fas fa-save"></i> 保存
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Webhook URL 模态框 -->
    <div v-if="showWebhookModal" class="modal show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5)">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-link"></i> Webhook URL
            </h5>
            <button type="button" class="btn-close" @click="showWebhookModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Webhook URL</label>
              <div class="input-group">
                <input 
                  :value="webhookUrl" 
                  type="text" 
                  class="form-control form-control-sm font-monospace" 
                  readonly
                  ref="webhookUrlInput"
                >
                <button class="btn btn-outline-secondary btn-sm" @click="copyWebhookUrl">
                  <i class="fas fa-copy"></i> 复制
                </button>
              </div>
            </div>
            <div class="alert alert-info small mb-0">
              <strong>使用说明：</strong><br>
              1. 在 Git 平台（GitHub/GitLab/Gitee）的仓库设置中添加 Webhook<br>
              2. 将上述 URL 粘贴到 Payload URL 中<br>
              3. Content Type 选择 <code>application/json</code><br>
              4. Secret 填写流水线配置的 Webhook 密钥（如果有）<br>
              5. 选择触发事件（通常是 Push events）
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 日志查看模态框 -->
    <div v-if="showLogModal && selectedTask" class="modal show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5)">
      <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-terminal"></i> 任务日志 - {{ selectedTask.image || '未知' }}:{{ selectedTask.tag || 'latest' }}
            </h5>
            <button type="button" class="btn-close" @click="closeLogModal"></button>
          </div>
          <div class="modal-body">
            <pre class="bg-dark text-light p-3 rounded" style="max-height: 500px; overflow-y: auto; font-size: 0.85rem; white-space: pre-wrap; word-wrap: break-word;">{{ taskLogs }}</pre>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeLogModal">关闭</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 历史构建模态框 -->
    <div v-if="showHistoryModal" class="modal show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5)">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-history"></i> 历史构建 - {{ currentPipeline?.name }}
            </h5>
            <button type="button" class="btn-close" @click="closeHistoryModal"></button>
          </div>
          <div class="modal-body">
            <!-- 过滤选项 -->
            <div class="row mb-3">
              <div class="col-md-4">
                <label class="form-label small">触发来源</label>
                <select v-model="historyFilter.trigger_source" class="form-select form-select-sm" @change="loadHistory">
                  <option value="">全部</option>
                  <option value="webhook">Webhook</option>
                  <option value="manual">手动</option>
                  <option value="cron">定时</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label small">任务状态</label>
                <select v-model="historyFilter.status" class="form-select form-select-sm" @change="loadHistory">
                  <option value="">全部</option>
                  <option value="pending">等待中</option>
                  <option value="running">进行中</option>
                  <option value="completed">已完成</option>
                  <option value="failed">失败</option>
                </select>
              </div>
              <div class="col-md-4 d-flex align-items-end">
                <button class="btn btn-sm btn-outline-primary" @click="loadHistory">
                  <i class="fas fa-sync-alt"></i> 刷新
                </button>
              </div>
            </div>

            <!-- 历史列表 -->
            <div v-if="historyLoading" class="text-center py-4">
              <span class="spinner-border spinner-border-sm"></span> 加载中...
            </div>
            <div v-else-if="historyTasks.length === 0" class="text-center py-4 text-muted">
              <i class="fas fa-inbox fa-2x mb-2"></i>
              <p class="mb-0">暂无历史构建记录</p>
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-hover">
                <thead>
                  <tr>
                    <th style="width: 10%;">任务ID</th>
                    <th style="width: 10%;">触发来源</th>
                    <th style="width: 10%;">状态</th>
                    <th style="width: 15%;">镜像</th>
                    <th style="width: 12%;">触发时间</th>
                    <th style="width: 12%;">完成时间</th>
                    <th style="width: 18%;">分支/信息</th>
                    <th style="width: 13%;">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="task in historyTasks" :key="task.task_id">
                    <td>
                      <code class="small">{{ task.task_id.substring(0, 8) }}</code>
                    </td>
                    <td>
                      <span v-if="task.trigger_source === 'webhook'" class="badge bg-info">
                        <i class="fas fa-link"></i> Webhook
                      </span>
                      <span v-else-if="task.trigger_source === 'manual'" class="badge bg-success">
                        <i class="fas fa-hand-pointer"></i> 手动
                      </span>
                      <span v-else-if="task.trigger_source === 'cron'" class="badge bg-warning">
                        <i class="fas fa-clock"></i> 定时
                      </span>
                      <span v-else class="badge bg-secondary">未知</span>
                    </td>
                    <td>
                      <span v-if="task.status === 'pending'" class="badge bg-secondary">
                        <i class="fas fa-clock"></i> 等待中
                      </span>
                      <span v-else-if="task.status === 'running'" class="badge bg-primary">
                        <span class="spinner-border spinner-border-sm me-1" style="width: 0.65rem; height: 0.65rem;"></span> 进行中
                      </span>
                      <span v-else-if="task.status === 'completed'" class="badge bg-success">
                        <i class="fas fa-check-circle"></i> 已完成
                      </span>
                      <span v-else-if="task.status === 'failed'" class="badge bg-danger">
                        <i class="fas fa-times-circle"></i> 失败
                      </span>
                      <span v-else-if="task.status === 'deleted'" class="badge bg-secondary">
                        <i class="fas fa-trash"></i> 已删除
                      </span>
                    </td>
                    <td>
                      <small class="font-monospace text-truncate d-block" :title="`${task.image}:${task.tag}`">
                        {{ task.image }}:{{ task.tag }}
                      </small>
                    </td>
                    <td>
                      <small class="text-muted" :title="formatDateTime(task.triggered_at)">
                        {{ formatDateTime(task.triggered_at) }}
                      </small>
                    </td>
                    <td>
                      <small v-if="task.completed_at" class="text-muted" :title="formatDateTime(task.completed_at)">
                        {{ formatDateTime(task.completed_at) }}
                      </small>
                      <small v-else class="text-muted">-</small>
                    </td>
                    <td>
                      <div v-if="task.trigger_info">
                        <span v-if="task.trigger_info.branch" class="badge bg-secondary mb-1">
                          {{ task.trigger_info.branch }}
                        </span>
                        <div v-if="task.trigger_info.platform" class="text-muted small">
                          {{ task.trigger_info.platform }}
                        </div>
                        <div v-if="task.trigger_info.last_commit" class="text-muted small text-truncate" :title="task.trigger_info.last_commit">
                          {{ task.trigger_info.last_commit.substring(0, 40) }}{{ task.trigger_info.last_commit.length > 40 ? '...' : '' }}
                        </div>
                      </div>
                      <small v-else class="text-muted">-</small>
                    </td>
                    <td>
                      <button 
                        v-if="task.status !== 'deleted' && task.task_id"
                        class="btn btn-sm btn-outline-info" 
                        @click="viewTaskLogs(task.task_id, task)"
                        :disabled="viewingLogs === task.task_id"
                        title="查看日志"
                      >
                        <i class="fas fa-terminal"></i> 日志
                        <span v-if="viewingLogs === task.task_id" class="spinner-border spinner-border-sm ms-1"></span>
                      </button>
                      <span v-else class="text-muted small">-</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer">
            <div class="text-muted small">
              共 {{ historyTasks.length }} 条记录
            </div>
            <button type="button" class="btn btn-secondary btn-sm" @click="closeHistoryModal">关闭</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, ref, inject } from 'vue'

const pipelines = ref([])
const templates = ref([])
const registries = ref([])
const loading = ref(false)
const running = ref(null)  // 正在运行的流水线ID
const showModal = ref(false)
const showWebhookModal = ref(false)
const showHistoryModal = ref(false)
const webhookUrl = ref('')
const webhookUrlInput = ref(null)
const editingPipeline = ref(null)
const currentPipeline = ref(null)
const historyTasks = ref([])
const historyLoading = ref(false)
const historyFilter = ref({
  trigger_source: '',
  status: ''
})
const showLogModal = ref(false)
const selectedTask = ref(null)
const taskLogs = ref('')
const viewingLogs = ref(null)

const formData = ref({
  name: '',
  description: '',
  git_url: '',
  branch: '',
  sub_path: '',
  project_type: 'jar',
  template: '',
  image_name: '',
  tag: 'latest',
  push: false,
  push_registry: '',
  webhook_secret: '',
  enabled: true,
  trigger_schedule: false,  // 是否启用定时触发
  cron_expression: '',  // Cron 表达式
})

onMounted(() => {
  loadPipelines()
  loadTemplates()
  loadRegistries()
})

async function loadPipelines() {
  loading.value = true
  try {
    const res = await axios.get('/api/pipelines')
    pipelines.value = res.data.pipelines || []
  } catch (error) {
    console.error('加载流水线列表失败:', error)
    alert('加载流水线列表失败')
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const res = await axios.get('/api/list-templates')
    templates.value = res.data || []
  } catch (error) {
    console.error('加载模板列表失败:', error)
  }
}

async function loadRegistries() {
  try {
    const res = await axios.get('/api/registries')
    registries.value = res.data.registries || []
  } catch (error) {
    console.error('加载仓库列表失败:', error)
  }
}

function showCreateModal() {
  editingPipeline.value = null
  formData.value = {
    name: '',
    description: '',
    git_url: '',
    branch: '',
    sub_path: '',
    project_type: 'jar',
    template: '',
    image_name: '',
    tag: 'latest',
    push: false,
    push_registry: '',
    webhook_secret: '',
    enabled: true,
    trigger_schedule: false,
    cron_expression: '',
  }
  showModal.value = true
}

function editPipeline(pipeline) {
  editingPipeline.value = pipeline
  formData.value = {
    name: pipeline.name,
    description: pipeline.description || '',
    git_url: pipeline.git_url,
    branch: pipeline.branch || '',
    sub_path: pipeline.sub_path || '',
    project_type: pipeline.project_type || 'jar',
    template: pipeline.template || '',
    image_name: pipeline.image_name || '',
    tag: pipeline.tag || 'latest',
    push: pipeline.push || false,
    push_registry: pipeline.push_registry || '',
    webhook_secret: pipeline.webhook_secret || '',
    enabled: pipeline.enabled !== false,
    trigger_schedule: !!pipeline.cron_expression,  // 如果有cron表达式则启用
    cron_expression: pipeline.cron_expression || '',
  }
  showModal.value = true
}

async function savePipeline() {
  try {
    // 准备提交数据
    const payload = {
      ...formData.value,
      // 如果未启用定时触发，则cron_expression为null
      cron_expression: formData.value.trigger_schedule ? formData.value.cron_expression : null
    }
    
    // 验证：如果启用定时触发，必须填写cron表达式
    if (payload.trigger_schedule && !payload.cron_expression) {
      alert('请填写 Cron 表达式')
      return
    }
    
    if (editingPipeline.value) {
      // 更新
      await axios.put(`/api/pipelines/${editingPipeline.value.pipeline_id}`, payload)
      alert('流水线更新成功')
    } else {
      // 创建
      await axios.post('/api/pipelines', payload)
      alert('流水线创建成功')
    }
    closeModal()
    loadPipelines()
  } catch (error) {
    console.error('保存流水线失败:', error)
    alert(error.response?.data?.detail || '保存流水线失败')
  }
}

function closeModal() {
  showModal.value = false
  editingPipeline.value = null
}

async function deletePipeline(pipeline) {
  if (!confirm(`确定要删除流水线"${pipeline.name}"吗？`)) {
    return
  }
  
  try {
    await axios.delete(`/api/pipelines/${pipeline.pipeline_id}`)
    alert('流水线已删除')
    loadPipelines()
  } catch (error) {
    console.error('删除流水线失败:', error)
    alert(error.response?.data?.detail || '删除流水线失败')
  }
}

// 手动运行流水线
async function runPipeline(pipeline) {
  if (running.value) return
  
  if (!confirm(`确定要运行流水线 "${pipeline.name}" 吗？`)) {
    return
  }
  
  running.value = pipeline.pipeline_id
  try {
    const res = await axios.post(`/api/pipelines/${pipeline.pipeline_id}/run`)
    
    if (res.data.task_id) {
      alert(`流水线已启动！\n任务 ID: ${res.data.task_id}\n分支: ${res.data.branch || '默认'}`)
      // 刷新流水线列表（更新触发次数和时间）
      loadPipelines()
    }
  } catch (error) {
    console.error('运行流水线失败:', error)
    alert(error.response?.data?.detail || '运行流水线失败')
  } finally {
    running.value = null
  }
}

function showWebhookUrl(pipeline) {
  const baseUrl = window.location.origin
  webhookUrl.value = `${baseUrl}/api/webhook/${pipeline.webhook_token}`
  showWebhookModal.value = true
}

function copyWebhookUrl() {
  if (webhookUrlInput.value) {
    webhookUrlInput.value.select()
    document.execCommand('copy')
    alert('Webhook URL 已复制到剪贴板')
  }
}

function formatGitUrl(url) {
  if (!url) return ''
  // 简化显示
  return url.replace('https://', '').replace('http://', '').replace('.git', '')
}

function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diff = (now - date) / 1000 // 秒
  
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`
  
  return date.toLocaleDateString('zh-CN')
}

function formatDateTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  
  // 格式：YYYY-MM-DD HH:mm:ss
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

function showHistory(pipeline) {
  currentPipeline.value = pipeline
  historyFilter.value = {
    trigger_source: '',
    status: ''
  }
  showHistoryModal.value = true
  loadHistory()
}

function closeHistoryModal() {
  showHistoryModal.value = false
  currentPipeline.value = null
  historyTasks.value = []
}

async function loadHistory() {
  if (!currentPipeline.value) return
  
  historyLoading.value = true
  try {
    const params = new URLSearchParams()
    if (historyFilter.value.trigger_source) {
      params.append('trigger_source', historyFilter.value.trigger_source)
    }
    if (historyFilter.value.status) {
      params.append('status', historyFilter.value.status)
    }
    params.append('limit', '100')
    
    const url = `/api/pipelines/${currentPipeline.value.pipeline_id}/tasks?${params.toString()}`
    const res = await axios.get(url)
    historyTasks.value = res.data.tasks || []
  } catch (error) {
    console.error('加载历史构建失败:', error)
    alert('加载历史构建失败')
    historyTasks.value = []
  } finally {
    historyLoading.value = false
  }
}

async function viewTaskLogs(taskId, task) {
  if (viewingLogs.value) return
  
  viewingLogs.value = taskId
  selectedTask.value = task
  showLogModal.value = true
  taskLogs.value = '加载中...'
  
  try {
    const res = await axios.get(`/api/build-tasks/${taskId}/logs`)
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
  viewingLogs.value = null
}
</script>

<style scoped>
.pipeline-panel {
  padding: 1rem;
}

.table {
  font-size: 0.875rem;
  table-layout: fixed; /* 固定表格布局，使列宽生效 */
}

.table th {
  white-space: nowrap; /* 表头不换行 */
  overflow: hidden;
  text-overflow: ellipsis;
}

.table td {
  word-wrap: break-word; /* 允许单元格内容换行 */
  overflow-wrap: break-word;
}

.font-monospace {
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
}

/* 确保操作按钮组不换行 */
.btn-group {
  flex-wrap: nowrap;
}
</style>

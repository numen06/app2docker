<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-rocket text-primary"></i> 部署任务管理
      </h5>
      <div>
        <button class="btn btn-primary btn-sm" @click="showImportModal = true">
          <i class="fas fa-file-import me-1"></i> 导入配置
        </button>
        <button class="btn btn-success btn-sm ms-2" @click="openSimpleCreateModal">
          <i class="fas fa-plus me-1"></i> 快速创建
        </button>
        <button class="btn btn-info btn-sm ms-2" @click="showCreateModal = true">
          <i class="fas fa-code me-1"></i> YAML创建
        </button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="table-responsive">
      <table class="table table-hover">
        <thead>
          <tr>
            <th width="10%">任务ID</th>
            <th width="15%">应用名称</th>
            <th width="10%">状态</th>
            <th width="15%">目标主机</th>
            <th width="15%">创建时间</th>
            <th width="15%">完成时间</th>
            <th width="20%">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="text-center py-4">
              <div class="spinner-border spinner-border-sm me-2"></div>
              加载中...
            </td>
          </tr>
          <tr v-else-if="tasks.length === 0">
            <td colspan="7" class="text-center py-4 text-muted">
              暂无部署任务
            </td>
          </tr>
          <tr v-else v-for="task in tasks" :key="task.task_id">
            <td>
              <code class="small">{{ task.task_id.substring(0, 8) }}</code>
            </td>
            <td>{{ task.config?.app?.name || '-' }}</td>
            <td>
              <span :class="getStatusBadgeClass(task.status?.status)" class="badge">
                {{ getStatusText(task.status?.status) }}
              </span>
            </td>
            <td>
              <span v-for="(target, idx) in task.status?.targets || []" :key="idx" class="badge bg-secondary me-1">
                {{ target.name }}
              </span>
            </td>
            <td>{{ formatTime(task.status?.created_at) }}</td>
            <td>{{ formatTime(task.status?.completed_at) || '-' }}</td>
            <td>
              <div class="btn-group" role="group">
                <button class="btn btn-sm btn-outline-primary" @click="viewTask(task)" title="查看详情">
                  <i class="fas fa-eye"></i>
                </button>
                <button 
                  v-if="task.status?.status === 'pending' || task.status?.status === 'failed'"
                  class="btn btn-sm btn-outline-success" 
                  @click="executeTask(task)"
                  title="执行任务"
                >
                  <i class="fas fa-play"></i>
                </button>
                <button 
                  v-if="task.status?.status === 'running'"
                  class="btn btn-sm btn-outline-warning" 
                  @click="refreshTask(task)"
                  title="刷新状态"
                >
                  <i class="fas fa-sync-alt"></i>
                </button>
                <button class="btn btn-sm btn-outline-secondary" @click="editTask(task)" title="编辑配置">
                  <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-info" @click="copyTask(task)" title="复制任务">
                  <i class="fas fa-copy"></i>
                </button>
                <button class="btn btn-sm btn-outline-info" @click="exportTask(task)" title="导出配置">
                  <i class="fas fa-download"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" @click="deleteTask(task)" title="删除任务">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 简易创建任务模态框 -->
    <div v-if="showSimpleCreateModal" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-rocket me-2"></i> 快速创建部署任务
            </h5>
            <button type="button" class="btn-close" @click="showSimpleCreateModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">应用名称 <span class="text-danger">*</span></label>
              <input v-model="simpleForm.appName" type="text" class="form-control" placeholder="my-app">
            </div>
            
            <div class="mb-3">
              <label class="form-label">选择目标主机 <span class="text-danger">*</span></label>
              <div v-if="loadingHosts" class="text-muted small">加载中...</div>
              <div v-else class="border rounded p-2" style="max-height: 200px; overflow-y: auto;">
                <div v-for="host in agentHosts" :key="host.host_id" class="form-check">
                  <input 
                    class="form-check-input" 
                    type="checkbox" 
                    :value="host.host_id"
                    :id="'host-' + host.host_id"
                    v-model="simpleForm.selectedHosts"
                    :disabled="host.status !== 'online'"
                  >
                  <label class="form-check-label" :for="'host-' + host.host_id">
                    {{ host.name }}
                    <span :class="getStatusBadgeClass(host.status)" class="badge ms-2">
                      {{ getStatusText(host.status) }}
                    </span>
                  </label>
                </div>
                <div v-if="agentHosts.length === 0" class="text-muted small">
                  暂无可用主机，请先在"主机管理"中添加Agent主机
                </div>
              </div>
            </div>

            <div class="mb-3">
              <label class="form-label">部署方式 <span class="text-danger">*</span></label>
              <div class="btn-group w-100" role="group">
                <input type="radio" class="btn-check" id="deploy-run" v-model="simpleForm.deployMode" value="docker_run" checked>
                <label class="btn btn-outline-primary" for="deploy-run">
                  <i class="fas fa-terminal me-1"></i> Docker Run
                </label>
                
                <input type="radio" class="btn-check" id="deploy-compose" v-model="simpleForm.deployMode" value="docker_compose">
                <label class="btn btn-outline-primary" for="deploy-compose">
                  <i class="fas fa-layer-group me-1"></i> Docker Compose
                </label>
              </div>
            </div>

            <!-- Docker Run 命令输入 -->
            <div v-if="simpleForm.deployMode === 'docker_run'" class="mb-3">
              <label class="form-label">Docker Run 命令 <span class="text-danger">*</span></label>
              <textarea 
                v-model="simpleForm.runCommand" 
                class="form-control font-monospace" 
                rows="6"
                placeholder="-d --name my-app -p 8000:8000 registry.cn-hangzhou.aliyuncs.com/namespace/app:tag"
              ></textarea>
              <small class="text-muted">输入 docker run 的参数（不包含 "docker run" 前缀）</small>
            </div>

            <!-- Docker Compose 命令输入 -->
            <div v-if="simpleForm.deployMode === 'docker_compose'" class="mb-3">
              <label class="form-label">Docker Compose 命令 <span class="text-danger">*</span></label>
              <input 
                v-model="simpleForm.composeCommand" 
                type="text" 
                class="form-control font-monospace" 
                placeholder="up -d"
              >
              <small class="text-muted">输入 docker-compose 命令参数（不包含 "docker-compose" 前缀，如：up -d）</small>
            </div>

            <div v-if="simpleForm.deployMode === 'docker_compose'" class="mb-3">
              <label class="form-label">docker-compose.yml 内容 <span class="text-danger">*</span></label>
              <textarea 
                v-model="simpleForm.composeContent" 
                class="form-control font-monospace" 
                rows="15"
                placeholder="version: '3.8'&#10;services:&#10;  app:&#10;    image: registry.cn-hangzhou.aliyuncs.com/namespace/app:tag&#10;    ports:&#10;      - '8000:8000'"
              ></textarea>
              <small class="text-muted">输入完整的 docker-compose.yml 内容</small>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showSimpleCreateModal = false">取消</button>
            <button type="button" class="btn btn-primary" @click="createSimpleTask" :disabled="creating">
              <span v-if="creating" class="spinner-border spinner-border-sm me-2"></span>
              创建
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- YAML创建任务模态框 -->
    <div v-if="showCreateModal" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-code me-2"></i> YAML方式创建部署任务
            </h5>
            <button type="button" class="btn-close" @click="showCreateModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">YAML 配置内容</label>
              <textarea 
                v-model="taskConfigContent" 
                class="form-control font-monospace" 
                rows="20"
                placeholder="请输入 deploy-config.yaml 格式的配置..."
              ></textarea>
            </div>
            <div class="row">
              <div class="col-md-6">
                <label class="form-label">镜像仓库（可选）</label>
                <input v-model="taskRegistry" type="text" class="form-control" placeholder="docker.io">
              </div>
              <div class="col-md-6">
                <label class="form-label">镜像标签（可选）</label>
                <input v-model="taskTag" type="text" class="form-control" placeholder="latest">
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showCreateModal = false">取消</button>
            <button type="button" class="btn btn-primary" @click="createTask" :disabled="creating">
              <span v-if="creating" class="spinner-border spinner-border-sm me-2"></span>
              创建
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 导入任务模态框 -->
    <div v-if="showImportModal" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-file-import me-2"></i> 导入部署配置
            </h5>
            <button type="button" class="btn-close" @click="showImportModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">选择 YAML 文件</label>
              <input type="file" class="form-control" @change="handleFileImport" accept=".yaml,.yml">
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showImportModal = false">取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 任务详情模态框 -->
    <div v-if="showDetailModal && selectedTask" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-info-circle me-2"></i> 任务详情 - {{ selectedTask.task_id.substring(0, 8) }}
            </h5>
            <button type="button" class="btn-close" @click="showDetailModal = false"></button>
          </div>
          <div class="modal-body">
            <ul class="nav nav-tabs mb-3">
              <li class="nav-item">
                <button class="nav-link" :class="{ active: detailTab === 'config' }" @click="detailTab = 'config'">
                  配置信息
                </button>
              </li>
              <li class="nav-item">
                <button class="nav-link" :class="{ active: detailTab === 'status' }" @click="detailTab = 'status'">
                  执行状态
                </button>
              </li>
            </ul>

            <div v-if="detailTab === 'config'">
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 500px; overflow-y: auto;"><code>{{ selectedTask.config_content }}</code></pre>
            </div>

            <div v-if="detailTab === 'status'">
              <div class="mb-3">
                <strong>任务状态:</strong>
                <span :class="getStatusBadgeClass(selectedTask.status?.status)" class="badge ms-2">
                  {{ getStatusText(selectedTask.status?.status) }}
                </span>
              </div>
              <div v-if="selectedTask.status?.targets" class="mb-3">
                <strong>目标主机执行状态:</strong>
                <table class="table table-sm mt-2">
                  <thead>
                    <tr>
                      <th>主机名称</th>
                      <th>状态</th>
                      <th>结果</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="target in selectedTask.status.targets" :key="target.name">
                      <td>{{ target.name }}</td>
                      <td>
                        <span :class="getStatusBadgeClass(target.status)" class="badge">
                          {{ getStatusText(target.status) }}
                        </span>
                      </td>
                      <td>
                        <span v-if="target.result" class="text-muted small">
                          {{ target.result.message || '-' }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showDetailModal = false">关闭</button>
            <button 
              class="btn btn-outline-secondary" 
              @click="editTask(selectedTask)"
            >
              <i class="fas fa-edit me-1"></i> 编辑
            </button>
            <button 
              class="btn btn-outline-info" 
              @click="copyTask(selectedTask)"
            >
              <i class="fas fa-copy me-1"></i> 复制
            </button>
            <button 
              v-if="selectedTask.status?.status === 'pending' || selectedTask.status?.status === 'failed'"
              class="btn btn-success" 
              @click="executeTask(selectedTask)"
            >
              <i class="fas fa-play me-1"></i> 执行任务
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑任务模态框 -->
    <div v-if="showEditModal && editingTask" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-edit me-2"></i> 编辑部署任务 - {{ editingTask.task_id.substring(0, 8) }}
            </h5>
            <button type="button" class="btn-close" @click="showEditModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">YAML 配置内容</label>
              <textarea 
                v-model="editingTask.config_content" 
                class="form-control font-monospace" 
                rows="20"
              ></textarea>
            </div>
            <div class="row">
              <div class="col-md-6">
                <label class="form-label">镜像仓库（可选）</label>
                <input v-model="editingTask.registry" type="text" class="form-control" placeholder="docker.io">
              </div>
              <div class="col-md-6">
                <label class="form-label">镜像标签（可选）</label>
                <input v-model="editingTask.tag" type="text" class="form-control" placeholder="latest">
              </div>
            </div>
            <div class="alert alert-warning mt-3">
              <i class="fas fa-exclamation-triangle me-2"></i>
              注意：编辑任务会删除原任务并创建新任务，任务ID会发生变化。
            </div>
            <div class="alert alert-warning mt-3">
              <i class="fas fa-exclamation-triangle me-2"></i>
              注意：编辑任务会删除原任务并创建新任务，任务ID会发生变化。
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showEditModal = false">取消</button>
            <button type="button" class="btn btn-primary" @click="saveEditTask" :disabled="creating">
              <span v-if="creating" class="spinner-border spinner-border-sm me-2"></span>
              保存
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import yaml from 'js-yaml'

export default {
  name: 'DeployTaskManager',
  data() {
    return {
      tasks: [],
      loading: false,
      showCreateModal: false,
      showSimpleCreateModal: false,
      showImportModal: false,
      showDetailModal: false,
      showEditModal: false,
      editingTask: null,
      selectedTask: null,
      detailTab: 'config',
      taskConfigContent: '',
      taskRegistry: '',
      taskTag: '',
      creating: false,
      agentHosts: [],
      loadingHosts: false,
      simpleForm: {
        appName: '',
        selectedHosts: [],
        imageName: '',
        containerName: '',
        deployMode: 'docker_run',
        ports: ['8000:8000'],
        envVars: [''],
        volumes: [''],
        restartPolicy: 'always'
      }
    }
  },
  mounted() {
    this.loadTasks()
    this.loadAgentHosts()
  },
  methods: {
    async loadTasks() {
      this.loading = true
      try {
        const res = await axios.get('/api/deploy-tasks')
        this.tasks = res.data.tasks || []
      } catch (error) {
        console.error('加载部署任务失败:', error)
        alert('加载部署任务失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loading = false
      }
    },
    async createTask() {
      if (!this.taskConfigContent.trim()) {
        alert('请输入配置内容')
        return
      }
      
      this.creating = true
      try {
        await axios.post('/api/deploy-tasks', {
          config_content: this.taskConfigContent,
          registry: this.taskRegistry || null,
          tag: this.taskTag || null
        })
        alert('创建成功')
        this.showCreateModal = false
        this.taskConfigContent = ''
        this.taskRegistry = ''
        this.taskTag = ''
        this.loadTasks()
      } catch (error) {
        console.error('创建部署任务失败:', error)
        alert('创建部署任务失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.creating = false
      }
    },
    async handleFileImport(event) {
      const file = event.target.files[0]
      if (!file) return
      
      const reader = new FileReader()
      reader.onload = async (e) => {
        try {
          const content = e.target.result
          const formData = new FormData()
          formData.append('file', file)
          
          await axios.post('/api/deploy-tasks/import', formData, {
            headers: {
              'Content-Type': 'multipart/form-data'
            }
          })
          alert('导入成功')
          this.showImportModal = false
          this.loadTasks()
        } catch (error) {
          console.error('导入部署任务失败:', error)
          alert('导入部署任务失败: ' + (error.response?.data?.detail || error.message))
        }
      }
      reader.readAsText(file)
    },
    async executeTask(task) {
      if (!confirm('确定要执行此部署任务吗？')) return
      
      try {
        await axios.post(`/api/deploy-tasks/${task.task_id}/execute`)
        alert('任务已开始执行')
        this.loadTasks()
        if (this.showDetailModal) {
          this.viewTask(task)
        }
      } catch (error) {
        console.error('执行部署任务失败:', error)
        alert('执行部署任务失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async deleteTask(task) {
      if (!confirm('确定要删除此部署任务吗？')) return
      
      try {
        await axios.delete(`/api/deploy-tasks/${task.task_id}`)
        alert('删除成功')
        this.loadTasks()
        if (this.showDetailModal && this.selectedTask?.task_id === task.task_id) {
          this.showDetailModal = false
        }
      } catch (error) {
        console.error('删除部署任务失败:', error)
        alert('删除部署任务失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async exportTask(task) {
      try {
        const res = await axios.get(`/api/deploy-tasks/${task.task_id}/export`, {
          responseType: 'blob'
        })
        const blob = new Blob([res.data], { type: 'application/x-yaml' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `deploy-task-${task.task_id}.yaml`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      } catch (error) {
        console.error('导出部署任务失败:', error)
        alert('导出部署任务失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async viewTask(task) {
      try {
        const res = await axios.get(`/api/deploy-tasks/${task.task_id}`)
        this.selectedTask = res.data.task
        this.detailTab = 'config'
        this.showDetailModal = true
      } catch (error) {
        console.error('获取任务详情失败:', error)
        alert('获取任务详情失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    getStatusBadgeClass(status) {
      const map = {
        'pending': 'bg-secondary',
        'running': 'bg-primary',
        'completed': 'bg-success',
        'failed': 'bg-danger'
      }
      return map[status] || 'bg-secondary'
    },
    getStatusText(status) {
      const map = {
        'pending': '待执行',
        'running': '执行中',
        'completed': '已完成',
        'failed': '失败'
      }
      return map[status] || status || '未知'
    },
    formatTime(time) {
      if (!time) return '-'
      return new Date(time).toLocaleString('zh-CN')
    },
    async loadAgentHosts() {
      this.loadingHosts = true
      try {
        const res = await axios.get('/api/agent-hosts')
        this.agentHosts = res.data.hosts || []
      } catch (error) {
        console.error('加载Agent主机列表失败:', error)
      } finally {
        this.loadingHosts = false
      }
    },
    async createSimpleTask() {
      // 验证必填字段
      if (!this.simpleForm.appName.trim()) {
        alert('请输入应用名称')
        return
      }
      if (this.simpleForm.selectedHosts.length === 0) {
        alert('请至少选择一个目标主机')
        return
      }
      if (this.simpleForm.deployMode === 'docker_run' && !this.simpleForm.runCommand.trim()) {
        alert('请输入 Docker Run 命令')
        return
      }
      if (this.simpleForm.deployMode === 'docker_compose') {
        if (!this.simpleForm.composeCommand.trim()) {
          alert('请输入 Docker Compose 命令')
          return
        }
        if (!this.simpleForm.composeContent.trim()) {
          alert('请输入 docker-compose.yml 内容')
          return
        }
      }

      // 将命令转换为统一的YAML配置格式
      // 无论前端是表单输入还是直接输入YAML，最终都统一为YAML格式保存
      // 后端会解析YAML并推送给Agent执行部署
      const targets = []
      for (const hostId of this.simpleForm.selectedHosts) {
        const host = this.agentHosts.find(h => h.host_id === hostId)
        if (!host) continue

        const dockerConfig = {
          deploy_mode: this.simpleForm.deployMode
        }

        if (this.simpleForm.deployMode === 'docker_run') {
          // Docker Run 模式：将命令保存到 command 字段
          dockerConfig.command = this.simpleForm.runCommand.trim()
          // 尝试从命令中提取镜像名称（用于显示）
          const imageMatch = this.simpleForm.runCommand.match(/([\w\.\-:\/]+(?::[\w\.\-]+)?)$/)
          if (imageMatch) {
            dockerConfig.image_template = imageMatch[1]
          } else {
            dockerConfig.image_template = 'unknown'
          }
        } else {
          // Docker Compose 模式：保存命令和compose内容
          dockerConfig.command = this.simpleForm.composeCommand.trim()
          dockerConfig.compose_content = this.simpleForm.composeContent.trim()
        }

        targets.push({
          name: `${host.name}-deploy`,
          mode: 'agent',
          agent: {
            name: host.name
          },
          docker: dockerConfig
        })
      }

      const yamlConfig = {
        version: '1.0',
        app: {
          name: this.simpleForm.appName
        },
        targets: targets
      }

      // 转换为YAML字符串（统一格式，与直接输入YAML的方式一致）
      const yamlContent = yaml.dump(yamlConfig, {
        defaultFlowStyle: false,
        allowUnicode: true
      })

      // 创建任务（统一调用后端API，后端会解析YAML并保存）
      this.creating = true
      try {
        await axios.post('/api/deploy-tasks', {
          config_content: yamlContent,
          registry: null,
          tag: null
        })
        alert('创建成功')
        this.showSimpleCreateModal = false
        this.resetSimpleForm()
        this.loadTasks()
      } catch (error) {
        console.error('创建部署任务失败:', error)
        alert('创建部署任务失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.creating = false
      }
    },
    resetSimpleForm() {
      this.simpleForm = {
        appName: '',
        selectedHosts: [],
        deployMode: 'docker_run',
        runCommand: '',
        composeCommand: '',
        composeContent: ''
      }
    },
    openSimpleCreateModal() {
      this.resetSimpleForm()
      this.loadAgentHosts()
      this.showSimpleCreateModal = true
    },
    async editTask(task) {
      try {
        const res = await axios.get(`/api/deploy-tasks/${task.task_id}`)
        const taskData = res.data.task
        this.editingTask = {
          task_id: taskData.task_id,
          config_content: taskData.config_content || '',
          registry: taskData.status?.registry || '',
          tag: taskData.status?.tag || ''
        }
        this.showEditModal = true
        // 如果详情模态框打开，先关闭它
        if (this.showDetailModal) {
          this.showDetailModal = false
        }
      } catch (error) {
        console.error('获取任务详情失败:', error)
        alert('获取任务详情失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async saveEditTask() {
      if (!this.editingTask.config_content.trim()) {
        alert('配置内容不能为空')
        return
      }
      
      if (!confirm('确定要保存修改吗？这将删除原任务并创建新任务。')) {
        return
      }
      
      this.creating = true
      try {
        // 删除旧任务
        await axios.delete(`/api/deploy-tasks/${this.editingTask.task_id}`)
        
        // 创建新任务
        await axios.post('/api/deploy-tasks', {
          config_content: this.editingTask.config_content,
          registry: this.editingTask.registry || null,
          tag: this.editingTask.tag || null
        })
        
        alert('保存成功')
        this.showEditModal = false
        this.editingTask = null
        this.loadTasks()
      } catch (error) {
        console.error('保存任务失败:', error)
        alert('保存任务失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.creating = false
      }
    },
    async copyTask(task) {
      try {
        const res = await axios.get(`/api/deploy-tasks/${task.task_id}`)
        const taskData = res.data.task
        
        // 创建新任务（使用相同的配置）
        await axios.post('/api/deploy-tasks', {
          config_content: taskData.config_content,
          registry: taskData.status?.registry || null,
          tag: taskData.status?.tag || null
        })
        
        alert('复制成功')
        this.loadTasks()
      } catch (error) {
        console.error('复制任务失败:', error)
        alert('复制任务失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async refreshTask(task) {
      // 刷新任务状态
      await this.loadTasks()
      // 如果详情模态框打开，重新加载任务详情
      if (this.showDetailModal && this.selectedTask?.task_id === task.task_id) {
        await this.viewTask(task)
      }
    }
  }
}
</script>

<style scoped>
.modal {
  z-index: 1050;
}
</style>


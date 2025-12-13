<template>
  <div class="agent-host-manager-panel">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h6 class="mb-0">
        <i class="fas fa-network-wired"></i> Agent主机管理
      </h6>
      <button class="btn btn-primary btn-sm" @click="showAddModal = true">
        <i class="fas fa-plus"></i> 新建Agent主机
      </button>
    </div>

    <!-- Agent主机列表 -->
    <div class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th>主机名称</th>
            <th>连接状态</th>
            <th>主机信息</th>
            <th>Docker信息</th>
            <th>最后心跳</th>
            <th>描述</th>
            <th>创建时间</th>
            <th class="text-end">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="text-center py-4">
              <div class="spinner-border spinner-border-sm me-2"></div>
              加载中...
            </td>
          </tr>
          <tr v-else-if="hosts.length === 0">
            <td colspan="8" class="text-center text-muted py-4">
              <i class="fas fa-network-wired fa-2x mb-2 d-block"></i>
              暂无Agent主机，请点击"新建Agent主机"添加
            </td>
          </tr>
          <tr v-for="host in hosts" :key="host.host_id">
            <td>
              <strong>{{ host.name }}</strong>
            </td>
            <td>
              <span :class="getStatusBadgeClass(host.status)" class="badge">
                <i :class="getStatusIcon(host.status)"></i>
                {{ getStatusText(host.status) }}
              </span>
            </td>
            <td>
              <div v-if="host.host_info && Object.keys(host.host_info).length > 0">
                <div class="small">
                  <span v-if="host.host_info.ip" class="me-2">
                    <i class="fas fa-network-wired"></i> {{ host.host_info.ip }}
                  </span>
                  <span v-if="host.host_info.os" class="me-2">
                    <i class="fas fa-desktop"></i> {{ host.host_info.os }}
                  </span>
                </div>
                <div v-if="host.host_info.cpu_usage !== undefined" class="small text-muted">
                  CPU: {{ host.host_info.cpu_usage }}% | 
                  内存: {{ host.host_info.memory_usage }}% | 
                  磁盘: {{ host.host_info.disk_usage }}%
                </div>
              </div>
              <span v-else class="text-muted small">未连接</span>
            </td>
            <td>
              <div v-if="host.docker_info && Object.keys(host.docker_info).length > 0">
                <span v-if="host.docker_info.version" class="badge bg-info mb-1 d-inline-block">
                  <i class="fab fa-docker me-1"></i>{{ host.docker_info.version }}
                </span>
                <div class="small text-muted">
                  <span v-if="host.docker_info.containers !== undefined">
                    容器: {{ host.docker_info.containers }}
                  </span>
                  <span v-if="host.docker_info.images !== undefined" class="ms-2">
                    镜像: {{ host.docker_info.images }}
                  </span>
                </div>
              </div>
              <span v-else class="text-muted small">未检测</span>
            </td>
            <td>
              <span v-if="host.last_heartbeat" class="small">
                {{ formatTime(host.last_heartbeat) }}
              </span>
              <span v-else class="text-muted small">-</span>
            </td>
            <td>
              <span class="text-muted small">{{ host.description || '无描述' }}</span>
            </td>
            <td>{{ formatTime(host.created_at) }}</td>
            <td class="text-end">
              <div class="btn-group btn-group-sm">
                <button 
                  class="btn btn-outline-info" 
                  @click="viewHost(host)"
                  title="查看详情"
                >
                  <i class="fas fa-info-circle"></i>
                </button>
                <button 
                  class="btn btn-outline-primary" 
                  @click="showDeployCommand(host)"
                  title="部署命令"
                >
                  <i class="fas fa-code"></i>
                </button>
                <button 
                  class="btn btn-outline-primary" 
                  @click="editHost(host)"
                  title="编辑"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button 
                  class="btn btn-outline-danger" 
                  @click="deleteHost(host)"
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

    <!-- 添加/编辑主机模态框 -->
    <div v-if="showAddModal || showEditModal" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-network-wired me-2"></i> {{ editingHost ? '编辑Agent主机' : '新建Agent主机' }}
            </h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveHost">
              <div class="mb-3">
                <label class="form-label">
                  主机名称 <span class="text-danger">*</span>
                </label>
                <input 
                  type="text" 
                  class="form-control form-control-sm" 
                  v-model="hostForm.name"
                  placeholder="例如：生产服务器-Agent"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label">描述（可选）</label>
                <input 
                  type="text" 
                  class="form-control form-control-sm" 
                  v-model="hostForm.description"
                  placeholder="请输入主机描述信息..."
                />
              </div>
              <div v-if="!editingHost" class="alert alert-info py-2 mb-0">
                <i class="fas fa-info-circle me-2"></i>
                创建后将自动生成Token和部署命令，请按照部署命令在目标主机上部署Agent。
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeModal">
              取消
            </button>
            <button 
              type="button" 
              class="btn btn-primary btn-sm" 
              @click="saveHost"
              :disabled="saving"
            >
              <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="fas fa-save me-1"></i>
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主机详情模态框 -->
    <div v-if="showDetailModal && selectedHost" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-info-circle me-2"></i> Agent主机详情
            </h5>
            <button type="button" class="btn-close" @click="showDetailModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="row">
              <div class="col-md-6">
                <h6 class="border-bottom pb-2">基本信息</h6>
                <table class="table table-sm">
                  <tr>
                    <td width="40%"><strong>主机名称:</strong></td>
                    <td>{{ selectedHost.name }}</td>
                  </tr>
                  <tr>
                    <td><strong>连接状态:</strong></td>
                    <td>
                      <span :class="getStatusBadgeClass(selectedHost.status)" class="badge">
                        <i :class="getStatusIcon(selectedHost.status)"></i>
                        {{ getStatusText(selectedHost.status) }}
                      </span>
                    </td>
                  </tr>
                  <tr>
                    <td><strong>Token:</strong></td>
                    <td>
                      <code class="small">{{ selectedHost.token }}</code>
                      <button class="btn btn-sm btn-outline-secondary ms-2" @click="copyToClipboard(selectedHost.token)">
                        <i class="fas fa-copy"></i>
                      </button>
                    </td>
                  </tr>
                  <tr>
                    <td><strong>创建时间:</strong></td>
                    <td>{{ formatTime(selectedHost.created_at) }}</td>
                  </tr>
                  <tr>
                    <td><strong>最后心跳:</strong></td>
                    <td>{{ selectedHost.last_heartbeat ? formatTime(selectedHost.last_heartbeat) : '-' }}</td>
                  </tr>
                  <tr>
                    <td><strong>描述:</strong></td>
                    <td>{{ selectedHost.description || '-' }}</td>
                  </tr>
                </table>
              </div>
              <div class="col-md-6">
                <h6 class="border-bottom pb-2">主机信息</h6>
                <div v-if="selectedHost.host_info && Object.keys(selectedHost.host_info).length > 0">
                  <table class="table table-sm">
                    <tr v-if="selectedHost.host_info.hostname">
                      <td width="40%"><strong>主机名:</strong></td>
                      <td>{{ selectedHost.host_info.hostname }}</td>
                    </tr>
                    <tr v-if="selectedHost.host_info.ip">
                      <td><strong>IP地址:</strong></td>
                      <td>{{ selectedHost.host_info.ip }}</td>
                    </tr>
                    <tr v-if="selectedHost.host_info.os">
                      <td><strong>操作系统:</strong></td>
                      <td>{{ selectedHost.host_info.os }}</td>
                    </tr>
                    <tr v-if="selectedHost.host_info.kernel">
                      <td><strong>内核版本:</strong></td>
                      <td>{{ selectedHost.host_info.kernel }}</td>
                    </tr>
                    <tr v-if="selectedHost.host_info.cpu_usage !== undefined">
                      <td><strong>CPU使用率:</strong></td>
                      <td>
                        <div class="progress" style="height: 20px;">
                          <div class="progress-bar" :style="{ width: selectedHost.host_info.cpu_usage + '%' }">
                            {{ selectedHost.host_info.cpu_usage }}%
                          </div>
                        </div>
                      </td>
                    </tr>
                    <tr v-if="selectedHost.host_info.memory_usage !== undefined">
                      <td><strong>内存使用率:</strong></td>
                      <td>
                        <div class="progress" style="height: 20px;">
                          <div class="progress-bar bg-warning" :style="{ width: selectedHost.host_info.memory_usage + '%' }">
                            {{ selectedHost.host_info.memory_usage }}%
                          </div>
                        </div>
                      </td>
                    </tr>
                    <tr v-if="selectedHost.host_info.disk_usage !== undefined">
                      <td><strong>磁盘使用率:</strong></td>
                      <td>
                        <div class="progress" style="height: 20px;">
                          <div class="progress-bar bg-danger" :style="{ width: selectedHost.host_info.disk_usage + '%' }">
                            {{ selectedHost.host_info.disk_usage }}%
                          </div>
                        </div>
                      </td>
                    </tr>
                  </table>
                </div>
                <div v-else class="text-muted">
                  <i class="fas fa-info-circle"></i> 主机未连接，暂无信息
                </div>
              </div>
            </div>
            <div class="row mt-3">
              <div class="col-12">
                <h6 class="border-bottom pb-2">Docker信息</h6>
                <div v-if="selectedHost.docker_info && Object.keys(selectedHost.docker_info).length > 0">
                  <table class="table table-sm">
                    <tr v-if="selectedHost.docker_info.version">
                      <td width="40%"><strong>Docker版本:</strong></td>
                      <td>{{ selectedHost.docker_info.version }}</td>
                    </tr>
                    <tr v-if="selectedHost.docker_info.containers !== undefined">
                      <td><strong>容器数量:</strong></td>
                      <td>{{ selectedHost.docker_info.containers }}</td>
                    </tr>
                    <tr v-if="selectedHost.docker_info.images !== undefined">
                      <td><strong>镜像数量:</strong></td>
                      <td>{{ selectedHost.docker_info.images }}</td>
                    </tr>
                    <tr v-if="selectedHost.docker_info.networks !== undefined">
                      <td><strong>网络数量:</strong></td>
                      <td>{{ selectedHost.docker_info.networks }}</td>
                    </tr>
                  </table>
                </div>
                <div v-else class="text-muted">
                  <i class="fas fa-info-circle"></i> Docker信息未检测
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="showDetailModal = false">
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 部署命令模态框 -->
    <div v-if="showDeployModal && selectedHost" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-code me-2"></i> 部署命令 - {{ selectedHost.name }}
            </h5>
            <button type="button" class="btn-close" @click="showDeployModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">部署方式</label>
              <div class="btn-group w-100" role="group">
                <input 
                  type="radio" 
                  class="btn-check" 
                  name="deployType" 
                  id="deployRun"
                  value="run"
                  v-model="deployType"
                  @change="loadDeployCommand"
                />
                <label class="btn btn-outline-primary" for="deployRun">
                  <i class="fas fa-play me-1"></i> Docker Run
                </label>
                
                <input 
                  type="radio" 
                  class="btn-check" 
                  name="deployType" 
                  id="deployStack"
                  value="stack"
                  v-model="deployType"
                  @change="loadDeployCommand"
                />
                <label class="btn btn-outline-primary" for="deployStack">
                  <i class="fas fa-layer-group me-1"></i> Docker Stack
                </label>
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label">Agent镜像</label>
              <input 
                type="text" 
                class="form-control form-control-sm" 
                v-model="agentImage"
                @change="loadDeployCommand"
                placeholder="registry.cn-hangzhou.aliyuncs.com/51jbm/app2docker-agent:latest"
              />
            </div>
            <div v-if="deployCommand" class="mb-3">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="form-label mb-0">部署命令</label>
                <button class="btn btn-sm btn-outline-primary" @click="copyDeployCommand">
                  <i class="fas fa-copy me-1"></i> 复制命令
                </button>
              </div>
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 400px; overflow-y: auto;"><code>{{ deployCommand }}</code></pre>
            </div>
            <div v-if="deployComposeContent && deployType === 'stack'" class="mb-3">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="form-label mb-0">docker-compose.yml 内容</label>
                <button class="btn btn-sm btn-outline-primary" @click="copyComposeContent">
                  <i class="fas fa-copy me-1"></i> 复制内容
                </button>
              </div>
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 300px; overflow-y: auto;"><code>{{ deployComposeContent }}</code></pre>
            </div>
            <div v-if="loadingDeployCommand" class="text-center py-3">
              <div class="spinner-border spinner-border-sm me-2"></div>
              加载中...
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="showDeployModal = false">
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'AgentHostManager',
  data() {
    return {
      hosts: [],
      loading: false,
      showAddModal: false,
      showEditModal: false,
      showDetailModal: false,
      showDeployModal: false,
      editingHost: null,
      selectedHost: null,
      saving: false,
      deployType: 'run',
      agentImage: 'registry.cn-hangzhou.aliyuncs.com/51jbm/app2docker-agent:latest',
      deployCommand: null,
      deployComposeContent: null,
      loadingDeployCommand: false,
      hostForm: {
        name: '',
        description: ''
      },
      wsConnections: {}, // WebSocket连接管理
      refreshInterval: null // 定期刷新定时器
    }
  },
  mounted() {
    this.loadHosts()
    // 启动WebSocket连接以实时更新状态
    this.initWebSocketConnections()
    // 定期刷新主机列表（每30秒）
    this.refreshInterval = setInterval(() => {
      this.loadHosts()
    }, 30000)
  },
  beforeUnmount() {
    // 清理定时器
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval)
    }
    // 清理WebSocket连接
    Object.values(this.wsConnections).forEach(ws => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close()
      }
    })
  },
  methods: {
    async loadHosts() {
      this.loading = true
      try {
        const res = await axios.get('/api/agent-hosts')
        if (res.data.hosts) {
          this.hosts = res.data.hosts || []
        }
      } catch (error) {
        console.error('加载Agent主机列表失败:', error)
        alert('加载Agent主机列表失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loading = false
      }
    },
    initWebSocketConnections() {
      // 为每个在线的主机建立WebSocket连接（如果需要实时更新）
      // 这里可以简化，只通过轮询更新状态
    },
    closeModal() {
      this.showAddModal = false
      this.showEditModal = false
      this.editingHost = null
      this.hostForm = {
        name: '',
        description: ''
      }
    },
    editHost(host) {
      this.editingHost = host
      this.showEditModal = true
      this.hostForm = {
        name: host.name,
        description: host.description || ''
      }
    },
    async saveHost() {
      if (!this.hostForm.name) {
        alert('请填写主机名称')
        return
      }

      this.saving = true
      try {
        let res
        if (this.editingHost) {
          res = await axios.put(`/api/agent-hosts/${this.editingHost.host_id}`, this.hostForm)
        } else {
          res = await axios.post('/api/agent-hosts', this.hostForm)
        }

        if (res.data.success) {
          alert(this.editingHost ? 'Agent主机更新成功' : 'Agent主机创建成功')
          this.closeModal()
          this.loadHosts()
          
          // 如果是新建，显示部署命令
          if (!this.editingHost && res.data.host) {
            this.selectedHost = res.data.host
            this.showDeployModal = true
            this.loadDeployCommand()
          }
        }
      } catch (error) {
        console.error('保存Agent主机失败:', error)
        alert('保存Agent主机失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.saving = false
      }
    },
    async deleteHost(host) {
      if (!confirm(`确定要删除Agent主机 "${host.name}" 吗？`)) {
        return
      }

      try {
        const res = await axios.delete(`/api/agent-hosts/${host.host_id}`)
        if (res.data.success) {
          alert('Agent主机已删除')
          this.loadHosts()
        }
      } catch (error) {
        console.error('删除Agent主机失败:', error)
        alert('删除Agent主机失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    viewHost(host) {
      this.selectedHost = host
      this.showDetailModal = true
    },
    showDeployCommand(host) {
      this.selectedHost = host
      this.showDeployModal = true
      this.loadDeployCommand()
    },
    async loadDeployCommand() {
      if (!this.selectedHost) return
      
      this.loadingDeployCommand = true
      this.deployCommand = null
      this.deployComposeContent = null
      
      try {
        const res = await axios.get(`/api/agent-hosts/${this.selectedHost.host_id}/deploy-command`, {
          params: {
            type: this.deployType,
            agent_image: this.agentImage
          }
        })
        
        this.deployCommand = res.data.command
        if (res.data.compose_content) {
          this.deployComposeContent = res.data.compose_content
        }
      } catch (error) {
        console.error('加载部署命令失败:', error)
        alert('加载部署命令失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loadingDeployCommand = false
      }
    },
    copyDeployCommand() {
      if (this.deployCommand) {
        this.copyToClipboard(this.deployCommand)
        alert('部署命令已复制到剪贴板')
      }
    },
    copyComposeContent() {
      if (this.deployComposeContent) {
        this.copyToClipboard(this.deployComposeContent)
        alert('docker-compose.yml 内容已复制到剪贴板')
      }
    },
    copyToClipboard(text) {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text)
      } else {
        // 降级方案
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
      }
    },
    getStatusBadgeClass(status) {
      const statusMap = {
        'online': 'bg-success',
        'offline': 'bg-secondary',
        'connecting': 'bg-warning'
      }
      return statusMap[status] || 'bg-secondary'
    },
    getStatusIcon(status) {
      const iconMap = {
        'online': 'fas fa-circle',
        'offline': 'fas fa-circle',
        'connecting': 'fas fa-spinner fa-spin'
      }
      return iconMap[status] || 'fas fa-circle'
    },
    getStatusText(status) {
      const textMap = {
        'online': '在线',
        'offline': '离线',
        'connecting': '连接中'
      }
      return textMap[status] || '未知'
    },
    formatTime(timeStr) {
      if (!timeStr) return '-'
      const date = new Date(timeStr)
      return date.toLocaleString('zh-CN')
    }
  }
}
</script>

<style scoped>
.agent-host-manager-panel {
  padding: 0;
}

.modal.show {
  display: block;
}

.progress {
  min-width: 100px;
}

code {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9em;
}

pre code {
  font-size: 0.85em;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.btn-group .btn-check:checked + .btn {
  background-color: #0d6efd;
  border-color: #0d6efd;
  color: white;
}

@media (max-width: 768px) {
  .modal-dialog {
    margin: 0.5rem;
  }
}
</style>


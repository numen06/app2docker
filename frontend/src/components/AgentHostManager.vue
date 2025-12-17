<template>
  <div class="agent-host-manager-panel" v-show="shouldShow">
    <!-- 添加主机按钮 -->
    <div class="d-flex justify-content-end mb-3" v-if="filterType === 'all' || filterType === 'agent'">
      <button class="btn btn-primary btn-sm" @click="showAddModal = true">
        <i class="fas fa-plus"></i> 新建Agent主机
      </button>
    </div>

    <!-- Agent主机列表 - 卡片式布局 -->
    <div v-if="loading" class="text-center py-5">
      <span class="spinner-border spinner-border-sm"></span> 加载中...
    </div>
    <div v-else-if="filteredHosts.length === 0" class="text-center py-5 text-muted">
      <i class="fas fa-network-wired fa-3x mb-3"></i>
      <p class="mb-0">暂无Agent主机</p>
      <button class="btn btn-primary btn-sm mt-2" @click="showAddModal = true">
        <i class="fas fa-plus"></i> 新建Agent主机
      </button>
    </div>
    <div v-else class="row g-4">
      <div
        v-for="host in filteredHosts"
        :key="host.host_id"
        class="col-12 col-md-6 col-xl-4"
      >
        <div class="card h-100 shadow-sm">
          <!-- 卡片头部 -->
          <div class="card-header bg-white">
            <div class="mb-2">
              <h5 class="card-title mb-2">
                <strong>{{ host.name }}</strong>
              </h5>
              <div class="d-flex align-items-center justify-content-between mb-1">
                <div>
                  <span class="badge" :class="host.host_type === 'portainer' ? 'bg-primary' : 'bg-secondary'">
                    <i class="fas fa-network-wired"></i> {{ host.host_type === 'portainer' ? 'Portainer' : 'Agent' }}
                  </span>
                  <span :class="getStatusBadgeClass(host.status)" class="badge ms-1">
                    <i :class="getStatusIcon(host.status)"></i>
                    {{ getStatusText(host.status) }}
                  </span>
                </div>
              </div>
              <p
                class="text-muted mb-0 mt-1"
                v-if="host.description"
                style="font-size: 0.9rem"
              >
                {{ host.description }}
              </p>
            </div>
            <!-- 操作按钮行 -->
            <div class="btn-group btn-group-sm w-100">
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
                class="btn btn-outline-success"
                @click="refreshHostStatus(host)"
                title="刷新状态"
              >
                <i class="fas fa-sync-alt"></i>
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
          </div>

          <!-- 卡片内容 -->
          <div class="card-body">
            <!-- 主机信息 -->
            <div class="mb-3">
              <div v-if="host.host_info && Object.keys(host.host_info).length > 0">
                <div class="d-flex align-items-center mb-2">
                  <i class="fas fa-network-wired text-muted me-2" style="width: 18px;"></i>
                  <div class="flex-grow-1">
                    <div class="small" v-if="host.host_info.ip">
                      <strong>{{ host.host_info.ip }}</strong>
                    </div>
                    <div class="small text-muted mt-1" v-if="host.host_info.os">
                      <i class="fas fa-desktop me-1"></i>{{ host.host_info.os }}
                    </div>
                  </div>
                </div>
                <div v-if="host.host_info.cpu_usage !== undefined" class="small text-muted mt-2">
                  <div class="d-flex justify-content-between mb-1">
                    <span>CPU: {{ host.host_info.cpu_usage }}%</span>
                    <span>内存: {{ host.host_info.memory_usage }}%</span>
                  </div>
                  <div>磁盘: {{ host.host_info.disk_usage }}%</div>
                </div>
              </div>
              <div v-else class="text-muted small">
                <i class="fas fa-exclamation-circle me-1"></i>未连接
              </div>
            </div>

            <!-- Docker信息 -->
            <div class="mb-3">
              <div v-if="host.docker_info && Object.keys(host.docker_info).length > 0">
                <div class="mb-2">
                  <span v-if="host.docker_info.version" class="badge bg-info">
                    <i class="fab fa-docker me-1"></i>{{ host.docker_info.version }}
                  </span>
                </div>
                <div class="small text-muted">
                  <span v-if="host.docker_info.containers !== undefined">
                    容器: {{ host.docker_info.containers }}
                  </span>
                  <span v-if="host.docker_info.images !== undefined" class="ms-2">
                    镜像: {{ host.docker_info.images }}
                  </span>
                </div>
              </div>
              <div v-else class="text-muted small">
                <i class="fas fa-exclamation-circle me-1"></i>未检测
              </div>
            </div>

            <!-- 最后心跳和创建时间 -->
            <div class="small text-muted border-top pt-2">
              <div v-if="host.last_heartbeat" class="mb-1">
                <i class="fas fa-heartbeat me-1"></i>最后心跳: {{ formatTime(host.last_heartbeat) }}
              </div>
              <div>
                <i class="fas fa-clock me-1"></i>{{ formatTime(host.created_at) }}
              </div>
            </div>
          </div>
        </div>
      </div>
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
            <form @submit.prevent="saveHost" novalidate>
              <div class="mb-3">
                <label class="form-label">
                  主机类型 <span class="text-danger">*</span>
                </label>
                <div class="btn-group w-100" role="group">
                  <input type="radio" class="btn-check" id="host-type-agent" v-model="hostForm.host_type" value="agent" :disabled="!!editingHost">
                  <label class="btn btn-outline-primary" for="host-type-agent">
                    <i class="fas fa-network-wired me-1"></i> Agent
                  </label>
                  
                  <input type="radio" class="btn-check" id="host-type-portainer" v-model="hostForm.host_type" value="portainer" :disabled="!!editingHost">
                  <label class="btn btn-outline-primary" for="host-type-portainer">
                    <i class="fab fa-docker me-1"></i> Portainer
                  </label>
                </div>
              </div>
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
              
              <!-- Portainer 配置 -->
              <div v-if="hostForm.host_type === 'portainer'">
                <div class="mb-3">
                  <label class="form-label">
                    Portainer API URL <span class="text-danger">*</span>
                  </label>
                  <input 
                    type="text" 
                    class="form-control form-control-sm" 
                    v-model="hostForm.portainer_url"
                    placeholder="http://portainer.example.com:9000"
                    required
                  />
                  <small class="text-muted">Portainer 服务器的 API 地址</small>
                </div>
                <div class="mb-3">
                  <label class="form-label">
                    Portainer API Key <span class="text-danger">*</span>
                  </label>
                  <input 
                    type="password" 
                    class="form-control form-control-sm" 
                    v-model="hostForm.portainer_api_key"
                    placeholder="ptc_xxxxxxxxxxxxx"
                    @blur="autoLoadEndpoints"
                    required
                  />
                  <small class="text-muted">在 Portainer 设置中生成的 API Key</small>
                </div>
                <div class="mb-3">
                  <label class="form-label">
                    Endpoint <span class="text-danger">*</span>
                  </label>
                  <div class="input-group">
                    <select 
                      class="form-select form-control-sm" 
                      v-model.number="hostForm.portainer_endpoint_id"
                      :disabled="loadingEndpoints"
                      required
                    >
                      <option value="" disabled>请选择 Endpoint</option>
                      <option v-for="ep in availableEndpoints" :key="ep.id" :value="ep.id">
                        {{ ep.name }} (ID: {{ ep.id }})
                      </option>
                    </select>
                    <button 
                      type="button" 
                      class="btn btn-sm btn-outline-secondary" 
                      @click="loadEndpoints"
                      :disabled="loadingEndpoints || !hostForm.portainer_url || !hostForm.portainer_api_key"
                      title="刷新 Endpoints 列表"
                    >
                      <span v-if="loadingEndpoints" class="spinner-border spinner-border-sm"></span>
                      <i v-else class="fas fa-sync-alt"></i>
                    </button>
                  </div>
                  <small class="text-muted">
                    <span v-if="availableEndpoints.length > 0">
                      已加载 {{ availableEndpoints.length }} 个 Endpoint
                    </span>
                    <span v-else>
                      点击刷新按钮加载 Endpoints 列表
                    </span>
                  </small>
                </div>
                <div class="mb-3">
                  <button 
                    type="button" 
                    class="btn btn-sm btn-outline-info" 
                    @click="testPortainerConnection"
                    :disabled="testingConnection"
                  >
                    <span v-if="testingConnection" class="spinner-border spinner-border-sm me-1"></span>
                    <i v-else class="fas fa-plug me-1"></i>
                    {{ testingConnection ? '测试中...' : '测试连接' }}
                  </button>
                </div>
              </div>
              
              <div v-if="!editingHost && hostForm.host_type === 'agent'" class="alert alert-info py-2 mb-0">
                <i class="fas fa-info-circle me-2"></i>
                创建后将自动生成Token和部署命令，请按照部署命令在目标主机上部署Agent。
              </div>
              <div v-if="hostForm.host_type === 'portainer'" class="alert alert-info py-2 mb-0">
                <i class="fas fa-info-circle me-2"></i>
                Portainer 主机通过 Portainer API 进行连接和部署，无需在目标主机上部署 Agent。
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
                  <tbody>
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
                  </tbody>
                </table>
              </div>
              <div class="col-md-6">
                <h6 class="border-bottom pb-2">主机信息</h6>
                <div v-if="selectedHost.host_info && Object.keys(selectedHost.host_info).length > 0">
                  <table class="table table-sm">
                    <tbody>
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
                    </tbody>
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
                    <tbody>
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
                    </tbody>
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
                placeholder="registry.cn-shanghai.aliyuncs.com/51jbm/app2docker-agent:latest"
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
import axios from 'axios';

export default {
  name: 'AgentHostManager',
  props: {
    filterType: {
      type: String,
      default: 'all'
    }
  },
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
      agentImage: 'registry.cn-shanghai.aliyuncs.com/51jbm/app2docker-agent:latest',
      deployCommand: null,
      deployComposeContent: null,
      loadingDeployCommand: false,
      hostForm: {
        host_type: 'agent',
        name: '',
        description: '',
        portainer_url: '',
        portainer_api_key: '',
        portainer_endpoint_id: null
      },
      testingConnection: false,
      loadingEndpoints: false,
      availableEndpoints: [],
      wsConnections: {}, // WebSocket连接管理
      refreshInterval: null // 定期刷新定时器
    }
  },
  computed: {
    shouldShow() {
      return this.filterType === 'all' || this.filterType === 'agent'
    },
    filteredHosts() {
      if (!this.shouldShow) return []
      return this.hosts
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
        host_type: 'agent',
        name: '',
        description: '',
        portainer_url: '',
        portainer_api_key: '',
        portainer_endpoint_id: null
      }
      this.availableEndpoints = []
    },
    editHost(host) {
      this.editingHost = host
      this.showEditModal = true
      this.hostForm = {
        host_type: host.host_type || 'agent',
        name: host.name,
        description: host.description || '',
        portainer_url: host.portainer_url || '',
        portainer_api_key: '', // 不显示 API Key
        portainer_endpoint_id: host.portainer_endpoint_id || null
      }
      this.availableEndpoints = []
      // 如果是 Portainer 类型，尝试加载 endpoints
      if (host.host_type === 'portainer' && host.portainer_url) {
        // 不自动加载，因为需要 API Key
      }
    },
    async autoLoadEndpoints() {
      // 当 API Key 输入完成后，自动加载 endpoints
      if (this.hostForm.host_type === 'portainer' && 
          this.hostForm.portainer_url && 
          this.hostForm.portainer_api_key &&
          this.availableEndpoints.length === 0) {
        await this.loadEndpoints()
      }
    },
    async loadEndpoints() {
      if (!this.hostForm.portainer_url || !this.hostForm.portainer_api_key) {
        alert('请先填写 Portainer URL 和 API Key')
        return
      }
      
      this.loadingEndpoints = true
      try {
        const res = await axios.post('/api/agent-hosts/list-portainer-endpoints', {
          portainer_url: this.hostForm.portainer_url,
          api_key: this.hostForm.portainer_api_key,
          endpoint_id: 0 // 不需要真实的 endpoint_id
        }, {
          timeout: 10000
        })
        
        if (res.data.success) {
          this.availableEndpoints = res.data.endpoints || []
          if (this.availableEndpoints.length === 0) {
            alert('未找到可用的 Endpoints')
          } else {
            // 如果只有一个 endpoint，自动选择
            if (this.availableEndpoints.length === 1) {
              this.hostForm.portainer_endpoint_id = this.availableEndpoints[0].id
            }
          }
        } else {
          alert('加载 Endpoints 失败：' + (res.data.message || '未知错误'))
        }
      } catch (error) {
        console.error('加载 Endpoints 失败:', error)
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          alert('加载超时，请检查 Portainer URL 是否正确且可访问')
        } else {
          alert('加载 Endpoints 失败: ' + (error.response?.data?.detail || error.message))
        }
      } finally {
        this.loadingEndpoints = false
      }
    },
    async testPortainerConnection() {
      if (!this.hostForm.portainer_url || !this.hostForm.portainer_api_key || 
          this.hostForm.portainer_endpoint_id === null || this.hostForm.portainer_endpoint_id === undefined) {
        alert('请填写完整的 Portainer 配置信息')
        return
      }
      
      this.testingConnection = true
      try {
        // 设置15秒超时
        const res = await axios.post('/api/agent-hosts/test-portainer', {
          portainer_url: this.hostForm.portainer_url,
          api_key: this.hostForm.portainer_api_key,
          endpoint_id: this.hostForm.portainer_endpoint_id
        }, {
          timeout: 15000 // 15秒超时
        })
        
        if (res.data.success) {
          alert('连接测试成功！')
        } else {
          let errorMsg = res.data.message || '未知错误'
          // 如果有可用的 endpoints，显示它们
          if (res.data.available_endpoints && res.data.available_endpoints.length > 0) {
            const endpointsList = res.data.available_endpoints.map(ep => `ID: ${ep.id} (${ep.name})`).join('\n')
            errorMsg += '\n\n可用的 Endpoints:\n' + endpointsList
          }
          alert('连接测试失败：' + errorMsg)
        }
      } catch (error) {
        console.error('测试连接失败:', error)
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          alert('连接测试超时，请检查 Portainer URL 是否正确且可访问')
        } else {
          alert('测试连接失败: ' + (error.response?.data?.detail || error.message))
        }
      } finally {
        this.testingConnection = false
      }
    },
    async refreshHostStatus(host) {
      try {
        const res = await axios.post(`/api/agent-hosts/${host.host_id}/refresh-status`)
        if (res.data.success) {
          alert('状态刷新成功！')
          this.loadHosts()
        } else {
          alert('状态刷新失败：' + (res.data.message || '未知错误'))
        }
      } catch (error) {
        console.error('刷新状态失败:', error)
        alert('刷新状态失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async saveHost() {
      if (!this.hostForm.name) {
        alert('请填写主机名称')
        return
      }
      
      if (this.hostForm.host_type === 'portainer') {
        if (!this.hostForm.portainer_url || !this.hostForm.portainer_api_key || 
            this.hostForm.portainer_endpoint_id === null || this.hostForm.portainer_endpoint_id === undefined) {
          alert('请填写完整的 Portainer 配置信息')
          return
        }
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
          alert(this.editingHost ? '主机更新成功' : '主机创建成功')
          this.closeModal()
          this.loadHosts()
          
          // 如果是新建 Agent 类型主机，显示部署命令
          if (!this.editingHost && res.data.host && res.data.host.host_type === 'agent') {
            this.selectedHost = res.data.host
            this.showDeployModal = true
            this.loadDeployCommand()
          }
          
          // 如果是新建 Portainer 类型主机，更新状态
          if (!this.editingHost && res.data.host && res.data.host.host_type === 'portainer') {
            // Portainer 主机创建后，可以尝试更新状态
            setTimeout(() => {
              this.loadHosts()
            }, 1000)
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

.card {
  transition: transform 0.2s, box-shadow 0.2s;
  border: 1px solid #dee2e6;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
}

.card-header {
  border-bottom: 1px solid #dee2e6;
  padding: 1rem;
}

.card-title {
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.card-body {
  padding: 1rem;
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


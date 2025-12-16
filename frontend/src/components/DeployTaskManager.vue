<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-rocket text-primary"></i> 部署配置管理
        <small class="text-muted ms-2">（配置触发后会生成任务）</small>
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

    <!-- 配置列表 -->
    <div class="table-responsive">
      <table class="table table-hover">
        <thead>
          <tr>
            <th width="8%">配置ID</th>
            <th width="12%">应用名称</th>
            <th width="10%">目标主机</th>
            <th width="8%">触发次数</th>
            <th width="12%">创建时间</th>
            <th width="12%">最后触发</th>
            <th width="18%">Webhook URL</th>
            <th width="20%">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="text-center py-4">
              <div class="spinner-border spinner-border-sm me-2"></div>
              加载中...
            </td>
          </tr>
          <tr v-else-if="tasks.length === 0">
            <td colspan="8" class="text-center py-4 text-muted">
              暂无部署配置
            </td>
          </tr>
          <tr v-else v-for="task in tasks" :key="task.task_id">
            <td>
              <code class="small">{{ task.task_id.substring(0, 8) }}</code>
            </td>
            <td>{{ task.config?.app?.name || '-' }}</td>
            <td>
              <span v-for="(target, idx) in task.config?.targets || []" :key="idx" class="badge bg-secondary me-1">
                {{ target.name || target.host_name || '-' }}
              </span>
            </td>
            <td>
              <span class="badge bg-info">
                <i class="fas fa-play-circle"></i> {{ task.execution_count || 0 }}
              </span>
              <button 
                v-if="task.execution_count > 0"
                class="btn btn-link btn-sm p-0 ms-1" 
                @click="viewExecutions(task)"
                title="查看执行历史"
                style="font-size: 0.75rem; text-decoration: none;"
              >
                <i class="fas fa-external-link-alt"></i>
              </button>
            </td>
            <td>{{ formatTime(task.created_at) }}</td>
            <td>
              <div class="d-flex flex-column">
                <span>{{ formatTime(task.last_executed_at) || '-' }}</span>
                <small v-if="task.status?.trigger_source" class="text-muted">
                  <span v-if="task.status.trigger_source === 'webhook'">
                    <i class="fas fa-link text-success me-1"></i> Webhook 触发
                  </span>
                  <span v-else-if="task.status.trigger_source === 'manual'">
                    <i class="fas fa-user text-primary me-1"></i> 手动触发
                  </span>
                  <span v-else-if="task.status.trigger_source === 'cron'">
                    <i class="fas fa-clock text-warning me-1"></i> 定时触发
                  </span>
                  <span v-else>
                    <i class="fas fa-question-circle text-secondary me-1"></i>
                    {{ task.status.trigger_source }}
                  </span>
                </small>
              </div>
            </td>
            <td>
              <div v-if="task.webhook_token" class="d-flex align-items-center gap-1">
                <code 
                  class="small" 
                  style="font-size: 0.75rem; word-break: break-all; max-width: 180px; display: block;"
                  :title="getWebhookUrl(task)"
                >
                  {{ getWebhookUrl(task) }}
                </code>
                <button 
                  class="btn btn-sm btn-link p-0" 
                  @click="copyWebhookUrl(task)" 
                  title="复制 Webhook URL"
                  style="font-size: 0.875rem; flex-shrink: 0;"
                >
                  <i class="fas fa-copy"></i>
                </button>
              </div>
              <span v-else class="text-muted small">未配置</span>
            </td>
            <td>
              <div class="btn-group" role="group">
                <button class="btn btn-sm btn-outline-primary" @click="viewTask(task)" title="查看详情">
                  <i class="fas fa-eye"></i>
                </button>
                <button 
                  class="btn btn-sm btn-outline-success" 
                  @click="executeTask(task)"
                  title="触发部署（将创建新任务）"
                >
                  <i class="fas fa-play"></i> 触发
                </button>
                <button class="btn btn-sm btn-outline-secondary" @click="editTask(task)" title="编辑配置">
                  <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-outline-info" @click="copyTask(task)" title="复制配置">
                  <i class="fas fa-copy"></i>
                </button>
                <button 
                  v-if="task.webhook_token" 
                  class="btn btn-sm btn-outline-success" 
                  @click="showWebhookUrl(task)" 
                  title="查看 Webhook URL 详情"
                >
                  <i class="fas fa-link"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" @click="deleteTask(task)" title="删除配置">
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
            <!-- 应用基本信息 -->
            <div class="mb-3">
              <label class="form-label">应用名称 <span class="text-danger">*</span></label>
              <input v-model="simpleForm.appName" type="text" class="form-control" placeholder="my-app">
              <small class="text-muted">用于标识此部署任务的应用名称</small>
            </div>
            
            <!-- 统一部署配置 -->
            <div class="card mb-3">
              <div class="card-header bg-light">
                <h6 class="mb-0">
                  <i class="fas fa-cogs me-2"></i> 部署配置（统一配置，适用于所有目标主机）
                </h6>
              </div>
              <div class="card-body">
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
                    
                    <input type="radio" class="btn-check" id="deploy-multi-step" v-model="simpleForm.deployMode" value="multi_step">
                    <label class="btn btn-outline-primary" for="deploy-multi-step">
                      <i class="fas fa-list-ol me-1"></i> 多步骤
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
                  <small class="text-muted">输入 docker run 的参数（可包含 "docker run" 前缀，系统会自动适配）</small>
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

                <!-- 多步骤配置 -->
                <div v-if="simpleForm.deployMode === 'multi_step'" class="mb-3">
                  <div class="d-flex justify-content-between align-items-center mb-2">
                    <div>
                      <label class="form-label mb-0">部署步骤 <span class="text-danger">*</span></label>
                      <small class="text-muted d-block">按顺序添加多个部署步骤，系统将依次执行</small>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-primary" @click="addStep">
                      <i class="fas fa-plus me-1"></i> 添加步骤
                    </button>
                  </div>
                  
                  <div v-if="simpleForm.steps.length === 0" class="alert alert-info mb-0">
                    <i class="fas fa-info-circle me-1"></i>
                    请至少添加一个部署步骤
                  </div>
                  
                  <div v-else class="steps-list">
                    <div 
                      v-for="(step, index) in simpleForm.steps" 
                      :key="index" 
                      class="card mb-2 step-card"
                      :class="{ 'border-primary': step.name || step.command }"
                    >
                      <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                          <div class="d-flex align-items-center">
                            <span class="badge bg-primary me-2" style="min-width: 60px;">步骤 {{ index + 1 }}</span>
                            <span v-if="step.name" class="text-muted small">{{ step.name }}</span>
                            <span v-else class="text-muted small fst-italic">未命名步骤</span>
                          </div>
                          <div class="btn-group btn-group-sm">
                            <button 
                              type="button" 
                              class="btn btn-outline-secondary" 
                              @click="moveStep(index, -1)"
                              :disabled="index === 0"
                              title="上移"
                            >
                              <i class="fas fa-arrow-up"></i>
                            </button>
                            <button 
                              type="button" 
                              class="btn btn-outline-secondary" 
                              @click="moveStep(index, 1)"
                              :disabled="index === simpleForm.steps.length - 1"
                              title="下移"
                            >
                              <i class="fas fa-arrow-down"></i>
                            </button>
                            <button 
                              type="button" 
                              class="btn btn-outline-danger" 
                              @click="removeStep(index)" 
                              title="删除步骤"
                            >
                              <i class="fas fa-trash"></i>
                            </button>
                          </div>
                        </div>
                        <div class="mb-2">
                          <label class="form-label small mb-1">步骤名称</label>
                          <input 
                            v-model="step.name" 
                            type="text" 
                            class="form-control form-control-sm" 
                            placeholder="例如：停止旧容器、拉取镜像、启动容器"
                          >
                        </div>
                        <div>
                          <label class="form-label small mb-1">执行命令</label>
                          <textarea 
                            v-model="step.command" 
                            class="form-control font-monospace form-control-sm" 
                            rows="4"
                            placeholder="docker stop my-app || true&#10;或&#10;docker pull registry.cn-hangzhou.aliyuncs.com/namespace/app:latest"
                          ></textarea>
                          <small class="text-muted">输入要执行的命令或脚本，支持多行</small>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="mb-0">
                  <div class="form-check form-switch">
                    <input 
                      class="form-check-input" 
                      type="checkbox" 
                      id="redeploySwitch"
                      v-model="simpleForm.redeploy"
                    >
                    <label class="form-check-label" for="redeploySwitch">
                      <i class="fas fa-redo me-1"></i> 重新发布（如果主机上已存在，先停止并删除）
                    </label>
                  </div>
                  <small class="text-muted">启用后，部署前会先停止并删除已有的容器或服务</small>
                </div>
              </div>
            </div>
            
            <!-- 目标主机选择 -->
            <div class="mb-3">
              <label class="form-label">选择目标主机 <span class="text-danger">*</span></label>
              <small class="text-muted d-block mb-2">选择要部署到的主机，上述部署配置将应用到所有选中的主机</small>
              
              <!-- 主机类型筛选和搜索 -->
              <div class="mb-2">
                <div class="btn-group btn-group-sm mb-2" role="group">
                  <input type="radio" class="btn-check" id="filter-all" v-model="hostFilter" value="all">
                  <label class="btn btn-outline-secondary" for="filter-all">全部</label>
                  
                  <input type="radio" class="btn-check" id="filter-agent" v-model="hostFilter" value="agent">
                  <label class="btn btn-outline-secondary" for="filter-agent">
                    <i class="fas fa-network-wired me-1"></i> Agent
                  </label>
                  
                  <input type="radio" class="btn-check" id="filter-portainer" v-model="hostFilter" value="portainer">
                  <label class="btn btn-outline-secondary" for="filter-portainer">
                    <i class="fas fa-server me-1"></i> Portainer
                  </label>
                  
                  <input type="radio" class="btn-check" id="filter-ssh" v-model="hostFilter" value="ssh">
                  <label class="btn btn-outline-secondary" for="filter-ssh">
                    <i class="fas fa-terminal me-1"></i> SSH
                  </label>
                </div>
                <div class="d-flex align-items-center gap-2">
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="filter-online" v-model="filterOnlineOnly">
                    <label class="form-check-label" for="filter-online">仅在线</label>
                  </div>
                  <input 
                    type="text" 
                    class="form-control form-control-sm flex-grow-1" 
                    v-model="hostSearchKeyword"
                    placeholder="搜索主机名称..."
                  >
                </div>
              </div>
              
              <!-- 主机列表（按类型分组） -->
              <div v-if="loadingHosts" class="text-muted small text-center py-3">
                <span class="spinner-border spinner-border-sm me-2"></span>加载中...
              </div>
              <div v-else class="border rounded p-2" style="max-height: 300px; overflow-y: auto;">
                <!-- Agent 主机 -->
                <div v-if="filteredHostsByType.agent.length > 0" class="mb-3">
                  <div class="fw-bold text-primary mb-2">
                    <i class="fas fa-network-wired me-1"></i> Agent 主机 ({{ filteredHostsByType.agent.length }})
                  </div>
                  <div v-for="host in filteredHostsByType.agent" :key="host.host_id" class="form-check ms-3">
                    <input
                      class="form-check-input"
                      type="checkbox"
                      :id="`host-${host.host_id}`"
                      :value="host.host_id"
                      v-model="simpleForm.selectedHosts"
                    >
                    <label class="form-check-label" :for="`host-${host.host_id}`">
                      {{ host.name }}
                      <span :class="getStatusBadgeClass(host.status)" class="badge ms-1">
                        {{ getStatusText(host.status) }}
                      </span>
                      <span v-if="host.description" class="text-muted small ms-1">({{ host.description }})</span>
                    </label>
                  </div>
                </div>
                
                <!-- Portainer 主机 -->
                <div v-if="filteredHostsByType.portainer.length > 0" class="mb-3">
                  <div class="fw-bold text-info mb-2">
                    <i class="fas fa-server me-1"></i> Portainer 主机 ({{ filteredHostsByType.portainer.length }})
                  </div>
                  <div v-for="host in filteredHostsByType.portainer" :key="host.host_id" class="form-check ms-3">
                    <input
                      class="form-check-input"
                      type="checkbox"
                      :id="`host-${host.host_id}`"
                      :value="host.host_id"
                      v-model="simpleForm.selectedHosts"
                    >
                    <label class="form-check-label" :for="`host-${host.host_id}`">
                      {{ host.name }}
                      <span :class="getStatusBadgeClass(host.status)" class="badge ms-1">
                        {{ getStatusText(host.status) }}
                      </span>
                      <span v-if="host.portainer_url" class="text-muted small ms-1">({{ host.portainer_url }})</span>
                    </label>
                  </div>
                </div>
                
                <!-- SSH 主机 -->
                <div v-if="filteredHostsByType.ssh.length > 0" class="mb-3">
                  <div class="fw-bold text-warning mb-2">
                    <i class="fas fa-terminal me-1"></i> SSH 主机 ({{ filteredHostsByType.ssh.length }})
                  </div>
                  <div v-for="host in filteredHostsByType.ssh" :key="host.host_id" class="form-check ms-3">
                    <input
                      class="form-check-input"
                      type="checkbox"
                      :id="`host-${host.host_id}`"
                      :value="host.host_id"
                      v-model="simpleForm.selectedHosts"
                    >
                    <label class="form-check-label" :for="`host-${host.host_id}`">
                      {{ host.name }}
                      <span v-if="host.docker_enabled" class="badge bg-info ms-1">Docker</span>
                      <span v-if="host.docker_version" class="text-muted small ms-1">({{ host.docker_version }})</span>
                      <span v-if="host.host" class="text-muted small ms-1">@{{ host.host }}:{{ host.port || 22 }}</span>
                    </label>
                  </div>
                </div>
                
                <div v-if="filteredHosts.length === 0" class="text-muted small text-center py-3">
                  <i class="fas fa-inbox me-1"></i>
                  <span v-if="hostSearchKeyword">未找到匹配的主机</span>
                  <span v-else>暂无可用主机，请先在"主机管理"中添加主机</span>
                </div>
              </div>
              
              <!-- 已选择的主机统计 -->
              <div v-if="simpleForm.selectedHosts.length > 0" class="mt-2">
                <small class="text-muted">
                  已选择 <strong>{{ simpleForm.selectedHosts.length }}</strong> 个主机
                  <button type="button" class="btn btn-link btn-sm p-0 ms-2" @click="simpleForm.selectedHosts = []">
                    清空
                  </button>
                </small>
              </div>
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
                  <i class="fas fa-cog me-1"></i> 配置信息
                </button>
              </li>
              <li class="nav-item">
                <button class="nav-link" :class="{ active: detailTab === 'status' }" @click="detailTab = 'status'">
                  <i class="fas fa-tasks me-1"></i> 执行状态
                </button>
              </li>
              <li class="nav-item">
                <button class="nav-link" :class="{ active: detailTab === 'logs' }" @click="detailTab = 'logs'">
                  <i class="fas fa-file-alt me-1"></i> 执行日志
                </button>
              </li>
            </ul>

            <div v-if="detailTab === 'config'">
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 500px; overflow-y: auto;"><code>{{ selectedTask.config_content || selectedTask.task_config?.config_content || '' }}</code></pre>
            </div>

            <div v-if="detailTab === 'status'">
              <div class="mb-3">
                <strong>任务状态:</strong>
                <span :class="getStatusBadgeClass(selectedTask.status)" class="badge ms-2">
                  {{ getStatusText(selectedTask.status) }}
                </span>
                <span v-if="selectedTask.created_at" class="text-muted small ms-3">
                  创建时间: {{ formatTime(selectedTask.created_at) }}
                </span>
                <span v-if="selectedTask.completed_at" class="text-muted small ms-3">
                  完成时间: {{ formatTime(selectedTask.completed_at) }}
                </span>
              </div>
              <div v-if="selectedTask.error" class="alert alert-danger mb-3">
                <strong>错误信息:</strong> {{ selectedTask.error }}
              </div>
              <div v-if="selectedTask.config?.targets" class="mb-3">
                <strong>目标主机配置:</strong>
                <table class="table table-sm mt-2">
                  <thead>
                    <tr>
                      <th>主机名称</th>
                      <th>主机类型</th>
                      <th>配置</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="target in selectedTask.config.targets" :key="target.name">
                      <td>{{ target.name || target.host_name || '-' }}</td>
                      <td>
                        <span class="badge bg-info">{{ target.host_type || target.mode || '-' }}</span>
                      </td>
                      <td>
                        <small class="text-muted">{{ target.host_name || target.host || target.agent?.name || '-' }}</small>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- 执行日志标签页 -->
            <div v-if="detailTab === 'logs'">
              <div class="mb-2 d-flex justify-content-between align-items-center">
                <strong>执行日志</strong>
                <button 
                  class="btn btn-sm btn-outline-secondary" 
                  @click="refreshTask(selectedTask)"
                  title="刷新日志"
                >
                  <i class="fas fa-sync-alt me-1"></i> 刷新
                </button>
              </div>
              
              <div v-if="taskLogs && taskLogs.length > 0">
                <div class="log-container bg-dark text-light p-3 rounded" style="max-height: 600px; overflow-y: auto; font-family: monospace; font-size: 12px;">
                  <div 
                    v-for="(log, idx) in taskLogs" 
                    :key="idx"
                    class="log-line mb-1"
                    :class="getLogLineClass(log)"
                  >
                    <span class="text-muted">[{{ formatTime(log.log_time) }}]</span>
                    <span class="ms-2" v-html="formatLogMessage(log.log_message)"></span>
                  </div>
                </div>
              </div>
              
              <div v-else class="text-muted text-center py-4">
                <i class="fas fa-info-circle me-1"></i>
                暂无执行日志
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
              class="btn btn-success" 
              @click="executeTask(selectedTask)"
              :disabled="selectedTask.status === 'running'"
            >
              <i class="fas fa-play me-1"></i> 
              {{ selectedTask.status === 'running' ? '执行中...' : '执行任务' }}
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
            <!-- 编辑方式切换标签页 -->
            <ul class="nav nav-tabs mb-3">
              <li class="nav-item">
                <button 
                  class="nav-link" 
                  :class="{ active: editMode === 'form' }" 
                  @click="editMode = 'form'"
                  type="button"
                >
                  <i class="fas fa-edit me-1"></i> 表单编辑
                </button>
              </li>
              <li class="nav-item">
                <button 
                  class="nav-link" 
                  :class="{ active: editMode === 'yaml' }" 
                  @click="switchToYamlMode"
                  type="button"
                >
                  <i class="fas fa-code me-1"></i> YAML编辑
                </button>
              </li>
              <li class="nav-item">
                <button 
                  class="nav-link" 
                  :class="{ active: editMode === 'webhook' }" 
                  @click="editMode = 'webhook'"
                  type="button"
                >
                  <i class="fas fa-link me-1"></i> Webhook设置
                </button>
              </li>
            </ul>

            <!-- 表单编辑模式 -->
            <div v-if="editMode === 'form'">
              <!-- 应用基本信息 -->
              <div class="mb-3">
                <label class="form-label">应用名称 <span class="text-danger">*</span></label>
                <input v-model="editForm.appName" type="text" class="form-control" placeholder="my-app">
                <small class="text-muted">用于标识此部署任务的应用名称</small>
              </div>
              
              <!-- 统一部署配置 -->
              <div class="card mb-3">
                <div class="card-header bg-light">
                  <h6 class="mb-0">
                    <i class="fas fa-cogs me-2"></i> 部署配置（统一配置，适用于所有目标主机）
                  </h6>
                </div>
                <div class="card-body">
                  <div class="mb-3">
                    <label class="form-label">部署方式 <span class="text-danger">*</span></label>
                    <div class="btn-group w-100" role="group">
                      <input type="radio" class="btn-check" id="edit-deploy-run" v-model="editForm.deployMode" value="docker_run">
                      <label class="btn btn-outline-primary" for="edit-deploy-run">
                        <i class="fas fa-terminal me-1"></i> Docker Run
                      </label>
                      
                      <input type="radio" class="btn-check" id="edit-deploy-compose" v-model="editForm.deployMode" value="docker_compose">
                      <label class="btn btn-outline-primary" for="edit-deploy-compose">
                        <i class="fas fa-layer-group me-1"></i> Docker Compose
                      </label>
                      
                      <input type="radio" class="btn-check" id="edit-deploy-multi-step" v-model="editForm.deployMode" value="multi_step">
                      <label class="btn btn-outline-primary" for="edit-deploy-multi-step">
                        <i class="fas fa-list-ol me-1"></i> 多步骤
                      </label>
                    </div>
                  </div>

                  <!-- Docker Run 命令输入 -->
                  <div v-if="editForm.deployMode === 'docker_run'" class="mb-3">
                    <label class="form-label">Docker Run 命令 <span class="text-danger">*</span></label>
                    <textarea 
                      v-model="editForm.runCommand" 
                      class="form-control font-monospace" 
                      rows="6"
                      placeholder="-d --name my-app -p 8000:8000 registry.cn-hangzhou.aliyuncs.com/namespace/app:tag"
                    ></textarea>
                    <small class="text-muted">输入 docker run 的参数（可包含 "docker run" 前缀，系统会自动适配）</small>
                  </div>

                  <!-- Docker Compose 命令输入 -->
                  <div v-if="editForm.deployMode === 'docker_compose'" class="mb-3">
                    <label class="form-label">Docker Compose 命令 <span class="text-danger">*</span></label>
                    <input 
                      v-model="editForm.composeCommand" 
                      type="text" 
                      class="form-control font-monospace" 
                      placeholder="up -d"
                    >
                    <small class="text-muted">输入 docker-compose 命令参数（不包含 "docker-compose" 前缀，如：up -d）</small>
                  </div>

                  <div v-if="editForm.deployMode === 'docker_compose'" class="mb-3">
                    <label class="form-label">docker-compose.yml 内容 <span class="text-danger">*</span></label>
                    <textarea 
                      v-model="editForm.composeContent" 
                      class="form-control font-monospace" 
                      rows="15"
                      placeholder="version: '3.8'&#10;services:&#10;  app:&#10;    image: registry.cn-hangzhou.aliyuncs.com/namespace/app:tag&#10;    ports:&#10;      - '8000:8000'"
                    ></textarea>
                    <small class="text-muted">输入完整的 docker-compose.yml 内容</small>
                  </div>

                  <!-- 多步骤配置 -->
                  <div v-if="editForm.deployMode === 'multi_step'" class="mb-3">
                    <div class="d-flex justify-content-between align-items-center mb-2">
                      <div>
                        <label class="form-label mb-0">部署步骤 <span class="text-danger">*</span></label>
                        <small class="text-muted d-block">按顺序添加多个部署步骤，系统将依次执行</small>
                      </div>
                      <button type="button" class="btn btn-sm btn-outline-primary" @click="addEditStep">
                        <i class="fas fa-plus me-1"></i> 添加步骤
                      </button>
                    </div>
                    
                    <div v-if="editForm.steps.length === 0" class="alert alert-info mb-0">
                      <i class="fas fa-info-circle me-1"></i>
                      请至少添加一个部署步骤
                    </div>
                    
                    <div v-else class="steps-list">
                      <div 
                        v-for="(step, index) in editForm.steps" 
                        :key="index" 
                        class="card mb-2 step-card"
                        :class="{ 'border-primary': step.name || step.command }"
                      >
                        <div class="card-body">
                          <div class="d-flex justify-content-between align-items-start mb-2">
                            <div class="d-flex align-items-center">
                              <span class="badge bg-primary me-2" style="min-width: 60px;">步骤 {{ index + 1 }}</span>
                              <span v-if="step.name" class="text-muted small">{{ step.name }}</span>
                              <span v-else class="text-muted small fst-italic">未命名步骤</span>
                            </div>
                            <div class="btn-group btn-group-sm">
                              <button 
                                type="button" 
                                class="btn btn-outline-secondary" 
                                @click="moveEditStep(index, -1)"
                                :disabled="index === 0"
                                title="上移"
                              >
                                <i class="fas fa-arrow-up"></i>
                              </button>
                              <button 
                                type="button" 
                                class="btn btn-outline-secondary" 
                                @click="moveEditStep(index, 1)"
                                :disabled="index === editForm.steps.length - 1"
                                title="下移"
                              >
                                <i class="fas fa-arrow-down"></i>
                              </button>
                              <button 
                                type="button" 
                                class="btn btn-outline-danger" 
                                @click="removeEditStep(index)" 
                                title="删除步骤"
                              >
                                <i class="fas fa-trash"></i>
                              </button>
                            </div>
                          </div>
                          <div class="mb-2">
                            <label class="form-label small mb-1">步骤名称</label>
                            <input 
                              v-model="step.name" 
                              type="text" 
                              class="form-control form-control-sm" 
                              placeholder="例如：停止旧容器、拉取镜像、启动容器"
                            >
                          </div>
                          <div>
                            <label class="form-label small mb-1">执行命令</label>
                            <textarea 
                              v-model="step.command" 
                              class="form-control font-monospace form-control-sm" 
                              rows="4"
                              placeholder="docker stop my-app || true&#10;或&#10;docker pull registry.cn-hangzhou.aliyuncs.com/namespace/app:latest"
                            ></textarea>
                            <small class="text-muted">输入要执行的命令或脚本，支持多行</small>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="mb-0">
                    <div class="form-check form-switch">
                      <input 
                        class="form-check-input" 
                        type="checkbox" 
                        id="edit-redeploySwitch"
                        v-model="editForm.redeploy"
                      >
                      <label class="form-check-label" for="edit-redeploySwitch">
                        <i class="fas fa-redo me-1"></i> 重新发布（如果主机上已存在，先停止并删除）
                      </label>
                    </div>
                    <small class="text-muted">启用后，部署前会先停止并删除已有的容器或服务</small>
                  </div>
                </div>
              </div>
              
              <!-- 目标主机选择 -->
              <div class="mb-3">
                <label class="form-label">选择目标主机 <span class="text-danger">*</span></label>
                <small class="text-muted d-block mb-2">选择要部署到的主机，上述部署配置将应用到所有选中的主机</small>
                
                <!-- 主机类型筛选和搜索 -->
                <div class="mb-2">
                  <div class="btn-group btn-group-sm mb-2" role="group">
                    <input type="radio" class="btn-check" id="edit-filter-all" v-model="editHostFilter" value="all">
                    <label class="btn btn-outline-secondary" for="edit-filter-all">全部</label>
                    
                    <input type="radio" class="btn-check" id="edit-filter-agent" v-model="editHostFilter" value="agent">
                    <label class="btn btn-outline-secondary" for="edit-filter-agent">
                      <i class="fas fa-network-wired me-1"></i> Agent
                    </label>
                    
                    <input type="radio" class="btn-check" id="edit-filter-portainer" v-model="editHostFilter" value="portainer">
                    <label class="btn btn-outline-secondary" for="edit-filter-portainer">
                      <i class="fas fa-server me-1"></i> Portainer
                    </label>
                    
                    <input type="radio" class="btn-check" id="edit-filter-ssh" v-model="editHostFilter" value="ssh">
                    <label class="btn btn-outline-secondary" for="edit-filter-ssh">
                      <i class="fas fa-terminal me-1"></i> SSH
                    </label>
                  </div>
                  <div class="d-flex align-items-center gap-2">
                    <div class="form-check">
                      <input class="form-check-input" type="checkbox" id="edit-filter-online" v-model="editFilterOnlineOnly">
                      <label class="form-check-label" for="edit-filter-online">仅在线</label>
                    </div>
                    <input 
                      type="text" 
                      class="form-control form-control-sm flex-grow-1" 
                      v-model="editHostSearchKeyword"
                      placeholder="搜索主机名称..."
                    >
                  </div>
                </div>
                
                <!-- 主机列表（按类型分组） -->
                <div v-if="loadingHosts" class="text-muted small text-center py-3">
                  <span class="spinner-border spinner-border-sm me-2"></span>加载中...
                </div>
                <div v-else class="border rounded p-2" style="max-height: 300px; overflow-y: auto;">
                  <!-- Agent 主机 -->
                  <div v-if="editFilteredHostsByType.agent.length > 0" class="mb-3">
                    <div class="fw-bold text-primary mb-2">
                      <i class="fas fa-network-wired me-1"></i> Agent 主机 ({{ editFilteredHostsByType.agent.length }})
                    </div>
                    <div v-for="host in editFilteredHostsByType.agent" :key="host.host_id" class="form-check ms-3">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        :id="`edit-host-${host.host_id}`"
                        :value="host.host_id"
                        v-model="editForm.selectedHosts"
                      >
                      <label class="form-check-label" :for="`edit-host-${host.host_id}`">
                        {{ host.name }}
                        <span :class="getStatusBadgeClass(host.status)" class="badge ms-1">
                          {{ getStatusText(host.status) }}
                        </span>
                        <span v-if="host.description" class="text-muted small ms-1">({{ host.description }})</span>
                      </label>
                    </div>
                  </div>
                  
                  <!-- Portainer 主机 -->
                  <div v-if="editFilteredHostsByType.portainer.length > 0" class="mb-3">
                    <div class="fw-bold text-info mb-2">
                      <i class="fas fa-server me-1"></i> Portainer 主机 ({{ editFilteredHostsByType.portainer.length }})
                    </div>
                    <div v-for="host in editFilteredHostsByType.portainer" :key="host.host_id" class="form-check ms-3">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        :id="`edit-host-${host.host_id}`"
                        :value="host.host_id"
                        v-model="editForm.selectedHosts"
                      >
                      <label class="form-check-label" :for="`edit-host-${host.host_id}`">
                        {{ host.name }}
                        <span :class="getStatusBadgeClass(host.status)" class="badge ms-1">
                          {{ getStatusText(host.status) }}
                        </span>
                        <span v-if="host.portainer_url" class="text-muted small ms-1">({{ host.portainer_url }})</span>
                      </label>
                    </div>
                  </div>
                  
                  <!-- SSH 主机 -->
                  <div v-if="editFilteredHostsByType.ssh.length > 0" class="mb-3">
                    <div class="fw-bold text-warning mb-2">
                      <i class="fas fa-terminal me-1"></i> SSH 主机 ({{ editFilteredHostsByType.ssh.length }})
                    </div>
                    <div v-for="host in editFilteredHostsByType.ssh" :key="host.host_id" class="form-check ms-3">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        :id="`edit-host-${host.host_id}`"
                        :value="host.host_id"
                        v-model="editForm.selectedHosts"
                      >
                      <label class="form-check-label" :for="`edit-host-${host.host_id}`">
                        {{ host.name }}
                        <span v-if="host.docker_enabled" class="badge bg-info ms-1">Docker</span>
                        <span v-if="host.docker_version" class="text-muted small ms-1">({{ host.docker_version }})</span>
                        <span v-if="host.host" class="text-muted small ms-1">@{{ host.host }}:{{ host.port || 22 }}</span>
                      </label>
                    </div>
                  </div>
                  
                  <div v-if="editFilteredHosts.length === 0" class="text-muted small text-center py-3">
                    <i class="fas fa-inbox me-1"></i>
                    <span v-if="editHostSearchKeyword">未找到匹配的主机</span>
                    <span v-else>暂无可用主机，请先在"主机管理"中添加主机</span>
                  </div>
                </div>
                
                <!-- 已选择的主机统计 -->
                <div v-if="editForm.selectedHosts.length > 0" class="mt-2">
                  <small class="text-muted">
                    已选择 <strong>{{ editForm.selectedHosts.length }}</strong> 个主机
                    <button type="button" class="btn btn-link btn-sm p-0 ms-2" @click="editForm.selectedHosts = []">
                      清空
                    </button>
                  </small>
                </div>
              </div>
            </div>

            <!-- Webhook设置模式 -->
            <div v-if="editMode === 'webhook'">
              <div class="mb-3">
                <label class="form-label">Webhook Token（用于 URL）</label>
                <div class="input-group input-group-sm">
                  <input
                    v-model="editForm.webhook_token"
                    type="text"
                    class="form-control font-monospace"
                    placeholder="留空自动生成"
                  />
                  <button
                    class="btn btn-outline-secondary"
                    type="button"
                    @click="regenerateEditWebhookToken"
                    title="重新生成 Token"
                  >
                    <i class="fas fa-sync-alt"></i> 重新生成
                  </button>
                </div>
                <small class="text-muted">用于构建 Webhook URL，留空将自动生成 UUID</small>
              </div>
              <div class="mb-3">
                <label class="form-label">Webhook 密钥</label>
                <div class="input-group input-group-sm">
                  <input
                    v-model="editForm.webhook_secret"
                    type="text"
                    class="form-control font-monospace"
                    placeholder="留空自动生成"
                  />
                  <button
                    class="btn btn-outline-secondary"
                    type="button"
                    @click="regenerateEditWebhookSecret"
                    title="重新生成密钥"
                  >
                    <i class="fas fa-sync-alt"></i> 重新生成
                  </button>
                </div>
                <small class="text-muted">用于验证 Webhook 签名（可选）</small>
              </div>
              <div class="mb-3">
                <label class="form-label"><strong>Webhook 分支策略</strong></label>
                <div class="btn-group w-100 d-flex flex-wrap" role="group" style="gap: 0.25rem">
                  <input type="radio" class="btn-check" id="edit-strategy-use-push" value="use_push" v-model="editForm.webhook_branch_strategy" />
                  <label class="btn btn-outline-primary flex-fill" for="edit-strategy-use-push" style="white-space: normal; padding: 0.5rem">
                    <i class="fas fa-code-branch d-block mb-1"></i>
                    <small class="d-block fw-bold">使用推送分支</small>
                    <small class="text-muted d-block" style="font-size: 0.7rem">所有分支都触发</small>
                  </label>
                  <input type="radio" class="btn-check" id="edit-strategy-filter-match" value="filter_match" v-model="editForm.webhook_branch_strategy" />
                  <label class="btn btn-outline-primary flex-fill" for="edit-strategy-filter-match" style="white-space: normal; padding: 0.5rem">
                    <i class="fas fa-filter d-block mb-1"></i>
                    <small class="d-block fw-bold">只允许匹配分支</small>
                    <small class="text-muted d-block" style="font-size: 0.7rem">使用推送分支构建</small>
                  </label>
                  <input type="radio" class="btn-check" id="edit-strategy-use-configured" value="use_configured" v-model="editForm.webhook_branch_strategy" />
                  <label class="btn btn-outline-primary flex-fill" for="edit-strategy-use-configured" style="white-space: normal; padding: 0.5rem">
                    <i class="fas fa-cog d-block mb-1"></i>
                    <small class="d-block fw-bold">使用配置分支</small>
                    <small class="text-muted d-block" style="font-size: 0.7rem">所有分支都触发</small>
                  </label>
                  <input type="radio" class="btn-check" id="edit-strategy-select-branches" value="select_branches" v-model="editForm.webhook_branch_strategy" />
                  <label class="btn btn-outline-primary flex-fill" for="edit-strategy-select-branches" style="white-space: normal; padding: 0.5rem">
                    <i class="fas fa-check-square d-block mb-1"></i>
                    <small class="d-block fw-bold">选择分支触发</small>
                    <small class="text-muted d-block" style="font-size: 0.7rem">仅选中的分支触发</small>
                  </label>
                </div>
              </div>
              <div v-if="editForm.webhook_branch_strategy === 'select_branches'" class="mb-3">
                <label class="form-label">允许触发的分支</label>
                <input
                  v-model="editForm.webhook_allowed_branches_input"
                  type="text"
                  class="form-control"
                  placeholder="输入分支名称，多个分支用逗号分隔，如：main,dev,release"
                />
                <small class="text-muted">输入分支名称，多个分支用逗号分隔</small>
              </div>
              <div class="mb-3">
                <button type="button" class="btn btn-sm btn-outline-info" @click="showEditWebhookUrl">
                  <i class="fas fa-link me-1"></i> 查看 Webhook URL
                </button>
              </div>
            </div>

            <!-- YAML编辑模式 -->
            <div v-if="editMode === 'yaml' && editingTask">
              <div class="mb-3">
                <label class="form-label">YAML 配置内容</label>
                <textarea 
                  v-model="editingTask.config_content" 
                  class="form-control font-monospace" 
                  rows="20"
                  placeholder="请输入 deploy-config.yaml 格式的配置..."
                ></textarea>
              </div>
              <div class="row">
                <div class="col-md-6">
                  <label class="form-label">镜像仓库（可选）</label>
                  <input 
                    v-model="editingTask.registry" 
                    type="text" 
                    class="form-control" 
                    placeholder="docker.io"
                  >
                </div>
                <div class="col-md-6">
                  <label class="form-label">镜像标签（可选）</label>
                  <input 
                    v-model="editingTask.tag" 
                    type="text" 
                    class="form-control" 
                    placeholder="latest"
                  >
                </div>
              </div>
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

    <!-- Webhook URL 模态框 -->
    <div
      v-if="showWebhookModal"
      class="modal fade show"
      style="display: block; z-index: 1050"
      tabindex="-1"
    >
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"><i class="fas fa-link"></i> Webhook URL</h5>
            <button
              type="button"
              class="btn-close"
              @click="showWebhookModal = false"
            ></button>
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
                />
                <button
                  class="btn btn-outline-secondary btn-sm"
                  @click="copyWebhookUrlFromModal"
                >
                  <i class="fas fa-copy"></i> 复制
                </button>
              </div>
            </div>
            <div class="alert alert-info small mb-0">
              <strong>使用说明：</strong><br />
              1. 在 Git 平台（GitHub/GitLab/Gitee）的仓库设置中添加 Webhook<br />
              2. 将上述 URL 粘贴到 Payload URL 中<br />
              3. Content Type 选择 <code>application/json</code><br />
              4. Secret 填写部署配置的 Webhook 密钥（如果有）<br />
              5. 选择触发事件（通常是 Push events）
            </div>
          </div>
        </div>
      </div>
    </div>
    <div
      v-if="showWebhookModal"
      class="modal-backdrop fade show"
      style="z-index: 1045"
    ></div>
  </div>
</template>

<script>
import axios from 'axios';
import yaml from 'js-yaml';

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
      taskLogs: [],
      detailTab: 'config',
      editMode: 'form', // 编辑模式：'form', 'yaml', 'webhook'
      editHostFilter: 'all',
      editFilterOnlineOnly: true,
      editHostSearchKeyword: '',
      showWebhookModal: false, // Webhook URL 模态框显示状态
      webhookUrl: '', // Webhook URL
      editForm: {
        appName: '',
        selectedHosts: [],
        deployMode: 'docker_run',
        runCommand: '',
        composeCommand: '',
        composeContent: '',
        redeploy: false,
        webhook_token: '',
        webhook_secret: '',
        webhook_branch_strategy: 'use_push',
        webhook_allowed_branches: [],
        webhook_allowed_branches_input: ''
      },
      taskConfigContent: '',
      taskRegistry: '',
      taskTag: '',
      creating: false,
      agentHosts: [],
      sshHosts: [],
      loadingHosts: false,
      hostFilter: 'all', // all, agent, portainer, ssh
      filterOnlineOnly: true,
      hostSearchKeyword: '',
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
      },
      autoRefreshInterval: null  // 自动刷新定时器
    }
  },
  computed: {
    // 过滤后的主机列表
    filteredHosts() {
      let hosts = []
      
      // 合并所有类型的主机
      if (this.hostFilter === 'all' || this.hostFilter === 'agent' || this.hostFilter === 'portainer') {
        hosts = hosts.concat(this.agentHosts || [])
      }
      if (this.hostFilter === 'all' || this.hostFilter === 'ssh') {
        hosts = hosts.concat(this.sshHosts || [])
      }
      
      // 按类型过滤
      if (this.hostFilter === 'agent') {
        hosts = hosts.filter(h => h.host_type === 'agent')
      } else if (this.hostFilter === 'portainer') {
        hosts = hosts.filter(h => h.host_type === 'portainer')
      } else if (this.hostFilter === 'ssh') {
        // SSH 主机没有 host_type，通过其他方式识别
        hosts = hosts.filter(h => !h.host_type)
      }
      
      // 仅在线过滤
      if (this.filterOnlineOnly) {
        hosts = hosts.filter(h => {
          if (h.host_type) {
            // Agent 或 Portainer 主机
            return h.status === 'online'
          } else {
            // SSH 主机（总是显示，因为没有状态）
            return true
          }
        })
      }
      
      // 搜索过滤
      if (this.hostSearchKeyword) {
        const keyword = this.hostSearchKeyword.toLowerCase()
        hosts = hosts.filter(h => 
          h.name.toLowerCase().includes(keyword) ||
          (h.description && h.description.toLowerCase().includes(keyword)) ||
          (h.portainer_url && h.portainer_url.toLowerCase().includes(keyword)) ||
          (h.host && h.host.toLowerCase().includes(keyword))
        )
      }
      
      return hosts
    },
    // 按类型分组的主机
    filteredHostsByType() {
      const result = {
        agent: [],
        portainer: [],
        ssh: []
      }
      
      this.filteredHosts.forEach(host => {
        if (host.host_type === 'agent') {
          result.agent.push(host)
        } else if (host.host_type === 'portainer') {
          result.portainer.push(host)
        } else {
          result.ssh.push(host)
        }
      })
      
      return result
    },
    // 编辑表单过滤后的主机列表
    editFilteredHosts() {
      let hosts = []
      
      // 合并所有类型的主机
      if (this.editHostFilter === 'all' || this.editHostFilter === 'agent' || this.editHostFilter === 'portainer') {
        hosts = hosts.concat(this.agentHosts || [])
      }
      if (this.editHostFilter === 'all' || this.editHostFilter === 'ssh') {
        hosts = hosts.concat(this.sshHosts || [])
      }
      
      // 按类型过滤
      if (this.editHostFilter === 'agent') {
        hosts = hosts.filter(h => h.host_type === 'agent')
      } else if (this.editHostFilter === 'portainer') {
        hosts = hosts.filter(h => h.host_type === 'portainer')
      } else if (this.editHostFilter === 'ssh') {
        hosts = hosts.filter(h => !h.host_type)
      }
      
      // 仅在线过滤
      if (this.editFilterOnlineOnly) {
        hosts = hosts.filter(h => {
          if (h.host_type) {
            return h.status === 'online'
          } else {
            return true
          }
        })
      }
      
      // 搜索过滤
      if (this.editHostSearchKeyword) {
        const keyword = this.editHostSearchKeyword.toLowerCase()
        hosts = hosts.filter(h => 
          h.name.toLowerCase().includes(keyword) ||
          (h.description && h.description.toLowerCase().includes(keyword)) ||
          (h.portainer_url && h.portainer_url.toLowerCase().includes(keyword)) ||
          (h.host && h.host.toLowerCase().includes(keyword))
        )
      }
      
      return hosts
    },
    // 编辑表单按类型分组的主机
    editFilteredHostsByType() {
      const result = {
        agent: [],
        portainer: [],
        ssh: []
      }
      
      this.editFilteredHosts.forEach(host => {
        if (host.host_type === 'agent') {
          result.agent.push(host)
        } else if (host.host_type === 'portainer') {
          result.portainer.push(host)
        } else {
          result.ssh.push(host)
        }
      })
      
      return result
    }
  },
  mounted() {
    this.loadTasks()
    this.loadAgentHosts()
    this.loadSSHHosts()
  },
  beforeUnmount() {
    // 清理资源（如果有自动刷新定时器，在这里清理）
    if (this.autoRefreshInterval) {
      clearInterval(this.autoRefreshInterval)
      this.autoRefreshInterval = null
    }
  },
  methods: {
    stopAutoRefresh() {
      // 停止自动刷新（兼容性方法）
      if (this.autoRefreshInterval) {
        clearInterval(this.autoRefreshInterval)
        this.autoRefreshInterval = null
      }
    },
    async loadTasks() {
      this.loading = true
      try {
        const res = await axios.get('/api/deploy-tasks')
        // 适配新的数据结构：后端返回的tasks已经是格式化后的
        this.tasks = (res.data.tasks || []).map(task => {
          // 确保数据结构一致
          return {
            ...task,
            status: task.status?.status || task.status || 'pending',
            config: task.config || task.task_config?.config || {},
            config_content: task.config_content || task.task_config?.config_content || '',
            execution_count: task.execution_count || 0,
            last_executed_at: task.last_executed_at || null
          }
        })
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
      if (!confirm('确定要触发此部署配置吗？\n\n触发后将创建新的部署任务，可在"任务管理"页面查看执行情况。')) return
      
      try {
        const res = await axios.post(`/api/deploy-tasks/${task.task_id}/execute`)
        const newTaskId = res.data.task_id
        alert(`部署配置已触发！\n\n新任务ID: ${newTaskId.substring(0, 8)}\n可在"任务管理"页面查看执行情况。`)
        this.loadTasks()
        if (this.showDetailModal) {
          this.viewTask(task)
        }
      } catch (error) {
        console.error('触发部署配置失败:', error)
        alert('触发部署配置失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    viewExecutions(task) {
      // 跳转到任务管理页面，筛选该配置的任务
      const configId = task.task_id
      sessionStorage.setItem('deployConfigFilter', configId)
      window.location.href = '/#/tasks?deploy_config=' + configId
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
        const taskData = res.data.task
        // 适配新的数据结构
        this.selectedTask = {
          ...taskData,
          status: taskData.status?.status || taskData.status || 'pending',
          config: taskData.config || taskData.task_config?.config || {},
          config_content: taskData.config_content || taskData.task_config?.config_content || '',
          created_at: taskData.created_at || taskData.status?.created_at,
          completed_at: taskData.completed_at || taskData.status?.completed_at,
          error: taskData.error
        }
        this.detailTab = 'config'
        this.showDetailModal = true
        
        // 加载任务日志
        await this.loadTaskLogs(task.task_id)
      } catch (error) {
        console.error('获取任务详情失败:', error)
        alert('获取任务详情失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async loadTaskLogs(taskId) {
      try {
        // 从任务管理API获取日志（部署任务现在也使用统一的任务管理）
        const res = await axios.get(`/api/tasks/${taskId}`)
        this.taskLogs = res.data.logs || []
      } catch (error) {
        console.error('加载任务日志失败:', error)
        this.taskLogs = []
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
    async loadSSHHosts() {
      try {
        const res = await axios.get('/api/hosts')
        this.sshHosts = res.data.hosts || []
      } catch (error) {
        console.error('加载 SSH 主机列表失败:', error)
        // SSH 主机加载失败不影响使用
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

      // 将命令转换为统一的YAML配置格式（新格式）
      // 新格式：统一的deploy配置 + targets列表
      const targets = []
      for (const hostId of this.simpleForm.selectedHosts) {
        // 在所有主机列表中查找（包括 Agent、Portainer 和 SSH）
        const host = [...this.agentHosts, ...this.sshHosts].find(h => h.host_id === hostId)
        if (!host) continue
        
        // 确定主机类型
        let hostType = 'agent'
        if (host.host_type === 'portainer') {
          hostType = 'portainer'
        } else if (host.host_type === 'agent') {
          hostType = 'agent'
        } else {
          hostType = 'ssh'
        }

        targets.push({
          name: `${host.name}-deploy`,
          host_type: hostType,
          host_name: host.name
        })
      }

      // 构建统一的deploy配置
      let deployConfig = {}
      
      if (this.simpleForm.deployMode === 'multi_step') {
        // 多步骤模式
        deployConfig = {
          steps: this.simpleForm.steps.map(step => ({
            name: step.name.trim(),
            command: step.command.trim()
          }))
        }
      } else {
        // 单命令模式
        deployConfig = {
          type: this.simpleForm.deployMode === 'docker_compose' ? 'docker_compose' : 'docker_run',
          command: this.simpleForm.deployMode === 'docker_run' 
            ? this.simpleForm.runCommand.trim()
            : this.simpleForm.composeCommand.trim()
        }

        if (this.simpleForm.deployMode === 'docker_compose') {
          deployConfig.compose_content = this.simpleForm.composeContent.trim()
        }
      }

      if (this.simpleForm.redeploy) {
        deployConfig.redeploy = true
      }

      const yamlConfig = {
        version: '1.0',
        app: {
          name: this.simpleForm.appName
        },
        deploy: deployConfig,
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
        composeContent: '',
        redeploy: false,
        steps: []
      }
    },
    addStep() {
      this.simpleForm.steps.push({
        name: '',
        command: ''
      })
    },
    removeStep(index) {
      this.simpleForm.steps.splice(index, 1)
    },
    moveStep(index, direction) {
      // direction: -1 上移, 1 下移
      if (direction === -1 && index > 0) {
        const temp = this.simpleForm.steps[index]
        this.simpleForm.steps[index] = this.simpleForm.steps[index - 1]
        this.simpleForm.steps[index - 1] = temp
      } else if (direction === 1 && index < this.simpleForm.steps.length - 1) {
        const temp = this.simpleForm.steps[index]
        this.simpleForm.steps[index] = this.simpleForm.steps[index + 1]
        this.simpleForm.steps[index + 1] = temp
      }
    },
    addEditStep() {
      this.editForm.steps.push({
        name: '',
        command: ''
      })
    },
    removeEditStep(index) {
      if (confirm(`确定要删除步骤 ${index + 1} 吗？`)) {
        this.editForm.steps.splice(index, 1)
      }
    },
    moveEditStep(index, direction) {
      // direction: -1 上移, 1 下移
      if (direction === -1 && index > 0) {
        const temp = this.editForm.steps[index]
        this.editForm.steps[index] = this.editForm.steps[index - 1]
        this.editForm.steps[index - 1] = temp
      } else if (direction === 1 && index < this.editForm.steps.length - 1) {
        const temp = this.editForm.steps[index]
        this.editForm.steps[index] = this.editForm.steps[index + 1]
        this.editForm.steps[index + 1] = temp
      }
    },
    switchToYamlMode() {
      // 切换到YAML模式时，确保 editingTask 有正确的数据
      if (!this.editingTask) {
        return
      }
      // 确保 registry 和 tag 字段存在
      if (this.editingTask.registry === undefined || this.editingTask.registry === null) {
        this.editingTask.registry = ''
      }
      if (this.editingTask.tag === undefined || this.editingTask.tag === null) {
        this.editingTask.tag = ''
      }
      this.editMode = 'yaml'
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
        // 确保 editingTask 对象完整初始化，包括 registry 和 tag
        // 后端返回的数据结构：task.config_content 或 task.task_config.config_content
        const configContent = taskData.config_content || (taskData.task_config && taskData.task_config.config_content) || ''
        const taskConfig = taskData.task_config || {}
        this.editingTask = {
          task_id: taskData.task_id,
          config_content: configContent,
          registry: (taskData.status && taskData.status.registry) || taskConfig.registry || '',
          tag: (taskData.status && taskData.status.tag) || taskConfig.tag || '',
          webhook_token: taskData.webhook_token || '',
          webhook_secret: taskData.webhook_secret || '',
          webhook_branch_strategy: taskData.webhook_branch_strategy || 'use_push',
          webhook_allowed_branches: taskData.webhook_allowed_branches || []
        }
        
        // 先加载主机列表（解析表单时需要主机列表）
        await this.loadAgentHosts()
        await this.loadSSHHosts()
        
        // 先保存webhook配置（因为parseYamlToForm会重置editForm）
        const savedWebhookToken = taskData.webhook_token || ''
        const savedWebhookSecret = taskData.webhook_secret || ''
        const savedWebhookBranchStrategy = taskData.webhook_branch_strategy || 'use_push'
        const savedWebhookAllowedBranches = taskData.webhook_allowed_branches || []
        
        // 解析YAML配置到表单
        const config = taskData.config || taskConfig.config || {}
        this.parseYamlToForm(configContent, config)
        
        // 恢复webhook配置（必须在parseYamlToForm之后）
        this.editForm.webhook_token = savedWebhookToken
        this.editForm.webhook_secret = savedWebhookSecret
        this.editForm.webhook_branch_strategy = savedWebhookBranchStrategy
        this.editForm.webhook_allowed_branches = savedWebhookAllowedBranches
        this.editForm.webhook_allowed_branches_input = savedWebhookAllowedBranches.join(',')
        
        console.log('加载webhook配置:', {
          webhook_token: savedWebhookToken ? savedWebhookToken.substring(0, 8) + '...' : '(空)',
          webhook_secret: savedWebhookSecret ? '***' : '(空)',
          webhook_branch_strategy: savedWebhookBranchStrategy,
          webhook_allowed_branches: savedWebhookAllowedBranches
        })
        
        this.showEditModal = true
        this.editMode = 'form' // 默认使用表单编辑
        // 如果详情模态框打开，先关闭它
        if (this.showDetailModal) {
          this.showDetailModal = false
        }
      } catch (error) {
        console.error('获取任务详情失败:', error)
        alert('获取任务详情失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    parseYamlToForm(configContent, config) {
      // 重置表单
      this.editForm = {
        appName: '',
        selectedHosts: [],
        deployMode: 'docker_run',
        runCommand: '',
        composeCommand: '',
        composeContent: '',
        redeploy: false,
        steps: [],
        webhook_token: '',
        webhook_secret: '',
        webhook_branch_strategy: 'use_push',
        webhook_allowed_branches: [],
        webhook_allowed_branches_input: ''
      }
      
      if (!config) {
        try {
          config = yaml.load(configContent)
        } catch (e) {
          console.error('解析YAML失败:', e)
          return
        }
      }
      
      // 解析应用名称
      if (config.app && config.app.name) {
        this.editForm.appName = config.app.name
      }
      
      // 解析部署配置（新格式优先，向后兼容旧格式）
      let deployConfig = config.deploy
      if (!deployConfig) {
        // 旧格式：从第一个target的docker配置提取
        const targets = config.targets || []
        if (targets.length > 0) {
          const firstTarget = targets[0]
          const dockerConfig = firstTarget.docker || {}
          const deployMode = dockerConfig.deploy_mode || 'docker_run'
          deployConfig = {
            type: deployMode === 'docker_compose' ? 'docker_compose' : 'docker_run',
            command: dockerConfig.command || ''
          }
          if (deployMode === 'docker_compose') {
            deployConfig.compose_content = dockerConfig.compose_content || ''
          }
          if (dockerConfig.redeploy) {
            deployConfig.redeploy = true
          }
        }
      }
      
      if (deployConfig) {
        // 判断是否为多步骤模式
        if (deployConfig.steps && Array.isArray(deployConfig.steps)) {
          // 多步骤模式
          this.editForm.deployMode = 'multi_step'
          this.editForm.steps = deployConfig.steps.map(step => ({
            name: step.name || '',
            command: step.command || ''
          }))
        } else {
          // 单命令模式
          this.editForm.deployMode = deployConfig.type === 'docker_compose' ? 'docker_compose' : 'docker_run'
          
          // 解析部署命令和内容
          if (this.editForm.deployMode === 'docker_run') {
            this.editForm.runCommand = deployConfig.command || ''
          } else {
            this.editForm.composeCommand = deployConfig.command || 'up -d'
            this.editForm.composeContent = deployConfig.compose_content || ''
          }
        }
        
        this.editForm.redeploy = deployConfig.redeploy || false
      }
      
      // 解析目标主机
      const targets = config.targets || []
      const selectedHostIds = []
      for (const target of targets) {
        let hostName = null
        
        // 新格式：使用host_type和host_name
        if (target.host_type && target.host_name) {
          hostName = target.host_name
        }
        // 旧格式：向后兼容
        else if (target.mode === 'agent' && target.agent && target.agent.name) {
          hostName = target.agent.name
        } else if (target.mode === 'ssh' && target.host) {
          hostName = target.host
        }
        
        if (hostName) {
          // 在所有主机列表中查找匹配的主机
          const allHosts = [...this.agentHosts, ...this.sshHosts]
          const host = allHosts.find(h => h.name === hostName)
          if (host && host.host_id) {
            selectedHostIds.push(host.host_id)
          }
        }
      }
      this.editForm.selectedHosts = selectedHostIds
    },
    async saveEditTask() {
      let yamlContent = ''
      const registry = this.editingTask.registry || null
      const tag = this.editingTask.tag || null
      
      if (this.editMode === 'form') {
        // 表单模式：验证并转换为YAML
        if (!this.editForm.appName.trim()) {
          alert('请输入应用名称')
          return
        }
        if (this.editForm.selectedHosts.length === 0) {
          alert('请至少选择一个目标主机')
          return
        }
        if (this.editForm.deployMode === 'docker_run' && !this.editForm.runCommand.trim()) {
          alert('请输入 Docker Run 命令')
          return
        }
        if (this.editForm.deployMode === 'docker_compose') {
          if (!this.editForm.composeCommand.trim()) {
            alert('请输入 Docker Compose 命令')
            return
          }
          if (!this.editForm.composeContent.trim()) {
            alert('请输入 docker-compose.yml 内容')
            return
          }
        }
        if (this.editForm.deployMode === 'multi_step') {
          if (this.editForm.steps.length === 0) {
            alert('请至少添加一个部署步骤')
            return
          }
          for (let i = 0; i < this.editForm.steps.length; i++) {
            const step = this.editForm.steps[i]
            if (!step.name || !step.name.trim()) {
              alert(`步骤 ${i + 1} 的名称不能为空`)
              return
            }
            if (!step.command || !step.command.trim()) {
              alert(`步骤 ${i + 1} 的命令不能为空`)
              return
            }
          }
        }
        
        // 将表单数据转换为YAML
        yamlContent = this.formToYaml(this.editForm)
      } else {
        // YAML模式：直接使用YAML内容
        if (!this.editingTask.config_content || !this.editingTask.config_content.trim()) {
          alert('YAML 配置内容不能为空')
          return
        }
        yamlContent = this.editingTask.config_content
      }
      
      if (!confirm('确定要保存修改吗？')) {
        return
      }
      
      this.creating = true
      try {
        // 处理webhook允许的分支列表
        let webhook_allowed_branches = []
        if (this.editForm.webhook_branch_strategy === 'select_branches' && this.editForm.webhook_allowed_branches_input) {
          webhook_allowed_branches = this.editForm.webhook_allowed_branches_input
            .split(',')
            .map(b => b.trim())
            .filter(b => b)
        }

        // 更新现有任务
        // 处理webhook字段：editForm中已经加载了webhook配置，直接使用
        // 确保webhook_token不为undefined，如果为空字符串则让后端生成新token
        const webhookToken = this.editForm.webhook_token !== undefined && this.editForm.webhook_token !== null
          ? this.editForm.webhook_token
          : ''
        const webhookSecret = this.editForm.webhook_secret !== undefined && this.editForm.webhook_secret !== null
          ? this.editForm.webhook_secret
          : ''
        const webhookBranchStrategy = this.editForm.webhook_branch_strategy || 'use_push'
        
        console.log('保存webhook配置:', {
          webhook_token: webhookToken ? webhookToken.substring(0, 8) + '...' : '(空，将生成)',
          webhook_secret: webhookSecret ? '***' : '(空)',
          webhook_branch_strategy: webhookBranchStrategy,
          webhook_allowed_branches: webhook_allowed_branches
        })
        
        await axios.put(`/api/deploy-tasks/${this.editingTask.task_id}`, {
          config_content: yamlContent,
          registry: registry,
          tag: tag,
          webhook_token: webhookToken,
          webhook_secret: webhookSecret,
          webhook_branch_strategy: webhookBranchStrategy,
          webhook_allowed_branches: webhook_allowed_branches.length > 0 
            ? webhook_allowed_branches 
            : (webhookBranchStrategy === 'select_branches' ? [] : null)
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
    formToYaml(form) {
      // 将表单数据转换为YAML配置（新格式）
      const targets = []
      for (const hostId of form.selectedHosts) {
        const host = [...this.agentHosts, ...this.sshHosts].find(h => h.host_id === hostId)
        if (!host) continue
        
        // 确定主机类型
        let hostType = 'agent'
        if (host.host_type === 'portainer') {
          hostType = 'portainer'
        } else if (host.host_type === 'agent') {
          hostType = 'agent'
        } else {
          hostType = 'ssh'
        }

        targets.push({
          name: `${host.name}-deploy`,
          host_type: hostType,
          host_name: host.name
        })
      }

      // 构建统一的deploy配置
      let deployConfig = {}
      
      if (form.deployMode === 'multi_step') {
        // 多步骤模式
        deployConfig = {
          steps: form.steps.map(step => ({
            name: step.name.trim(),
            command: step.command.trim()
          }))
        }
      } else {
        // 单命令模式
        deployConfig = {
          type: form.deployMode === 'docker_compose' ? 'docker_compose' : 'docker_run',
          command: form.deployMode === 'docker_run' 
            ? form.runCommand.trim()
            : form.composeCommand.trim()
        }

        if (form.deployMode === 'docker_compose') {
          deployConfig.compose_content = form.composeContent.trim()
        }
      }

      if (form.redeploy) {
        deployConfig.redeploy = true
      }

      const yamlConfig = {
        version: '1.0',
        app: {
          name: form.appName
        },
        deploy: deployConfig,
        targets: targets
      }

      return yaml.dump(yamlConfig, {
        defaultFlowStyle: false,
        allowUnicode: true
      })
    },
    async copyTask(task) {
      // 显示确认提示
      // 尝试多种方式获取应用名称
      let appName = '未知任务'
      if (task.config && task.config.app && task.config.app.name) {
        appName = task.config.app.name
      } else if (task.status && task.status.app_name) {
        appName = task.status.app_name
      } else if (task.task_id) {
        appName = `任务 ${task.task_id.substring(0, 8)}`
      }
      
      // 显示确认对话框
      const confirmed = window.confirm(
        `确定要克隆部署任务 "${appName}" 吗？\n\n` +
        `克隆后将创建一个新的任务，使用相同的配置。\n\n` +
        `点击"确定"继续，点击"取消"放弃。`
      )
      
      if (!confirmed) {
        return
      }
      
      try {
        const res = await axios.get(`/api/deploy-tasks/${task.task_id}`)
        const taskData = res.data.task
        
        // 创建新任务（使用相同的配置）
        const configContent = taskData.config_content || (taskData.task_config && taskData.task_config.config_content) || ''
        const taskConfig = taskData.task_config || {}
        const createRes = await axios.post('/api/deploy-tasks', {
          config_content: configContent,
          registry: (taskData.status && taskData.status.registry) || taskConfig.registry || null,
          tag: (taskData.status && taskData.status.tag) || taskConfig.tag || null
        })
        
        alert('任务克隆成功！\n\n已创建新的部署任务，您可以对其进行编辑和执行。')
        this.loadTasks()
        
        // 如果详情模态框打开，刷新显示
        if (this.showDetailModal && this.selectedTask?.task_id === task.task_id) {
          // 可以选择打开新任务或保持当前任务
        }
      } catch (error) {
        console.error('复制任务失败:', error)
        alert('克隆任务失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async refreshTask(task) {
      // 刷新任务状态
      await this.loadTasks()
      // 如果详情模态框打开，重新加载任务详情和日志
      if (this.showDetailModal && this.selectedTask?.task_id === task.task_id) {
        await this.viewTask(task)
      }
    },
    formatLogMessage(message) {
      // 格式化日志消息，支持简单的HTML标记
      if (!message) return ''
      // 转义HTML，但保留换行
      return message
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>')
    },
    getLogLineClass(log) {
      // 根据日志消息内容返回样式类
      // log可能是字符串或对象
      const message = typeof log === 'string' ? log : (log.log_message || log.message || '')
      if (!message) return ''
      const msg = message.toLowerCase()
      if (msg.includes('错误') || msg.includes('error') || msg.includes('失败') || msg.includes('failed') || msg.includes('❌')) {
        return 'text-danger'
      }
      if (msg.includes('成功') || msg.includes('success') || msg.includes('完成') || msg.includes('completed') || msg.includes('✅')) {
        return 'text-success'
      }
      if (msg.includes('警告') || msg.includes('warning') || msg.includes('⚠️')) {
        return 'text-warning'
      }
      if (msg.includes('信息') || msg.includes('info') || msg.includes('📦') || msg.includes('🚀')) {
        return 'text-info'
      }
      return 'text-light'
    },
    generateUUID() {
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0
        const v = c === 'x' ? r : (r & 0x3 | 0x8)
        return v.toString(16)
      })
    },
    regenerateEditWebhookToken() {
      if (confirm('确定要重新生成 Webhook Token 吗？重新生成后需要更新外部系统的 Webhook URL。')) {
        this.editForm.webhook_token = this.generateUUID()
      }
    },
    regenerateEditWebhookSecret() {
      if (confirm('确定要重新生成 Webhook Secret 吗？重新生成后需要更新外部系统的 Webhook Secret。')) {
        this.editForm.webhook_secret = this.generateUUID()
      }
    },
    showEditWebhookUrl() {
      const token = this.editForm.webhook_token || '未设置'
      const baseUrl = window.location.origin.replace(':3000', ':8000').replace(':5173', ':8000')
      this.webhookUrl = token !== '未设置' ? `${baseUrl}/api/webhook/deploy/${token}` : '请先设置 Webhook Token'
      this.showWebhookModal = true
    },
    getWebhookUrl(task) {
      const token = task.webhook_token
      if (!token) return ''
      // 使用后端API的URL（通常是8000端口），而不是前端开发服务器的URL
      // 如果前端和后端在同一域名下，使用window.location.origin
      // 否则需要配置后端URL
      const baseUrl = window.location.origin.replace(':3000', ':8000').replace(':5173', ':8000')
      return `${baseUrl}/api/webhook/deploy/${token}`
    },
    copyWebhookUrl(task) {
      const url = this.getWebhookUrl(task)
      if (!url) {
        alert('Webhook URL 未配置')
        return
      }
      // 复制到剪贴板
      navigator.clipboard.writeText(url).then(() => {
        alert('Webhook URL 已复制到剪贴板')
      }).catch(() => {
        // 降级方案：使用传统方法
        const textarea = document.createElement('textarea')
        textarea.value = url
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        try {
          document.execCommand('copy')
          alert('Webhook URL 已复制到剪贴板')
        } catch (err) {
          alert('复制失败，请手动复制：\n\n' + url)
        }
        document.body.removeChild(textarea)
      })
    },
    showWebhookUrl(task) {
      const url = this.getWebhookUrl(task)
      if (!url) {
        alert('Webhook URL 未配置，请在编辑配置的"Webhook设置"tab中配置。')
        return
      }
      this.webhookUrl = url
      this.showWebhookModal = true
    },
    copyWebhookUrlFromModal() {
      if (this.$refs.webhookUrlInput) {
        this.$refs.webhookUrlInput.select()
        document.execCommand('copy')
        alert('Webhook URL 已复制到剪贴板')
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


<template>
  <div class="agent-host-manager-panel">
    <!-- 标签页切换 -->
    <div class="card mb-3">
      <div class="card-body p-2">
        <ul class="nav nav-tabs nav-tabs-custom mb-0" role="tablist">
          <li class="nav-item" role="presentation">
            <button 
              class="nav-link" 
              :class="{ active: activeTab === 'hosts' }"
              @click="activeTab = 'hosts'"
              type="button"
            >
              <i class="fas fa-server me-1"></i> 主机列表
            </button>
          </li>
          <li class="nav-item" role="presentation">
            <button 
              class="nav-link" 
              :class="{ active: activeTab === 'secrets' }"
              @click="activeTab = 'secrets'"
              type="button"
            >
              <i class="fas fa-key me-1"></i> 密钥管理
            </button>
          </li>
          <li class="nav-item" role="presentation">
            <button 
              class="nav-link" 
              :class="{ active: activeTab === 'pending' }"
              @click="activeTab = 'pending'"
              type="button"
            >
              <i class="fas fa-clock me-1"></i> 待加入主机
              <span v-if="pendingHostsCount > 0" class="badge bg-danger ms-1">{{ pendingHostsCount }}</span>
            </button>
          </li>
        </ul>
      </div>
    </div>

    <!-- 主机列表标签页 -->
    <div v-show="activeTab === 'hosts'">
      <!-- 主机类型筛选器和添加按钮 -->
      <div class="card mb-3">
        <div class="card-body py-2">
          <div class="d-flex justify-content-between align-items-center">
            <div class="btn-group" role="group">
              <input
                type="radio"
                class="btn-check"
                id="filter-all"
                value="all"
                v-model="filterType"
              />
              <label class="btn btn-outline-secondary btn-sm" for="filter-all">
                <i class="fas fa-list me-1"></i> 全部
              </label>

              <input
                type="radio"
                class="btn-check"
                id="filter-ssh"
                value="ssh"
                v-model="filterType"
              />
              <label class="btn btn-outline-secondary btn-sm" for="filter-ssh">
                <i class="fas fa-server me-1"></i> SSH主机
              </label>

              <input
                type="radio"
                class="btn-check"
                id="filter-agent"
                value="agent"
                v-model="filterType"
              />
              <label class="btn btn-outline-secondary btn-sm" for="filter-agent">
                <i class="fas fa-network-wired me-1"></i> Agent主机
              </label>
            </div>
            
            <!-- 添加主机按钮 -->
            <div class="d-flex gap-2" v-if="filterType === 'all' || filterType === 'agent'">
              <div class="btn-group" v-if="filterType === 'all'">
                <button class="btn btn-primary btn-sm" @click="showSshAddModal">
                  <i class="fas fa-plus me-1"></i> 添加SSH主机
                </button>
              </div>
              <div class="btn-group">
                <button 
                  type="button" 
                  class="btn btn-primary btn-sm dropdown-toggle" 
                  data-bs-toggle="dropdown" 
                  aria-expanded="false"
                >
                  <i class="fas fa-plus me-1"></i> 添加主机
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                  <li v-if="filterType === 'all'">
                    <a class="dropdown-item" href="#" @click.prevent="showSshAddModal">
                      <i class="fas fa-server me-2"></i> SSH主机
                    </a>
                  </li>
                  <li>
                    <a class="dropdown-item" href="#" @click.prevent="openAddModal('agent')">
                      <i class="fas fa-network-wired me-2"></i> Agent主机
                    </a>
                  </li>
                  <li>
                    <a class="dropdown-item" href="#" @click.prevent="openAddModal('portainer')">
                      <i class="fab fa-docker me-2"></i> Portainer主机
                    </a>
                  </li>
                </ul>
              </div>
            </div>
            <div class="d-flex gap-2" v-else-if="filterType === 'ssh'">
              <button class="btn btn-primary btn-sm" @click="showSshAddModal">
                <i class="fas fa-plus me-1"></i> 添加SSH主机
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 统一显示所有主机（当filterType为all时） -->
      <template v-if="filterType === 'all'">
        <div v-if="allHostsLoading" class="text-center py-5">
          <span class="spinner-border spinner-border-sm"></span> 加载中...
        </div>
        <div v-else-if="allHosts.length === 0" class="text-center py-5 text-muted">
          <i class="fas fa-server fa-3x mb-3"></i>
          <p class="mb-0">暂无主机</p>
        </div>
        <div v-else class="row g-4">
          <div
            v-for="host in allHosts"
            :key="`${host.host_type || 'ssh'}-${host.host_id}`"
            class="col-12 col-md-6 col-xl-4"
          >
            <!-- SSH主机卡片 -->
            <div v-if="!host.host_type || host.host_type === 'ssh'" class="card h-100 shadow-sm">
              <div class="card-header bg-white">
                <div class="mb-2">
                  <h5 class="card-title mb-1">
                    <strong>{{ host.name }}</strong>
                  </h5>
                  <div class="small text-muted mb-1">
                    <i class="fas fa-network-wired me-1"></i>{{ host.host }}<span class="ms-1">:{{ host.port }}</span>
                  </div>
                  <div class="d-flex align-items-center justify-content-between mb-1">
                    <div>
                      <span class="badge bg-secondary">
                        <i class="fas fa-server"></i> SSH主机
                      </span>
                      <span v-if="host.has_private_key" class="badge bg-info ms-1">
                        <i class="fas fa-key"></i> 密钥
                      </span>
                      <span v-else-if="host.has_password" class="badge bg-secondary ms-1">
                        <i class="fas fa-lock"></i> 密码
                      </span>
                    </div>
                  </div>
                  <p class="text-muted mb-0 mt-1" v-if="host.description" style="font-size: 0.9rem">
                    {{ host.description }}
                  </p>
                </div>
                <div class="btn-group btn-group-sm w-100">
                  <button class="btn btn-outline-info" @click="handleSshHostAction('test', host)" title="测试连接">
                    <i class="fas fa-plug"></i>
                  </button>
                  <button class="btn btn-outline-primary" @click="handleSshHostAction('edit', host)" title="编辑">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button class="btn btn-outline-danger" @click="handleSshHostAction('delete', host)" title="删除">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </div>
              <div class="card-body">
                <div class="mb-3">
                  <div class="d-flex align-items-center mb-2">
                    <i class="fas fa-user text-muted me-2" style="width: 18px;"></i>
                    <div class="flex-grow-1 small text-muted">
                      {{ host.username }}
                    </div>
                  </div>
                </div>
                <div v-if="host.docker_version" class="mb-3">
                  <span class="badge bg-success">
                    <i class="fab fa-docker me-1"></i>Docker可用
                  </span>
                  <div class="small text-muted mt-1">
                    Docker {{ host.docker_version }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Agent主机卡片 -->
            <div v-else class="card h-100 shadow-sm">
              <div class="card-header bg-white">
                <div class="mb-2">
                  <h5 class="card-title mb-1">
                    <strong>{{ host.name }}</strong>
                  </h5>
                  <div v-if="host.host_info && host.host_info.ip" class="small text-muted mb-1">
                    <i class="fas fa-network-wired me-1"></i>{{ host.host_info.ip }}
                  </div>
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
                  <p class="text-muted mb-0 mt-1" v-if="host.description" style="font-size: 0.9rem">
                    {{ host.description }}
                  </p>
                </div>
                <div class="btn-group btn-group-sm w-100">
                  <button class="btn btn-outline-info" @click="viewHost(host)" title="查看详情">
                    <i class="fas fa-info-circle"></i>
                  </button>
                  <button class="btn btn-outline-primary" @click="editHost(host)" title="编辑">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button class="btn btn-outline-danger" @click="deleteHost(host)" title="删除">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </div>
              <div class="card-body">
                <div v-if="host.host_info && Object.keys(host.host_info).length > 0" class="mb-3">
                  <div class="d-flex align-items-center mb-2">
                    <i class="fas fa-desktop text-muted me-2" style="width: 18px;"></i>
                    <div class="flex-grow-1">
                      <div class="small text-muted" v-if="host.host_info.os">
                        <i class="fas fa-desktop me-1"></i>{{ host.host_info.os }}
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="host.docker_info && Object.keys(host.docker_info).length > 0" class="mb-3">
                  <span v-if="host.docker_info.version" class="badge bg-info">
                    <i class="fab fa-docker me-1"></i>{{ host.docker_info.version }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 单独显示SSH或Agent主机 -->
      <template v-else>
        <!-- SSH主机管理 -->
        <HostManager v-if="filterType === 'ssh'" ref="hostManager" :filterType="filterType" />
        
        <!-- Agent主机列表 -->
        <div v-if="filterType === 'agent'">
          <!-- Agent主机列表 - 卡片式布局 -->
          <div v-if="loading" class="text-center py-5">
            <span class="spinner-border spinner-border-sm"></span> 加载中...
          </div>
          <div v-else-if="filteredHosts.length === 0" class="text-center py-5 text-muted">
            <i class="fas fa-network-wired fa-3x mb-3"></i>
            <p class="mb-0">暂无Agent主机</p>
            <div class="btn-group mt-2">
              <button 
                type="button" 
                class="btn btn-primary btn-sm dropdown-toggle" 
                data-bs-toggle="dropdown" 
                aria-expanded="false"
              >
                <i class="fas fa-plus me-1"></i> 添加主机
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li>
                  <a class="dropdown-item" href="#" @click.prevent="openAddModal('agent')">
                    <i class="fas fa-network-wired me-2"></i> Agent主机
                  </a>
                </li>
                <li>
                  <a class="dropdown-item" href="#" @click.prevent="openAddModal('portainer')">
                    <i class="fab fa-docker me-2"></i> Portainer主机
                  </a>
                </li>
              </ul>
            </div>
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
        </div>
      </template>
    </div>

    <!-- 密钥管理标签页 -->
    <div v-show="activeTab === 'secrets'">
      <div class="card mb-3">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-center">
            <h6 class="mb-0"><i class="fas fa-key me-2"></i>Agent连接密钥</h6>
            <button class="btn btn-primary btn-sm" @click="showAddSecretModal = true">
              <i class="fas fa-plus me-1"></i> 生成新密钥
            </button>
          </div>
        </div>
      </div>

      <div v-if="loadingSecrets" class="text-center py-5">
        <span class="spinner-border spinner-border-sm"></span> 加载中...
      </div>
      <div v-else-if="secrets.length === 0" class="text-center py-5 text-muted">
        <i class="fas fa-key fa-3x mb-3"></i>
        <p class="mb-0">暂无密钥</p>
        <button class="btn btn-primary btn-sm mt-2" @click="showAddSecretModal = true">
          <i class="fas fa-plus"></i> 生成新密钥
        </button>
      </div>
      <div v-else class="card">
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-hover table-sm mb-0">
              <thead class="table-light">
                <tr>
                  <th style="width: 15%;">密钥名称</th>
                  <th style="width: 35%;">密钥值</th>
                  <th style="width: 10%;">状态</th>
                  <th style="width: 20%;">创建时间</th>
                  <th style="width: 20%;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="secret in secrets" :key="secret.secret_id">
                  <td>
                    <div v-if="editingSecretId === secret.secret_id" class="input-group input-group-sm">
                      <input
                        type="text"
                        class="form-control"
                        v-model="editingSecretName"
                        placeholder="请输入密钥名称"
                        @keyup.enter="saveSecretName(secret)"
                        @blur="saveSecretName(secret)"
                      />
                      <button
                        class="btn btn-outline-success"
                        type="button"
                        @click.stop="saveSecretName(secret)"
                        title="保存名称"
                      >
                        <i class="fas fa-check"></i>
                      </button>
                    </div>
                    <div v-else class="d-flex align-items-center">
                      <strong>{{ secret.name || '未命名' }}</strong>
                      <button
                        class="btn btn-sm btn-link text-decoration-none ms-1 p-0"
                        type="button"
                        @click.stop="startEditSecretName(secret)"
                        title="编辑名称"
                      >
                        <i class="fas fa-edit"></i>
                      </button>
                    </div>
                  </td>
                  <td>
                    <div class="d-flex align-items-center">
                      <code class="small text-break me-2" style="max-width: 200px;">{{ secret.secret_key }}</code>
                      <button
                        class="btn btn-sm btn-outline-secondary"
                        type="button"
                        @click="copyToClipboard(secret.secret_key, '密钥已复制到剪贴板')"
                        title="复制密钥"
                      >
                        <i class="fas fa-copy"></i>
                      </button>
                    </div>
                  </td>
                  <td>
                    <span :class="secret.enabled ? 'badge bg-success' : 'badge bg-secondary'">
                      {{ secret.enabled ? '启用' : '禁用' }}
                    </span>
                  </td>
                  <td class="small text-muted">{{ formatTime(secret.created_at) }}</td>
                  <td>
                    <div class="btn-group btn-group-sm" role="group">
                      <button 
                        class="btn btn-outline-primary" 
                        @click="showSecretDeployCommand(secret)"
                        title="生成部署命令"
                      >
                        <i class="fas fa-code me-1"></i>部署
                      </button>
                      <button 
                        v-if="secret.enabled"
                        class="btn btn-outline-warning" 
                        @click="disableSecret(secret)"
                        title="禁用"
                      >
                        <i class="fas fa-ban"></i>
                      </button>
                      <button 
                        v-else
                        class="btn btn-outline-success" 
                        @click="enableSecret(secret)"
                        title="启用"
                      >
                        <i class="fas fa-check"></i>
                      </button>
                      <button 
                        class="btn btn-outline-danger" 
                        @click="deleteSecret(secret)"
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
        </div>
      </div>
    </div>

    <!-- 待加入主机标签页 -->
    <div v-show="activeTab === 'pending'">
      <div class="card mb-3">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-center">
            <h6 class="mb-0">
              <i class="fas fa-clock me-2"></i>待加入主机
              <span v-if="pendingHostsCount > 0" class="badge bg-danger ms-2">{{ pendingHostsCount }}</span>
            </h6>
            <button class="btn btn-sm btn-outline-secondary" @click="loadPendingHosts" title="刷新">
              <i class="fas fa-sync-alt"></i>
            </button>
          </div>
        </div>
      </div>

      <div v-if="loadingPendingHosts" class="card">
        <div class="card-body text-center py-5">
          <span class="spinner-border spinner-border-sm me-2"></span> 加载中...
        </div>
      </div>
      <div v-else-if="pendingHosts.length === 0" class="card">
        <div class="card-body text-center py-5 text-muted">
          <i class="fas fa-clock fa-3x mb-3"></i>
          <p class="mb-0">暂无待加入主机</p>
          <small class="d-block mt-2">使用密钥部署Agent后，主机将自动出现在这里</small>
        </div>
      </div>
      <div v-else class="row g-3">
        <div
          v-for="host in pendingHosts"
          :key="host.agent_token"
          class="col-12 col-md-6 col-xl-4"
        >
            <div class="card h-100 border-warning shadow-sm">
            <div class="card-header bg-warning bg-opacity-10">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <h6 class="mb-0">
                  <i class="fas fa-clock me-2"></i>待加入主机
                </h6>
                <span class="badge bg-warning text-dark">待批准</span>
              </div>
              <div v-if="host.host_info && host.host_info.ip" class="small text-muted">
                <i class="fas fa-network-wired me-1"></i>{{ host.host_info.ip }}
              </div>
            </div>
            <div class="card-body">

              <div class="mb-3">
                <label class="small text-muted d-block mb-1">唯一标识</label>
                <div class="d-flex align-items-center">
                  <code class="small text-break me-2 flex-grow-1">{{ host.agent_token || '生成中...' }}</code>
                  <button
                    class="btn btn-sm btn-outline-secondary"
                    @click="copyToClipboard(host.agent_token, '唯一标识已复制到剪贴板')"
                    title="复制"
                  >
                    <i class="fas fa-copy"></i>
                  </button>
                </div>
              </div>
              
              <div v-if="host.host_info && Object.keys(host.host_info).length > 0" class="mb-3 border-top pt-3">
                <h6 class="small text-muted mb-2">主机信息</h6>
                <div v-if="host.host_info.ip" class="small text-muted mb-1">
                  <i class="fas fa-network-wired me-1"></i>IP: {{ host.host_info.ip }}
                </div>
                <div v-if="host.host_info.os" class="small text-muted mb-1">
                  <i class="fas fa-desktop me-1"></i>{{ host.host_info.os }}
                </div>
                <div v-if="host.host_info.hostname" class="small text-muted">
                  <i class="fas fa-server me-1"></i>{{ host.host_info.hostname }}
                </div>
              </div>
              
              <div v-if="host.docker_info && Object.keys(host.docker_info).length > 0" class="mb-3 border-top pt-3">
                <h6 class="small text-muted mb-2">Docker信息</h6>
                <div v-if="host.docker_info.version" class="small mb-1">
                  <i class="fab fa-docker me-1 text-info"></i>
                  <strong>版本:</strong> {{ host.docker_info.version }}
                </div>
                <div v-if="host.docker_info.containers !== undefined" class="small text-muted">
                  <i class="fas fa-box me-1"></i>容器: {{ host.docker_info.containers }}
                </div>
              </div>
              
              <div class="small text-muted border-top pt-2">
                <div class="mb-1">
                  <i class="fas fa-clock me-1"></i>连接: {{ formatTime(host.connected_at) }}
                </div>
                <div>
                  <i class="fas fa-heartbeat me-1"></i>心跳: {{ formatTime(host.last_heartbeat) }}
                </div>
              </div>
            </div>
            <div class="card-footer bg-white">
              <div class="d-grid gap-2 d-md-flex">
                <button 
                  class="btn btn-success btn-sm flex-fill" 
                  @click="approvePendingHost(host)"
                  title="批准加入"
                >
                  <i class="fas fa-check me-1"></i>批准加入
                </button>
                <button 
                  class="btn btn-danger btn-sm" 
                  @click="rejectPendingHost(host)"
                  title="拒绝"
                >
                  <i class="fas fa-times"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加/编辑主机模态框 -->
    <div v-if="showAddModal || showEditModal" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);" @click.self="closeModal">
      <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-network-wired me-2"></i> {{ editingHost ? '编辑主机' : (hostForm.host_type === 'agent' ? '新建Agent主机' : '新建Portainer主机') }}
            </h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
            <form @submit.prevent="saveHost" novalidate>
              <div class="mb-3" v-if="!editingHost">
                <label class="form-label">
                  主机类型 <span class="text-danger">*</span>
                </label>
                <div class="alert alert-info py-2 mb-0">
                  <i :class="hostForm.host_type === 'agent' ? 'fas fa-network-wired' : 'fab fa-docker'"></i>
                  <strong class="ms-2">{{ hostForm.host_type === 'agent' ? 'Agent主机' : 'Portainer主机' }}</strong>
                </div>
              </div>
              <div class="mb-3" v-else>
                <label class="form-label">主机类型</label>
                <div class="form-control-plaintext">
                  <span class="badge" :class="hostForm.host_type === 'portainer' ? 'bg-primary' : 'bg-secondary'">
                    <i :class="hostForm.host_type === 'agent' ? 'fas fa-network-wired' : 'fab fa-docker'"></i>
                    {{ hostForm.host_type === 'portainer' ? 'Portainer' : 'Agent' }}
                  </span>
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
    <div v-if="showDetailModal && selectedHost" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);" @click.self="showDetailModal = false">
      <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-info-circle me-2"></i> Agent主机详情
            </h5>
            <button type="button" class="btn-close" @click="showDetailModal = false"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
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
    <div v-if="showDeployModal && selectedHost" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);" @click.self="showDeployModal = false">
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-code me-2"></i> {{ selectedHost.name }}
            </h5>
            <button type="button" class="btn-close" @click="showDeployModal = false"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
            <div class="mb-3">
              <div class="btn-group w-100" role="group">
                <input 
                  type="radio" 
                  class="btn-check" 
                  name="deployType" 
                  id="deployCompose"
                  value="compose"
                  v-model="deployType"
                  @change="loadDeployCommand"
                />
                <label class="btn btn-outline-primary" for="deployCompose">
                  <i class="fab fa-docker me-1"></i> docker-compose
                </label>
                
                <input 
                  type="radio" 
                  class="btn-check" 
                  name="deployType" 
                  id="deploySingle"
                  value="single"
                  v-model="deployType"
                  @change="loadDeployCommand"
                />
                <label class="btn btn-outline-primary" for="deploySingle">
                  <i class="fas fa-server me-1"></i> 单机
                </label>
                
                <input 
                  type="radio" 
                  class="btn-check" 
                  name="deployType" 
                  id="deploySwarm"
                  value="swarm"
                  v-model="deployType"
                  @change="loadDeployCommand"
                />
                <label class="btn btn-outline-primary" for="deploySwarm">
                  <i class="fas fa-layer-group me-1"></i> Swarm
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
                <label class="form-label mb-0">
                  <span v-if="deployType === 'single'">Docker Run 命令</span>
                  <span v-else-if="deployType === 'compose'">Docker Compose 命令</span>
                  <span v-else-if="deployType === 'swarm'">Docker Stack 部署命令</span>
                </label>
                <button class="btn btn-sm btn-outline-primary" @click="copyDeployCommand">
                  <i class="fas fa-copy me-1"></i> 复制
                </button>
              </div>
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 400px; overflow-y: auto;"><code>{{ deployCommand }}</code></pre>
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

    <!-- 生成密钥模态框 -->
    <div v-if="showAddSecretModal" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);" @click.self="showAddSecretModal = false">
      <div class="modal-dialog modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-key me-2"></i> 生成新密钥
            </h5>
            <button type="button" class="btn-close" @click="showAddSecretModal = false"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
            <div class="mb-3">
              <label class="form-label">密钥名称（可选）</label>
              <input 
                type="text" 
                class="form-control form-control-sm" 
                v-model="secretForm.name"
                placeholder="例如：生产环境密钥"
              />
            </div>
            <div class="alert alert-info py-2 mb-0">
              <i class="fas fa-info-circle me-2"></i>
              密钥用于Agent连接认证，生成后请妥善保管。
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="showAddSecretModal = false">
              取消
            </button>
            <button 
              type="button" 
              class="btn btn-primary btn-sm" 
              @click="createSecret"
              :disabled="creatingSecret"
            >
              <span v-if="creatingSecret" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="fas fa-key me-1"></i>
              {{ creatingSecret ? '生成中...' : '生成密钥' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 批准待加入主机模态框 -->
    <div v-if="showApproveModal && selectedPendingHost" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);" @click.self="showApproveModal = false">
      <div class="modal-dialog modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-check-circle me-2"></i> 批准待加入主机
            </h5>
            <button type="button" class="btn-close" @click="showApproveModal = false"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
            <div class="mb-3">
              <label class="form-label">
                主机名称 <span class="text-danger">*</span>
              </label>
              <input 
                type="text" 
                class="form-control form-control-sm" 
                v-model="approveForm.name"
                placeholder="例如：生产服务器-Agent"
                required
              />
            </div>
            <div class="mb-3">
              <label class="form-label">描述（可选）</label>
              <input 
                type="text" 
                class="form-control form-control-sm" 
                v-model="approveForm.description"
                placeholder="请输入主机描述信息..."
              />
            </div>
            <div class="alert alert-info py-2 mb-0">
              <i class="fas fa-info-circle me-2"></i>
              唯一标识: <code>{{ selectedPendingHost.agent_token }}</code>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="showApproveModal = false">
              取消
            </button>
            <button 
              type="button" 
              class="btn btn-success btn-sm" 
              @click="confirmApprovePendingHost"
              :disabled="approving"
            >
              <span v-if="approving" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="fas fa-check me-1"></i>
              {{ approving ? '批准中...' : '批准加入' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 密钥部署命令模态框 -->
    <div v-if="showSecretDeployModal && selectedSecret" class="modal fade show d-block" style="background-color: rgba(0,0,0,0.5);" @click.self="showSecretDeployModal = false">
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title mb-0">
              <i class="fas fa-code me-2"></i> {{ selectedSecret.name || '未命名密钥' }}
            </h5>
            <button type="button" class="btn-close" @click="showSecretDeployModal = false"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
            <div class="alert alert-info py-2 mb-3">
              <i class="fas fa-info-circle me-2"></i>
              <strong>使用密钥部署Agent：</strong>部署后Agent会自动生成唯一标识并加入待加入列表，您可以在"待加入主机"标签页中批准加入。
            </div>
            <div class="mb-3">
              <div class="btn-group w-100" role="group">
                <input 
                  type="radio" 
                  class="btn-check" 
                  name="secretDeployType" 
                  id="secretDeployCompose"
                  value="compose"
                  v-model="secretDeployType"
                  @change="loadSecretDeployCommand"
                />
                <label class="btn btn-outline-primary" for="secretDeployCompose">
                  <i class="fab fa-docker me-1"></i> docker-compose
                </label>
                
                <input 
                  type="radio" 
                  class="btn-check" 
                  name="secretDeployType" 
                  id="secretDeploySingle"
                  value="single"
                  v-model="secretDeployType"
                  @change="loadSecretDeployCommand"
                />
                <label class="btn btn-outline-primary" for="secretDeploySingle">
                  <i class="fas fa-server me-1"></i> 单机
                </label>
                
                <input 
                  type="radio" 
                  class="btn-check" 
                  name="secretDeployType" 
                  id="secretDeploySwarm"
                  value="swarm"
                  v-model="secretDeployType"
                  @change="loadSecretDeployCommand"
                />
                <label class="btn btn-outline-primary" for="secretDeploySwarm">
                  <i class="fas fa-layer-group me-1"></i> Swarm
                </label>
              </div>
            </div>
            <div class="mb-3">
              <label class="form-label">Agent镜像</label>
              <input 
                type="text" 
                class="form-control form-control-sm" 
                v-model="agentImage"
                @change="loadSecretDeployCommand"
                placeholder="registry.cn-shanghai.aliyuncs.com/51jbm/app2docker-agent:latest"
              />
            </div>
            <div class="mb-3">
              <label class="form-label">服务器地址（可选，留空自动检测）</label>
              <input 
                type="text" 
                class="form-control form-control-sm" 
                v-model="serverUrl"
                @change="loadSecretDeployCommand"
                placeholder="ws://192.168.1.100:8000"
              />
              <small class="text-muted">WebSocket地址，格式：ws://IP:端口 或 wss://域名:端口</small>
            </div>
            <div v-if="secretDeployCommand" class="mb-3">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <label class="form-label mb-0">
                  <span v-if="secretDeployType === 'single'">Docker Run 命令</span>
                  <span v-else-if="secretDeployType === 'compose'">Docker Compose 命令</span>
                  <span v-else-if="secretDeployType === 'swarm'">Docker Stack 部署命令</span>
                </label>
                <button class="btn btn-sm btn-outline-primary" @click="copySecretDeployCommand">
                  <i class="fas fa-copy me-1"></i> 复制
                </button>
              </div>
              <pre class="bg-dark text-light p-3 rounded" style="max-height: 400px; overflow-y: auto;"><code>{{ secretDeployCommand }}</code></pre>
            </div>
            <div v-if="loadingSecretDeployCommand" class="text-center py-3">
              <div class="spinner-border spinner-border-sm me-2"></div>
              加载中...
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="showSecretDeployModal = false">
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
import HostManager from './HostManager.vue';

export default {
  name: 'AgentHostManager',
  components: {
    HostManager
  },
  data() {
    return {
      activeTab: 'hosts', // 当前标签页: hosts, secrets, pending
      filterType: 'all', // 主机类型筛选: all, ssh, agent
      hosts: [], // Agent主机列表
      sshHosts: [], // SSH主机列表
      allHostsLoading: false, // 加载所有主机时的loading状态
      loading: false,
      showAddModal: false,
      showEditModal: false,
      showDetailModal: false,
      showDeployModal: false,
      editingHost: null,
      selectedHost: null,
      saving: false,
      deployType: 'compose',
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
      refreshInterval: null, // 定期刷新定时器
      // 密钥管理
      secrets: [],
      loadingSecrets: false,
      showAddSecretModal: false,
      creatingSecret: false,
      secretForm: {
        name: ''
      },
      // 编辑密钥名称
      editingSecretId: null,
      editingSecretName: '',
      // 待加入主机
      pendingHosts: [],
      loadingPendingHosts: false,
      showApproveModal: false,
      selectedPendingHost: null,
      approving: false,
      approveForm: {
        name: '',
        description: ''
      },
      // 密钥部署命令
      showSecretDeployModal: false,
      selectedSecret: null,
      secretDeployType: 'compose',
      secretDeployCommand: null,
      secretDeployComposeContent: null,
      loadingSecretDeployCommand: false
    }
  },
  computed: {
    allHosts() {
      if (this.filterType !== 'all') return [];
      // 合并SSH和Agent主机
      const ssh = (this.sshHosts || []).map(h => ({ ...h, host_type: 'ssh' }));
      const agent = (this.hosts || []).map(h => ({ ...h, host_type: h.host_type || 'agent' }));
      return [...ssh, ...agent];
    },
    filteredHosts() {
      if (this.filterType === 'ssh') {
        return this.sshHosts || [];
      } else if (this.filterType === 'agent') {
        return this.hosts || [];
      }
      return [];
    },
    pendingHostsCount() {
      return this.pendingHosts.length
    }
  },
  mounted() {
    this.loadHosts()
    this.loadSecrets()
    this.loadPendingHosts()
    // 如果筛选器是all，加载SSH主机
    if (this.filterType === 'all') {
      this.loadSshHosts()
    }
    // 启动WebSocket连接以实时更新状态
    this.initWebSocketConnections()
    // 定期刷新主机列表（每30秒）
    this.refreshInterval = setInterval(() => {
      this.loadHosts()
      if (this.filterType === 'all') {
        this.loadSshHosts()
      }
      if (this.activeTab === 'pending') {
        this.loadPendingHosts()
      }
    }, 30000)
  },
  watch: {
    filterType(newVal) {
      if (newVal === 'all' && this.activeTab === 'hosts') {
        this.loadSshHosts()
      }
    }
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
    async loadSshHosts() {
      try {
        const res = await axios.get('/api/hosts')
        if (res.data.hosts) {
          this.sshHosts = res.data.hosts || []
        }
      } catch (error) {
        console.error('加载SSH主机列表失败:', error)
      }
    },
    async loadHosts() {
      this.loading = true
      if (this.filterType === 'all') {
        this.allHostsLoading = true
      }
      try {
        const res = await axios.get('/api/agent-hosts')
        if (res.data.hosts) {
          this.hosts = res.data.hosts || []
        }
        // 如果筛选器是all，同时加载SSH主机
        if (this.filterType === 'all') {
          await this.loadSshHosts()
        }
      } catch (error) {
        console.error('加载Agent主机列表失败:', error)
        alert('加载Agent主机列表失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loading = false
        this.allHostsLoading = false
      }
    },
    showSshAddModal() {
      // 如果当前在SSH筛选模式，直接调用HostManager的方法
      if (this.filterType === 'ssh' && this.$refs.hostManager) {
        this.$refs.hostManager.showAddModal = true
      } else {
        // 如果不在SSH模式，切换到SSH模式并打开添加模态框
        this.filterType = 'ssh'
        this.$nextTick(() => {
          if (this.$refs.hostManager) {
            this.$refs.hostManager.showAddModal = true
          }
        })
      }
    },
    handleSshHostAction(action, host) {
      // 切换到SSH模式并执行操作
      if (this.filterType !== 'ssh') {
        this.filterType = 'ssh'
      }
      this.$nextTick(() => {
        const hostManager = this.$refs.hostManager
        if (hostManager) {
          if (action === 'test') {
            hostManager.testConnection(host)
          } else if (action === 'edit') {
            hostManager.editHost(host)
          } else if (action === 'delete') {
            hostManager.deleteHost(host)
          }
        }
      })
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
        // 映射前端类型到后端类型
        let backendType = 'run'
        if (this.deployType === 'compose' || this.deployType === 'swarm') {
          backendType = 'stack'
        } else if (this.deployType === 'single') {
          backendType = 'run'
        }
        
        const res = await axios.get(`/api/agent-hosts/${this.selectedHost.host_id}/deploy-command`, {
          params: {
            type: backendType,
            agent_image: this.agentImage
          }
        })
        
        // 根据部署类型生成主要命令
        if (this.deployType === 'compose') {
          // Compose模式：生成 docker-compose up -d 命令
          if (res.data.compose_content) {
            this.deployCommand = `# 1. 创建docker-compose.yml文件
cat > docker-compose.yml << 'EOF'
${res.data.compose_content}
EOF

# 2. 启动服务
docker-compose up -d`
          } else {
            this.deployCommand = res.data.command
          }
          this.deployComposeContent = null
        } else if (this.deployType === 'swarm') {
          // Swarm模式：只显示stack deploy命令
          if (res.data.compose_content) {
            this.deployCommand = `# 1. 创建docker-compose.yml文件
cat > docker-compose.yml << 'EOF'
${res.data.compose_content}
EOF

# 2. 全局部署stack
docker stack deploy -c docker-compose.yml app2docker-agent`
          } else {
            this.deployCommand = res.data.command
          }
          this.deployComposeContent = null
        } else {
          // 单机模式：只显示run命令
          this.deployCommand = res.data.command
          this.deployComposeContent = null
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
    copyToClipboard(text, message) {
      if (!text) {
        alert('暂无可复制内容')
        return
      }

      const fallbackCopy = () => {
        const textarea = document.createElement('textarea')
        textarea.value = text
        textarea.style.position = 'fixed'
        textarea.style.opacity = '0'
        document.body.appendChild(textarea)
        textarea.select()
        document.execCommand('copy')
        document.body.removeChild(textarea)
        if (message) {
          alert(message)
        }
      }

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text)
          .then(() => {
            if (message) {
              alert(message)
            }
          })
          .catch(() => {
            // 无法使用 clipboard API 时，回退到旧方案
            fallbackCopy()
          })
      } else {
        // 降级方案
        fallbackCopy()
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
    },
    // 密钥管理方法
    async loadSecrets() {
      this.loadingSecrets = true
      try {
        const res = await axios.get('/api/agent-secrets')
        if (res.data.secrets) {
          this.secrets = res.data.secrets || []
        }
      } catch (error) {
        console.error('加载密钥列表失败:', error)
        alert('加载密钥列表失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loadingSecrets = false
      }
    },
    async createSecret() {
      if (!this.secretForm.name) {
        if (!confirm('未填写密钥名称，是否继续生成？')) {
          return
        }
      }

      this.creatingSecret = true
      try {
        const res = await axios.post('/api/agent-secrets', {
          name: this.secretForm.name || ''
        })
        if (res.data.success) {
          alert('密钥生成成功！\n密钥值: ' + res.data.secret.secret_key + '\n\n请妥善保管，此密钥将不再显示。')
          this.showAddSecretModal = false
          this.secretForm.name = ''
          this.loadSecrets()
        }
      } catch (error) {
        console.error('生成密钥失败:', error)
        alert('生成密钥失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.creatingSecret = false
      }
    },
    startEditSecretName(secret) {
      this.editingSecretId = secret.secret_id
      this.editingSecretName = secret.name || ''
    },
    async saveSecretName(secret) {
      if (!this.editingSecretId || this.editingSecretId !== secret.secret_id) {
        return
      }
      const newName = (this.editingSecretName || '').trim()
      // 如果名称未变化，直接退出编辑
      if ((secret.name || '') === newName) {
        this.editingSecretId = null
        this.editingSecretName = ''
        return
      }
      try {
        const res = await axios.put(`/api/agent-secrets/${secret.secret_id}`, {
          name: newName
        })
        if (res.data && res.data.success && res.data.secret) {
          secret.name = res.data.secret.name || ''
          alert('密钥名称已更新')
        } else {
          // 后端未返回 success 字段时，尝试直接刷新列表
          alert('密钥名称已更新')
          this.loadSecrets()
        }
      } catch (error) {
        console.error('更新密钥名称失败:', error)
        alert('更新密钥名称失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.editingSecretId = null
        this.editingSecretName = ''
      }
    },
    async enableSecret(secret) {
      try {
        const res = await axios.put(`/api/agent-secrets/${secret.secret_id}/enable`)
        if (res.data.success) {
          alert('密钥已启用')
          this.loadSecrets()
        }
      } catch (error) {
        console.error('启用密钥失败:', error)
        alert('启用密钥失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async disableSecret(secret) {
      if (!confirm(`确定要禁用密钥 "${secret.name || secret.secret_key}" 吗？`)) {
        return
      }
      try {
        const res = await axios.put(`/api/agent-secrets/${secret.secret_id}/disable`)
        if (res.data.success) {
          alert('密钥已禁用')
          this.loadSecrets()
        }
      } catch (error) {
        console.error('禁用密钥失败:', error)
        alert('禁用密钥失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    async deleteSecret(secret) {
      if (!confirm(`确定要删除密钥 "${secret.name || secret.secret_key}" 吗？\n此操作不可恢复！`)) {
        return
      }
      try {
        const res = await axios.delete(`/api/agent-secrets/${secret.secret_id}`)
        if (res.data.success) {
          alert('密钥已删除')
          this.loadSecrets()
        }
      } catch (error) {
        console.error('删除密钥失败:', error)
        alert('删除密钥失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    // 待加入主机方法
    async loadPendingHosts() {
      this.loadingPendingHosts = true
      try {
        const res = await axios.get('/api/agent-hosts/pending')
        if (res.data.hosts) {
          this.pendingHosts = res.data.hosts || []
        }
      } catch (error) {
        console.error('加载待加入主机列表失败:', error)
        alert('加载待加入主机列表失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loadingPendingHosts = false
      }
    },
    approvePendingHost(host) {
      this.selectedPendingHost = host
      this.approveForm.name = ''
      this.approveForm.description = ''
      this.showApproveModal = true
    },
    async confirmApprovePendingHost() {
      if (!this.approveForm.name) {
        alert('请填写主机名称')
        return
      }

      this.approving = true
      try {
        const res = await axios.post(`/api/agent-hosts/pending/${this.selectedPendingHost.agent_token}/approve`, {
          name: this.approveForm.name,
          description: this.approveForm.description || ''
        })
        if (res.data.success) {
          alert('主机已批准加入系统')
          this.showApproveModal = false
          this.selectedPendingHost = null
          this.loadPendingHosts()
          this.loadHosts()
        }
      } catch (error) {
        console.error('批准待加入主机失败:', error)
        alert('批准待加入主机失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.approving = false
      }
    },
    async rejectPendingHost(host) {
      if (!confirm(`确定要拒绝待加入主机吗？\n唯一标识: ${host.agent_token}`)) {
        return
      }
      try {
        const res = await axios.delete(`/api/agent-hosts/pending/${host.agent_token}`)
        if (res.data.success) {
          alert('待加入主机已拒绝')
          this.loadPendingHosts()
        }
      } catch (error) {
        console.error('拒绝待加入主机失败:', error)
        alert('拒绝待加入主机失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    // 密钥部署命令方法
    showSecretDeployCommand(secret) {
      this.selectedSecret = secret
      this.secretDeployType = 'compose'
      this.serverUrl = ''
      this.showSecretDeployModal = true
      this.loadSecretDeployCommand()
    },
    async loadSecretDeployCommand() {
      if (!this.selectedSecret) return
      
      this.loadingSecretDeployCommand = true
      this.secretDeployCommand = null
      this.secretDeployComposeContent = null
      
      try {
        // 获取服务器URL
        let serverUrl = this.serverUrl
        if (!serverUrl) {
          // 从当前页面URL获取
          const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
          const host = window.location.hostname
          const port = window.location.port || (window.location.protocol === 'https:' ? '443' : '80')
          // 如果端口是80或443，不显示端口
          if (port === '80' || port === '443') {
            serverUrl = `${protocol}://${host}`
          } else {
            serverUrl = `${protocol}://${host}:${port}`
          }
        }

        const secretKey = this.selectedSecret.secret_key
        
        // 根据类型生成不同的命令
        if (this.secretDeployType === 'single') {
          // 单机模式：docker run
          this.secretDeployCommand = `docker run -d \\
  --name app2docker-agent \\
  --restart=always \\
  -e AGENT_SECRET_KEY=${secretKey} \\
  -e SERVER_URL=${serverUrl} \\
  -v /var/run/docker.sock:/var/run/docker.sock \\
  -v /proc:/host/proc:ro \\
  -v /sys:/host/sys:ro \\
  ${this.agentImage}`
          this.secretDeployComposeContent = null
        } else if (this.secretDeployType === 'compose') {
          // docker-compose模式：生成 docker-compose up -d 命令
          const composeContent = `version: '3.8'

services:
  agent:
    image: ${this.agentImage}
    container_name: app2docker-agent
    restart: always
    environment:
      - AGENT_SECRET_KEY=${secretKey}
      - SERVER_URL=${serverUrl}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge`

          this.secretDeployCommand = `# 1. 创建docker-compose.yml文件
cat > docker-compose.yml << 'EOF'
${composeContent}
EOF

# 2. 启动服务
docker-compose up -d`
          this.secretDeployComposeContent = null
        } else if (this.secretDeployType === 'swarm') {
          // Swarm模式：只显示docker stack deploy命令
          const composeContent = `version: '3.8'

services:
  agent:
    image: ${this.agentImage}
    deploy:
      mode: global
      restart_policy:
        condition: any
    environment:
      - AGENT_SECRET_KEY=${secretKey}
      - SERVER_URL=${serverUrl}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
    networks:
      - agent-network

networks:
  agent-network:
    driver: overlay`

          this.secretDeployCommand = `# 1. 创建docker-compose.yml文件
cat > docker-compose.yml << 'EOF'
${composeContent}
EOF

# 2. 全局部署stack
docker stack deploy -c docker-compose.yml app2docker-agent`
          this.secretDeployComposeContent = null
        }
      } catch (error) {
        console.error('生成部署命令失败:', error)
        alert('生成部署命令失败: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.loadingSecretDeployCommand = false
      }
    },
    copySecretDeployCommand() {
      if (this.secretDeployCommand) {
        this.copyToClipboard(this.secretDeployCommand)
        alert('部署命令已复制到剪贴板')
      }
    },
    copySecretComposeContent() {
      if (this.secretDeployComposeContent) {
        this.copyToClipboard(this.secretDeployComposeContent)
        alert('docker-compose.yml 内容已复制到剪贴板')
      }
    }
  },
  watch: {
    activeTab(newTab) {
      if (newTab === 'pending') {
        this.loadPendingHosts()
      } else if (newTab === 'secrets') {
        this.loadSecrets()
      }
    }
  }
}
</script>

<style scoped>
.agent-host-manager-panel {
  padding: 0;
  min-height: 100%;
  overflow: visible;
}

/* 标签页样式优化 */
.nav-tabs-custom {
  border-bottom: none;
}

.nav-tabs-custom .nav-link {
  border: none;
  border-bottom: 2px solid transparent;
  color: #6c757d;
  padding: 0.5rem 1rem;
  transition: all 0.2s;
}

.nav-tabs-custom .nav-link:hover {
  border-bottom-color: #dee2e6;
  color: #495057;
}

.nav-tabs-custom .nav-link.active {
  border-bottom-color: #0d6efd;
  color: #0d6efd;
  font-weight: 500;
  background-color: transparent;
}

/* 卡片样式 */
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

/* 表格样式优化 */
.table-sm th,
.table-sm td {
  padding: 0.5rem;
  vertical-align: middle;
}

.table thead th {
  font-weight: 600;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 代码样式 */
code {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.85em;
  background-color: #f8f9fa;
  padding: 0.2rem 0.4rem;
  border-radius: 0.25rem;
  word-break: break-all;
}

pre code {
  font-size: 0.85em;
  white-space: pre-wrap;
  word-wrap: break-word;
  background-color: transparent;
  padding: 0;
}

/* 模态框 */
.modal.show {
  display: block;
}

.modal-dialog-scrollable .modal-body {
  overflow-y: auto;
}

.modal.show .modal-dialog {
  margin: 1.75rem auto;
  max-height: calc(100vh - 3.5rem);
}

.modal.show .modal-content {
  max-height: calc(100vh - 3.5rem);
  display: flex;
  flex-direction: column;
}

.modal.show .modal-body {
  overflow-y: auto;
  flex: 1 1 auto;
}

/* 进度条 */
.progress {
  min-width: 100px;
}

/* 按钮组 */
.btn-group .btn-check:checked + .btn {
  background-color: #0d6efd;
  border-color: #0d6efd;
  color: white;
}

/* 响应式 */
@media (max-width: 768px) {
  .modal-dialog {
    margin: 0.5rem;
  }
  
  .nav-tabs-custom .nav-link {
    padding: 0.4rem 0.6rem;
    font-size: 0.875rem;
  }
  
  .table-responsive {
    font-size: 0.875rem;
  }
}

/* 待加入主机卡片特殊样式 */
.card.border-warning {
  border-width: 2px;
}

.card.border-warning .card-header {
  border-bottom: 2px solid #ffc107;
}
</style>


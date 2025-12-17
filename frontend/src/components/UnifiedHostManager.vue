<template>
  <div class="unified-host-manager">
    <!-- 顶部工具栏 -->
    <div class="card mb-3">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
          <h5 class="mb-0"><i class="fas fa-server me-2"></i> 主机管理</h5>
          <div class="d-flex gap-2 align-items-center">
            <!-- 主机类型过滤 -->
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
          </div>
        </div>
      </div>
    </div>

    <!-- 全部模式：统一显示所有主机 -->
    <template v-if="filterType === 'all'">
      <!-- 添加主机按钮 -->
      <div class="d-flex justify-content-end mb-3">
        <div class="btn-group me-2">
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
            <i class="fas fa-plus me-1"></i> 添加Agent主机
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
            <li>
              <a class="dropdown-item" href="#" @click.prevent="openAgentAddModal('agent')">
                <i class="fas fa-network-wired me-2"></i> Agent主机
              </a>
            </li>
            <li>
              <a class="dropdown-item" href="#" @click.prevent="openAgentAddModal('portainer')">
                <i class="fab fa-docker me-2"></i> Portainer主机
              </a>
            </li>
          </ul>
        </div>
      </div>

      <!-- 统一的主机列表 -->
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
                <h5 class="card-title mb-2">
                  <strong>{{ host.name }}</strong>
                </h5>
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
                  <i class="fas fa-network-wired text-muted me-2" style="width: 18px;"></i>
                  <div class="flex-grow-1">
                    <div class="small">
                      <strong>{{ host.host }}</strong>
                      <span class="text-muted ms-2">:{{ host.port }}</span>
                    </div>
                    <div class="small text-muted mt-1">
                      <i class="fas fa-user me-1"></i>{{ host.username }}
                    </div>
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
                <h5 class="card-title mb-2">
                  <strong>{{ host.name }}</strong>
                </h5>
                <div class="d-flex align-items-center justify-content-between mb-1">
                  <div>
                    <span class="badge" :class="host.host_type === 'portainer' ? 'bg-primary' : 'bg-secondary'">
                      <i class="fas fa-network-wired"></i> {{ host.host_type === 'portainer' ? 'Portainer' : 'Agent' }}
                    </span>
                    <span :class="getAgentStatusBadgeClass(host.status)" class="badge ms-1">
                      <i :class="getAgentStatusIcon(host.status)"></i>
                      {{ getAgentStatusText(host.status) }}
                    </span>
                  </div>
                </div>
                <p class="text-muted mb-0 mt-1" v-if="host.description" style="font-size: 0.9rem">
                  {{ host.description }}
                </p>
              </div>
              <div class="btn-group btn-group-sm w-100">
                <button class="btn btn-outline-info" @click="handleAgentHostAction('view', host)" title="查看详情">
                  <i class="fas fa-info-circle"></i>
                </button>
                <button class="btn btn-outline-primary" @click="handleAgentHostAction('edit', host)" title="编辑">
                  <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-outline-danger" @click="handleAgentHostAction('delete', host)" title="删除">
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
            <div class="card-body">
              <div v-if="host.host_info && Object.keys(host.host_info).length > 0" class="mb-3">
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

    <!-- 单独模式：分别显示 -->
    <template v-else>
      <!-- SSH主机管理 -->
      <HostManager ref="hostManager" :filterType="filterType" />
      <!-- Agent主机管理 -->
      <AgentHostManager ref="agentHostManager" :filterType="filterType" />
    </template>
    
    <!-- 隐藏的子组件，用于在全部模式下访问ref -->
    <HostManager v-show="false" ref="hostManagerHidden" :filterType="'ssh'" v-if="filterType === 'all'" />
    <AgentHostManager v-show="false" ref="agentHostManagerHidden" :filterType="'agent'" v-if="filterType === 'all'" />
  </div>
</template>

<script>
import axios from "axios";
import { computed, onMounted, ref, watch } from "vue";
import AgentHostManager from "./AgentHostManager.vue";
import HostManager from "./HostManager.vue";

export default {
  name: "UnifiedHostManager",
  components: {
    HostManager,
    AgentHostManager,
  },
  setup() {
    const filterType = ref("all");
    const sshHosts = ref([]);
    const agentHosts = ref([]);
    const allHostsLoading = ref(false);
    const hostManagerRef = ref(null);
    const agentHostManagerRef = ref(null);

    const allHosts = computed(() => {
      if (filterType.value !== 'all') return [];
      // 合并SSH和Agent主机，SSH主机标记为host_type: 'ssh'
      const ssh = (sshHosts.value || []).map(h => ({ ...h, host_type: 'ssh' }));
      const agent = (agentHosts.value || []).map(h => ({ ...h, host_type: h.host_type || 'agent' }));
      return [...ssh, ...agent];
    });

    const loadAllHosts = async () => {
      if (filterType.value !== 'all') return;
      allHostsLoading.value = true;
      try {
        const [sshRes, agentRes] = await Promise.all([
          axios.get('/api/hosts'),
          axios.get('/api/agent-hosts')
        ]);
        sshHosts.value = sshRes.data?.hosts || [];
        agentHosts.value = agentRes.data?.hosts || [];
      } catch (error) {
        console.error('加载主机列表失败:', error);
      } finally {
        allHostsLoading.value = false;
      }
    };

    // Agent主机状态相关方法
    const getAgentStatusBadgeClass = (status) => {
      const statusMap = {
        'online': 'bg-success',
        'offline': 'bg-secondary',
        'connecting': 'bg-warning'
      };
      return statusMap[status] || 'bg-secondary';
    };

    const getAgentStatusIcon = (status) => {
      const iconMap = {
        'online': 'fas fa-circle',
        'offline': 'fas fa-circle',
        'connecting': 'fas fa-spinner fa-spin'
      };
      return iconMap[status] || 'fas fa-circle';
    };

    const getAgentStatusText = (status) => {
      const textMap = {
        'online': '在线',
        'offline': '离线',
        'connecting': '连接中'
      };
      return textMap[status] || '未知';
    };

    watch(filterType, (newVal) => {
      if (newVal === 'all') {
        loadAllHosts();
      }
    });

    onMounted(() => {
      if (filterType.value === 'all') {
        loadAllHosts();
      }
    });

    return {
      filterType,
      allHosts,
      allHostsLoading,
      loadAllHosts,
      hostManagerRef,
      agentHostManagerRef,
      getAgentStatusBadgeClass,
      getAgentStatusIcon,
      getAgentStatusText,
    };
  },
  methods: {
    showSshAddModal() {
      const hostManager = this.$refs.hostManager || this.$refs.hostManagerHidden;
      if (hostManager) {
        hostManager.showAddModal = true;
      }
    },
    openAgentAddModal(type) {
      const agentHostManager = this.$refs.agentHostManager || this.$refs.agentHostManagerHidden;
      if (agentHostManager) {
        agentHostManager.openAddModal(type);
      }
    },
    handleSshHostAction(action, host) {
      const hostManager = this.$refs.hostManager || this.$refs.hostManagerHidden;
      if (hostManager) {
        if (action === 'test') {
          hostManager.testConnection(host);
        } else if (action === 'edit') {
          hostManager.editHost(host);
        } else if (action === 'delete') {
          hostManager.deleteHost(host);
        }
      }
    },
    handleAgentHostAction(action, host) {
      const agentHostManager = this.$refs.agentHostManager || this.$refs.agentHostManagerHidden;
      if (agentHostManager) {
        if (action === 'view') {
          agentHostManager.viewHost(host);
        } else if (action === 'edit') {
          agentHostManager.editHost(host);
        } else if (action === 'delete') {
          agentHostManager.deleteHost(host);
        }
      }
    }
  }
};
</script>

<style scoped>
.unified-host-manager {
  padding: 0;
}

.btn-group .btn-check:checked + .btn {
  background-color: #0d6efd;
  border-color: #0d6efd;
  color: white;
}

/* 当显示全部时，两个组件之间添加分隔 */
.unified-host-manager .host-manager-panel:not(:last-child) {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 2px solid #dee2e6;
}
</style>

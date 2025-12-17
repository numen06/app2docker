<template>
  <div class="unified-host-manager">
    <!-- 直接显示AgentHostManager，它内部有标签页和筛选器 -->
    <AgentHostManager ref="agentHostManager" />
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
  min-height: 100%;
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

/* 确保内容可以正常滚动 */
.unified-host-manager .row {
  margin-bottom: 1rem;
}
</style>

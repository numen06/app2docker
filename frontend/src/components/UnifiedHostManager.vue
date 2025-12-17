<template>
  <div class="unified-host-manager">
    <!-- 顶部工具栏 -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0"><i class="fas fa-server"></i> 主机管理</h5>
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

    <!-- SSH主机管理 -->
    <HostManager :filterType="filterType" />

    <!-- Agent主机管理 -->
    <AgentHostManager :filterType="filterType" />
  </div>
</template>

<script>
import HostManager from "./HostManager.vue";
import AgentHostManager from "./AgentHostManager.vue";
import { ref } from "vue";

export default {
  name: "UnifiedHostManager",
  components: {
    HostManager,
    AgentHostManager,
  },
  setup() {
    const filterType = ref("all");

    return {
      filterType,
    };
  },
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
</style>

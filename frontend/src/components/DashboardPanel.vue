<template>
  <div class="dashboard-panel">
    <!-- 刷新按钮 -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-chart-line text-primary"></i> 系统仪表盘
      </h5>
      <button
        class="btn btn-outline-secondary btn-sm"
        @click="loadDashboard"
        :disabled="loading"
        title="刷新数据"
      >
        <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i> 刷新
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && !stats" class="text-center py-5">
      <span class="spinner-border spinner-border-sm"></span> 加载中...
    </div>

    <!-- 仪表盘内容 -->
    <div v-else>
      <!-- 统计卡片 -->
      <div class="row g-3 mb-4">
        <!-- 任务统计 -->
        <div class="col-6 col-md-3">
          <div class="card h-100 shadow-sm border-primary">
            <div class="card-body">
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div
                    class="stat-icon bg-primary text-white rounded-circle d-flex align-items-center justify-content-center"
                    style="width: 48px; height: 48px"
                  >
                    <i class="fas fa-tasks fa-lg"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <div class="stat-label text-muted small">总任务数</div>
                  <div class="stat-value h4 mb-0">
                    {{ stats?.totalTasks || 0 }}
                  </div>
                </div>
              </div>
              <div class="mt-2 pt-2 border-top">
                <div class="row g-2 text-center">
                  <div class="col-6">
                    <small class="text-muted d-block">运行中</small>
                    <strong class="text-warning">{{
                      stats?.runningTasks || 0
                    }}</strong>
                  </div>
                  <div class="col-6">
                    <small class="text-muted d-block">已完成</small>
                    <strong class="text-success">{{
                      stats?.completedTasks || 0
                    }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 流水线统计 -->
        <div class="col-6 col-md-3">
          <div class="card h-100 shadow-sm border-info">
            <div class="card-body">
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div
                    class="stat-icon bg-info text-white rounded-circle d-flex align-items-center justify-content-center"
                    style="width: 48px; height: 48px"
                  >
                    <i class="fas fa-project-diagram fa-lg"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <div class="stat-label text-muted small">流水线</div>
                  <div class="stat-value h4 mb-0">
                    {{ stats?.pipelines || 0 }}
                  </div>
                </div>
              </div>
              <div class="mt-2 pt-2 border-top">
                <div class="row g-2 text-center">
                  <div class="col-6">
                    <small class="text-muted d-block">已启用</small>
                    <strong class="text-success">{{
                      stats?.enabledPipelines || 0
                    }}</strong>
                  </div>
                  <div class="col-6">
                    <small class="text-muted d-block">已禁用</small>
                    <strong class="text-secondary">{{
                      stats?.disabledPipelines || 0
                    }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 数据源统计 -->
        <div class="col-6 col-md-3">
          <div class="card h-100 shadow-sm border-success">
            <div class="card-body">
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div
                    class="stat-icon bg-success text-white rounded-circle d-flex align-items-center justify-content-center"
                    style="width: 48px; height: 48px"
                  >
                    <i class="fas fa-database fa-lg"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <div class="stat-label text-muted small">数据源</div>
                  <div class="stat-value h4 mb-0">
                    {{ stats?.datasources || 0 }}
                  </div>
                </div>
              </div>
              <div class="mt-2 pt-2 border-top">
                <div class="row g-2 text-center">
                  <div class="col-12">
                    <small class="text-muted d-block">Git 仓库</small>
                    <strong>{{ stats?.datasources || 0 }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 镜像仓库统计 -->
        <div class="col-6 col-md-3">
          <div class="card h-100 shadow-sm border-warning">
            <div class="card-body">
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div
                    class="stat-icon bg-warning text-white rounded-circle d-flex align-items-center justify-content-center"
                    style="width: 48px; height: 48px"
                  >
                    <i class="fas fa-box fa-lg"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <div class="stat-label text-muted small">镜像仓库</div>
                  <div class="stat-value h4 mb-0">
                    {{ stats?.registries || 0 }}
                  </div>
                </div>
              </div>
              <div class="mt-2 pt-2 border-top">
                <div class="row g-2 text-center">
                  <div class="col-12">
                    <small class="text-muted d-block">已配置</small>
                    <strong>{{ stats?.registries || 0 }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 第二行统计卡片 -->
      <div class="row g-3 mb-4">
        <!-- 模板统计 -->
        <div class="col-6 col-md-3">
          <div class="card h-100 shadow-sm border-secondary">
            <div class="card-body">
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div
                    class="stat-icon bg-secondary text-white rounded-circle d-flex align-items-center justify-content-center"
                    style="width: 48px; height: 48px"
                  >
                    <i class="fas fa-layer-group fa-lg"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <div class="stat-label text-muted small">模板</div>
                  <div class="stat-value h4 mb-0">
                    {{ stats?.templates || 0 }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 资源包统计 -->
        <div class="col-6 col-md-3">
          <div class="card h-100 shadow-sm border-dark">
            <div class="card-body">
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div
                    class="stat-icon bg-dark text-white rounded-circle d-flex align-items-center justify-content-center"
                    style="width: 48px; height: 48px"
                  >
                    <i class="fas fa-archive fa-lg"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <div class="stat-label text-muted small">资源包</div>
                  <div class="stat-value h4 mb-0">
                    {{ stats?.resourcePackages || 0 }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 主机统计 -->
        <div class="col-6 col-md-3">
          <div class="card h-100 shadow-sm border-danger">
            <div class="card-body">
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div
                    class="stat-icon bg-danger text-white rounded-circle d-flex align-items-center justify-content-center"
                    style="width: 48px; height: 48px"
                  >
                    <i class="fas fa-server fa-lg"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <div class="stat-label text-muted small">主机</div>
                  <div class="stat-value h4 mb-0">{{ stats?.hosts || 0 }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 存储统计 -->
        <div class="col-6 col-md-3">
          <div class="card h-100 shadow-sm border-primary">
            <div class="card-body">
              <div class="d-flex align-items-center">
                <div class="flex-shrink-0">
                  <div
                    class="stat-icon bg-primary text-white rounded-circle d-flex align-items-center justify-content-center"
                    style="width: 48px; height: 48px"
                  >
                    <i class="fas fa-hdd fa-lg"></i>
                  </div>
                </div>
                <div class="flex-grow-1 ms-3">
                  <div class="stat-label text-muted small">存储使用</div>
                  <div class="stat-value h6 mb-0">
                    {{ formatStorage(stats?.totalStorage || 0) }}
                  </div>
                </div>
              </div>
              <div class="mt-2 pt-2 border-top">
                <div class="row g-2">
                  <div class="col-12">
                    <small class="text-muted d-block">构建目录</small>
                    <strong>{{
                      formatStorage(stats?.buildStorage || 0)
                    }}</strong>
                  </div>
                  <div class="col-12">
                    <small class="text-muted d-block">导出目录</small>
                    <strong>{{
                      formatStorage(stats?.exportStorage || 0)
                    }}</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 系统信息 -->
      <div class="row g-3">
        <div class="col-12">
          <div class="card shadow-sm">
            <div class="card-header bg-white">
              <h6 class="mb-0">
                <i class="fas fa-info-circle text-info"></i> 系统信息
              </h6>
            </div>
            <div class="card-body">
              <div v-if="systemInfo" class="system-info">
                <div class="row g-3">
                  <!-- Docker 连接状态 -->
                  <div class="col-12 col-md-6 col-lg-3">
                    <div class="border rounded p-3 h-100 bg-light">
                      <div class="d-flex align-items-center mb-2">
                        <i class="fab fa-docker text-info fa-lg me-2"></i>
                        <strong>Docker 状态</strong>
                      </div>
                      <div class="mb-2">
                        <span
                          class="badge"
                          :class="
                            systemInfo.connected ? 'bg-success' : 'bg-danger'
                          "
                        >
                          {{ systemInfo.connected ? "已连接" : "未连接" }}
                        </span>
                      </div>
                      <div
                        v-if="systemInfo.builder_type"
                        class="small text-muted"
                      >
                        <div>
                          类型:
                          <strong>{{
                            systemInfo.builder_type === "local"
                              ? "本地"
                              : systemInfo.builder_type === "remote"
                              ? "远程"
                              : "模拟"
                          }}</strong>
                        </div>
                        <div v-if="systemInfo.remote_host" class="mt-1">
                          地址: <strong>{{ systemInfo.remote_host }}</strong>
                        </div>
                      </div>
                      <div v-if="systemInfo.connection_error" class="mt-2">
                        <div class="alert alert-danger alert-sm mb-0 py-1 px-2">
                          <small
                            ><i class="fas fa-exclamation-triangle"></i>
                            {{ systemInfo.connection_error }}</small
                          >
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Docker 版本信息 -->
                  <div class="col-12 col-md-6 col-lg-3">
                    <div class="border rounded p-3 h-100 bg-light">
                      <div class="d-flex align-items-center mb-2">
                        <i
                          class="fas fa-code-branch text-primary fa-lg me-2"
                        ></i>
                        <strong>版本信息</strong>
                      </div>
                      <div class="small">
                        <div v-if="systemInfo.version" class="mb-1">
                          <span class="text-muted">Docker:</span>
                          <strong class="ms-1">{{ systemInfo.version }}</strong>
                        </div>
                        <div v-if="systemInfo.api_version" class="mb-1">
                          <span class="text-muted">API:</span>
                          <strong class="ms-1">{{
                            systemInfo.api_version
                          }}</strong>
                        </div>
                        <div v-if="systemInfo.runtime" class="mb-1">
                          <span class="text-muted">运行时:</span>
                          <strong class="ms-1">{{ systemInfo.runtime }}</strong>
                        </div>
                        <div v-if="systemInfo.buildx_available" class="mb-1">
                          <span class="badge bg-success">Buildx 可用</span>
                          <span
                            v-if="systemInfo.buildx_version"
                            class="text-muted small ms-1"
                          >
                            (v{{ systemInfo.buildx_version }})
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 系统资源 -->
                  <div class="col-12 col-md-6 col-lg-3">
                    <div class="border rounded p-3 h-100 bg-light">
                      <div class="d-flex align-items-center mb-2">
                        <i class="fas fa-server text-success fa-lg me-2"></i>
                        <strong>系统资源</strong>
                      </div>
                      <div class="small">
                        <div v-if="systemInfo.ncpu" class="mb-1">
                          <span class="text-muted">CPU 核心:</span>
                          <strong class="ms-1">{{ systemInfo.ncpu }} 核</strong>
                        </div>
                        <div v-if="systemInfo.mem_total" class="mb-1">
                          <span class="text-muted">内存:</span>
                          <strong class="ms-1">{{
                            formatStorage(systemInfo.mem_total)
                          }}</strong>
                        </div>
                        <div v-if="systemInfo.os_type" class="mb-1">
                          <span class="text-muted">系统:</span>
                          <strong class="ms-1">{{ systemInfo.os_type }}</strong>
                        </div>
                        <div v-if="systemInfo.arch" class="mb-1">
                          <span class="text-muted">架构:</span>
                          <strong class="ms-1">{{ systemInfo.arch }}</strong>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Docker 资源统计 -->
                  <div class="col-12 col-md-6 col-lg-3">
                    <div class="border rounded p-3 h-100 bg-light">
                      <div class="d-flex align-items-center mb-2">
                        <i class="fas fa-cubes text-warning fa-lg me-2"></i>
                        <strong>资源统计</strong>
                      </div>
                      <div class="small">
                        <div
                          v-if="systemInfo.images_count !== undefined"
                          class="mb-1"
                        >
                          <span class="text-muted">镜像:</span>
                          <strong class="ms-1">{{
                            systemInfo.images_count
                          }}</strong>
                          <span
                            v-if="systemInfo.images_size > 0"
                            class="text-muted small ms-1"
                          >
                            ({{ formatStorage(systemInfo.images_size) }})
                          </span>
                        </div>
                        <div
                          v-if="systemInfo.containers_total !== undefined"
                          class="mb-1"
                        >
                          <span class="text-muted">容器:</span>
                          <strong class="ms-1">{{
                            systemInfo.containers_total
                          }}</strong>
                          <span
                            v-if="systemInfo.containers_running !== undefined"
                            class="text-success small ms-1"
                          >
                            (运行: {{ systemInfo.containers_running }})
                          </span>
                        </div>
                        <div
                          v-if="systemInfo.volumes_count !== undefined"
                          class="mb-1"
                        >
                          <span class="text-muted">数据卷:</span>
                          <strong class="ms-1">{{
                            systemInfo.volumes_count
                          }}</strong>
                        </div>
                        <div
                          v-if="systemInfo.networks_count !== undefined"
                          class="mb-1"
                        >
                          <span class="text-muted">网络:</span>
                          <strong class="ms-1">{{
                            systemInfo.networks_count
                          }}</strong>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 其他系统信息 -->
                <div
                  v-if="
                    systemInfo.storage_driver ||
                    systemInfo.docker_root ||
                    systemInfo.kernel_version
                  "
                  class="row g-3 mt-2"
                >
                  <div class="col-12">
                    <div class="border rounded p-3 bg-light">
                      <div class="d-flex align-items-center mb-2">
                        <i class="fas fa-cog text-secondary fa-lg me-2"></i>
                        <strong>系统配置</strong>
                      </div>
                      <div class="row g-2 small">
                        <div
                          v-if="systemInfo.storage_driver"
                          class="col-12 col-md-4"
                        >
                          <span class="text-muted">存储驱动:</span>
                          <strong class="ms-1">{{
                            systemInfo.storage_driver
                          }}</strong>
                        </div>
                        <div
                          v-if="systemInfo.docker_root"
                          class="col-12 col-md-4"
                        >
                          <span class="text-muted">Docker 根目录:</span>
                          <strong class="ms-1 font-monospace small">{{
                            systemInfo.docker_root
                          }}</strong>
                        </div>
                        <div
                          v-if="systemInfo.kernel_version"
                          class="col-12 col-md-4"
                        >
                          <span class="text-muted">内核版本:</span>
                          <strong class="ms-1">{{
                            systemInfo.kernel_version
                          }}</strong>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="text-center py-4 text-muted">
                <span class="spinner-border spinner-border-sm"></span>
                <span class="ms-2">加载系统信息中...</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from "axios";
import { onMounted, onUnmounted, ref } from "vue";

const emit = defineEmits(["navigate"]);

const loading = ref(false);
const stats = ref(null);
const systemInfo = ref(null);

// 加载仪表盘数据
async function loadDashboard() {
  loading.value = true;
  try {
    // 并行加载仪表盘统计和 Docker 信息
    const [dashboardRes, dockerInfoRes] = await Promise.all([
      axios.get("/api/dashboard/stats"),
      axios.get("/api/docker/info").catch(() => ({ data: null })), // Docker 信息可能加载失败，不影响其他数据
    ]);

    // 使用后台计算的统计数据
    if (dashboardRes.data && dashboardRes.data.success) {
      stats.value = dashboardRes.data.stats;
    } else {
      // 如果后台接口失败，使用默认值
      stats.value = {
        totalTasks: 0,
        runningTasks: 0,
        completedTasks: 0,
        pipelines: 0,
        enabledPipelines: 0,
        disabledPipelines: 0,
        datasources: 0,
        registries: 0,
        templates: 0,
        resourcePackages: 0,
        hosts: 0,
        buildStorage: 0,
        exportStorage: 0,
        totalStorage: 0,
      };
    }

    // 加载系统信息
    if (dockerInfoRes && dockerInfoRes.data) {
      systemInfo.value = dockerInfoRes.data;
    }
  } catch (error) {
    console.error("加载仪表盘数据失败:", error);
    alert(
      "加载仪表盘数据失败: " + (error.response?.data?.detail || error.message)
    );
    // 发生错误时使用默认值
    stats.value = {
      totalTasks: 0,
      runningTasks: 0,
      completedTasks: 0,
      pipelines: 0,
      enabledPipelines: 0,
      disabledPipelines: 0,
      datasources: 0,
      registries: 0,
      templates: 0,
      resourcePackages: 0,
      hosts: 0,
      buildStorage: 0,
      exportStorage: 0,
      totalStorage: 0,
    };
  } finally {
    loading.value = false;
  }
}

// 格式化存储大小
function formatStorage(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

// 格式化时间
function formatTime(timeStr) {
  if (!timeStr) return "-";
  try {
    const date = new Date(timeStr);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "刚刚";
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;
    return date.toLocaleDateString("zh-CN");
  } catch {
    return timeStr;
  }
}

// 获取任务类型标签
function getTaskTypeLabel(type) {
  const map = {
    build: "构建",
    export: "导出",
  };
  return map[type] || type;
}

// 获取任务类型徽章样式
function getTaskTypeBadge(type) {
  const map = {
    build: "bg-primary",
    export: "bg-info",
  };
  return map[type] || "bg-secondary";
}

// 获取状态标签
function getStatusLabel(status) {
  const map = {
    pending: "等待中",
    running: "运行中",
    completed: "已完成",
    failed: "失败",
    cancelled: "已取消",
  };
  return map[status] || status;
}

// 获取状态徽章样式
function getStatusBadge(status) {
  const map = {
    pending: "bg-secondary",
    running: "bg-warning",
    completed: "bg-success",
    failed: "bg-danger",
    cancelled: "bg-dark",
  };
  return map[status] || "bg-secondary";
}

onMounted(() => {
  loadDashboard();
});
</script>

<style scoped>
.dashboard-panel {
  min-height: 400px;
}

.stat-icon {
  font-size: 1.2rem;
}

.stat-label {
  font-size: 0.85rem;
  font-weight: 500;
}

.stat-value {
  font-weight: 600;
  color: #212529;
}

.card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15) !important;
}

.table {
  font-size: 0.9rem;
}

.table th {
  font-weight: 600;
  font-size: 0.85rem;
  background-color: #f8f9fa;
}

code {
  font-size: 0.8rem;
  background-color: #f8f9fa;
  padding: 0.2rem 0.4rem;
  border-radius: 0.25rem;
}

.system-info {
  font-size: 0.9rem;
}

.alert-sm {
  font-size: 0.85rem;
  padding: 0.5rem 0.75rem;
}

.bg-light {
  background-color: #f8f9fa !important;
}
</style>

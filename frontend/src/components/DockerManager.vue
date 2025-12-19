<template>
  <div class="docker-manager">
    <!-- Docker 服务信息区域 -->
    <div class="card mb-3">
      <div
        class="card-header bg-primary text-white d-flex justify-content-between align-items-center py-2"
      >
        <div>
          <i class="fas fa-server"></i>
          <strong class="ms-1">Docker 服务信息</strong>
          <small
            v-if="dockerInfo && dockerInfo.cached_at"
            class="ms-3 opacity-75"
          >
            <i class="fas fa-clock"></i>
            缓存时间: {{ formatTime(dockerInfo.cached_at) }}
            <span v-if="dockerInfo.cache_age_minutes" class="ms-1">
              ({{ dockerInfo.cache_age_minutes }}分钟前)
            </span>
          </small>
        </div>
        <div class="d-flex gap-2">
          <button
            class="btn btn-sm btn-light"
            @click="refreshDockerInfo(false)"
            :disabled="loadingInfo"
            title="刷新（使用缓存）"
          >
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingInfo }"></i>
          </button>
          <button
            class="btn btn-sm btn-warning"
            @click="forceRefreshDockerInfo()"
            :disabled="loadingInfo"
            title="强制刷新（重新获取）"
          >
            <i class="fas fa-sync-alt fa-spin" v-if="loadingInfo"></i>
            <i class="fas fa-redo" v-else></i>
            <span class="ms-1 d-none d-md-inline">强制刷新</span>
          </button>
        </div>
      </div>
      <div class="card-body py-2">
        <div v-if="loadingInfo" class="text-center py-3">
          <div class="spinner-border spinner-border-sm text-primary"></div>
          <span class="ms-2">正在获取 Docker 信息...</span>
        </div>

        <div v-else-if="dockerInfo" class="row g-2">
          <!-- 第一行：基本信息 -->
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">连接状态</div>
              <div class="info-value">
                <span
                  class="badge"
                  :class="dockerInfo.connected ? 'bg-success' : 'bg-danger'"
                >
                  {{ dockerInfo.connected ? "已连接" : "未连接" }}
                </span>
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">Docker 版本</div>
              <div class="info-value">{{ dockerInfo.version || "-" }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">API 版本</div>
              <div class="info-value">{{ dockerInfo.api_version || "-" }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">构建器类型</div>
              <div class="info-value">
                <span
                  class="badge"
                  :class="getBuilderBadgeClass(dockerInfo.builder_type)"
                >
                  {{ getBuilderLabel(dockerInfo.builder_type) }}
                </span>
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">Buildx 支持</div>
              <div class="info-value">
                <span
                  class="badge"
                  :class="
                    dockerInfo.buildx_available ? 'bg-success' : 'bg-warning'
                  "
                >
                  {{ dockerInfo.buildx_available ? "✓ 支持" : "✗ 不支持" }}
                </span>
                <small
                  v-if="dockerInfo.buildx_version"
                  class="d-block text-muted mt-1"
                >
                  {{ dockerInfo.buildx_version }}
                </small>
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2" v-if="dockerInfo.remote_host">
            <div class="info-item">
              <div class="info-label">远程主机</div>
              <div class="info-value small">{{ dockerInfo.remote_host }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">操作系统</div>
              <div class="info-value">
                {{ dockerInfo.os_type || "-" }} {{ dockerInfo.arch || "" }}
              </div>
            </div>
          </div>

          <!-- 第二行：资源统计 -->
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">镜像数量</div>
              <div class="info-value">{{ dockerInfo.images_count || 0 }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">容器(运行/总)</div>
              <div class="info-value">
                <span class="text-success">{{
                  dockerInfo.containers_running || 0
                }}</span>
                / {{ dockerInfo.containers_total || 0 }}
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">存储驱动</div>
              <div class="info-value">
                {{ dockerInfo.storage_driver || "-" }}
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">数据根目录</div>
              <div
                class="info-value small text-truncate"
                :title="dockerInfo.docker_root"
              >
                {{ dockerInfo.docker_root || "-" }}
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">镜像占用</div>
              <div class="info-value">
                {{ formatBytes(dockerInfo.images_size) }}
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">容器占用</div>
              <div class="info-value">
                {{ formatBytes(dockerInfo.containers_size) }}
              </div>
            </div>
          </div>

          <!-- 第三行：系统信息 -->
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">CPU 核心</div>
              <div class="info-value">{{ dockerInfo.ncpu || "-" }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">总内存</div>
              <div class="info-value">
                {{ formatBytes(dockerInfo.mem_total) }}
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">内核版本</div>
              <div class="info-value small">
                {{ dockerInfo.kernel_version || "-" }}
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">运行时</div>
              <div class="info-value">{{ dockerInfo.runtime || "-" }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">数据卷数量</div>
              <div class="info-value">{{ dockerInfo.volumes_count || 0 }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">网络数量</div>
              <div class="info-value">{{ dockerInfo.networks_count || 0 }}</div>
            </div>
          </div>
        </div>

        <div v-else class="alert alert-warning mb-0 py-2">
          <i class="fas fa-exclamation-triangle"></i>
          无法获取 Docker 信息，请检查服务状态
        </div>

        <!-- 编译方式限制说明 -->
        <div v-if="dockerInfo" class="alert alert-info alert-sm mb-0 mt-2 py-2">
          <div class="d-flex align-items-start">
            <i class="fas fa-info-circle me-2 mt-1"></i>
            <div class="flex-grow-1">
              <strong>编译方式说明：</strong>
              <ul class="mb-0 mt-1 small">
                <li>
                  <strong>容器内编译（本地 Docker）：</strong>
                  通过挂载的 docker.sock 连接本地
                  Docker，仅支持简单的编译任务，适用于基础项目构建
                </li>
                <li>
                  <strong>远程 Docker：</strong>
                  通过 TCP 或 TLS 连接远程 Docker 服务器进行构建。 TCP
                  模式（默认端口 2375）为明文传输，TLS 模式（默认端口
                  2376）为加密传输。
                  支持完整的编译功能，适用于复杂项目构建和生产环境
                </li>
              </ul>
              <div
                v-if="dockerInfo.builder_type === 'local'"
                class="mt-2 small text-muted"
              >
                <i class="fas fa-check-circle text-success"></i>
                当前模式：<strong>容器内编译（本地 Docker）</strong>
                <span v-if="dockerInfo.buildx_available" class="ms-2">
                  <i class="fas fa-check text-success"></i> Buildx:
                  {{ dockerInfo.buildx_version }}
                </span>
                <span v-else class="ms-2">
                  <i class="fas fa-exclamation-triangle text-warning"></i>
                  Buildx 不可用
                </span>
              </div>
              <div
                v-else-if="
                  dockerInfo.builder_type === 'remote' && dockerInfo.remote_host
                "
                class="mt-2 small text-muted"
              >
                <i class="fas fa-check-circle text-success"></i>
                当前模式：<strong>{{ getCurrentBuildMode() }}</strong> ({{
                  dockerInfo.remote_host
                }})
                <span v-if="dockerInfo.buildx_available" class="ms-2">
                  <i class="fas fa-check text-success"></i> Buildx:
                  {{ dockerInfo.buildx_version }}
                </span>
                <span v-else class="ms-2">
                  <i class="fas fa-exclamation-triangle text-warning"></i>
                  Buildx 不可用
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 容器和镜像 Tab 管理 -->
    <div class="card">
      <div class="card-header bg-white py-0">
        <ul class="nav nav-tabs border-0">
          <li class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'containers' }"
              @click="activeTab = 'containers'"
              type="button"
            >
              <i class="fas fa-cubes"></i> 容器管理
              <span v-if="containerTotal > 0" class="badge bg-info ms-1">{{
                containerTotal
              }}</span>
            </button>
          </li>
          <li class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'images' }"
              @click="activeTab = 'images'"
              type="button"
            >
              <i class="fas fa-images"></i> 镜像管理
              <span v-if="imageTotal > 0" class="badge bg-secondary ms-1">{{
                imageTotal
              }}</span>
            </button>
          </li>
        </ul>
      </div>

      <!-- 容器 Tab -->
      <div v-show="activeTab === 'containers'" class="card-body p-0">
        <!-- 搜索和操作栏 -->
        <div
          class="d-flex justify-content-between align-items-center p-2 border-bottom bg-light"
        >
          <div class="d-flex gap-2 align-items-center flex-grow-1">
            <div class="input-group input-group-sm" style="max-width: 300px">
              <span class="input-group-text"
                ><i class="fas fa-search"></i
              ></span>
              <input
                type="text"
                class="form-control"
                v-model="containerSearch"
                placeholder="搜索容器名称/镜像..."
                @input="filterContainers"
              />
            </div>
            <select
              class="form-select form-select-sm"
              style="width: auto"
              v-model="containerStatusFilter"
              @change="filterContainers"
            >
              <option value="">全部状态</option>
              <option value="running">运行中</option>
              <option value="exited">已停止</option>
              <option value="paused">已暂停</option>
            </select>
            <small v-if="containerLastSync" class="text-muted">
              <i class="fas fa-clock"></i> {{ formatTime(containerLastSync) }}
            </small>
          </div>
          <div class="d-flex gap-1">
            <button
              class="btn btn-sm btn-warning"
              @click="pruneContainers"
              :disabled="loadingContainers"
              title="清理已停止的容器"
            >
              <i class="fas fa-broom"></i> 清理
            </button>
            <button
              class="btn btn-sm btn-primary"
              @click="loadContainers(true)"
              :disabled="loadingContainers"
            >
              <i
                class="fas fa-sync-alt"
                :class="{ 'fa-spin': loadingContainers }"
              ></i>
            </button>
          </div>
        </div>

        <div v-if="loadingContainers" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-info"></div>
          <span class="ms-2">加载容器列表...</span>
        </div>

        <div
          v-else-if="containers.length === 0"
          class="text-center text-muted py-4"
        >
          <i class="fas fa-cube"></i>
          {{
            containerSearch || containerStatusFilter
              ? "未找到匹配的容器"
              : "暂无容器"
          }}
        </div>

        <div v-else class="table-responsive">
          <table class="table table-hover table-sm mb-0">
            <thead class="table-light">
              <tr>
                <th>容器名称</th>
                <th>镜像</th>
                <th>状态</th>
                <th>端口</th>
                <th>创建时间</th>
                <th class="text-end">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in containers" :key="c.id">
                <td>
                  <code class="small">{{ c.name }}</code>
                </td>
                <td
                  class="small text-muted text-truncate"
                  style="max-width: 200px"
                  :title="c.image"
                >
                  {{ c.image }}
                </td>
                <td>
                  <span class="badge" :class="getStatusBadge(c.state)">{{
                    c.status
                  }}</span>
                </td>
                <td class="small">{{ c.ports || "-" }}</td>
                <td class="small">{{ formatTime(c.created) }}</td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button
                      v-if="c.state !== 'running'"
                      class="btn btn-outline-success"
                      @click="startContainer(c)"
                      title="启动"
                    >
                      <i class="fas fa-play"></i>
                    </button>
                    <button
                      v-if="c.state === 'running'"
                      class="btn btn-outline-warning"
                      @click="stopContainer(c, false)"
                      title="停止"
                    >
                      <i class="fas fa-stop"></i>
                    </button>
                    <button
                      v-if="c.state === 'running'"
                      class="btn btn-outline-danger"
                      @click="stopContainer(c, true)"
                      title="强制停止"
                    >
                      <i class="fas fa-power-off"></i>
                    </button>
                    <button
                      v-if="c.state === 'running'"
                      class="btn btn-outline-info"
                      @click="restartContainer(c)"
                      title="重启"
                    >
                      <i class="fas fa-redo"></i>
                    </button>
                    <button
                      class="btn btn-outline-danger"
                      @click="removeContainer(c)"
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

        <!-- 容器分页 -->
        <div
          v-if="containerTotalPages > 1"
          class="d-flex justify-content-between align-items-center p-2 border-top"
        >
          <div class="text-muted small">
            显示第
            {{
              containerTotal > 0
                ? (containerPage - 1) * containerPageSize + 1
                : 0
            }}
            -
            {{ Math.min(containerPage * containerPageSize, containerTotal) }}
            条，共 {{ containerTotal }} 条
          </div>
          <nav>
            <ul class="pagination pagination-sm mb-0">
              <li class="page-item" :class="{ disabled: containerPage === 1 }">
                <button
                  class="page-link"
                  @click="changeContainerPage(1)"
                  :disabled="containerPage === 1"
                >
                  <i class="fas fa-angle-double-left"></i>
                </button>
              </li>
              <li class="page-item" :class="{ disabled: containerPage === 1 }">
                <button
                  class="page-link"
                  @click="changeContainerPage(containerPage - 1)"
                  :disabled="containerPage === 1"
                >
                  <i class="fas fa-angle-left"></i>
                </button>
              </li>
              <li
                v-for="page in visibleContainerPages"
                :key="page"
                class="page-item"
                :class="{ active: containerPage === page }"
              >
                <button class="page-link" @click="changeContainerPage(page)">
                  {{ page }}
                </button>
              </li>
              <li
                class="page-item"
                :class="{ disabled: containerPage === containerTotalPages }"
              >
                <button
                  class="page-link"
                  @click="changeContainerPage(containerPage + 1)"
                  :disabled="containerPage === containerTotalPages"
                >
                  <i class="fas fa-angle-right"></i>
                </button>
              </li>
              <li
                class="page-item"
                :class="{ disabled: containerPage === containerTotalPages }"
              >
                <button
                  class="page-link"
                  @click="changeContainerPage(containerTotalPages)"
                  :disabled="containerPage === containerTotalPages"
                >
                  <i class="fas fa-angle-double-right"></i>
                </button>
              </li>
            </ul>
          </nav>
        </div>
      </div>

      <!-- 镜像 Tab -->
      <div v-show="activeTab === 'images'" class="card-body p-0">
        <!-- 搜索和操作栏 -->
        <div
          class="d-flex justify-content-between align-items-center p-2 border-bottom bg-light"
        >
          <div class="d-flex gap-2 align-items-center flex-grow-1">
            <div class="input-group input-group-sm" style="max-width: 300px">
              <span class="input-group-text"
                ><i class="fas fa-search"></i
              ></span>
              <input
                type="text"
                class="form-control"
                v-model="imageSearch"
                placeholder="搜索镜像名称/标签..."
                @input="filterImages"
              />
            </div>
            <select
              class="form-select form-select-sm"
              style="width: auto"
              v-model="imageTagFilter"
              @change="filterImages"
            >
              <option value="">全部标签</option>
              <option value="latest">latest</option>
              <option value="none">&lt;none&gt;</option>
            </select>
            <small v-if="imageLastSync" class="text-muted">
              <i class="fas fa-clock"></i> {{ formatTime(imageLastSync) }}
            </small>
          </div>
          <div class="d-flex gap-1">
            <button
              class="btn btn-sm btn-warning"
              @click="pruneImages"
              :disabled="loadingImages"
              title="清理未使用镜像"
            >
              <i class="fas fa-broom"></i> 清理
            </button>
            <button
              class="btn btn-sm btn-primary"
              @click="loadImages(true)"
              :disabled="loadingImages"
            >
              <i
                class="fas fa-sync-alt"
                :class="{ 'fa-spin': loadingImages }"
              ></i>
            </button>
          </div>
        </div>

        <div v-if="loadingImages" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-secondary"></div>
          <span class="ms-2">加载镜像列表...</span>
        </div>

        <div
          v-else-if="images.length === 0"
          class="text-center text-muted py-4"
        >
          <i class="fas fa-box-open"></i>
          {{ imageSearch || imageTagFilter ? "未找到匹配的镜像" : "暂无镜像" }}
        </div>

        <div v-else class="table-responsive">
          <table class="table table-hover table-sm mb-0">
            <thead class="table-light">
              <tr>
                <th>镜像名称</th>
                <th>标签</th>
                <th>镜像ID</th>
                <th>大小</th>
                <th>创建时间</th>
                <th class="text-end">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="img in images" :key="img.id + img.tag">
                <td>
                  <code class="small text-primary">{{
                    img.repository || "&lt;none&gt;"
                  }}</code>
                </td>
                <td>
                  <span class="badge bg-info">{{
                    img.tag || "&lt;none&gt;"
                  }}</span>
                </td>
                <td>
                  <small class="text-muted font-monospace">{{
                    img.id ? img.id.substring(7, 19) : "-"
                  }}</small>
                </td>
                <td class="small">{{ formatBytes(img.size) }}</td>
                <td class="small">{{ formatTime(img.created) }}</td>
                <td class="text-end">
                  <button
                    class="btn btn-sm btn-outline-danger"
                    @click="deleteImage(img)"
                    title="删除镜像"
                  >
                    <i class="fas fa-trash"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 镜像分页 -->
        <div
          v-if="imageTotalPages > 1"
          class="d-flex justify-content-between align-items-center p-2 border-top"
        >
          <div class="text-muted small">
            显示第
            {{ imageTotal > 0 ? (imagePage - 1) * imagePageSize + 1 : 0 }} -
            {{ Math.min(imagePage * imagePageSize, imageTotal) }}
            条，共 {{ imageTotal }} 条
          </div>
          <nav>
            <ul class="pagination pagination-sm mb-0">
              <li class="page-item" :class="{ disabled: imagePage === 1 }">
                <button
                  class="page-link"
                  @click="changeImagePage(1)"
                  :disabled="imagePage === 1"
                >
                  <i class="fas fa-angle-double-left"></i>
                </button>
              </li>
              <li class="page-item" :class="{ disabled: imagePage === 1 }">
                <button
                  class="page-link"
                  @click="changeImagePage(imagePage - 1)"
                  :disabled="imagePage === 1"
                >
                  <i class="fas fa-angle-left"></i>
                </button>
              </li>
              <li
                v-for="page in visibleImagePages"
                :key="page"
                class="page-item"
                :class="{ active: imagePage === page }"
              >
                <button class="page-link" @click="changeImagePage(page)">
                  {{ page }}
                </button>
              </li>
              <li
                class="page-item"
                :class="{ disabled: imagePage === imageTotalPages }"
              >
                <button
                  class="page-link"
                  @click="changeImagePage(imagePage + 1)"
                  :disabled="imagePage === imageTotalPages"
                >
                  <i class="fas fa-angle-right"></i>
                </button>
              </li>
              <li
                class="page-item"
                :class="{ disabled: imagePage === imageTotalPages }"
              >
                <button
                  class="page-link"
                  @click="changeImagePage(imageTotalPages)"
                  :disabled="imagePage === imageTotalPages"
                >
                  <i class="fas fa-angle-double-right"></i>
                </button>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, onMounted, ref, watch } from "vue";

// === Tab 控制 ===
const activeTab = ref("containers");

// === Docker 服务信息 ===
const dockerInfo = ref(null);
const loadingInfo = ref(false);
const infoLastSync = ref(null);
const infoCacheTimeout = 5 * 60 * 1000;

async function refreshDockerInfo(force = false) {
  loadingInfo.value = true;
  try {
    // 使用新的缓存API，force参数控制是否强制刷新
    const res = await axios.get("/api/docker/info", {
      params: { force_refresh: force },
    });
    dockerInfo.value = res.data;
    infoLastSync.value = dockerInfo.value.cached_at || new Date().toISOString();
  } catch (error) {
    console.error("获取 Docker 信息失败:", error);
    dockerInfo.value = null;
  } finally {
    loadingInfo.value = false;
  }
}

async function forceRefreshDockerInfo() {
  loadingInfo.value = true;
  try {
    // 使用强制刷新API
    const res = await axios.post("/api/docker/info/refresh");
    if (res.data.success && res.data.info) {
      dockerInfo.value = res.data.info;
      infoLastSync.value =
        dockerInfo.value.cached_at || new Date().toISOString();
      alert("Docker信息已强制刷新");
    }
  } catch (error) {
    console.error("强制刷新 Docker 信息失败:", error);
    alert("强制刷新失败: " + (error.response?.data?.detail || error.message));
  } finally {
    loadingInfo.value = false;
  }
}

// === 容器管理 ===
const containers = ref([]);
const loadingContainers = ref(false);
const containerLastSync = ref(null);
const containerPage = ref(1);
const containerPageSize = ref(10);
const containerTotal = ref(0);
const containerTotalPages = ref(0);
const containerSearch = ref("");
const containerStatusFilter = ref("");

// 容器可见页码列表
const visibleContainerPages = computed(() => {
  const total = containerTotalPages.value;
  const current = containerPage.value;
  const pages = [];

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i);
    }
  } else {
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) pages.push(i);
      pages.push("...");
      pages.push(total);
    } else if (current >= total - 3) {
      pages.push(1);
      pages.push("...");
      for (let i = total - 4; i <= total; i++) pages.push(i);
    } else {
      pages.push(1);
      pages.push("...");
      for (let i = current - 1; i <= current + 1; i++) pages.push(i);
      pages.push("...");
      pages.push(total);
    }
  }

  return pages.filter(
    (p) => p !== "..." || pages.indexOf(p) === pages.lastIndexOf(p)
  );
});

// 切换容器页码
function changeContainerPage(page) {
  if (
    page < 1 ||
    page > containerTotalPages.value ||
    page === containerPage.value
  )
    return;
  containerPage.value = page;
  loadContainers();
}

function filterContainers() {
  containerPage.value = 1;
  loadContainers();
}

async function loadContainers(force = false) {
  loadingContainers.value = true;
  try {
    // 使用后台分页，传递搜索和状态过滤参数
    const params = {
      page: containerPage.value,
      page_size: containerPageSize.value,
    };
    if (containerSearch.value) {
      params.search = containerSearch.value;
    }
    if (containerStatusFilter.value) {
      params.state = containerStatusFilter.value;
    }

    const res = await axios.get("/api/docker/containers", { params });
    containers.value = res.data.containers || [];
    containerTotal.value = res.data.total || 0;
    containerTotalPages.value = res.data.total_pages || 0;
    containerLastSync.value = new Date().toISOString();
  } catch (error) {
    console.error("加载容器列表失败:", error);
    containers.value = [];
    containerTotal.value = 0;
    containerTotalPages.value = 0;
  } finally {
    loadingContainers.value = false;
  }
}

async function startContainer(c) {
  try {
    await axios.post(`/api/docker/containers/${c.id}/start`);
    loadContainers(true);
  } catch (e) {
    alert(e.response?.data?.detail || "启动容器失败");
  }
}

async function stopContainer(c, force = false) {
  try {
    await axios.post(`/api/docker/containers/${c.id}/stop`, null, {
      params: { force },
    });
    loadContainers(true);
  } catch (e) {
    alert(e.response?.data?.detail || "停止容器失败");
  }
}

async function restartContainer(c) {
  try {
    await axios.post(`/api/docker/containers/${c.id}/restart`);
    loadContainers(true);
  } catch (e) {
    alert(e.response?.data?.detail || "重启容器失败");
  }
}

async function removeContainer(c) {
  if (!confirm(`确定要删除容器 ${c.name} 吗？`)) return;
  try {
    await axios.delete(`/api/docker/containers/${c.id}`);
    loadContainers(true);
  } catch (e) {
    alert(e.response?.data?.detail || "删除容器失败");
  }
}

async function pruneContainers() {
  if (!confirm("确定要清理所有已停止的容器吗？")) return;
  try {
    const res = await axios.post("/api/docker/containers/prune");
    alert(`已清理 ${res.data.deleted || 0} 个容器`);
    loadContainers(true);
    refreshDockerInfo(true);
  } catch (e) {
    alert(e.response?.data?.detail || "清理容器失败");
  }
}

// === 镜像管理 ===
const images = ref([]);
const loadingImages = ref(false);
const imageLastSync = ref(null);
const imagePage = ref(1);
const imagePageSize = ref(10);
const imageTotal = ref(0);
const imageTotalPages = ref(0);
const imageSearch = ref("");
const imageTagFilter = ref("");

// 镜像可见页码列表
const visibleImagePages = computed(() => {
  const total = imageTotalPages.value;
  const current = imagePage.value;
  const pages = [];

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      pages.push(i);
    }
  } else {
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) pages.push(i);
      pages.push("...");
      pages.push(total);
    } else if (current >= total - 3) {
      pages.push(1);
      pages.push("...");
      for (let i = total - 4; i <= total; i++) pages.push(i);
    } else {
      pages.push(1);
      pages.push("...");
      for (let i = current - 1; i <= current + 1; i++) pages.push(i);
      pages.push("...");
      pages.push(total);
    }
  }

  return pages.filter(
    (p) => p !== "..." || pages.indexOf(p) === pages.lastIndexOf(p)
  );
});

// 切换镜像页码
function changeImagePage(page) {
  if (page < 1 || page > imageTotalPages.value || page === imagePage.value)
    return;
  imagePage.value = page;
  loadImages();
}

function filterImages() {
  imagePage.value = 1;
  loadImages();
}

async function loadImages(force = false) {
  loadingImages.value = true;
  try {
    // 使用后台分页，传递搜索和标签过滤参数
    const params = {
      page: imagePage.value,
      page_size: imagePageSize.value,
    };
    if (imageSearch.value) {
      params.search = imageSearch.value;
    }
    if (imageTagFilter.value) {
      params.tag_filter = imageTagFilter.value;
    }

    const res = await axios.get("/api/docker/images", { params });
    images.value = res.data.images || [];
    imageTotal.value = res.data.total || 0;
    imageTotalPages.value = res.data.total_pages || 0;
    imageLastSync.value = new Date().toISOString();
  } catch (error) {
    console.error("加载镜像列表失败:", error);
    images.value = [];
    imageTotal.value = 0;
    imageTotalPages.value = 0;
  } finally {
    loadingImages.value = false;
  }
}

async function deleteImage(img) {
  const imgName =
    img.repository && img.tag ? `${img.repository}:${img.tag}` : img.id;
  if (!confirm(`确定要删除镜像 ${imgName} 吗？`)) return;
  try {
    await axios.delete("/api/docker/images", { data: { image_id: img.id } });
    loadImages(true);
    refreshDockerInfo(true);
  } catch (e) {
    alert(e.response?.data?.detail || "删除镜像失败");
  }
}

async function pruneImages() {
  if (!confirm("确定要清理所有未使用的镜像吗？这将释放磁盘空间。")) return;
  try {
    const res = await axios.post("/api/docker/images/prune");
    alert(`已清理，释放空间: ${formatBytes(res.data.space_reclaimed || 0)}`);
    loadImages(true);
    refreshDockerInfo(true);
  } catch (e) {
    alert(e.response?.data?.detail || "清理镜像失败");
  }
}

// === 工具函数 ===
function formatBytes(bytes) {
  if (!bytes) return "-";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let idx = 0,
    value = bytes;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx++;
  }
  return `${value.toFixed(1)} ${units[idx]}`;
}

function formatTime(timeStr) {
  if (!timeStr) return "-";
  try {
    return new Date(timeStr).toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return timeStr;
  }
}

function getBuilderBadgeClass(type) {
  return (
    { local: "bg-success", remote: "bg-primary", mock: "bg-warning" }[type] ||
    "bg-secondary"
  );
}

function getBuilderLabel(type) {
  return { local: "本地", remote: "远程", mock: "模拟" }[type] || "未知";
}

function getStatusBadge(state) {
  return (
    {
      running: "bg-success",
      exited: "bg-secondary",
      paused: "bg-warning",
      created: "bg-info",
    }[state] || "bg-secondary"
  );
}

// 获取当前编译模式名称
function getCurrentBuildMode() {
  if (!dockerInfo.value || dockerInfo.value.builder_type !== "remote") {
    return "";
  }
  // 优先使用 remote_config，如果没有则从 remote_host 解析
  const remoteConfig = dockerInfo.value.remote_config;
  if (remoteConfig) {
    if (remoteConfig.use_tls) {
      return "远程 Docker 主机（TLS）";
    } else if (remoteConfig.port === 2375) {
      return "TCP 2375 编译";
    } else {
      // 统一显示为"远程 Docker"
      const protocol = remoteConfig.use_tls ? "TLS" : "TCP";
      const port = remoteConfig.port || (remoteConfig.use_tls ? 2376 : 2375);
      return `远程 Docker (${protocol}://${remoteConfig.host}:${port})`;
    }
  } else {
    // 兼容旧格式：从 remote_host 解析
    const remoteHost = dockerInfo.value.remote_host || "";
    const portMatch = remoteHost.match(/:(\d+)$/);
    if (portMatch) {
      const port = parseInt(portMatch[1]);
      const protocol = port === 2376 ? "TLS" : "TCP";
      return `远程 Docker (${protocol}://${remoteHost})`;
    }
    return remoteHost ? `远程 Docker (${remoteHost})` : "远程 Docker";
  }
}

// 监听过滤条件变化，更新分页信息
watch([containerSearch, containerStatusFilter], () => {
  containerPage.value = 1;
  updateContainerPagination();
});

watch([imageSearch, imageTagFilter], () => {
  imagePage.value = 1;
  updateImagePagination();
});

onMounted(() => {
  refreshDockerInfo();
  loadContainers();
  loadImages();
});
</script>

<style scoped>
.docker-manager {
  animation: fadeIn 0.3s;
}
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Docker 信息卡片 */
.info-item {
  padding: 0.5rem;
  background: #f8f9fa;
  border-radius: 0.25rem;
  height: 100%;
}
.info-label {
  font-size: 0.75rem;
  color: #6c757d;
  margin-bottom: 0.15rem;
}
.info-value {
  font-size: 0.9rem;
  color: #212529;
  font-weight: 600;
}

/* 表格样式 */
.table th {
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
}
.table td {
  vertical-align: middle;
  font-size: 0.9rem;
}
.table-sm td,
.table-sm th {
  padding: 0.4rem 0.5rem;
}

/* 分页样式优化 */
.pagination .page-link {
  min-width: 38px;
  text-align: center;
}

.pagination .page-item.disabled .page-link {
  cursor: not-allowed;
}

.pagination .page-item.active .page-link {
  font-weight: 600;
}
</style>

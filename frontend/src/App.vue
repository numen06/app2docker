<template>
  <div id="app">
    <!-- 登录页面 -->
    <LoginPage v-if="!authenticated" @login-success="handleLoginSuccess" />

    <!-- 主应用 -->
    <div v-else class="bg-light" style="min-height: 100vh">
      <div class="container-fluid px-3 py-3" style="max-width: 1400px">
        <!-- 标题 -->
        <div class="text-center mb-4">
          <h1 class="mb-2 d-flex flex-wrap align-items-center justify-content-center gap-2">
            <span>
              <i class="fas fa-box-open text-primary"></i> App2Docker
            </span>
            <button
              type="button"
              class="btn btn-outline-secondary btn-sm align-middle"
              title="版本与更新"
              @click="openVersionModal"
            >
              <i class="fas fa-tag me-1"></i>v{{ appVersion || "…" }}
              <span
                v-if="updateStatus.hasUpdate"
                class="badge bg-danger ms-1"
                style="font-size: 0.65rem"
                >新</span
              >
            </button>
          </h1>
          <p class="lead text-muted mb-0">
            上传 Java/Node.js/Python/Go 应用，一键构建并推送 Docker 镜像
          </p>
        </div>

        <!-- 操作面板 -->
        <div class="card shadow-sm">
          <!-- 卡片头部：标题+操作按钮 -->
          <div
            class="card-header bg-white d-flex justify-content-between align-items-center py-2"
          >
            <h5 class="mb-0">
              <i class="fas fa-tools text-primary"></i> 操作面板
            </h5>
            <div class="d-flex gap-2">
              <div class="position-relative" v-if="runningTasksCount > 0">
                <button
                  class="btn btn-outline-warning btn-sm"
                  @click.stop="toggleRunningTasksPopup"
                  :class="{ active: showRunningTasksPopup }"
                >
                  <i class="fas fa-spinner fa-spin"></i> 运行任务
                  <span class="badge bg-danger ms-1">{{
                    runningTasksCount
                  }}</span>
                </button>
                <!-- 任务概况弹出框 -->
                <div
                  v-if="showRunningTasksPopup && runningTasksList.length > 0"
                  class="running-tasks-popup position-absolute top-100 start-0 mt-1 shadow-lg"
                  @click.stop
                >
                  <div
                    class="card border-warning"
                    style="min-width: 300px; max-width: 400px"
                  >
                    <div
                      class="card-header bg-warning bg-opacity-10 py-2 d-flex justify-content-between align-items-center"
                    >
                      <h6 class="mb-0">
                        <i class="fas fa-spinner fa-spin text-warning"></i>
                        正在运行的任务 ({{ runningTasksCount }})
                      </h6>
                      <button
                        class="btn-close btn-close-sm"
                        @click="showRunningTasksPopup = false"
                        aria-label="关闭"
                      ></button>
                    </div>
                    <div
                      class="card-body p-2"
                      style="max-height: 300px; overflow-y: auto"
                    >
                      <div
                        v-for="task in runningTasksList.slice(0, 10)"
                        :key="task.task_id"
                        class="mb-2 pb-2 border-bottom"
                      >
                        <div class="d-flex align-items-start">
                          <code class="small me-2">{{
                            task.task_id?.substring(0, 8) || "-"
                          }}</code>
                          <span
                            class="badge"
                            :class="getTaskTypeBadge(task.task_category)"
                          >
                            {{ getTaskTypeLabel(task.task_category) }}
                          </span>
                        </div>
                        <div
                          v-if="task.image || task.task_name"
                          class="mt-1 small text-muted"
                        >
                          {{ task.image || task.task_name || "-" }}
                          <span v-if="task.tag" class="ms-1"
                            >:{{ task.tag }}</span
                          >
                        </div>
                      </div>
                      <div
                        v-if="runningTasksCount > 10"
                        class="text-center text-muted small mt-2"
                      >
                        还有 {{ runningTasksCount - 10 }} 个任务...
                      </div>
                      <div class="text-center mt-3">
                        <button
                          class="btn btn-primary btn-sm"
                          @click="goToRunningTasks"
                        >
                          <i class="fas fa-arrow-right"></i> 查看详情
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <button
                v-else
                class="btn btn-outline-secondary btn-sm"
                @click="goToRunningTasks"
                title="暂无运行中的任务"
                disabled
              >
                <i class="fas fa-check-circle"></i> 运行任务
                <span class="badge bg-secondary ms-1">0</span>
              </button>
              <button
                class="btn btn-outline-primary btn-sm"
                @click="showUserCenter = true"
              >
                <i class="fas fa-user-circle"></i> 用户中心
              </button>
              <button
                class="btn btn-outline-primary btn-sm"
                @click="activeTab = 'logs'"
              >
                <i class="fas fa-history"></i> 操作日志
              </button>
              <button
                class="btn btn-outline-primary btn-sm"
                @click="showConfig = true"
              >
                <i class="fas fa-cog"></i> 配置
              </button>
              <button
                class="btn btn-outline-danger btn-sm"
                @click="handleLogout"
              >
                <i class="fas fa-sign-out-alt"></i> 登出
              </button>
            </div>
          </div>

          <!-- Tab 导航 -->
          <div class="card-header bg-white py-0 border-top-0">
            <ul class="nav nav-tabs border-0">
              <li v-if="hasPermission('menu.dashboard')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'dashboard' }"
                  @click="activeTab = 'dashboard'"
                >
                  <i class="fas fa-chart-line"></i> 仪表盘
                </button>
              </li>
              <li v-if="hasPermission('menu.build')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'step-build' }"
                  @click="activeTab = 'step-build'"
                >
                  <i class="fas fa-list-ol"></i> 镜像构建
                </button>
              </li>
              <li v-if="hasPermission('menu.export')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'export' }"
                  @click="activeTab = 'export'"
                >
                  <i class="fas fa-file-export"></i> 导出镜像
                </button>
              </li>
              <li v-if="hasPermission('menu.tasks')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'tasks' }"
                  @click="activeTab = 'tasks'"
                >
                  <i class="fas fa-list-check"></i> 任务管理
                </button>
              </li>
              <li v-if="hasPermission('menu.pipeline')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'pipeline' }"
                  @click="activeTab = 'pipeline'"
                >
                  <i class="fas fa-project-diagram"></i> 流水线
                </button>
              </li>
              <li v-if="hasPermission('menu.datasource')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'datasource' }"
                  @click="activeTab = 'datasource'"
                >
                  <i class="fas fa-database"></i> 数据源
                </button>
              </li>
              <li v-if="hasPermission('menu.registry')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'registry' }"
                  @click="activeTab = 'registry'"
                >
                  <i class="fas fa-box"></i> 镜像仓库
                </button>
              </li>
              <li v-if="hasPermission('menu.template')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'template' }"
                  @click="activeTab = 'template'"
                >
                  <i class="fas fa-layer-group"></i> 模板管理
                </button>
              </li>
              <li
                v-if="hasPermission('menu.resource-package')"
                class="nav-item"
              >
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'resource-package' }"
                  @click="activeTab = 'resource-package'"
                >
                  <i class="fas fa-archive"></i> 资源包
                </button>
              </li>
              <li v-if="hasPermission('menu.host')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'host' }"
                  @click="activeTab = 'host'"
                >
                  <i class="fas fa-server"></i> 主机管理
                </button>
              </li>
              <li v-if="hasPermission('menu.docker')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'docker' }"
                  @click="activeTab = 'docker'"
                >
                  <i class="fas fa-server"></i> Docker 管理
                </button>
              </li>
              <li v-if="hasPermission('menu.deploy')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'deploy' }"
                  @click="activeTab = 'deploy'"
                >
                  <i class="fas fa-rocket"></i> 部署管理
                </button>
              </li>
              <li v-if="hasPermission('menu.users')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'users' }"
                  @click="activeTab = 'users'"
                >
                  <i class="fas fa-users"></i> 用户管理
                </button>
              </li>
              <li v-if="hasPermission('menu.users')" class="nav-item">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: activeTab === 'roles' }"
                  @click="activeTab = 'roles'"
                >
                  <i class="fas fa-user-shield"></i> 角色管理
                </button>
              </li>
            </ul>
          </div>

          <!-- 标签页内容 -->
          <div class="card-body p-3" style="min-height: 400px">
            <DashboardPanel
              v-if="
                activeTab === 'dashboard' && hasPermission('menu.dashboard')
              "
              @navigate="handleNavigate"
            />
            <StepBuildPanel
              v-if="activeTab === 'step-build' && hasPermission('menu.build')"
            />
            <ExportPanel
              v-if="activeTab === 'export' && hasPermission('menu.export')"
            />
            <TemplatePanel
              v-if="activeTab === 'template' && hasPermission('menu.template')"
            />
            <OperationLogs v-if="activeTab === 'logs'" />
            <DockerManager
              v-if="activeTab === 'docker' && hasPermission('menu.docker')"
            />
            <PipelinePanel
              v-if="activeTab === 'pipeline' && hasPermission('menu.pipeline')"
            />
            <DataSourcePanel
              v-if="
                activeTab === 'datasource' && hasPermission('menu.datasource')
              "
            />
            <RegistryPanel
              v-if="activeTab === 'registry' && hasPermission('menu.registry')"
            />
            <TaskManager
              v-if="activeTab === 'tasks' && hasPermission('menu.tasks')"
            />
            <ResourcePackagePanel
              v-if="
                activeTab === 'resource-package' &&
                hasPermission('menu.resource-package')
              "
            />
            <UnifiedHostManager
              v-if="activeTab === 'host' && hasPermission('menu.host')"
            />
            <DeployTaskManager
              v-if="activeTab === 'deploy' && hasPermission('menu.deploy')"
            />
            <UserManagement
              v-if="activeTab === 'users' && hasPermission('menu.users')"
            />
            <RoleManagement
              v-if="activeTab === 'roles' && hasPermission('menu.users')"
            />
            <BuildConfigEditor
              v-if="activeTab === 'build-config-editor'"
              :initial-config="buildConfigToEdit"
              @save="handleBuildConfigSave"
              @cancel="handleBuildConfigCancel"
            />
          </div>
        </div>
      </div>

      <!-- 版本与更新（底部，与标题区按钮呼应） -->
      <div class="text-center text-muted small mt-2 mb-2 px-2">
        <span class="me-1">当前版本</span>
        <strong class="text-body">v{{ appVersion || "…" }}</strong>
        <span class="mx-1">·</span>
        <button
          type="button"
          class="btn btn-link btn-sm text-muted p-0 text-decoration-none align-baseline"
          @click="openVersionModal"
        >
          检查更新与发行说明
        </button>
      </div>

      <!-- 版本与更新对话框 -->
      <div
        ref="versionModalEl"
        class="modal fade"
        id="appVersionModal"
        tabindex="-1"
        aria-labelledby="appVersionModalLabel"
        aria-hidden="true"
      >
        <div class="modal-dialog modal-dialog-scrollable">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="appVersionModalLabel">
                <i class="fas fa-code-branch me-2"></i>版本与更新
              </h5>
              <button
                type="button"
                class="btn-close"
                data-bs-dismiss="modal"
                aria-label="关闭"
              ></button>
            </div>
            <div class="modal-body" v-if="checkLoading">
              <div class="text-center py-3 text-muted">
                <i class="fas fa-spinner fa-spin me-2"></i>正在检查…
              </div>
            </div>
            <div class="modal-body" v-else>
              <dl class="row small mb-2">
                <dt class="col-sm-4">当前版本</dt>
                <dd class="col-sm-8">
                  {{ displayCurrentVersion }}
                </dd>
                <dt class="col-sm-4">Gitee 最新</dt>
                <dd class="col-sm-8">
                  {{ updateStatus.latestVersion || "—" }}
                </dd>
                <dt v-if="updateStatus.releaseName" class="col-sm-4">
                  Release
                </dt>
                <dd v-if="updateStatus.releaseName" class="col-sm-8">
                  {{ updateStatus.releaseName }}
                </dd>
              </dl>
              <div
                v-if="!updateStatus.checkSuccess"
                class="alert alert-danger py-2 small"
                role="alert"
              >
                {{ updateStatus.checkMessage || "检查更新失败" }}
              </div>
              <div
                v-else-if="updateStatus.hasUpdate"
                class="alert alert-warning py-2 small"
                role="alert"
              >
                <strong>发现新版本</strong>，请前往 Gitee Release 拉取镜像或按说明升级。
              </div>
              <div
                v-else-if="updateStatus.latestVersion"
                class="alert alert-success py-2 small"
                role="alert"
              >
                已是最新版本。
              </div>
              <div v-if="updateStatus.checkSuccess && updateStatus.releaseBody">
                <div class="fw-semibold small mb-1">发行说明</div>
                <pre
                  class="small bg-light border rounded p-2 mb-0"
                  style="max-height: 240px; overflow-y: auto; white-space: pre-wrap"
                  >{{ updateStatus.releaseBody }}</pre
                >
              </div>
              <div v-else-if="updateStatus.checkSuccess && updateStatus.latestVersion" class="small text-muted">
                本 Release 暂无正文，可点击「在 Gitee 查看」。
              </div>
              <div class="mt-2 small d-flex flex-wrap gap-3">
                <a
                  href="https://gitee.com/numen06/app2docker/releases"
                  target="_blank"
                  rel="noopener noreferrer"
                  >全部发行版</a
                >
                <a
                  href="https://gitee.com/numen06/app2docker/tree/master/release-notes"
                  target="_blank"
                  rel="noopener noreferrer"
                  >仓库内版本说明（release-notes）</a
                >
              </div>
            </div>
            <div class="modal-footer">
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                data-bs-dismiss="modal"
              >
                关闭
              </button>
              <button
                type="button"
                class="btn btn-outline-primary btn-sm"
                :disabled="checkLoading"
                @click="refreshVersionCheck"
              >
                <i
                  class="fas fa-sync-alt"
                  :class="{ 'fa-spin': checkLoading }"
                ></i>
                重新检查
              </button>
              <button
                type="button"
                class="btn btn-primary btn-sm"
                :disabled="!updateStatus.releaseUrl"
                @click="openReleaseUrl"
              >
                在 Gitee 查看
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 新版本 Toast（每会话每个远端版本仅提示一次） -->
      <div
        class="toast-container position-fixed bottom-0 end-0 p-3"
        style="z-index: 1080"
      >
        <div
          ref="updateToastEl"
          id="appUpdateToast"
          class="toast"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
        >
          <div class="toast-header">
            <i class="fas fa-bell text-primary me-2"></i>
            <strong class="me-auto">发现新版本</strong>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="toast"
              aria-label="关闭"
            ></button>
          </div>
          <div class="toast-body small" ref="updateToastBody"></div>
        </div>
      </div>

      <!-- 配置模态框 -->
      <ConfigModal v-if="showConfig" v-model="showConfig" />

      <!-- 用户中心模态框 -->
      <UserCenterModal
        v-if="showUserCenter"
        v-model:show="showUserCenter"
        :username="username"
      />
    </div>
  </div>
</template>

<script setup>
import axios from "axios";
import { Modal, Toast } from "bootstrap";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useModalEscape } from "./composables/useModalEscape";
import { getToken, getUsername, isAuthenticated, logout } from "./utils/auth";

// 懒加载组件
import BuildConfigEditor from "./components/BuildConfigEditor.vue";
import ConfigModal from "./components/ConfigModal.vue";
import DashboardPanel from "./components/DashboardPanel.vue";
import DataSourcePanel from "./components/DataSourcePanel.vue";
import DeployTaskManager from "./components/DeployTaskManager.vue";
import DockerManager from "./components/DockerManager.vue";
import ExportPanel from "./components/ExportPanel.vue";
import LoginPage from "./components/LoginPage.vue";
import OperationLogs from "./components/OperationLogs.vue";
import PipelinePanel from "./components/PipelinePanel.vue";
import RegistryPanel from "./components/RegistryPanel.vue";
import ResourcePackagePanel from "./components/ResourcePackagePanel.vue";
import RoleManagement from "./components/RoleManagement.vue";
import StepBuildPanel from "./components/StepBuildPanel.vue";
import TaskManager from "./components/TaskManager.vue";
import TemplatePanel from "./components/TemplatePanel.vue";
import UnifiedHostManager from "./components/UnifiedHostManager.vue";
import UserCenterModal from "./components/UserCenterModal.vue";
import UserManagement from "./components/UserManagement.vue";
import { clearPermissionsCache, getUserPermissions } from "./utils/permissions";

const authenticated = ref(false);
const username = ref("");
const activeTab = ref("dashboard");
const showConfig = ref(false);
const showUserCenter = ref(false);
const runningTasksCount = ref(0);
const runningTasksList = ref([]);
const showRunningTasksPopup = ref(false);
const buildConfigToEdit = ref({});
const permissionsLoaded = ref(false);
const userPermissions = ref(new Set()); // 响应式的权限集合
let runningTasksTimer = null;

/** 版本与更新检查 */
const appVersion = ref("");
const checkLoading = ref(false);
const versionModalEl = ref(null);
const updateToastEl = ref(null);
const updateToastBody = ref(null);
const updateStatus = ref({
  hasUpdate: false,
  latestVersion: null,
  releaseUrl: null,
  releaseName: null,
  releaseBodySummary: null,
  currentVersion: null,
  releaseBody: null,
  checkSuccess: true,
  checkMessage: "",
});

const displayCurrentVersion = computed(() => {
  return (
    updateStatus.value.currentVersion ||
    appVersion.value ||
    "—"
  );
});

async function loadSystemVersion() {
  if (!authenticated.value) return;
  try {
    const res = await axios.get("/api/system/version");
    if (res.data?.success && res.data.version) {
      appVersion.value = res.data.version;
    }
  } catch (e) {
    console.error("获取系统版本失败:", e);
  }
}

function showUpdateToastOnce(resData) {
  const key = `update-notified-${resData.latest_version || "unknown"}`;
  if (sessionStorage.getItem(key)) return;
  sessionStorage.setItem(key, "1");
  const el = updateToastEl.value;
  const body = updateToastBody.value;
  if (!el || !body) return;
  const summary = resData.release_body_summary
    ? `\n${resData.release_body_summary}`
    : "";
  body.textContent = `当前 ${resData.current_version || "-"}，最新 ${resData.latest_version || "-"}${summary}`;
  body.onclick = null;
  body.style.cursor = "default";
  body.removeAttribute("title");
  if (resData.release_url) {
    body.style.cursor = "pointer";
    body.title = "点击打开 Gitee Release";
    body.onclick = () => {
      window.open(resData.release_url, "_blank", "noopener,noreferrer");
    };
  }
  const toast = Toast.getOrCreateInstance(el, { delay: 8000 });
  toast.show();
}

async function loadUpdateCheck(options = { showLoading: false }) {
  if (!authenticated.value) return;
  if (options.showLoading) checkLoading.value = true;
  try {
    const res = await axios.get("/api/system/version/check-update");
    const d = res.data || {};
    updateStatus.value = {
      hasUpdate: !!d.has_update,
      latestVersion: d.latest_version || null,
      releaseUrl: d.release_url || null,
      releaseName: d.release_name || null,
      releaseBodySummary: d.release_body_summary || null,
      currentVersion: d.current_version || null,
      releaseBody: d.release_body || null,
      checkSuccess: !!d.success,
      checkMessage: d.message || "",
    };
    if (d.success && d.has_update) {
      showUpdateToastOnce(d);
    }
  } catch (e) {
    console.error("检查系统更新失败:", e);
    const detail =
      e?.response?.data?.detail ||
      e?.message ||
      "网络错误，检查更新失败";
    updateStatus.value = {
      ...updateStatus.value,
      checkSuccess: false,
      checkMessage: typeof detail === "string" ? detail : "检查更新失败",
    };
  } finally {
    if (options.showLoading) checkLoading.value = false;
  }
}

function openVersionModal() {
  const el = versionModalEl.value;
  if (el) {
    Modal.getOrCreateInstance(el).show();
  }
  loadUpdateCheck({ showLoading: true });
}

function refreshVersionCheck() {
  loadUpdateCheck({ showLoading: true });
}

function openReleaseUrl() {
  if (updateStatus.value.releaseUrl) {
    window.open(
      updateStatus.value.releaseUrl,
      "_blank",
      "noopener,noreferrer",
    );
  }
}

// 权限检查函数（响应式）
function hasPermission(permissionCode) {
  if (!permissionsLoaded.value) {
    // 权限未加载时，默认返回true（向后兼容，显示所有菜单）
    return true;
  }
  return userPermissions.value.has(permissionCode);
}

function handleNavigate(tab, params) {
  activeTab.value = tab;
  // 如果传递了参数（比如筛选条件），可以在这里处理
  // 例如设置到localStorage或通过其他方式传递给目标组件
  if (params && params.status) {
    sessionStorage.setItem("taskStatusFilter", params.status);
  }
}

// 切换运行任务弹出框显示
function toggleRunningTasksPopup() {
  showRunningTasksPopup.value = !showRunningTasksPopup.value;
}

// 跳转到运行中的任务
function goToRunningTasks() {
  showRunningTasksPopup.value = false;
  handleNavigate("tasks", { status: "running" });
}

// 获取运行中的任务数量
async function updateRunningTasksCount() {
  if (!authenticated.value) return;
  try {
    const res = await axios.get("/api/tasks");
    const tasks = res.data.tasks || [];
    const running = tasks
      .filter((t) => t.status === "running")
      .sort((a, b) => {
        const timeA = new Date(a.created_at || 0).getTime();
        const timeB = new Date(b.created_at || 0).getTime();
        return timeB - timeA;
      });
    runningTasksCount.value = running.length;
    runningTasksList.value = running;
  } catch (error) {
    console.error("获取运行任务数量失败:", error);
  }
}

// 获取任务类型标签
function getTaskTypeLabel(type) {
  const map = {
    build: "构建",
    export: "导出",
    deploy: "部署",
  };
  return map[type] || type;
}

// 获取任务类型徽章样式
function getTaskTypeBadge(type) {
  const map = {
    build: "bg-primary",
    export: "bg-info",
    deploy: "bg-success",
  };
  return map[type] || "bg-secondary";
}

// 启动运行任务数量定时刷新
function startRunningTasksTimer() {
  // 清除之前的定时器
  if (runningTasksTimer) {
    clearInterval(runningTasksTimer);
  }

  // 立即获取一次
  updateRunningTasksCount();

  // 每10秒刷新一次
  runningTasksTimer = setInterval(() => {
    updateRunningTasksCount();
  }, 10000);
}

// 停止运行任务数量定时刷新
function stopRunningTasksTimer() {
  if (runningTasksTimer) {
    clearInterval(runningTasksTimer);
    runningTasksTimer = null;
  }
}

async function handleLoginSuccess(data) {
  authenticated.value = true;
  username.value = data.username;
  console.log("✅ 登录成功:", data.username);

  // 获取用户权限
  try {
    const permissions = await getUserPermissions();
    userPermissions.value = permissions; // 更新响应式权限集合
    permissionsLoaded.value = true;
  } catch (error) {
    console.error("获取用户权限失败:", error);
    // 即使失败也标记为已加载，使用默认权限（显示所有菜单）
    userPermissions.value = new Set();
    permissionsLoaded.value = true;
  }

  // 登录后启动运行任务数量定时刷新
  startRunningTasksTimer();

  await loadSystemVersion();
  await loadUpdateCheck();
}

async function handleLogout() {
  if (confirm("确定要退出登录吗？")) {
    await logout();
    authenticated.value = false;
    permissionsLoaded.value = false;
    userPermissions.value = new Set(); // 清空权限
    clearPermissionsCache(); // 清除权限缓存
    username.value = "";
    runningTasksCount.value = 0;
    runningTasksList.value = [];
    showRunningTasksPopup.value = false;
    stopRunningTasksTimer();
    clearPermissionsCache();
    console.log("👋 已登出");
  }
}

// 统一处理所有模态框的 ESC 键
useModalEscape();

// 点击外部关闭运行任务弹出框
function handleClickOutside(event) {
  const popup = document.querySelector(".running-tasks-popup");
  const button = event.target.closest(".btn-outline-warning");

  if (
    showRunningTasksPopup.value &&
    popup &&
    !popup.contains(event.target) &&
    !button
  ) {
    showRunningTasksPopup.value = false;
  }
}

// 处理构建配置保存
function handleBuildConfigSave(config) {
  // 将配置保存回流水线编辑页面
  localStorage.setItem("buildConfigEdited", JSON.stringify(config));
  // 触发事件通知流水线编辑页面
  window.dispatchEvent(new CustomEvent("buildConfigSaved"));
  // 返回流水线页面
  activeTab.value = "pipeline";
}

// 处理构建配置取消
function handleBuildConfigCancel() {
  activeTab.value = "pipeline";
}

onMounted(async () => {
  console.log("🚀 App 组件挂载");

  // 检查是否已登录
  if (isAuthenticated()) {
    authenticated.value = true;
    username.value = getUsername() || "User";

    // 设置 axios 默认 Authorization header
    const token = getToken();
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    }

    // 获取用户权限
    try {
      const permissions = await getUserPermissions();
      userPermissions.value = permissions; // 更新响应式权限集合
      permissionsLoaded.value = true;
    } catch (error) {
      console.error("获取用户权限失败:", error);
      // 即使失败也标记为已加载，使用默认权限（显示所有菜单）
      userPermissions.value = new Set();
      permissionsLoaded.value = true;
    }

    // 启动运行任务数量定时刷新
    startRunningTasksTimer();

    await loadSystemVersion();
    await loadUpdateCheck();

    console.log("✅ 已登录用户:", username.value);
  } else {
    console.log("🔒 未登录，显示登录页面");
  }

  // 添加点击外部关闭弹出框的监听
  document.addEventListener("click", handleClickOutside);

  // 监听子组件的页面导航事件（如从部署配置跳转到任务管理）
  window.addEventListener("navigate", handleNavigateEvent);
});

function handleNavigateEvent(e) {
  if (e.detail && e.detail.tab) {
    activeTab.value = e.detail.tab;
  }
}

onUnmounted(() => {
  stopRunningTasksTimer();
  document.removeEventListener("click", handleClickOutside);
  window.removeEventListener("navigate", handleNavigateEvent);
});
</script>

<style>
/* 导入 Bootstrap 和 FontAwesome */
@import "bootstrap/dist/css/bootstrap.min.css";
@import "@fortawesome/fontawesome-free/css/all.min.css";

/* === 全局统一样式 === */

/* Tab 样式统一 */
.nav-tabs {
  border-bottom: 1px solid #dee2e6;
}

.nav-tabs .nav-link {
  padding: 0.75rem 1.25rem;
  font-size: 0.95rem;
  cursor: pointer;
  border: none;
  border-bottom: 2px solid transparent;
  background: none;
  color: #6c757d;
  transition: color 0.15s, border-color 0.15s;
}

.nav-tabs .nav-link:hover {
  color: #0d6efd;
  border-bottom-color: #dee2e6;
}

.nav-tabs .nav-link.active {
  color: #0d6efd;
  background-color: transparent;
  border-bottom-color: #0d6efd;
  font-weight: 500;
}

/* 表单样式统一 */
.form-label {
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
  font-weight: 500;
}

.form-control,
.form-select {
  font-size: 0.95rem;
}

/* 卡片样式统一 */
.card {
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.card-header {
  background-color: #f8f9fa;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  padding: 0.75rem 1rem;
}

.card-header.bg-white {
  background-color: #fff !important;
}

/* 按钮样式统一 */
.btn {
  font-size: 0.9rem;
  border-radius: 0.375rem;
}

.btn-sm {
  font-size: 0.8rem;
  padding: 0.35rem 0.65rem;
}

/* 表格样式统一 */
.table {
  margin-bottom: 0;
}

.table th {
  font-weight: 600;
  font-size: 0.85rem;
  background-color: #f8f9fa;
  border-bottom-width: 1px;
}

.table td {
  vertical-align: middle;
  font-size: 0.9rem;
}

.table-hover tbody tr:hover {
  background-color: rgba(13, 110, 253, 0.04);
}

/* Badge 样式统一 */
.badge {
  font-weight: 500;
  font-size: 0.75rem;
}

/* 搜索栏样式 */
.input-group-text {
  background-color: #f8f9fa;
  border-color: #dee2e6;
}

/* 分页样式 */
.pagination {
  margin-bottom: 0;
}

.page-link {
  font-size: 0.85rem;
  padding: 0.35rem 0.65rem;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}

/* 运行任务弹出框样式 */
.running-tasks-popup {
  z-index: 1050;
  animation: fadeIn 0.2s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.running-tasks-tooltip .card {
  border: 2px solid #ffc107;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
}
</style>

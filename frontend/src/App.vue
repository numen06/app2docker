<template>
  <div id="app">
    <LoginPage v-if="!authenticated" @login-success="handleLoginSuccess" />

    <div
      v-else
      class="admin-layout"
      :class="{ 'admin-layout--sidebar-collapsed': sidebarCollapsed }"
    >
      <!-- 顶部导航 -->
      <nav
        class="admin-navbar navbar navbar-dark fixed-top border-bottom border-secondary border-opacity-25"
        style="background-color: var(--admin-navbar-bg, #1e293b)"
      >
        <div class="container-fluid px-2 px-sm-3 d-flex flex-wrap align-items-center gap-2">
          <div class="d-flex align-items-center gap-1 gap-sm-2 flex-shrink-0">
            <button
              type="button"
              class="btn btn-link text-white p-2 admin-navbar-icon-btn"
              title="展开/收起侧边栏"
              aria-label="展开或收起侧边栏"
              @click="toggleSidebar"
            >
              <i class="fas fa-bars"></i>
            </button>
            <span class="navbar-brand mb-0 d-flex align-items-center gap-2 text-white fw-semibold">
              <i class="fas fa-box-open text-info"></i>
              <span class="d-none d-sm-inline">App2Docker</span>
            </span>
            <button
              type="button"
              class="btn btn-outline-light btn-sm py-0 px-2"
              title="版本与更新"
              @click="openVersionModal"
            >
              <i class="fas fa-tag me-1"></i>
              <span class="small">v{{ appVersion || "…" }}</span>
              <span
                v-if="updateStatus.hasUpdate"
                class="badge bg-danger ms-1"
                style="font-size: 0.65rem"
                >新</span
              >
            </button>
          </div>

          <div class="d-flex align-items-center gap-2 ms-auto flex-shrink-0">
            <!-- 运行任务：下拉菜单 -->
            <div v-if="runningTasksCount > 0" class="dropdown">
              <button
                id="adminRunningTasksDropdown"
                class="btn btn-warning btn-sm dropdown-toggle"
                type="button"
                data-bs-toggle="dropdown"
                data-bs-auto-close="outside"
                aria-expanded="false"
              >
                <i class="fas fa-spinner fa-spin"></i>
                <span class="d-none d-md-inline ms-1">运行任务</span>
                <span class="badge bg-danger ms-1">{{ runningTasksCount }}</span>
              </button>
              <div
                class="dropdown-menu dropdown-menu-end p-0 shadow admin-running-dropdown"
                aria-labelledby="adminRunningTasksDropdown"
                style="min-width: 300px; max-width: 400px"
              >
                <div
                  class="px-3 py-2 border-bottom bg-warning bg-opacity-10 d-flex justify-content-between align-items-center"
                >
                  <span class="small fw-semibold">
                    <i class="fas fa-spinner fa-spin text-warning me-1"></i>
                    正在运行 ({{ runningTasksCount }})
                  </span>
                </div>
                <div class="p-2" style="max-height: 300px; overflow-y: auto">
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
                      <span v-if="task.tag" class="ms-1">:{{ task.tag }}</span>
                    </div>
                  </div>
                  <div
                    v-if="runningTasksCount > 10"
                    class="text-center text-muted small mt-2"
                  >
                    还有 {{ runningTasksCount - 10 }} 个任务…
                  </div>
                  <div class="text-center mt-3">
                    <button
                      type="button"
                      class="btn btn-primary btn-sm"
                      @click="goToRunningTasks"
                    >
                      <i class="fas fa-arrow-right"></i> 查看详情
                    </button>
                  </div>
                </div>
              </div>
            </div>
            <button
              v-else
              type="button"
              class="btn btn-outline-light btn-sm"
              title="暂无运行中的任务"
              disabled
            >
              <i class="fas fa-check-circle"></i>
              <span class="d-none d-md-inline ms-1">运行任务</span>
              <span class="badge bg-secondary ms-1">0</span>
            </button>

            <!-- 用户菜单 -->
            <div class="dropdown">
              <button
                id="adminUserDropdown"
                class="btn btn-outline-light btn-sm dropdown-toggle"
                type="button"
                data-bs-toggle="dropdown"
                aria-expanded="false"
              >
                <i class="fas fa-user-circle"></i>
                <span class="d-none d-md-inline ms-1 text-truncate" style="max-width: 8rem">{{
                  username
                }}</span>
              </button>
              <ul
                class="dropdown-menu dropdown-menu-end shadow"
                aria-labelledby="adminUserDropdown"
              >
                <li>
                  <button
                    type="button"
                    class="dropdown-item"
                    @click="showUserCenter = true"
                  >
                    <i class="fas fa-user me-2 text-muted"></i>用户中心
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    class="dropdown-item"
                    @click="activeTab = 'logs'"
                  >
                    <i class="fas fa-history me-2 text-muted"></i>操作日志
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    class="dropdown-item"
                    @click="showConfig = true"
                  >
                    <i class="fas fa-cog me-2 text-muted"></i>配置
                  </button>
                </li>
                <li><hr class="dropdown-divider" /></li>
                <li>
                  <button
                    type="button"
                    class="dropdown-item text-danger"
                    @click="handleLogout"
                  >
                    <i class="fas fa-sign-out-alt me-2"></i>登出
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </nav>

      <!-- 侧边栏 -->
      <aside class="admin-sidebar" aria-label="主导航">
        <nav class="admin-sidebar-nav">
          <button
            v-for="item in visibleSidebarItems"
            :key="item.id"
            type="button"
            class="admin-sidebar-link"
            :class="{ active: activeTab === item.id }"
            :title="item.label"
            @click="activeTab = item.id"
          >
            <i :class="['fa-fw', item.iconPrefix || 'fas', item.icon]"></i>
            <span class="admin-sidebar-label">{{ item.label }}</span>
          </button>
        </nav>
      </aside>

      <!-- 主内容 -->
      <div class="admin-main-wrap">
        <main class="admin-main">
          <header class="admin-page-header">
            <h1 class="admin-page-title h4 mb-1">{{ pageTitle }}</h1>
            <p v-if="pageDescription" class="admin-page-desc text-muted small mb-0">
              {{ pageDescription }}
            </p>
          </header>

          <div class="admin-content-surface rounded-3 shadow-sm border bg-white p-3 p-md-4">
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

          <footer class="admin-footer text-muted small mt-4 pb-3">
            <div class="d-flex flex-wrap align-items-center gap-2">
              <span>当前版本 <strong class="text-body">v{{ appVersion || "…" }}</strong></span>
              <span class="text-secondary">·</span>
              <button
                type="button"
                class="btn btn-link btn-sm text-muted p-0 align-baseline"
                @click="openVersionModal"
              >
                检查更新与发行说明
              </button>
            </div>
            <div class="mt-2">
              <i class="fas fa-code-branch me-1 opacity-75"></i>
              <span class="me-1">Gitee</span>
              <a
                :href="GITEE_REPO_URL"
                target="_blank"
                rel="noopener noreferrer"
                class="link-secondary text-break"
                >{{ GITEE_REPO_URL }}</a
              >
            </div>
          </footer>
        </main>
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
              <div
                v-else-if="updateStatus.checkSuccess && updateStatus.latestVersion"
                class="small text-muted"
              >
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
                :disabled="checkLoading"
                @click="openReleaseUrl"
              >
                在 Gitee 查看
              </button>
            </div>
          </div>
        </div>
      </div>

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

      <ConfigModal v-if="showConfig" v-model="showConfig" />
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
import { Dropdown, Modal, Toast } from "bootstrap";
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useModalEscape } from "./composables/useModalEscape";
import { getToken, getUsername, isAuthenticated, logout } from "./utils/auth";

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

const SIDEBAR_ITEMS = [
  { id: "dashboard", perm: "menu.dashboard", label: "仪表盘", icon: "fa-chart-line" },
  { id: "step-build", perm: "menu.build", label: "镜像构建", icon: "fa-list-ol" },
  { id: "export", perm: "menu.export", label: "导出镜像", icon: "fa-file-export" },
  { id: "tasks", perm: "menu.tasks", label: "任务管理", icon: "fa-list-check" },
  { id: "pipeline", perm: "menu.pipeline", label: "流水线", icon: "fa-project-diagram" },
  { id: "datasource", perm: "menu.datasource", label: "数据源", icon: "fa-database" },
  { id: "registry", perm: "menu.registry", label: "镜像仓库", icon: "fa-box" },
  { id: "template", perm: "menu.template", label: "模板管理", icon: "fa-layer-group" },
  {
    id: "resource-package",
    perm: "menu.resource-package",
    label: "资源包",
    icon: "fa-archive",
  },
  { id: "host", perm: "menu.host", label: "主机管理", icon: "fa-server" },
  {
    id: "docker",
    perm: "menu.docker",
    label: "Docker 管理",
    icon: "fa-docker",
    iconPrefix: "fab",
  },
  { id: "deploy", perm: "menu.deploy", label: "部署管理", icon: "fa-rocket" },
  { id: "users", perm: "menu.users", label: "用户管理", icon: "fa-users" },
  { id: "roles", perm: "menu.users", label: "角色管理", icon: "fa-user-shield" },
  { id: "logs", perm: null, label: "操作日志", icon: "fa-history" },
];

const PAGE_META = {
  dashboard: { title: "仪表盘", desc: "总览与快捷入口" },
  "step-build": { title: "镜像构建", desc: "上传应用，构建并推送 Docker 镜像" },
  export: { title: "导出镜像", desc: "导出镜像为离线包" },
  tasks: { title: "任务管理", desc: "查看与管理构建、导出、部署任务" },
  pipeline: { title: "流水线", desc: "流水线编排与配置" },
  datasource: { title: "数据源", desc: "管理代码与构建数据源" },
  registry: { title: "镜像仓库", desc: "镜像仓库配置与镜像列表" },
  template: { title: "模板管理", desc: "Dockerfile 与构建模板" },
  "resource-package": { title: "资源包", desc: "资源包管理" },
  host: { title: "主机管理", desc: "构建与部署目标主机" },
  docker: { title: "Docker 管理", desc: "容器与镜像运维" },
  deploy: { title: "部署管理", desc: "部署任务与目标环境" },
  users: { title: "用户管理", desc: "系统用户与权限" },
  roles: { title: "角色管理", desc: "角色与权限配置" },
  logs: { title: "操作日志", desc: "审计与操作记录" },
  "build-config-editor": { title: "构建配置", desc: "编辑流水线构建配置" },
};

const SIDEBAR_STORAGE_KEY = "app2docker-admin-sidebar-collapsed";

const authenticated = ref(false);
const username = ref("");
const activeTab = ref("dashboard");
const showConfig = ref(false);
const showUserCenter = ref(false);
const runningTasksCount = ref(0);
const runningTasksList = ref([]);
const buildConfigToEdit = ref({});
const permissionsLoaded = ref(false);
const userPermissions = ref(new Set());
let runningTasksTimer = null;

const sidebarCollapsed = ref(
  typeof localStorage !== "undefined" &&
    localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1"
);

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  try {
    localStorage.setItem(
      SIDEBAR_STORAGE_KEY,
      sidebarCollapsed.value ? "1" : "0"
    );
  } catch {
    /* ignore */
  }
}

const visibleSidebarItems = computed(() =>
  SIDEBAR_ITEMS.filter((item) => !item.perm || hasPermission(item.perm))
);

const pageTitle = computed(() => {
  const m = PAGE_META[activeTab.value];
  return m?.title || "App2Docker";
});

const pageDescription = computed(() => {
  const m = PAGE_META[activeTab.value];
  return m?.desc || "";
});

const GITEE_REPO_URL = "https://gitee.com/numen06/app2docker";

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
  return updateStatus.value.currentVersion || appVersion.value || "—";
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

async function loadUpdateCheck(options = {}) {
  const { showLoading = false, force = false } = options;
  if (!authenticated.value) return;
  if (showLoading) checkLoading.value = true;
  try {
    const res = await axios.get("/api/system/version/check-update", {
      params: force ? { force: true } : undefined,
    });
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
    if (showLoading) checkLoading.value = false;
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
  loadUpdateCheck({ showLoading: true, force: true });
}

function openReleaseUrl() {
  const url =
    updateStatus.value.releaseUrl || `${GITEE_REPO_URL}/releases`;
  window.open(url, "_blank", "noopener,noreferrer");
}

function hasPermission(permissionCode) {
  if (!permissionsLoaded.value) {
    return true;
  }
  return userPermissions.value.has(permissionCode);
}

function handleNavigate(tab, params) {
  activeTab.value = tab;
  if (params && params.status) {
    sessionStorage.setItem("taskStatusFilter", params.status);
  }
}

function hideRunningTasksDropdown() {
  const el = document.getElementById("adminRunningTasksDropdown");
  if (el) {
    const inst = Dropdown.getInstance(el) || Dropdown.getOrCreateInstance(el);
    inst.hide();
  }
}

function goToRunningTasks() {
  hideRunningTasksDropdown();
  handleNavigate("tasks", { status: "running" });
}

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

function getTaskTypeLabel(type) {
  const map = {
    build: "构建",
    export: "导出",
    deploy: "部署",
  };
  return map[type] || type;
}

function getTaskTypeBadge(type) {
  const map = {
    build: "bg-primary",
    export: "bg-info",
    deploy: "bg-success",
  };
  return map[type] || "bg-secondary";
}

function startRunningTasksTimer() {
  if (runningTasksTimer) {
    clearInterval(runningTasksTimer);
  }
  updateRunningTasksCount();
  runningTasksTimer = setInterval(() => {
    updateRunningTasksCount();
  }, 10000);
}

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

  try {
    const permissions = await getUserPermissions();
    userPermissions.value = permissions;
    permissionsLoaded.value = true;
  } catch (error) {
    console.error("获取用户权限失败:", error);
    userPermissions.value = new Set();
    permissionsLoaded.value = true;
  }

  startRunningTasksTimer();

  await loadSystemVersion();
  await loadUpdateCheck();
}

async function handleLogout() {
  if (confirm("确定要退出登录吗？")) {
    await logout();
    authenticated.value = false;
    permissionsLoaded.value = false;
    userPermissions.value = new Set();
    clearPermissionsCache();
    username.value = "";
    runningTasksCount.value = 0;
    runningTasksList.value = [];
    stopRunningTasksTimer();
    clearPermissionsCache();
    console.log("👋 已登出");
  }
}

useModalEscape();

function handleBuildConfigSave(config) {
  localStorage.setItem("buildConfigEdited", JSON.stringify(config));
  window.dispatchEvent(new CustomEvent("buildConfigSaved"));
  activeTab.value = "pipeline";
}

function handleBuildConfigCancel() {
  activeTab.value = "pipeline";
}

onMounted(async () => {
  console.log("🚀 App 组件挂载");

  if (isAuthenticated()) {
    authenticated.value = true;
    username.value = getUsername() || "User";

    const token = getToken();
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    }

    try {
      const permissions = await getUserPermissions();
      userPermissions.value = permissions;
      permissionsLoaded.value = true;
    } catch (error) {
      console.error("获取用户权限失败:", error);
      userPermissions.value = new Set();
      permissionsLoaded.value = true;
    }

    startRunningTasksTimer();

    await loadSystemVersion();
    await loadUpdateCheck();

    console.log("✅ 已登录用户:", username.value);
  } else {
    console.log("🔒 未登录，显示登录页面");
  }

  window.addEventListener("navigate", handleNavigateEvent);
});

function handleNavigateEvent(e) {
  if (e.detail && e.detail.tab) {
    activeTab.value = e.detail.tab;
  }
}

onUnmounted(() => {
  stopRunningTasksTimer();
  window.removeEventListener("navigate", handleNavigateEvent);
});
</script>

<style>
@import "bootstrap/dist/css/bootstrap.min.css";
@import "@fortawesome/fontawesome-free/css/all.min.css";

/* === 管理后台布局 === */
.admin-layout {
  min-height: 100vh;
  background-color: var(--admin-content-bg, #f1f5f9);
}

.admin-navbar {
  height: var(--admin-navbar-height, 56px);
  z-index: 1030;
}

.admin-navbar-icon-btn {
  text-decoration: none;
  border: none;
  line-height: 1;
}
.admin-navbar-icon-btn:hover,
.admin-navbar-icon-btn:focus {
  color: #e2e8f0 !important;
}

.admin-sidebar {
  position: fixed;
  top: var(--admin-navbar-height, 56px);
  left: 0;
  bottom: 0;
  width: var(--admin-sidebar-width, 256px);
  background: var(--admin-sidebar-bg, #f8fafc);
  border-right: 1px solid var(--admin-sidebar-border, #e2e8f0);
  z-index: 1020;
  transition: width 0.2s ease;
  overflow-x: hidden;
  overflow-y: auto;
}

.admin-layout--sidebar-collapsed .admin-sidebar {
  width: var(--admin-sidebar-collapsed-width, 64px);
}

.admin-sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 0.75rem 0;
  gap: 0.125rem;
}

.admin-sidebar-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.6rem 1rem;
  border: none;
  background: transparent;
  color: #334155;
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition:
    background 0.15s ease,
    color 0.15s ease,
    border-color 0.15s ease;
  white-space: nowrap;
}

.admin-sidebar-link:hover {
  background: rgba(59, 130, 246, 0.08);
  color: #1e40af;
}

.admin-sidebar-link.active {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
  border-left-color: #2563eb;
  font-weight: 600;
}

.admin-sidebar-label {
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity 0.15s ease;
}

.admin-layout--sidebar-collapsed .admin-sidebar-label {
  opacity: 0;
  width: 0;
  pointer-events: none;
}

.admin-layout--sidebar-collapsed .admin-sidebar-link {
  justify-content: center;
  padding-left: 0.5rem;
  padding-right: 0.5rem;
}

.admin-main-wrap {
  margin-top: var(--admin-navbar-height, 56px);
  margin-left: var(--admin-sidebar-width, 256px);
  min-height: calc(100vh - var(--admin-navbar-height, 56px));
  transition: margin-left 0.2s ease;
}

.admin-layout--sidebar-collapsed .admin-main-wrap {
  margin-left: var(--admin-sidebar-collapsed-width, 64px);
}

.admin-main {
  max-width: 1600px;
  margin: 0 auto;
  padding: 1.25rem 1.25rem 0;
}

@media (min-width: 992px) {
  .admin-main {
    padding: 1.5rem 1.75rem 0;
  }
}

.admin-page-header {
  margin-bottom: 1rem;
}

.admin-page-title {
  font-weight: 600;
  color: #0f172a;
}

.admin-content-surface {
  min-height: 400px;
}

.admin-running-dropdown {
  z-index: 1055;
}

/* === 子页面通用（表格、表单、Tab）=== */
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
  transition:
    color 0.15s,
    border-color 0.15s;
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

.form-label {
  margin-bottom: 0.5rem;
  font-size: 0.95rem;
  font-weight: 500;
}

.form-control,
.form-select {
  font-size: 0.95rem;
}

.admin-content-surface > .card,
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

.btn {
  font-size: 0.9rem;
  border-radius: 0.375rem;
}

.btn-sm {
  font-size: 0.8rem;
  padding: 0.35rem 0.65rem;
}

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

.badge {
  font-weight: 500;
  font-size: 0.75rem;
}

.input-group-text {
  background-color: #f8f9fa;
  border-color: #dee2e6;
}

.pagination {
  margin-bottom: 0;
}

.page-link {
  font-size: 0.85rem;
  padding: 0.35rem 0.65rem;
}

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
</style>

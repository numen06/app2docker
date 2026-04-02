<template>
  <div id="app">
    <LoginPage v-if="!authenticated" @login-success="handleLoginSuccess" />

    <div
      v-else
      class="admin-layout"
      :class="{ 'admin-layout--sidebar-collapsed': sidebarCollapsed }"
    >
      <!-- 顶部导航（Flowbite 风格） -->
      <nav class="fixed left-0 right-0 top-0 z-30 h-14 border-b border-gray-200 bg-white">
        <div class="mx-auto flex h-full w-full items-center gap-2 px-2 sm:px-3">
          <div class="flex shrink-0 items-center gap-1 sm:gap-2">
            <button
              type="button"
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 transition hover:bg-gray-100 hover:text-gray-900"
              title="展开/收起侧边栏"
              aria-label="展开或收起侧边栏"
              @click="toggleSidebar"
            >
              <i class="fas fa-bars"></i>
            </button>
            <span class="mb-0 flex items-center gap-2 font-semibold text-gray-900">
              <i class="fas fa-box-open text-blue-600"></i>
              <span class="hidden sm:inline">App2Docker</span>
            </span>
            <button
              type="button"
              class="inline-flex items-center rounded-lg border border-gray-300 px-2 py-1 text-xs text-gray-700 transition hover:bg-gray-50"
              title="版本与更新"
              @click="openVersionModal"
            >
              <i class="fas fa-tag me-1"></i>
              <span>v{{ appVersion || "…" }}</span>
              <span
                v-if="updateStatus.hasUpdate"
                class="ms-1 rounded bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-700"
                style="font-size: 0.65rem"
                >新</span
              >
            </button>
          </div>

          <div class="ms-auto flex shrink-0 items-center gap-2">
            <!-- 运行任务：下拉菜单 -->
            <div v-if="runningTasksCount > 0" class="dropdown">
              <button
                id="adminRunningTasksDropdown"
                class="inline-flex items-center rounded-lg bg-amber-100 px-2 py-1 text-sm text-amber-900 hover:bg-amber-200 dropdown-toggle"
                type="button"
                data-bs-toggle="dropdown"
                data-bs-auto-close="outside"
                aria-expanded="false"
              >
                <i class="fas fa-spinner fa-spin"></i>
                <span class="ms-1 hidden md:inline">运行任务</span>
                <span class="ms-1 rounded bg-red-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">{{ runningTasksCount }}</span>
              </button>
              <div
                class="dropdown-menu dropdown-menu-end admin-running-dropdown rounded-lg border border-gray-200 p-0 shadow-lg"
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
              class="inline-flex items-center rounded-lg border border-gray-300 px-2 py-1 text-sm text-gray-500"
              title="暂无运行中的任务"
              disabled
            >
              <i class="fas fa-check-circle"></i>
              <span class="ms-1 hidden md:inline">运行任务</span>
              <span class="ms-1 rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-medium text-gray-600">0</span>
            </button>

            <!-- 用户菜单 -->
            <div class="dropdown">
              <button
                id="adminUserDropdown"
                class="inline-flex items-center rounded-lg border border-gray-300 px-2 py-1 text-sm text-gray-700 hover:bg-gray-50 dropdown-toggle"
                type="button"
                data-bs-toggle="dropdown"
                aria-expanded="false"
              >
                <i class="fas fa-user-circle"></i>
                <span class="ms-1 hidden max-w-32 truncate md:inline">{{
                  username
                }}</span>
              </button>
              <ul
                class="dropdown-menu dropdown-menu-end rounded-lg border border-gray-200 py-1 shadow-lg"
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

      <!-- 侧边栏（Flowbite Sidebar 结构） -->
      <aside
        class="fixed bottom-0 left-0 top-14 z-20 overflow-y-auto border-r border-gray-200 bg-white transition-all duration-200"
        :class="sidebarCollapsed ? 'w-16' : 'w-64'"
        aria-label="主导航"
      >
        <nav v-if="!sidebarCollapsed" class="space-y-2 p-3">
          <button
            v-if="hasPermission('menu.dashboard')"
            type="button"
            class="group flex w-full items-center rounded-lg px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100 hover:text-gray-900"
            :class="activeTab === 'dashboard' ? 'bg-blue-50 text-blue-700' : ''"
            title="首页"
            @click="activeTab = 'dashboard'"
          >
            <i class="fas fa-house fa-fw text-gray-500 group-hover:text-gray-700"></i>
            <span class="truncate">首页</span>
          </button>
          <div
            v-if="hasPermission('menu.dashboard') && visibleSidebarGroups.length"
            class="my-2 h-px bg-gray-200"
            role="separator"
          />
          <div
            v-for="group in visibleSidebarGroups"
            :key="group.id"
            class="space-y-1"
          >
            <button
              type="button"
              class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500 transition hover:bg-gray-100 hover:text-gray-700"
              :class="groupHasActiveChild(group) ? 'text-gray-700' : ''"
              :aria-expanded="isGroupExpanded(group.id)"
              @click="toggleGroup(group.id)"
            >
              <i :class="['fa-fw', 'fas', group.icon, 'text-gray-400']"></i>
              <span class="grow text-start truncate">{{
                group.label
              }}</span>
              <i
                class="fas fa-chevron-down text-[10px] text-gray-400 transition-transform duration-200"
                :class="isGroupExpanded(group.id) ? 'rotate-180' : ''"
                aria-hidden="true"
              ></i>
            </button>
            <div
              v-show="isGroupExpanded(group.id)"
              class="space-y-1 pl-3"
            >
              <button
                v-for="child in group.children"
                :key="child.id"
                type="button"
                class="group flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 transition hover:bg-gray-100 hover:text-gray-900"
                :class="activeTab === child.id ? 'bg-blue-50 text-blue-700' : ''"
                :title="child.label"
                @click="activeTab = child.id"
              >
                <i
                  :class="[
                    'fa-fw',
                    child.iconPrefix || 'fas',
                    child.icon,
                    activeTab === child.id ? 'text-blue-600' : 'text-gray-400',
                  ]"
                ></i>
                <span class="truncate">{{ child.label }}</span>
              </button>
            </div>
          </div>
        </nav>
        <nav
          v-else
          class="flex flex-col items-center gap-2 px-2 py-3"
          aria-label="主导航"
        >
          <button
            v-if="hasPermission('menu.dashboard')"
            type="button"
            class="inline-flex h-10 w-10 items-center justify-center rounded-lg text-gray-500 transition hover:bg-gray-100 hover:text-gray-800"
            :class="activeTab === 'dashboard' ? 'bg-blue-50 text-blue-700' : ''"
            title="首页"
            @click="activeTab = 'dashboard'"
          >
            <i class="fas fa-house fa-fw"></i>
          </button>
          <div
            v-if="hasPermission('menu.dashboard') && visibleSidebarGroups.length"
            class="my-1 h-px w-8 bg-gray-200"
            role="separator"
          />
          <div
            v-for="group in visibleSidebarGroups"
            :key="'fly-' + group.id"
            class="dropend flex w-full justify-center"
          >
            <button
              :id="'sidebar-flyout-' + group.id"
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-lg text-gray-500 transition hover:bg-gray-100 hover:text-gray-800"
              data-bs-toggle="dropdown"
              data-bs-offset="0,8"
              aria-expanded="false"
              :title="group.label"
            >
              <i :class="['fa-fw', 'fas', group.icon]"></i>
            </button>
            <ul
              class="dropdown-menu dropdown-menu-start admin-sidebar-flyout-menu rounded-lg border border-gray-200 py-1 shadow-lg"
              :aria-labelledby="'sidebar-flyout-' + group.id"
            >
              <li v-for="child in group.children" :key="child.id">
                <button
                  type="button"
                  class="dropdown-item flex items-center gap-2 py-2"
                  :class="activeTab === child.id ? 'active' : ''"
                  @click="selectTabFromFlyout(group.id, child.id)"
                >
                  <i
                    :class="[child.iconPrefix || 'fas', child.icon, 'text-muted']"
                  ></i>
                  {{ child.label }}
                </button>
              </li>
            </ul>
          </div>
        </nav>
      </aside>

      <!-- 主内容 -->
      <div class="admin-main-wrap">
        <main class="admin-main">
          <div class="admin-content-panel">
            <header class="admin-content-panel__header">
              <h1 class="admin-page-title h5 mb-0">{{ pageTitle }}</h1>
            </header>
            <div class="admin-content-panel__body">
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

          <footer class="admin-footer" role="contentinfo">
            <div class="admin-footer__inner">
              <div class="admin-footer__row">
                <span class="admin-footer__meta">
                  当前版本
                  <strong class="admin-footer__strong">v{{ appVersion || "…" }}</strong>
                </span>
                <span class="admin-footer__sep" aria-hidden="true">·</span>
                <button
                  type="button"
                  class="btn btn-link btn-sm admin-footer__link p-0"
                  @click="openVersionModal"
                >
                  检查更新与发行说明
                </button>
              </div>
              <div class="admin-footer__row">
                <i class="fas fa-code-branch admin-footer__icon" aria-hidden="true"></i>
                <span class="admin-footer__label">Gitee</span>
                <a
                  :href="GITEE_REPO_URL"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="admin-footer__anchor text-break"
                  >{{ GITEE_REPO_URL }}</a
                >
              </div>
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
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
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

/** 侧边栏二级分组（仪表盘单独「首页」一级入口，其余为分组 + 二级菜单） */
const SIDEBAR_GROUPS = [
  {
    id: "cicd",
    label: "构建与交付",
    icon: "fa-gears",
    children: [
      {
        id: "step-build",
        perm: "menu.build",
        label: "镜像构建",
        icon: "fa-list-ol",
      },
      {
        id: "export",
        perm: "menu.export",
        label: "导出镜像",
        icon: "fa-file-export",
      },
      {
        id: "tasks",
        perm: "menu.tasks",
        label: "任务管理",
        icon: "fa-list-check",
      },
      {
        id: "pipeline",
        perm: "menu.pipeline",
        label: "流水线",
        icon: "fa-project-diagram",
      },
    ],
  },
  {
    id: "resources",
    label: "资源与模板",
    icon: "fa-folder-tree",
    children: [
      {
        id: "datasource",
        perm: "menu.datasource",
        label: "数据源",
        icon: "fa-database",
      },
      {
        id: "registry",
        perm: "menu.registry",
        label: "镜像仓库",
        icon: "fa-box",
      },
      {
        id: "template",
        perm: "menu.template",
        label: "模板管理",
        icon: "fa-layer-group",
      },
      {
        id: "resource-package",
        perm: "menu.resource-package",
        label: "资源包",
        icon: "fa-archive",
      },
    ],
  },
  {
    id: "runtime",
    label: "运行与部署",
    icon: "fa-network-wired",
    children: [
      { id: "host", perm: "menu.host", label: "主机管理", icon: "fa-server" },
      {
        id: "docker",
        perm: "menu.docker",
        label: "Docker 管理",
        icon: "fa-docker",
        iconPrefix: "fab",
      },
      {
        id: "deploy",
        perm: "menu.deploy",
        label: "部署管理",
        icon: "fa-rocket",
      },
    ],
  },
  {
    id: "system",
    label: "系统与安全",
    icon: "fa-shield-halved",
    children: [
      {
        id: "users",
        perm: "menu.users",
        label: "用户管理",
        icon: "fa-users",
      },
      {
        id: "roles",
        perm: "menu.users",
        label: "角色管理",
        icon: "fa-user-shield",
      },
      { id: "logs", perm: null, label: "操作日志", icon: "fa-history" },
    ],
  },
];

const PAGE_TITLES = {
  dashboard: "仪表盘",
  "step-build": "镜像构建",
  export: "导出镜像",
  tasks: "任务管理",
  pipeline: "流水线",
  datasource: "数据源",
  registry: "镜像仓库",
  template: "模板管理",
  "resource-package": "资源包",
  host: "主机管理",
  docker: "Docker 管理",
  deploy: "部署管理",
  users: "用户管理",
  roles: "角色管理",
  logs: "操作日志",
  "build-config-editor": "构建配置",
};

const SIDEBAR_STORAGE_KEY = "app2docker-admin-sidebar-collapsed";

const authenticated = ref(false);
const username = ref("");
const ACTIVE_TAB_STORAGE_KEY = "app2docker-active-tab";

const activeTab = ref(
  typeof sessionStorage !== "undefined"
    ? sessionStorage.getItem(ACTIVE_TAB_STORAGE_KEY) || "dashboard"
    : "dashboard"
);

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

const visibleSidebarGroups = computed(() =>
  SIDEBAR_GROUPS.map((g) => ({
    ...g,
    children: g.children.filter((c) => !c.perm || hasPermission(c.perm)),
  })).filter((g) => g.children.length > 0)
);

const expandedGroupIds = ref(/** @type {string[]} */ ([]));

function isGroupExpanded(groupId) {
  return expandedGroupIds.value.includes(groupId);
}

function toggleGroup(groupId) {
  const cur = expandedGroupIds.value;
  const i = cur.indexOf(groupId);
  expandedGroupIds.value =
    i >= 0 ? cur.filter((id) => id !== groupId) : [...cur, groupId];
}

function expandGroupForTab(tab) {
  const g = SIDEBAR_GROUPS.find((grp) =>
    grp.children.some((c) => c.id === tab)
  );
  if (!g) return;
  if (!expandedGroupIds.value.includes(g.id)) {
    expandedGroupIds.value = [...expandedGroupIds.value, g.id];
  }
}

function groupHasActiveChild(group) {
  return group.children.some((c) => c.id === activeTab.value);
}

function selectTabFromFlyout(groupId, childId) {
  activeTab.value = childId;
  const el = document.getElementById(`sidebar-flyout-${groupId}`);
  if (el) {
    const inst = Dropdown.getInstance(el) || Dropdown.getOrCreateInstance(el);
    inst.hide();
  }
}

watch(
  activeTab,
  (newTab) => {
    try {
      sessionStorage.setItem(ACTIVE_TAB_STORAGE_KEY, newTab);
    } catch {
      /* ignore */
    }
    expandGroupForTab(newTab);
  },
  { immediate: true }
);

const pageTitle = computed(() => {
  return PAGE_TITLES[activeTab.value] || "App2Docker";
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

.admin-sidebar-flyout-menu {
  min-width: 11.5rem;
  font-size: 0.875rem;
  z-index: 1055;
}

.admin-main-wrap {
  margin-top: var(--admin-navbar-height, 56px);
  margin-left: var(--admin-sidebar-width, 256px);
  min-height: calc(100vh - var(--admin-navbar-height, 56px));
  transition: margin-left 0.2s ease;
  display: flex;
  flex-direction: column;
}

.admin-layout--sidebar-collapsed .admin-main-wrap {
  margin-left: var(--admin-sidebar-collapsed-width, 64px);
}

.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 1rem 1rem 0;
  box-sizing: border-box;
}

@media (min-width: 992px) {
  .admin-main {
    padding: 1.5rem 1.5rem 0;
  }
}

/* Flowbite 式主内容面板：灰底上的白卡片 */
.admin-content-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border: 1px solid var(--admin-panel-border, #e2e8f0);
  border-radius: var(--admin-panel-radius, 0.5rem);
  box-shadow: var(--admin-panel-shadow, 0 1px 2px 0 rgb(15 23 42 / 0.05));
  overflow: hidden;
}

.admin-content-panel__header {
  flex-shrink: 0;
  padding: 0.875rem 1rem;
  border-bottom: 1px solid var(--admin-panel-border, #e2e8f0);
  background: #fff;
}

.admin-content-panel__body {
  flex: 1;
  padding: 1rem 1rem 1.25rem;
  min-height: 400px;
}

@media (min-width: 992px) {
  .admin-content-panel__header {
    padding: 1rem 1.5rem;
  }
  .admin-content-panel__body {
    padding: 1.25rem 1.5rem 1.5rem;
  }
}

.admin-page-title {
  font-weight: 600;
  color: #0f172a;
  letter-spacing: -0.01em;
}

/* 底部栏：与主内容区左右对齐、统一字色与分隔 */
.admin-footer {
  flex-shrink: 0;
  margin-top: 1.25rem;
  padding: 1rem 0 1.25rem;
  border-top: 1px solid var(--admin-panel-border, #e2e8f0);
}

.admin-footer__inner {
  max-width: 100%;
}

.admin-footer__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: #64748b;
}

.admin-footer__row + .admin-footer__row {
  margin-top: 0.4rem;
}

.admin-footer__meta {
  color: #64748b;
}

.admin-footer__strong {
  color: #334155;
  font-weight: 600;
}

.admin-footer__sep {
  color: #cbd5e1;
  user-select: none;
}

.admin-footer__link {
  font-size: inherit;
  line-height: inherit;
  color: #64748b !important;
  text-decoration: none;
  vertical-align: baseline;
}

.admin-footer__link:hover {
  color: #0d6efd !important;
  text-decoration: underline;
}

.admin-footer__icon {
  color: #94a3b8;
  font-size: 0.875rem;
}

.admin-footer__label {
  color: #64748b;
  margin-right: 0.15rem;
}

.admin-footer__anchor {
  color: #64748b;
  text-decoration: none;
}

.admin-footer__anchor:hover {
  color: #0d6efd;
  text-decoration: underline;
}

/* 面板内嵌套卡片略减阴影，避免层次过重 */
.admin-content-panel__body .card {
  box-shadow: 0 1px 2px rgb(15 23 42 / 0.04);
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

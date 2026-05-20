<template>
  <div
    id="admin-root"
    class="admin-layout"
    :class="{
      'admin-layout--sidebar-collapsed': sidebarCollapsed && !isMobile,
      'admin-layout--mobile': isMobile,
    }"
  >
      <!-- 顶部导航（Flowbite 风格） -->
      <nav class="fixed left-0 right-0 top-0 z-30 h-14 border-b border-slate-200 bg-white">
        <div class="mx-auto flex h-full w-full items-center gap-2 px-2 sm:px-3">
          <div class="flex shrink-0 items-center gap-1 sm:gap-2">
            <button
              type="button"
              class="inline-flex h-11 w-11 min-h-11 min-w-11 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
              title="展开/收起侧边栏"
              :aria-label="isMobile ? (sidebarOpen ? '关闭菜单' : '打开菜单') : '展开或收起侧边栏'"
              @click="toggleSidebar"
            >
              <i class="fas fa-bars"></i>
            </button>
            <span class="mb-0 flex items-center gap-2 font-semibold text-slate-900">
              <i class="fas fa-box-open text-blue-600"></i>
              <span class="hidden sm:inline">App2Docker</span>
            </span>
          </div>

          <div class="admin-topbar-actions ms-auto flex shrink-0 items-center gap-2">
            <!-- 全局团队选择（左侧图标区分管理者 / 成员） -->
            <div
              v-if="teamStore.memberships.length"
              ref="teamDropdownWrap"
              class="relative max-w-[9.5rem] sm:max-w-[11rem]"
            >
              <button
                type="button"
                class="admin-topbar-control admin-team-switcher-trigger inline-flex w-full max-w-full items-center gap-1.5 rounded-lg border border-slate-300 px-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                :disabled="teamSwitching"
                :aria-expanded="teamMenuOpen ? 'true' : 'false'"
                :title="activeTeamMenuTitle"
                @click.stop="toggleTeamMenu"
              >
                <i
                  :class="teamRoleIconClass(activeMembership?.role)"
                  class="shrink-0 text-xs"
                  aria-hidden="true"
                ></i>
                <span class="min-w-0 flex-1 truncate text-left">{{
                  activeTeamDisplayName
                }}</span>
                <i
                  class="fas fa-chevron-down shrink-0 text-[10px] text-slate-400"
                  aria-hidden="true"
                ></i>
              </button>
              <ul
                v-show="teamMenuOpen"
                class="admin-team-switcher-menu absolute right-0 top-full z-[1055] mt-1 max-h-[min(60vh,16rem)] min-w-[11rem] max-w-[15rem] overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
              >
                <li v-for="m in teamStore.memberships" :key="m.team.team_id">
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 px-2.5 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    :class="
                      m.team.team_id === teamStore.activeTeamId
                        ? 'bg-blue-50 text-blue-800'
                        : ''
                    "
                    :title="teamOptionTitle(m)"
                    @click="selectTeam(m.team.team_id)"
                  >
                    <i
                      :class="teamRoleIconClass(m.role)"
                      class="shrink-0 text-xs"
                      aria-hidden="true"
                    ></i>
                    <span class="min-w-0 flex-1 truncate">{{ m.team.name }}</span>
                    <i
                      v-if="m.team.team_id === teamStore.activeTeamId"
                      class="fas fa-check shrink-0 text-xs text-blue-600"
                      aria-hidden="true"
                    ></i>
                  </button>
                </li>
              </ul>
            </div>
            <RouterLink
              v-else-if="!authStore.isGlobalAdmin"
              to="/onboarding"
              class="admin-topbar-control hidden rounded-lg border border-dashed border-slate-300 px-2.5 text-xs text-slate-600 hover:bg-slate-50 sm:inline-flex"
            >
              <i class="fas fa-plus mr-1"></i>创建/加入团队
            </RouterLink>

            <!-- 运行任务：下拉菜单 -->
            <div
              v-if="runningTasksCount > 0"
              ref="runningTasksDropdownWrap"
              class="relative"
            >
              <button
                class="admin-topbar-control inline-flex items-center rounded-lg bg-amber-100 px-2.5 text-sm text-amber-900 hover:bg-amber-200 dropdown-toggle"
                type="button"
                :aria-expanded="runningTasksMenuOpen ? 'true' : 'false'"
                @click.stop="toggleRunningTasksMenu"
              >
                <i class="fas fa-spinner fa-spin"></i>
                <span class="ms-1 hidden md:inline">运行任务</span>
                <span class="ms-1 rounded bg-red-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">{{ runningTasksCount }}</span>
              </button>
              <div
                v-show="runningTasksMenuOpen"
                ref="runningTasksDropdownMenu"
                class="admin-running-dropdown absolute right-0 top-full z-[1055] mt-1 rounded-lg border border-slate-200 bg-white p-0 shadow-lg"
                :style="{ ...runningTasksMenuStyle, minWidth: '300px', maxWidth: '400px' }"
                @click.stop
              >
                <div
                  class="flex items-center justify-between border-b border-amber-200 bg-amber-50 px-3 py-2"
                >
                  <span class="text-xs font-semibold text-amber-950">
                    <i class="fas fa-spinner fa-spin text-amber-600 me-1"></i>
                    正在运行 ({{ runningTasksCount }})
                  </span>
                </div>
                <div class="p-2" style="max-height: 300px; overflow-y: auto">
                  <div
                    v-for="task in runningTasksList.slice(0, 10)"
                    :key="task.task_id"
                    class="mb-2 border-b border-slate-100 pb-2"
                  >
                    <div class="flex items-start gap-2">
                      <code class="text-xs">{{
                        task.task_id?.substring(0, 8) || "-"
                      }}</code>
                      <span
                        class="rounded px-2 py-0.5 text-[11px] font-medium text-white"
                        :class="getTaskTypeBadge(task.task_category)"
                      >
                        {{ getTaskTypeLabel(task.task_category) }}
                      </span>
                    </div>
                    <div
                      v-if="task.image || task.task_name"
                      class="mt-1 text-xs text-slate-500"
                    >
                      {{ task.image || task.task_name || "-" }}
                      <span v-if="task.tag" class="ms-1">:{{ task.tag }}</span>
                    </div>
                  </div>
                  <div
                    v-if="runningTasksCount > 10"
                    class="mt-2 text-center text-xs text-slate-500"
                  >
                    还有 {{ runningTasksCount - 10 }} 个任务…
                  </div>
                  <div class="mt-3 text-center">
                    <button
                      type="button"
                      class="inline-flex items-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
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
              class="admin-topbar-control inline-flex items-center rounded-lg border border-slate-300 px-2.5 text-sm text-slate-500"
              title="暂无运行中的任务"
              disabled
            >
              <i class="fas fa-check-circle"></i>
              <span class="ms-1 hidden md:inline">运行任务</span>
              <span class="ms-1 rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">0</span>
            </button>

            <!-- 用户菜单 -->
            <div ref="userDropdownWrap" class="relative">
              <button
                class="admin-topbar-control inline-flex items-center rounded-lg border border-slate-300 px-2.5 text-sm text-slate-700 hover:bg-slate-50"
                type="button"
                :aria-expanded="userMenuOpen ? 'true' : 'false'"
                @click.stop="toggleUserMenu"
              >
                <i class="fas fa-user-circle"></i>
                <span class="ms-1 hidden max-w-32 truncate md:inline">{{
                  username
                }}</span>
              </button>
              <ul
                v-show="userMenuOpen"
                ref="userDropdownMenu"
                class="absolute right-0 top-full z-[1055] mt-1 min-w-[12rem] rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
                :style="userMenuStyle"
              >
                <li>
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    @click="openUserCenter('password')"
                  >
                    <i class="fas fa-user w-4 text-slate-400"></i>用户中心
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    @click="openUserCenter('appkeys')"
                  >
                    <i class="fas fa-key w-4 text-slate-400"></i>APPKEY管理
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    @click="
                      goTab('logs');
                      closeUserMenu();
                    "
                  >
                    <i class="fas fa-history w-4 text-slate-400"></i>操作日志
                  </button>
                </li>
                <li>
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                    @click="
                      showConfig = true;
                      closeUserMenu();
                    "
                  >
                    <i class="fas fa-cog w-4 text-slate-400"></i>配置
                  </button>
                </li>
                <li class="my-1 border-t border-slate-100"></li>
                <li>
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                    @click="handleLogout"
                  >
                    <i class="fas fa-sign-out-alt w-4"></i>登出
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </nav>

      <!-- 移动端侧边栏遮罩 -->
      <div
        v-if="isMobile && sidebarOpen"
        class="admin-sidebar-overlay fixed inset-0 top-14 z-[15] bg-black/40"
        aria-hidden="true"
        @click="closeMobileSidebar"
      />

      <!-- 侧边栏（Flowbite Sidebar 结构） -->
      <aside
        class="fixed bottom-0 left-0 top-14 z-20 overflow-y-auto border-r border-slate-200 bg-white transition-all duration-200"
        :class="[
          isMobile ? 'w-64' : sidebarCollapsed ? 'w-16' : 'w-64',
          isMobile ? (sidebarOpen ? 'translate-x-0' : '-translate-x-full') : '',
        ]"
        aria-label="主导航"
      >
        <nav v-if="!sidebarCollapsed || isMobile" class="flex h-full min-h-0 flex-col p-3">
          <div class="flex-1 space-y-2 overflow-y-auto">
            <button
              v-if="hasPermission('menu.dashboard')"
              type="button"
              class="group flex w-full items-center rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-900"
              :class="activeTab === 'dashboard' ? 'bg-blue-50 text-blue-700' : ''"
              title="首页"
              @click="goTab('dashboard')"
            >
              <i class="fas fa-house fa-fw text-slate-500 group-hover:text-slate-700"></i>
              <span class="truncate">首页</span>
            </button>
            <button
              type="button"
              class="group flex w-full items-center rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-900"
              :class="activeTab === 'team' ? 'bg-blue-50 text-blue-700' : ''"
              title="团队管理"
              @click="goTab('team')"
            >
              <i class="fas fa-people-group fa-fw text-slate-500 group-hover:text-slate-700"></i>
              <span class="truncate">团队管理</span>
            </button>
            <div
              v-if="hasPermission('menu.dashboard') && visibleSidebarGroups.length"
              class="my-2 h-px bg-slate-200"
              role="separator"
            />
            <div
              v-for="group in visibleSidebarGroups"
              :key="group.id"
              class="space-y-1"
            >
              <button
                type="button"
                class="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 hover:text-slate-900"
                :class="groupHasActiveChild(group) ? 'text-slate-700' : ''"
                :aria-expanded="isGroupExpanded(group.id)"
                @click="toggleGroup(group.id)"
              >
                <i :class="['fa-fw', 'fas', group.icon, 'text-slate-400']"></i>
                <span class="grow text-start truncate">{{
                  group.label
                }}</span>
                <i
                  class="fas fa-chevron-down text-[10px] text-slate-400 transition-transform duration-200"
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
                  class="group flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
                  :class="sidebarActiveTab === child.id ? 'bg-blue-50 text-blue-700' : ''"
                  :title="child.label"
                  @click="goTab(child.id)"
                >
                  <i
                    :class="[
                      'fa-fw',
                      child.iconPrefix || 'fas',
                      child.icon,
                      sidebarActiveTab === child.id ? 'text-blue-600' : 'text-slate-400',
                    ]"
                  ></i>
                  <span class="truncate">{{ child.label }}</span>
                </button>
              </div>
            </div>
          </div>
          <div class="mt-3 shrink-0 border-t border-slate-200 pt-3">
            <button
              type="button"
              class="relative inline-flex w-full items-center justify-center rounded-lg border border-slate-300 px-2 py-2 text-xs text-slate-700 transition hover:bg-slate-50"
              title="版本与更新"
              @click="openVersionModal"
            >
              <i class="fas fa-tag me-1"></i>
              <span>v{{ appVersion || "…" }}</span>
              <span
                v-if="updateStatus.hasUpdate"
                class="absolute inset-e-2 top-1/2 inline-flex h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-red-500"
                aria-label="有新版本"
                title="有新版本"
              />
            </button>
          </div>
        </nav>
        <nav
          v-else-if="sidebarCollapsed && !isMobile"
          class="flex h-full min-h-0 flex-col items-center gap-2 px-2 py-3"
          aria-label="主导航"
        >
          <div class="flex w-full flex-1 flex-col items-center gap-2">
            <button
              v-if="hasPermission('menu.dashboard')"
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
              :class="activeTab === 'dashboard' ? 'bg-blue-50 text-blue-700' : ''"
              title="首页"
              @click="goTab('dashboard')"
            >
              <i class="fas fa-house fa-fw"></i>
            </button>
            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
              :class="activeTab === 'team' ? 'bg-blue-50 text-blue-700' : ''"
              title="团队管理"
              @click="goTab('team')"
            >
              <i class="fas fa-people-group fa-fw"></i>
            </button>
            <div
              v-if="hasPermission('menu.dashboard') && visibleSidebarGroups.length"
              class="my-1 h-px w-8 bg-slate-200"
              role="separator"
            />
            <div
              v-for="group in visibleSidebarGroups"
              :key="'fly-' + group.id"
              class="relative flex w-full justify-center"
              data-sidebar-flyout
            >
              <button
                :id="'sidebar-flyout-' + group.id"
                type="button"
                class="inline-flex h-10 w-10 items-center justify-center rounded-lg text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
                :title="group.label"
                @click.stop="toggleSidebarFlyout(group.id)"
              >
                <i :class="['fa-fw', 'fas', group.icon]"></i>
              </button>
              <ul
                v-show="flyoutOpenGroupId === group.id"
                class="admin-sidebar-flyout-menu absolute left-full top-0 z-[1060] ml-2 min-w-[11.5rem] rounded-lg border border-slate-200 bg-white py-1 text-sm shadow-lg"
                data-sidebar-flyout
                @click.stop
              >
                <li v-for="child in group.children" :key="child.id">
                  <button
                    type="button"
                    class="flex w-full items-center gap-2 px-3 py-2 text-left text-slate-700 hover:bg-slate-50"
                    :class="sidebarActiveTab === child.id ? 'bg-blue-50 text-blue-700' : ''"
                    @click="selectFlyoutTab(group.id, child.id)"
                  >
                    <i
                      :class="[child.iconPrefix || 'fas', child.icon, 'w-4 text-slate-400']"
                    ></i>
                    {{ child.label }}
                  </button>
                </li>
              </ul>
            </div>
          </div>
          <div class="relative w-full shrink-0 border-t border-slate-200 pt-3">
            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-300 text-slate-600 transition hover:bg-slate-50"
              title="版本与更新"
              @click="openVersionModal"
            >
              <i class="fas fa-tag"></i>
            </button>
            <span
              v-if="updateStatus.hasUpdate"
              class="absolute ml-[-8px] mt-[-6px] inline-flex h-2.5 w-2.5 rounded-full bg-red-500"
              aria-label="有新版本"
              title="有新版本"
            />
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
            <div class="admin-content-panel__body" :key="panelContentKey">
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
            <PipelineCreatePage
              v-if="isPipelineCreateRoute && hasPermission('menu.pipeline')"
            />
            <PipelineConfigPage
              v-if="isPipelineDetailRoute && hasPermission('menu.pipeline')"
            />
            <PipelineHistoryPage
              v-if="isPipelineHistoryRoute && hasPermission('menu.pipeline')"
            />
            <PipelinePanel
              v-if="
                activeTab === 'pipeline' &&
                !isPipelinePipelineSubRoute &&
                hasPermission('menu.pipeline')
              "
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
            <ApiDocsPanel v-if="activeTab === 'api-docs'" />
            <BuildConfigEditor
              v-if="activeTab === 'build-config-editor'"
              :initial-config="buildConfigToEdit"
              @save="handleBuildConfigSave"
              @cancel="handleBuildConfigCancel"
            />
            <TeamSettings v-if="activeTab === 'team'" />
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
                  class="border-0 bg-transparent p-0 text-sm text-slate-500 underline-offset-2 hover:text-blue-600 hover:underline"
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

      <FormDialog
        v-model="versionDialogOpen"
        title="版本与更新"
        icon="fa-code-branch"
        size="lg"
      >
        <div>
          <div v-if="checkLoading" class="py-6 text-center text-sm text-slate-500">
            <i class="fas fa-spinner fa-spin mr-2"></i>正在检查…
          </div>
          <template v-else>
            <dl class="grid grid-cols-1 gap-2 text-sm sm:grid-cols-[auto_1fr]">
              <dt class="font-medium text-slate-600">当前版本</dt>
              <dd>{{ displayCurrentVersion }}</dd>
              <dt class="font-medium text-slate-600">Gitee 最新</dt>
              <dd>{{ updateStatus.latestVersion || "—" }}</dd>
              <template v-if="updateStatus.releaseName">
                <dt class="font-medium text-slate-600">Release</dt>
                <dd>{{ updateStatus.releaseName }}</dd>
              </template>
            </dl>
            <div
              v-if="!updateStatus.checkSuccess"
              class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
            >
              {{ updateStatus.checkMessage || "检查更新失败" }}
            </div>
            <div
              v-else-if="updateStatus.hasUpdate"
              class="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            >
              <strong>发现新版本</strong>，请前往 Gitee Release 拉取镜像或按说明升级。
            </div>
            <div
              v-else-if="updateStatus.latestVersion"
              class="mt-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
            >
              已是最新版本。
            </div>
            <div v-if="updateStatus.checkSuccess && updateStatus.releaseBody" class="mt-3">
              <div class="mb-1 text-sm font-semibold text-slate-800">发行说明</div>
              <pre
                class="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-md border border-slate-100 bg-slate-50 p-3 text-xs text-slate-700"
              >{{ updateStatus.releaseBody }}</pre>
            </div>
            <div
              v-else-if="updateStatus.checkSuccess && updateStatus.latestVersion"
              class="mt-3 text-xs text-slate-500"
            >
              本 Release 暂无正文，可点击「在 Gitee 查看」。
            </div>
            <div class="mt-3 flex flex-wrap gap-3 text-sm">
              <a
                href="https://gitee.com/numen06/app2docker/releases"
                target="_blank"
                rel="noopener noreferrer"
                class="text-blue-600 hover:underline"
                >全部发行版</a
              >
              <a
                href="https://gitee.com/numen06/app2docker/tree/master/release-notes"
                target="_blank"
                rel="noopener noreferrer"
                class="text-blue-600 hover:underline"
                >仓库内版本说明（release-notes）</a
              >
            </div>
          </template>
        </div>
        <template #footer>
          <button
            type="button"
            class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 sm:w-auto sm:py-1.5"
            @click="versionDialogOpen = false"
          >
            关闭
          </button>
          <button
            type="button"
            class="w-full rounded-md border border-blue-200 bg-white px-3 py-2 text-sm text-blue-700 hover:bg-blue-50 disabled:opacity-50 sm:w-auto sm:py-1.5"
            :disabled="checkLoading"
            @click="refreshVersionCheck"
          >
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': checkLoading }"></i>
            重新检查
          </button>
          <button
            type="button"
            class="w-full rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 sm:w-auto sm:py-1.5"
            :disabled="checkLoading"
            @click="openReleaseUrl"
          >
            在 Gitee 查看
          </button>
        </template>
      </FormDialog>

      <ConfigModal v-if="showConfig" v-model="showConfig" />
      <UserCenterModal
        v-if="showUserCenter"
        v-model:show="showUserCenter"
        :username="username"
        :initial-tab="userCenterInitialTab"
      />

      <ToastHost />

      <transition name="fade">
        <div
          v-if="updateSnackVisible"
          class="fixed bottom-4 left-4 right-4 z-[2100] max-w-sm rounded-lg border border-slate-200 bg-white p-4 shadow-xl sm:left-auto"
          role="status"
        >
          <div class="flex items-start gap-2">
            <i class="fas fa-bell mt-0.5 text-blue-600"></i>
            <div class="flex-1 text-sm text-slate-800">{{ updateSnackMessage }}</div>
            <button
              type="button"
              class="rounded p-1 text-slate-500 hover:bg-slate-100"
              aria-label="关闭"
              @click="dismissUpdateSnack"
            >
              <i class="fas fa-times"></i>
            </button>
          </div>
        </div>
      </transition>
    </div>
</template>

<script setup>
import axios from "axios";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import ToastHost from "@/components/ui/ToastHost.vue";
import { useTaskCompletionWatcher } from "@/composables/useTaskCompletionWatcher";
import { useAuthStore } from "@/stores/auth";
import { useTeamStore } from "@/stores/team";
import { useModalEscape } from "@/composables/useModalEscape";
import { getToken, getUsername, logout } from "@/utils/auth";

import ApiDocsPanel from "@/components/ApiDocsPanel.vue";
import BuildConfigEditor from "@/components/BuildConfigEditor.vue";
import ConfigModal from "@/components/ConfigModal.vue";
import DashboardPanel from "@/components/DashboardPanel.vue";
import DataSourcePanel from "@/components/DataSourcePanel.vue";
import DeployTaskManager from "@/components/DeployTaskManager.vue";
import DockerManager from "@/components/DockerManager.vue";
import ExportPanel from "@/components/ExportPanel.vue";
import OperationLogs from "@/components/OperationLogs.vue";
import PipelinePanel from "@/components/PipelinePanel.vue";
import PipelineConfigPage from "@/pages/PipelineConfigPage.vue";
import PipelineCreatePage from "@/pages/PipelineCreatePage.vue";
import PipelineHistoryPage from "@/pages/PipelineHistoryPage.vue";
import RegistryPanel from "@/components/RegistryPanel.vue";
import ResourcePackagePanel from "@/components/ResourcePackagePanel.vue";
import RoleManagement from "@/components/RoleManagement.vue";
import StepBuildPanel from "@/components/StepBuildPanel.vue";
import TaskManager from "@/components/TaskManager.vue";
import TemplatePanel from "@/components/TemplatePanel.vue";
import TeamSettings from "@/components/team/TeamSettings.vue";
import UnifiedHostManager from "@/components/UnifiedHostManager.vue";
import UserCenterModal from "@/components/UserCenterModal.vue";
import UserManagement from "@/components/UserManagement.vue";
import { clearPermissionsCache, getUserPermissions } from "@/utils/permissions";

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
      { id: "api-docs", perm: null, label: "接口说明", icon: "fa-book" },
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
  "api-docs": "接口说明",
  "build-config-editor": "构建配置",
  team: "团队管理",
};

const SIDEBAR_STORAGE_KEY = "app2docker-admin-sidebar-collapsed";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const teamStore = useTeamStore();

const teamSwitching = ref(false);

const ACTIVE_TAB_STORAGE_KEY = "app2docker-active-tab";

const username = computed(() => authStore.username || getUsername() || "User");

const isPipelineCreateRoute = computed(() => route.name === "pipeline-create");

const isPipelineDetailRoute = computed(() => route.name === "pipeline-detail");

const isPipelineHistoryRoute = computed(() => route.name === "pipeline-history");

const isPipelinePipelineSubRoute = computed(
  () =>
    isPipelineCreateRoute.value ||
    isPipelineDetailRoute.value ||
    isPipelineHistoryRoute.value
);

const activeTab = computed(() => {
  if (isPipelinePipelineSubRoute.value) {
    return "";
  }
  const p = route.params.tab;
  return typeof p === "string" && p.length ? p : "dashboard";
});

const sidebarActiveTab = computed(() => {
  if (isPipelinePipelineSubRoute.value) return "pipeline";
  return activeTab.value;
});

const panelContentKey = computed(
  () =>
    `${teamStore.activeTeamId || "none"}-${route.fullPath || activeTab.value}`
);

const MOBILE_BREAKPOINT = 768;
const isMobile = ref(
  typeof window !== "undefined" ? window.innerWidth < MOBILE_BREAKPOINT : false
);
const sidebarOpen = ref(false);

function updateMobileState() {
  const mobile = window.innerWidth < MOBILE_BREAKPOINT;
  if (isMobile.value && !mobile) {
    sidebarOpen.value = false;
  }
  isMobile.value = mobile;
}

function closeMobileSidebar() {
  if (isMobile.value) {
    sidebarOpen.value = false;
  }
}

function goTab(tabId) {
  closeMobileSidebar();
  if (activeTab.value !== tabId) {
    router.push(`/app/${tabId}`);
  }
}

const flyoutOpenGroupId = ref(null);

function toggleSidebarFlyout(groupId) {
  flyoutOpenGroupId.value =
    flyoutOpenGroupId.value === groupId ? null : groupId;
}

function selectFlyoutTab(_groupId, childId) {
  flyoutOpenGroupId.value = null;
  goTab(childId);
}

const showConfig = ref(false);
const showUserCenter = ref(false);
const userCenterInitialTab = ref("password");
const runningTasksCount = ref(0);
const runningTasksList = ref([]);
const runningTasksDropdownWrap = ref(null);
const runningTasksDropdownMenu = ref(null);
const teamDropdownWrap = ref(null);
const userDropdownWrap = ref(null);
const userDropdownMenu = ref(null);
const runningTasksMenuOpen = ref(false);
const teamMenuOpen = ref(false);
const userMenuOpen = ref(false);
const runningTasksMenuStyle = ref({});
const userMenuStyle = ref({});
const buildConfigToEdit = ref({});
const permissionsLoaded = ref(false);
const userPermissions = ref(new Set());
const globalPermissions = ref(new Set());
const SYSTEM_TABS = new Set(["users", "roles"]);
let runningTasksTimer = null;

const sidebarCollapsed = ref(
  typeof localStorage !== "undefined" &&
    localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1"
);

function toggleSidebar() {
  if (isMobile.value) {
    sidebarOpen.value = !sidebarOpen.value;
    return;
  }
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
  SIDEBAR_GROUPS.map((g) => {
    if (g.id === "system" && !authStore.isGlobalAdmin) {
      return { ...g, children: [] };
    }
    return {
      ...g,
      children: g.children.filter((c) => {
        if (g.id === "system") {
          if (c.perm === "menu.users") {
            return globalPermissions.value.has("menu.users");
          }
          if (!c.perm) return true;
        }
        return !c.perm || hasPermission(c.perm);
      }),
    };
  }).filter((g) => g.children.length > 0)
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
  return group.children.some((c) => c.id === sidebarActiveTab.value);
}

watch(
  sidebarActiveTab,
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
  if (route.name === "pipeline-create") return "新建流水线";
  if (route.name === "pipeline-detail") return "流水线配置";
  if (route.name === "pipeline-history") return "历史构建";
  return PAGE_TITLES[activeTab.value] || "App2Docker";
});

const GITEE_REPO_URL = "https://gitee.com/numen06/app2docker";

const appVersion = ref("");
const checkLoading = ref(false);
const versionDialogOpen = ref(false);
const updateSnackVisible = ref(false);
const updateSnackMessage = ref("");
let updateSnackTimer = null;
const taskCompletionWatcher = useTaskCompletionWatcher();
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
  try {
    const res = await axios.get("/api/system/version");
    if (res.data?.success && res.data.version) {
      appVersion.value = res.data.version;
    }
  } catch (e) {
    console.error("获取系统版本失败:", e);
  }
}

function dismissUpdateSnack() {
  updateSnackVisible.value = false;
  if (updateSnackTimer) {
    clearTimeout(updateSnackTimer);
    updateSnackTimer = null;
  }
}

function showUpdateToastOnce(resData) {
  const key = `update-notified-${resData.latest_version || "unknown"}`;
  if (sessionStorage.getItem(key)) return;
  sessionStorage.setItem(key, "1");
  const summary = resData.release_body_summary
    ? `\n${resData.release_body_summary}`
    : "";
  updateSnackMessage.value = `当前 ${resData.current_version || "-"}，最新 ${resData.latest_version || "-"}${summary}`;
  updateSnackVisible.value = true;
  if (updateSnackTimer) clearTimeout(updateSnackTimer);
  updateSnackTimer = setTimeout(() => {
    dismissUpdateSnack();
  }, 8000);
}

async function loadUpdateCheck(options = {}) {
  const { showLoading = false, force = false } = options;
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
  versionDialogOpen.value = true;
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

async function refreshEffectivePermissions() {
  try {
    const global = await getUserPermissions();
    globalPermissions.value = global;

    const onSystemTab = SYSTEM_TABS.has(activeTab.value);
    if (authStore.isGlobalAdmin && onSystemTab) {
      userPermissions.value = new Set(global);
      return;
    }

    if (teamStore.activeTeamId) {
      if (!teamStore.menuPermissions.length) {
        await teamStore.fetchMenuPermissions(teamStore.activeTeamId);
      }
      const merged = new Set(teamStore.menuPermissions);
      if (authStore.isGlobalAdmin && global.has("menu.users")) {
        merged.add("menu.users");
      }
      userPermissions.value = merged;
    } else if (authStore.isGlobalAdmin) {
      userPermissions.value = new Set(global);
    } else {
      userPermissions.value = new Set(teamStore.menuPermissions || []);
    }
  } catch (error) {
    console.error("刷新菜单权限失败:", error);
    userPermissions.value = new Set();
  }
}

function handleNavigate(tab, params) {
  goTab(tab);
  if (params && params.status) {
    sessionStorage.setItem("taskStatusFilter", params.status);
  }
}

function teamRoleLabel(role) {
  const map = { owner: "所有者", admin: "管理员", member: "成员" };
  return map[role] || role;
}

/** 管理者（所有者/管理员）与成员用不同图标 */
function teamRoleIconClass(role) {
  if (role === "owner" || role === "admin") {
    return "fas fa-user-shield text-blue-600";
  }
  return "fas fa-user text-slate-500";
}

const activeMembership = computed(() =>
  teamStore.memberships.find((m) => m.team?.team_id === teamStore.activeTeamId)
);

const activeTeamDisplayName = computed(
  () => activeMembership.value?.team?.name || "选择团队"
);

const activeTeamMenuTitle = computed(() => {
  const m = activeMembership.value;
  if (!m?.team?.name) return "切换当前团队";
  return `${m.team.name} · ${teamRoleLabel(m.role)}`;
});

function teamOptionTitle(m) {
  return `${m.team?.name || ""} · ${teamRoleLabel(m.role)}`;
}

function closeTeamMenu() {
  teamMenuOpen.value = false;
}

function toggleTeamMenu() {
  teamMenuOpen.value = !teamMenuOpen.value;
  if (teamMenuOpen.value) {
    closeRunningTasksMenu();
    closeUserMenu();
  }
}

async function selectTeam(nextId) {
  closeTeamMenu();
  if (!nextId || nextId === teamStore.activeTeamId) return;
  teamSwitching.value = true;
  try {
    await teamStore.setCurrentTeam(nextId);
    if (permissionsLoaded.value) {
      await refreshEffectivePermissions();
    }
    window.dispatchEvent(
      new CustomEvent("team-context-changed", { detail: { teamId: nextId } })
    );
  } finally {
    teamSwitching.value = false;
  }
}

function openUserCenter(tab = "password") {
  userCenterInitialTab.value = tab === "appkeys" ? "appkeys" : "password";
  showUserCenter.value = true;
  closeUserMenu();
}

function adjustRunningTasksMenuPosition() {
  const menu = runningTasksDropdownMenu.value;
  if (!menu) return;
  const gap = 8;
  const rect = menu.getBoundingClientRect();
  const style = {};
  if (rect.right > window.innerWidth - gap) {
    style.right = "0";
    style.left = "auto";
  }
  if (rect.left < gap) {
    style.left = "0";
    style.right = "auto";
  }
  if (rect.bottom > window.innerHeight - gap) {
    style.top = "100%";
    style.bottom = "auto";
    style.maxHeight = "60vh";
    style.overflowY = "auto";
  }
  runningTasksMenuStyle.value = style;
}

function closeRunningTasksMenu() {
  runningTasksMenuOpen.value = false;
}

function closeUserMenu() {
  userMenuOpen.value = false;
  userMenuStyle.value = {};
}

function adjustUserMenuPosition() {
  const menu = userDropdownMenu.value;
  if (!menu || !userMenuOpen.value) return;
  const gap = 8;
  const rect = menu.getBoundingClientRect();
  const style = {
    zIndex: 1050,
    maxHeight: "min(60vh, calc(100vh - 16px))",
    overflowY: "auto",
  };

  let tx = 0;
  if (rect.right > window.innerWidth - gap) {
    tx += window.innerWidth - gap - rect.right;
  }
  if (rect.left + tx < gap) {
    tx = gap - rect.left;
  }
  if (tx !== 0) {
    style.transform = `translateX(${tx}px)`;
  }

  if (rect.bottom > window.innerHeight - gap) {
    style.top = "auto";
    style.bottom = "100%";
    style.marginBottom = "0.25rem";
    style.marginTop = "0";
  }

  userMenuStyle.value = style;
}

function handleTopbarResize() {
  updateMobileState();
  if (runningTasksMenuOpen.value) {
    adjustRunningTasksMenuPosition();
  }
  if (userMenuOpen.value) {
    adjustUserMenuPosition();
  }
}

function closeTopbarMenus() {
  closeRunningTasksMenu();
  closeTeamMenu();
  closeUserMenu();
}

function handleTopbarOutsideClick(event) {
  const inRunning = runningTasksDropdownWrap.value?.contains(event.target);
  const inTeam = teamDropdownWrap.value?.contains(event.target);
  const inUser = userDropdownWrap.value?.contains(event.target);
  const inFlyout = event.target.closest?.("[data-sidebar-flyout]");
  if (!inRunning) closeRunningTasksMenu();
  if (!inTeam) closeTeamMenu();
  if (!inUser) closeUserMenu();
  if (!inFlyout) {
    flyoutOpenGroupId.value = null;
  }
}

function toggleRunningTasksMenu() {
  runningTasksMenuOpen.value = !runningTasksMenuOpen.value;
  if (runningTasksMenuOpen.value) {
    closeTeamMenu();
    closeUserMenu();
    nextTick(() => {
      adjustRunningTasksMenuPosition();
    });
  }
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value;
  if (userMenuOpen.value) {
    closeTeamMenu();
    closeRunningTasksMenu();
    userMenuStyle.value = {};
    nextTick(() => {
      requestAnimationFrame(() => {
        adjustUserMenuPosition();
      });
    });
  } else {
    userMenuStyle.value = {};
  }
}

function goToRunningTasks() {
  closeRunningTasksMenu();
  handleNavigate("tasks", { status: "running" });
}

async function updateRunningTasksCount() {
  if (!getToken()) return;
  const teamId = teamStore.activeTeamIdForApi;
  if (!teamId) {
    runningTasksCount.value = 0;
    runningTasksList.value = [];
    return;
  }
  try {
    const res = await axios.get("/api/tasks/running", {
      params: { team_id: teamId },
    });
    const tasks = (res.data.tasks || [])
      .filter((t) => t.status === "running" || t.status === "pending")
      .sort((a, b) => {
        const timeA = new Date(a.created_at || 0).getTime();
        const timeB = new Date(b.created_at || 0).getTime();
        return timeB - timeA;
      });
    runningTasksCount.value = tasks.length;
    runningTasksList.value = tasks;
  } catch (error) {
    console.error("获取运行任务数量失败:", error);
  }
}

function handleGlobalTaskCreated() {
  try {
    sessionStorage.setItem("tasksNeedRefresh", "1");
  } catch {
    /* ignore */
  }
  updateRunningTasksCount();
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
    build: "bg-blue-600",
    export: "bg-cyan-600",
    deploy: "bg-emerald-600",
  };
  return map[type] || "bg-slate-500";
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

async function handleLogout() {
  if (!confirm("确定要退出登录吗？")) return;
  await logout();
  authStore.clearSession();
  teamStore.reset();
  permissionsLoaded.value = false;
  userPermissions.value = new Set();
  globalPermissions.value = new Set();
  clearPermissionsCache();
  runningTasksCount.value = 0;
  runningTasksList.value = [];
  stopRunningTasksTimer();
  closeTopbarMenus();
  flyoutOpenGroupId.value = null;
  dismissUpdateSnack();
  router.push("/login");
}

useModalEscape();

function handleBuildConfigSave(config) {
  localStorage.setItem("buildConfigEdited", JSON.stringify(config));
  window.dispatchEvent(new CustomEvent("buildConfigSaved"));
  router.push("/app/pipeline");
}

function handleBuildConfigCancel() {
  router.push("/app/pipeline");
}

watch(
  () => teamStore.activeTeamId,
  async () => {
    if (!permissionsLoaded.value) return;
    await refreshEffectivePermissions();
  }
);

watch(activeTab, async () => {
  if (!permissionsLoaded.value) return;
  await refreshEffectivePermissions();
});

onMounted(async () => {
  updateMobileState();
  authStore.syncUsernameFromStorage();
  authStore.applyAxiosAuthHeader();

  try {
    await authStore.fetchMe().catch(() => {});
    await teamStore.fetchTeams().catch(() => {});
    const qTeam = route.query.team_id;
    if (typeof qTeam === "string" && qTeam) {
      const ok = teamStore.memberships.some((m) => m.team?.team_id === qTeam);
      if (ok) await teamStore.setCurrentTeam(qTeam);
    }
    await refreshEffectivePermissions();
  } catch (error) {
    console.error("获取用户权限失败:", error);
    userPermissions.value = new Set();
  } finally {
    permissionsLoaded.value = true;
  }

  startRunningTasksTimer();
  taskCompletionWatcher.start();

  await loadSystemVersion();
  await loadUpdateCheck();

  window.addEventListener("navigate", handleNavigateEvent);
  window.addEventListener("taskCreated", handleGlobalTaskCreated);
  document.addEventListener("click", handleTopbarOutsideClick);
  window.addEventListener("resize", handleTopbarResize);
});

function handleNavigateEvent(e) {
  if (e.detail && e.detail.tab) {
    goTab(e.detail.tab);
  }
}

onUnmounted(() => {
  taskCompletionWatcher.stop();
  stopRunningTasksTimer();
  dismissUpdateSnack();
  window.removeEventListener("navigate", handleNavigateEvent);
  window.removeEventListener("taskCreated", handleGlobalTaskCreated);
  document.removeEventListener("click", handleTopbarOutsideClick);
  window.removeEventListener("resize", handleTopbarResize);
});

watch(runningTasksCount, () => {
  if (!runningTasksCount.value) {
    closeRunningTasksMenu();
  }
});
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

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
  min-width: 0;
  max-width: 100%;
  transition: margin-left 0.2s ease;
  display: flex;
  flex-direction: column;
}

.admin-layout--sidebar-collapsed .admin-main-wrap {
  margin-left: var(--admin-sidebar-collapsed-width, 64px);
}

.admin-layout--mobile .admin-main-wrap,
.admin-layout--mobile.admin-layout--sidebar-collapsed .admin-main-wrap {
  margin-left: 0;
}

.admin-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  max-width: 100%;
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
  min-width: 0;
  max-width: 100%;
  background: #fff;
  border: 1px solid var(--admin-panel-border, #e2e8f0);
  border-radius: var(--admin-panel-radius, 0.5rem);
  box-shadow: var(--admin-panel-shadow, 0 1px 2px 0 rgb(15 23 42 / 0.05));
  overflow: visible;
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
  min-width: 0;
  max-width: 100%;
  overflow: visible;
}

/* Bootstrap 宽表：移动端横向滚动 */
.admin-content-panel__body .table-responsive {
  display: block;
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.admin-content-panel__body .table-responsive > table,
.admin-content-panel__body .table-responsive > .table {
  min-width: 36rem;
  margin-bottom: 0;
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

.admin-topbar-actions .admin-topbar-control {
  box-sizing: border-box;
  height: 2.25rem;
  min-height: 2.25rem;
}

.admin-team-switcher-trigger {
  max-width: 100%;
}

.admin-team-switcher-menu {
  z-index: 1055;
}

.admin-running-dropdown {
  z-index: 1055;
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

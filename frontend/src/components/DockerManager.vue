<template>
  <div class="docker-manager">
    <!-- Docker 服务信息区域 -->
    <div class="rounded-lg border border-slate-200 bg-white shadow-sm mb-3">
      <div
        class="border-b border-slate-200 bg-slate-50 px-4 py-3 bg-blue-600 text-white flex justify-between items-center py-2"
      >
        <div>
          <AppIcon  name="server" />
          <strong class="ms-1">Docker 服务信息</strong>
          <small
            v-if="dockerInfo && dockerInfo.cached_at"
            class="ms-3 opacity-75"
          >
            <AppIcon  name="clock" />
            缓存时间: {{ formatTime(dockerInfo.cached_at) }}
            <span v-if="dockerInfo.cache_age_minutes" class="ms-1">
              ({{ dockerInfo.cache_age_minutes }}分钟前)
            </span>
          </small>
        </div>
        <div class="flex gap-2">
          <button
            class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 min-h-9 py-1.5 text-xs border border-slate-200 bg-white text-slate-700"
            @click="refreshDockerInfo(false)"
            :disabled="loadingInfo"
            title="刷新（使用缓存）"
          >
            <AppIcon name="sync-alt" />
          </button>
          <button
            class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 min-h-9 py-1.5 text-xs border border-amber-400 bg-amber-400 text-slate-900 hover:bg-amber-500"
            @click="forceRefreshDockerInfo()"
            :disabled="loadingInfo"
            title="强制刷新（重新获取）"
          >
            <AppIcon  v-if="loadingInfo" name="sync-alt" spin />
            <AppIcon  v-else name="redo" />
            <span class="ms-1 hidden md:inline">强制刷新</span>
          </button>
        </div>
      </div>
      <div class="p-4 py-2">
        <div v-if="loadingInfo" class="text-center py-3">
          <AppIcon name="spinner" spin />
          <span class="ms-2">正在获取 Docker 信息...</span>
        </div>

        <div v-else-if="dockerInfo" class="grid grid-cols-1 gap-3 md:grid-cols-12 gap-2">
          <!-- 第一行：基本信息 -->
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">连接状态</div>
              <div class="info-value">
                <span
                  class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                  :class="dockerInfo.connected ? 'bg-green-600 text-white' : 'bg-red-600 text-white'"
                >
                  {{ dockerInfo.connected ?"已连接" :"未连接" }}
                </span>
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">Docker 版本</div>
              <div class="info-value">{{ dockerInfo.version ||"-" }}</div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">API 版本</div>
              <div class="info-value">{{ dockerInfo.api_version ||"-" }}</div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">构建器类型</div>
              <div class="info-value">
                <span
                  class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                  :class="getBuilderBadgeClass(dockerInfo.builder_type)"
                >
                  {{ getBuilderLabel(dockerInfo.builder_type) }}
                </span>
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">Buildx 支持</div>
              <div class="info-value">
                <span
                  class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium"
                  :class="dockerInfo.buildx_available ? 'bg-green-600 text-white' : 'bg-amber-400 text-slate-900'"
                >
                  {{ dockerInfo.buildx_available ?"✓ 支持" :"✗ 不支持" }}
                </span>
                <small
                  v-if="dockerInfo.buildx_version"
                  class="block text-slate-500 mt-1"
                >
                  {{ dockerInfo.buildx_version }}
                </small>
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2" v-if="dockerInfo.remote_host">
            <div class="info-item">
              <div class="info-label">远程主机</div>
              <div class="info-value text-sm">{{ dockerInfo.remote_host }}</div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">操作系统</div>
              <div class="info-value">
                {{ dockerInfo.os_type ||"-" }} {{ dockerInfo.arch ||"" }}
              </div>
            </div>
          </div>

          <!-- 第二行：资源统计 -->
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">镜像数量</div>
              <div class="info-value">{{ dockerInfo.images_count || 0 }}</div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">容器(运行/总)</div>
              <div class="info-value">
                <span class="text-green-600">{{
                  dockerInfo.containers_running || 0
                }}</span>
                / {{ dockerInfo.containers_total || 0 }}
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">存储驱动</div>
              <div class="info-value">
                {{ dockerInfo.storage_driver ||"-" }}
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">数据根目录</div>
              <div
                class="info-value text-sm truncate"
                :title="dockerInfo.docker_root"
              >
                {{ dockerInfo.docker_root ||"-" }}
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">镜像占用</div>
              <div class="info-value">
                {{ formatBytes(dockerInfo.images_size) }}
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">容器占用</div>
              <div class="info-value">
                {{ formatBytes(dockerInfo.containers_size) }}
              </div>
            </div>
          </div>

          <!-- 第三行：系统信息 -->
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">CPU 核心</div>
              <div class="info-value">{{ dockerInfo.ncpu ||"-" }}</div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">总内存</div>
              <div class="info-value">
                {{ formatBytes(dockerInfo.mem_total) }}
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">内核版本</div>
              <div class="info-value text-sm">
                {{ dockerInfo.kernel_version ||"-" }}
              </div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">运行时</div>
              <div class="info-value">{{ dockerInfo.runtime ||"-" }}</div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">数据卷数量</div>
              <div class="info-value">{{ dockerInfo.volumes_count || 0 }}</div>
            </div>
          </div>
          <div class="col-span-6 md:col-span-2">
            <div class="info-item">
              <div class="info-label">网络数量</div>
              <div class="info-value">{{ dockerInfo.networks_count || 0 }}</div>
            </div>
          </div>
        </div>

        <div v-else class="rounded-md border px-3 py-2 text-sm border-amber-200 bg-amber-50 text-amber-900 mb-0">
          <AppIcon  name="exclamation-triangle" />
          无法获取 Docker 信息，请检查服务状态
        </div>

        <!-- 编译方式限制说明 -->
        <div v-if="dockerInfo" class="rounded-md border px-3 py-2 text-sm border-sky-200 bg-sky-50 text-sky-900 px-2 py-1 text-xs mb-0 mt-2">
          <div class="flex items-start">
            <AppIcon  name="info-circle" class="me-2 mt-1" />
            <div class="flex-1">
              <strong>编译方式说明：</strong>
              <ul class="mb-0 mt-1 text-sm">
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
                class="mt-2 text-sm text-slate-500"
              >
                <AppIcon  name="check-circle" class="text-green-600" />
                当前模式：<strong>容器内编译（本地 Docker）</strong>
                <span v-if="dockerInfo.buildx_available" class="ms-2">
                  <AppIcon  name="check" class="text-green-600" /> Buildx:
                  {{ dockerInfo.buildx_version }}
                </span>
                <span v-else class="ms-2">
                  <AppIcon  name="exclamation-triangle" class="text-amber-600" />
                  Buildx 不可用
                </span>
              </div>
              <div
                v-else-if="
                  dockerInfo.builder_type === 'remote' && dockerInfo.remote_host"
                class="mt-2 text-sm text-slate-500"
              >
                <AppIcon  name="check-circle" class="text-green-600" />
                当前模式：<strong>{{ getCurrentBuildMode() }}</strong> ({{
                  dockerInfo.remote_host
                }})
                <span v-if="dockerInfo.buildx_available" class="ms-2">
                  <AppIcon  name="check" class="text-green-600" /> Buildx:
                  {{ dockerInfo.buildx_version }}
                </span>
                <span v-else class="ms-2">
                  <AppIcon  name="exclamation-triangle" class="text-amber-600" />
                  Buildx 不可用
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 容器和镜像 Tab 管理 -->
    <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div class="border-b border-slate-200 bg-slate-50 px-4 py-3 bg-white py-0">
        <ul class="docker-tabs">
          <li class="docker-tabs__item">
            <button
              class="docker-tab"
              :class="{ 'is-active': activeTab === 'containers' }"
              @click="activeTab = 'containers'"
              type="button"
            >
              <AppIcon  name="cubes" /> 容器管理
              <span v-if="containerTotal > 0" class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-sky-500 text-white ms-1">{{
                containerTotal
              }}</span>
            </button>
          </li>
          <li class="docker-tabs__item">
            <button
              class="docker-tab"
              :class="{ 'is-active': activeTab === 'images' }"
              @click="activeTab = 'images'"
              type="button"
            >
              <AppIcon  name="images" /> 镜像管理
              <span v-if="imageTotal > 0" class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-slate-500 text-white ms-1">{{
                imageTotal
              }}</span>
            </button>
          </li>
        </ul>
      </div>

      <!-- 容器 Tab -->
      <div v-show="activeTab === 'containers'" class="p-4 p-0">
        <!-- 搜索和操作栏 -->
        <div
          class="flex justify-between items-center p-2 border-b border-slate-200 bg-slate-50"
        >
          <div class="flex gap-2 items-center flex-1">
            <div class="flex w-full text-sm" style="max-width: 300px">
              <span class="inline-flex items-center border border-slate-200 bg-slate-50 px-3 text-sm text-slate-500"
                ><AppIcon name="search" /></span>
              <input
                type="text"
                class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
                v-model="containerSearch"
                placeholder="搜索容器名称/镜像..."
                @input="filterContainers"
              />
            </div>
            <select
              class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50 "
              style="width: auto"
              v-model="containerStatusFilter"
              @change="filterContainers"
            >
              <option value="">全部状态</option>
              <option value="running">运行中</option>
              <option value="exited">已停止</option>
              <option value="paused">已暂停</option>
            </select>
            <small v-if="containerLastSync" class="text-slate-500">
              <AppIcon  name="clock" /> {{ formatTime(containerLastSync) }}
            </small>
          </div>
          <div class="flex gap-1">
            <button
              class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 min-h-9 py-1.5 text-xs border border-amber-400 bg-amber-400 text-slate-900 hover:bg-amber-500"
              @click="pruneContainers"
              :disabled="loadingContainers"
              title="清理已停止的容器"
            >
              <AppIcon  name="broom" /> 清理
            </button>
            <button
              class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 min-h-9 py-1.5 text-xs border border-blue-600 bg-blue-600 text-white hover:bg-blue-700"
              @click="loadContainers(true)"
              :disabled="loadingContainers"
            >
              <AppIcon
               name="sync-alt" />
            </button>
          </div>
        </div>

        <div v-if="loadingContainers" class="text-center py-4">
          <AppIcon name="spinner" spin />
          <span class="ms-2">加载容器列表...</span>
        </div>

        <div
          v-else-if="containers.length === 0"
          class="text-center text-slate-500 py-4"
        >
          <AppIcon  name="cube" />
          {{
            containerSearch || containerStatusFilter
              ?"未找到匹配的容器"
              :"暂无容器"
          }}
        </div>

        <div v-else class="table-scroll overflow-x-auto">
          <table class="docker-table mb-0">
            <thead class="bg-slate-50">
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
                  <code class="text-sm">{{ c.name }}</code>
                </td>
                <td
                  class="text-sm text-slate-500 truncate"
                  style="max-width: 200px"
                  :title="c.image"
                >
                  {{ c.image }}
                </td>
                <td>
                  <span class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium" :class="getStatusBadge(c.state)">{{
                    c.status
                  }}</span>
                </td>
                <td class="text-sm">{{ c.ports ||"-" }}</td>
                <td class="text-sm">{{ formatTime(c.created) }}</td>
                <td class="text-end">
                  <div class="inline-flex items-stretch text-sm">
                    <button
                      v-if="c.state !== 'running'"
                      class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 border border-green-300 text-green-700 hover:bg-green-50"
                      @click="startContainer(c)"
                      title="启动"
                    >
                      <AppIcon  name="play" />
                    </button>
                    <button
                      v-if="c.state === 'running'"
                      class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 border border-amber-300 text-amber-800 hover:bg-amber-50"
                      @click="stopContainer(c, false)"
                      title="停止"
                    >
                      <AppIcon  name="stop" />
                    </button>
                    <button
                      v-if="c.state === 'running'"
                      class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 border border-red-300 text-red-700 hover:bg-red-50"
                      @click="stopContainer(c, true)"
                      title="强制停止"
                    >
                      <AppIcon  name="power-off" />
                    </button>
                    <button
                      v-if="c.state === 'running'"
                      class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 border border-sky-300 text-sky-700 hover:bg-sky-50"
                      @click="restartContainer(c)"
                      title="重启"
                    >
                      <AppIcon  name="redo" />
                    </button>
                    <button
                      class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 border border-red-300 text-red-700 hover:bg-red-50"
                      @click="removeContainer(c)"
                      title="删除"
                    >
                      <AppIcon  name="trash" />
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
          class="flex justify-between items-center p-2 border-t border-slate-200"
        >
          <div class="text-slate-500 text-sm">
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
            <ul class="docker-pager mb-0">
              <li class="docker-pager-item" :class="{ 'is-disabled': containerPage === 1 }">
                <button
                  class="docker-pager-button"
                  @click="changeContainerPage(1)"
                  :disabled="containerPage === 1"
                >
                  <AppIcon  name="angle-double-left" />
                </button>
              </li>
              <li class="docker-pager-item" :class="{ 'is-disabled': containerPage === 1 }">
                <button
                  class="docker-pager-button"
                  @click="changeContainerPage(containerPage - 1)"
                  :disabled="containerPage === 1"
                >
                  <AppIcon  name="angle-left" />
                </button>
              </li>
              <li
                v-for="page in visibleContainerPages"
                :key="page"
                class="docker-pager-item"
                :class="{ 'is-active': containerPage === page }"
              >
                <button class="docker-pager-button" @click="changeContainerPage(page)">
                  {{ page }}
                </button>
              </li>
              <li
                class="docker-pager-item"
                :class="{ 'is-disabled': containerPage === containerTotalPages }"
              >
                <button
                  class="docker-pager-button"
                  @click="changeContainerPage(containerPage + 1)"
                  :disabled="containerPage === containerTotalPages"
                >
                  <AppIcon  name="angle-right" />
                </button>
              </li>
              <li
                class="docker-pager-item"
                :class="{ 'is-disabled': containerPage === containerTotalPages }"
              >
                <button
                  class="docker-pager-button"
                  @click="changeContainerPage(containerTotalPages)"
                  :disabled="containerPage === containerTotalPages"
                >
                  <AppIcon  name="angle-double-right" />
                </button>
              </li>
            </ul>
          </nav>
        </div>
      </div>

      <!-- 镜像 Tab -->
      <div v-show="activeTab === 'images'" class="p-4 p-0">
        <!-- 搜索和操作栏 -->
        <div
          class="flex justify-between items-center p-2 border-b border-slate-200 bg-slate-50"
        >
          <div class="flex gap-2 items-center flex-1">
            <div class="flex w-full text-sm" style="max-width: 300px">
              <span class="inline-flex items-center border border-slate-200 bg-slate-50 px-3 text-sm text-slate-500"
                ><AppIcon name="search" /></span>
              <input
                type="text"
                class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
                v-model="imageSearch"
                placeholder="搜索镜像名称/标签..."
                @input="filterImages"
              />
            </div>
            <select
              class="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50 "
              style="width: auto"
              v-model="imageTagFilter"
              @change="filterImages"
            >
              <option value="">全部标签</option>
              <option value="latest">latest</option>
              <option value="none">&lt;none&gt;</option>
            </select>
            <small v-if="imageLastSync" class="text-slate-500">
              <AppIcon  name="clock" /> {{ formatTime(imageLastSync) }}
            </small>
          </div>
          <div class="flex gap-1">
            <button
              class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 min-h-9 py-1.5 text-xs border border-amber-400 bg-amber-400 text-slate-900 hover:bg-amber-500"
              @click="pruneImages"
              :disabled="loadingImages"
              title="清理未使用镜像"
            >
              <AppIcon  name="broom" /> 清理
            </button>
            <button
              class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 min-h-9 py-1.5 text-xs border border-blue-600 bg-blue-600 text-white hover:bg-blue-700"
              @click="loadImages(true)"
              :disabled="loadingImages"
            >
              <AppIcon
               name="sync-alt" />
            </button>
          </div>
        </div>

        <div v-if="loadingImages" class="text-center py-4">
          <AppIcon name="spinner" spin />
          <span class="ms-2">加载镜像列表...</span>
        </div>

        <div
          v-else-if="images.length === 0"
          class="text-center text-slate-500 py-4"
        >
          <AppIcon  name="box-open" />
          {{ imageSearch || imageTagFilter ?"未找到匹配的镜像" :"暂无镜像" }}
        </div>

        <div v-else class="table-scroll overflow-x-auto">
          <table class="docker-table mb-0">
            <thead class="bg-slate-50">
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
                  <code class="text-sm text-primary">{{
                    img.repository ||"&lt;none&gt;"
                  }}</code>
                </td>
                <td>
                  <span class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-sky-500 text-white">{{
                    img.tag ||"&lt;none&gt;"
                  }}</span>
                </td>
                <td>
                  <small class="text-slate-500 font-monospace">{{
                    img.id ? img.id.substring(7, 19) :"-"
                  }}</small>
                </td>
                <td class="text-sm">{{ formatBytes(img.size) }}</td>
                <td class="text-sm">{{ formatTime(img.created) }}</td>
                <td class="text-end">
                  <button
                    class="inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50 min-h-9 py-1.5 text-xs border border-red-300 text-red-700 hover:bg-red-50"
                    @click="deleteImage(img)"
                    title="删除镜像"
                  >
                    <AppIcon  name="trash" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 镜像分页 -->
        <div
          v-if="imageTotalPages > 1"
          class="flex justify-between items-center p-2 border-t border-slate-200"
        >
          <div class="text-slate-500 text-sm">
            显示第
            {{ imageTotal > 0 ? (imagePage - 1) * imagePageSize + 1 : 0 }} -
            {{ Math.min(imagePage * imagePageSize, imageTotal) }}
            条，共 {{ imageTotal }} 条
          </div>
          <nav>
            <ul class="docker-pager mb-0">
              <li class="docker-pager-item" :class="{ 'is-disabled': imagePage === 1 }">
                <button
                  class="docker-pager-button"
                  @click="changeImagePage(1)"
                  :disabled="imagePage === 1"
                >
                  <AppIcon  name="angle-double-left" />
                </button>
              </li>
              <li class="docker-pager-item" :class="{ 'is-disabled': imagePage === 1 }">
                <button
                  class="docker-pager-button"
                  @click="changeImagePage(imagePage - 1)"
                  :disabled="imagePage === 1"
                >
                  <AppIcon  name="angle-left" />
                </button>
              </li>
              <li
                v-for="page in visibleImagePages"
                :key="page"
                class="docker-pager-item"
                :class="{ 'is-active': imagePage === page }"
              >
                <button class="docker-pager-button" @click="changeImagePage(page)">
                  {{ page }}
                </button>
              </li>
              <li
                class="docker-pager-item"
                :class="{ 'is-disabled': imagePage === imageTotalPages }"
              >
                <button
                  class="docker-pager-button"
                  @click="changeImagePage(imagePage + 1)"
                  :disabled="imagePage === imageTotalPages"
                >
                  <AppIcon  name="angle-right" />
                </button>
              </li>
              <li
                class="docker-pager-item"
                :class="{ 'is-disabled': imagePage === imageTotalPages }"
              >
                <button
                  class="docker-pager-button"
                  @click="changeImagePage(imageTotalPages)"
                  :disabled="imagePage === imageTotalPages"
                >
                  <AppIcon  name="angle-double-right" />
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
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

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
      toastInfo("Docker信息已强制刷新");
    }
  } catch (error) {
    console.error("强制刷新 Docker 信息失败:", error);
    toastError("强制刷新失败:" + (error.response?.data?.detail || error.message));
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
    (p) => p !=="..." || pages.indexOf(p) === pages.lastIndexOf(p)
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
    toastApiError(e,"启动容器失败");
  }
}

async function stopContainer(c, force = false) {
  try {
    await axios.post(`/api/docker/containers/${c.id}/stop`, null, {
      params: { force },
    });
    loadContainers(true);
  } catch (e) {
    toastApiError(e,"停止容器失败");
  }
}

async function restartContainer(c) {
  try {
    await axios.post(`/api/docker/containers/${c.id}/restart`);
    loadContainers(true);
  } catch (e) {
    toastApiError(e,"重启容器失败");
  }
}

async function removeContainer(c) {
  if (!(await showConfirm({ message: `确定要删除容器 ${c.name} 吗？`, danger: true }))) return;
  try {
    await axios.delete(`/api/docker/containers/${c.id}`);
    loadContainers(true);
  } catch (e) {
    toastApiError(e,"删除容器失败");
  }
}

async function pruneContainers() {
  if (!(await showConfirm({ message:"确定要清理所有已停止的容器吗？", danger: true }))) return;
  try {
    const res = await axios.post("/api/docker/containers/prune");
    toastSuccess(`已清理 ${res.data.deleted || 0} 个容器`);
    loadContainers(true);
    refreshDockerInfo(true);
  } catch (e) {
    toastApiError(e,"清理容器失败");
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
    (p) => p !=="..." || pages.indexOf(p) === pages.lastIndexOf(p)
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
  if (!(await showConfirm({ message: `确定要删除镜像 ${imgName} 吗？`, danger: true }))) return;
  try {
    await axios.delete("/api/docker/images", { data: { image_id: img.id } });
    loadImages(true);
    refreshDockerInfo(true);
  } catch (e) {
    toastApiError(e,"删除镜像失败");
  }
}

async function pruneImages() {
  if (!(await showConfirm({ message:"确定要清理所有未使用的镜像吗？这将释放磁盘空间。", danger: true }))) return;
  try {
    const res = await axios.post("/api/docker/images/prune");
    toastSuccess(`已清理，释放空间: ${formatBytes(res.data.space_reclaimed || 0)}`);
    loadImages(true);
    refreshDockerInfo(true);
  } catch (e) {
    toastApiError(e,"清理镜像失败");
  }
}

// === 工具函数 ===
function formatBytes(bytes) {
  if (!bytes) return"-";
  const units = ["B","KB","MB","GB","TB"];
  let idx = 0,
    value = bytes;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx++;
  }
  return `${value.toFixed(1)} ${units[idx]}`;
}

function formatTime(timeStr) {
  if (!timeStr) return"-";
  try {
    return new Date(timeStr).toLocaleString("zh-CN", {
      month:"2-digit",
      day:"2-digit",
      hour:"2-digit",
      minute:"2-digit",
    });
  } catch {
    return timeStr;
  }
}

function getBuilderBadgeClass(type) {
  return (
    { local:"bg-green-600 text-white", remote:"bg-blue-600 text-white", mock:"bg-amber-400 text-slate-900" }[type] ||"bg-slate-500 text-white"
  );
}

function getBuilderLabel(type) {
  return { local:"本地", remote:"远程", mock:"模拟" }[type] ||"未知";
}

function getStatusBadge(state) {
  return (
    {
      running:"bg-green-600 text-white",
      exited:"bg-slate-500 text-white",
      paused:"bg-amber-400 text-slate-900",
      created:"bg-sky-500 text-white",
    }[state] ||"bg-slate-500 text-white"
  );
}

// 获取当前编译模式名称
function getCurrentBuildMode() {
  if (!dockerInfo.value || dockerInfo.value.builder_type !=="remote") {
    return"";
  }
  // 优先使用 remote_config，如果没有则从 remote_host 解析
  const remoteConfig = dockerInfo.value.remote_config;
  if (remoteConfig) {
    if (remoteConfig.use_tls) {
      return"远程 Docker 主机（TLS）";
    } else if (remoteConfig.port === 2375) {
      return"TCP 2375 编译";
    } else {
      // 统一显示为"远程 Docker"
      const protocol = remoteConfig.use_tls ?"TLS" :"TCP";
      const port = remoteConfig.port || (remoteConfig.use_tls ? 2376 : 2375);
      return `远程 Docker (${protocol}://${remoteConfig.host}:${port})`;
    }
  } else {
    // 兼容旧格式：从 remote_host 解析
    const remoteHost = dockerInfo.value.remote_host ||"";
    const portMatch = remoteHost.match(/:(\d+)$/);
    if (portMatch) {
      const port = parseInt(portMatch[1]);
      const protocol = port === 2376 ?"TLS" :"TCP";
      return `远程 Docker (${protocol}://${remoteHost})`;
    }
    return remoteHost ? `远程 Docker (${remoteHost})` :"远程 Docker";
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

.docker-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin: 0;
  padding: 0.25rem;
  list-style: none;
}

.docker-tab {
  display: inline-flex;
  min-height: 2.5rem;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  color: rgb(71 85 105);
  font-size: 0.875rem;
  font-weight: 500;
}

.docker-tab:hover {
  background: rgb(241 245 249);
  color: rgb(15 23 42);
}

.docker-tab.is-active {
  background: rgb(37 99 235);
  color: #fff;
}

/* 表格样式 */
.docker-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.docker-table th {
  font-weight: 600;
  font-size: 0.85rem;
  white-space: nowrap;
  padding: 0.5rem;
  color: rgb(51 65 85);
}
.docker-table td {
  vertical-align: middle;
  font-size: 0.9rem;
  padding: 0.4rem 0.5rem;
  border-top: 1px solid rgb(226 232 240);
}

/* 分页样式优化 */
.docker-pager {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  padding: 0;
  list-style: none;
}

.docker-pager-button {
  display: inline-flex;
  min-height: 2.25rem;
  align-items: center;
  justify-content: center;
  border: 1px solid rgb(226 232 240);
  border-radius: 0.375rem;
  padding: 0.375rem 0.625rem;
  background: #fff;
  color: rgb(51 65 85);
  font-size: 0.875rem;
  min-width: 38px;
  text-align: center;
}

.docker-pager-button:hover {
  background: rgb(248 250 252);
}

.docker-pager-item.is-disabled .docker-pager-button,
.docker-pager-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.docker-pager-item.is-active .docker-pager-button {
  border-color: rgb(37 99 235);
  background: rgb(37 99 235);
  color: #fff;
  font-weight: 600;
}
</style>

<template>
  <div class="animate-in fade-in duration-300">
    <!-- 统计信息栏 -->
    <div class="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
      <StatCard title="总任务" :value="taskStats.total" icon="fa-tasks" accent="blue">
        <template #footer>
          <div class="flex flex-wrap gap-1.5">
            <Badge variant="success">{{ taskStats.completed }}</Badge>
            <Badge variant="warning">{{ taskStats.running }}</Badge>
            <Badge variant="danger">{{ taskStats.failed }}</Badge>
          </div>
        </template>
      </StatCard>

      <StatCard
        title="任务类型"
        :value="taskStats.build + taskStats.export + taskStats.deploy"
        icon="fa-layer-group"
        accent="sky"
      >
        <template #footer>
          <div class="flex flex-wrap gap-1.5">
            <Badge variant="default">{{ taskStats.build }} 构建</Badge>
            <Badge variant="success">{{ taskStats.export }} 导出</Badge>
            <Badge variant="info">{{ taskStats.deploy }} 部署</Badge>
          </div>
        </template>
      </StatCard>

      <StatCard title="目录统计" value="—" icon="fa-folder" accent="slate">
        <template #footer>
          <div class="space-y-1 text-sm text-slate-600">
            <div class="flex items-center gap-1.5">
              <i class="fas fa-download text-green-600"></i>
              <span>{{ exportDirSize }}</span>
            </div>
            <div class="flex items-center gap-1.5">
              <i class="fas fa-folder-open text-slate-500"></i>
              <span>{{ buildDirSize }}</span>
            </div>
          </div>
        </template>
      </StatCard>

      <StatCard
        title="成功率"
        :value="taskStats.successRate + '%'"
        icon="fa-chart-line"
        accent="green"
      >
        <template #footer>
          <p class="text-xs text-slate-500">
            {{ taskStats.completed }}/{{ taskStats.total || 1 }} 完成
          </p>
        </template>
      </StatCard>

      <StatCard
        title="全局并发"
        :value="queueRunningCount + '/' + maxConcurrentTasks"
        icon="fa-stream"
        accent="amber"
      >
        <template #footer>
          <p class="text-xs text-slate-500">排队中 {{ queuePendingCount }} 个任务</p>
        </template>
      </StatCard>
    </div>

    <PageToolbar title="任务管理" icon="fa-tasks">
      <template #actions>
        <div class="flex flex-wrap gap-1 rounded-md border border-slate-200 p-0.5">
          <Button
            size="sm"
            :variant="statusFilter === '' ? 'default' : 'ghost'"
            title="全部状态"
            @click="statusFilter = ''; handleFilterChange()"
          >
            全部状态
          </Button>
          <Button
            size="sm"
            :variant="statusFilter === 'pending' ? 'default' : 'ghost'"
            title="等待中"
            @click="statusFilter = 'pending'; handleFilterChange()"
          >
            等待中
          </Button>
          <Button
            size="sm"
            :variant="statusFilter === 'running' ? 'default' : 'ghost'"
            title="进行中"
            @click="statusFilter = 'running'; handleFilterChange()"
          >
            进行中
          </Button>
          <Button
            size="sm"
            :variant="statusFilter === 'completed' ? 'default' : 'ghost'"
            title="已完成"
            @click="statusFilter = 'completed'; handleFilterChange()"
          >
            已完成
          </Button>
          <Button
            size="sm"
            :variant="statusFilter === 'failed' ? 'default' : 'ghost'"
            title="失败"
            @click="statusFilter = 'failed'; handleFilterChange()"
          >
            失败
          </Button>
        </div>

        <div class="flex flex-wrap gap-1 rounded-md border border-slate-200 p-0.5">
          <Button
            size="sm"
            :variant="categoryFilter === '' ? 'default' : 'ghost'"
            title="全部类型"
            @click="categoryFilter = ''; handleFilterChange()"
          >
            全部类型
          </Button>
          <Button
            size="sm"
            :variant="categoryFilter === 'build' ? 'default' : 'ghost'"
            title="构建任务"
            @click="categoryFilter = 'build'; handleFilterChange()"
          >
            构建任务
          </Button>
          <Button
            size="sm"
            :variant="categoryFilter === 'export' ? 'default' : 'ghost'"
            title="导出任务"
            @click="categoryFilter = 'export'; handleFilterChange()"
          >
            导出任务
          </Button>
          <Button
            size="sm"
            :variant="categoryFilter === 'deploy' ? 'default' : 'ghost'"
            title="部署任务"
            @click="categoryFilter = 'deploy'; handleFilterChange()"
          >
            部署任务
          </Button>
        </div>

        <Button variant="outline" size="sm" @click="loadTasks">
          <i class="fas fa-sync-alt"></i>
          刷新
        </Button>
        <Button
          variant="outline"
          size="sm"
          :disabled="savingSystemSettings"
          title="修改全局最大并发任务数"
          @click="openConcurrentModal"
        >
          <i class="fas fa-sliders-h"></i>
          并发设置
        </Button>

        <div class="relative" ref="cleanupDropdownWrap">
          <Button
            variant="outline"
            size="sm"
            class="text-red-600 hover:text-red-700"
            :disabled="cleaning"
            :aria-expanded="cleanupMenuOpen ? 'true' : 'false'"
            @click.stop="toggleCleanupMenu"
          >
            <i class="fas fa-broom"></i>
            清理任务
            <i v-if="cleaning" class="fas fa-spinner fa-spin"></i>
            <i v-else class="fas fa-chevron-down text-xs opacity-70"></i>
          </Button>
          <ul
            ref="cleanupDropdownMenu"
            v-show="cleanupMenuOpen"
            class="absolute right-0 z-50 mt-1 min-w-[15rem] overflow-y-auto rounded-md border border-slate-200 bg-white py-1 shadow-lg"
            :style="cleanupMenuStyle"
            @click.stop
          >
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 hover:bg-slate-50"
                @click="cleanupAll"
              >
                <i class="fas fa-trash-alt w-4"></i>
                清理全部（非运行中）
              </button>
            </li>
            <li class="my-1 border-t border-slate-100"></li>
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                @click="cleanupByStatus('completed')"
              >
                <i class="fas fa-check-circle w-4"></i>
                清理已完成的任务
              </button>
            </li>
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                @click="cleanupByStatus('failed')"
              >
                <i class="fas fa-times-circle w-4"></i>
                清理失败的任务
              </button>
            </li>
            <li class="my-1 border-t border-slate-100"></li>
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                @click="cleanupByDays(7)"
              >
                <i class="fas fa-calendar-alt w-4"></i>
                清理7天前的任务（默认）
              </button>
            </li>
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                @click="cleanupByDaysPrompt"
              >
                <i class="fas fa-calendar-alt w-4"></i>
                清理N天前的任务…
              </button>
            </li>
            <li class="my-1 border-t border-slate-100"></li>
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                @click="cleanupOrphanDirs"
              >
                <i class="fas fa-exclamation-triangle w-4"></i>
                清理异常目录
              </button>
            </li>
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                :class="{ 'text-slate-400': buildDirCount === 0 }"
                @click="cleanupBuildDir"
              >
                <i class="fas fa-folder-open w-4"></i>
                清理编译目录（全部）
                <span v-if="buildDirCount > 0" class="ml-auto text-xs text-slate-400"
                  >({{ buildDirSize }})</span
                >
              </button>
            </li>
            <li class="my-1 border-t border-slate-100"></li>
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                :class="{ 'text-slate-400': exportDirCount === 0 }"
                @click="cleanupExportDir"
              >
                <i class="fas fa-download w-4"></i>
                清理下载目录（全部）
                <span v-if="exportDirCount > 0" class="ml-auto text-xs text-slate-400"
                  >({{ exportDirSize }})</span
                >
              </button>
            </li>
            <li>
              <button
                type="button"
                class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50"
                :class="{ 'text-slate-400': exportDirCount === 0 }"
                @click="cleanupExportDirDays"
              >
                <i class="fas fa-calendar-times w-4"></i>
                清理N天前的下载文件
              </button>
            </li>
          </ul>
        </div>
      </template>
    </PageToolbar>

    <div v-if="loading" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <i class="fas fa-spinner fa-spin"></i>
      加载中…
    </div>

    <div
      v-else-if="filtering"
      class="flex items-center justify-center gap-2 py-6 text-sm text-slate-500"
    >
      <i class="fas fa-spinner fa-spin"></i>
      筛选中…
    </div>

    <EmptyState v-else-if="paginatedTasks.length === 0" message="暂无任务" />

    <template v-else>
    <div class="space-y-3 md:hidden">
      <div
        v-for="task in paginatedTasks"
        :key="task.task_id"
        class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
      >
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="flex flex-wrap gap-1">
            <Badge v-if="task.task_category === 'build'" variant="info">
              <i class="fas fa-hammer mr-1"></i> 构建
            </Badge>
            <Badge v-else-if="task.task_category === 'deploy'" variant="success">
              <i class="fas fa-rocket mr-1"></i> 部署
            </Badge>
            <Badge v-else variant="default">
              <i class="fas fa-download mr-1"></i> 导出
            </Badge>
            <Badge v-if="task.status === 'pending'" variant="default">等待中</Badge>
            <Badge v-else-if="task.status === 'running'" variant="default">进行中</Badge>
            <Badge v-else-if="task.status === 'stopped'" variant="warning">已停止</Badge>
            <Badge v-else-if="task.status === 'completed'" variant="success">已完成</Badge>
            <Badge v-else-if="task.status === 'failed'" variant="danger">失败</Badge>
          </div>
          <span class="text-xs text-slate-500">{{ formatTime(task.created_at) }}</span>
        </div>
        <p class="mt-2 truncate text-sm font-medium text-slate-900">
          <template v-if="task.source === '流水线' && task.pipeline_name">
            {{ task.pipeline_name }}
          </template>
          <template v-else>
            {{ task.image || task.task_type || "未知" }}
            <span v-if="task.tag" class="text-slate-500">:{{ task.tag }}</span>
          </template>
        </p>
        <p v-if="task.branch" class="mt-1 text-xs text-slate-500">
          <i class="fas fa-code-branch mr-1"></i>{{ task.branch }}
        </p>
        <div class="mt-3 flex flex-wrap gap-1 border-t border-slate-200 pt-3">
          <Button
            v-if="task.task_category === 'build' || task.task_category === 'deploy'"
            variant="outline"
            size="sm"
            title="查看日志"
            @click="buildTaskLogs.viewLogs(task)"
          >
            <i class="fas fa-terminal"></i>
          </Button>
          <Button
            v-if="task.task_category === 'export' && task.status === 'completed'"
            size="sm"
            title="下载"
            :disabled="downloading === task.task_id"
            @click="downloadTask(task)"
          >
            <i class="fas fa-download"></i>
          </Button>
          <Button
            size="sm"
            :variant="task.status === 'running' || task.status === 'pending' ? 'outline' : 'destructive'"
            :title="task.status === 'running' || task.status === 'pending' ? '停止' : '删除'"
            @click="task.status === 'running' || task.status === 'pending' ? stopTask(task) : deleteTask(task)"
          >
            <i :class="task.status === 'running' || task.status === 'pending' ? 'fas fa-stop' : 'fas fa-trash'"></i>
          </Button>
        </div>
      </div>
    </div>

    <div class="hidden md:block">
    <Table min-width-class="min-w-[72rem]">
      <TableHeader>
        <TableRow>
          <TableHead class="w-[100px]">类型</TableHead>
          <TableHead class="w-[180px]">镜像/任务</TableHead>
          <TableHead class="w-[120px]">分支/Tag</TableHead>
          <TableHead class="hidden w-[90px] xl:table-cell">来源</TableHead>
          <TableHead class="w-[100px]">状态</TableHead>
          <TableHead class="w-[140px]">创建时间</TableHead>
          <TableHead class="hidden w-[90px] lg:table-cell">时长</TableHead>
          <TableHead class="w-[90px]">文件大小</TableHead>
          <TableHead class="min-w-[200px] text-end">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="task in paginatedTasks" :key="task.task_id">
          <TableCell>
            <Badge v-if="task.task_category === 'build'" variant="info">
              <i class="fas fa-hammer mr-1"></i> 构建
            </Badge>
            <Badge v-else-if="task.task_category === 'deploy'" variant="success">
              <i class="fas fa-rocket mr-1"></i> 部署
            </Badge>
            <Badge v-else variant="default">
              <i class="fas fa-download mr-1"></i> 导出
            </Badge>
          </TableCell>
          <TableCell>
            <div>
              <div class="flex items-center gap-2">
                <div class="flex min-w-0 flex-col">
                  <span
                    v-if="task.source === '流水线' && task.pipeline_name"
                    class="truncate"
                  >
                    <i class="fas fa-project-diagram mr-1 text-blue-600"></i>
                    <strong>{{ task.pipeline_name }}</strong>
                  </span>
                  <code v-else class="mb-0 rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                    {{ task.image || (task.task_type ? task.task_type : "未知") }}
                  </code>
                </div>
                <Badge
                  v-if="task.selected_services && task.selected_services.length > 0"
                  variant="info"
                  class="shrink-0 text-[0.7rem] font-semibold"
                  :title="`多服务构建: ${task.selected_services.join(', ')}`"
                >
                  <i class="fas fa-layer-group mr-1"></i>
                  {{ task.selected_services.length }} 服务
                </Badge>
                <Badge
                  v-else-if="task.push_mode === 'multi' && task.task_category === 'build'"
                  variant="default"
                  class="shrink-0 text-[0.7rem] font-semibold"
                >
                  <i class="fas fa-cube mr-1"></i> 单服务
                </Badge>
              </div>
              <div
                v-if="task.task_category === 'deploy' && task.task_config?.targets"
                class="mt-1"
              >
                <Badge variant="success" class="text-[0.7rem]">
                  <i class="fas fa-server mr-1"></i>
                  {{ task.task_config.targets.length }} 个目标
                </Badge>
              </div>
              <div
                v-else-if="task.selected_services && task.selected_services.length > 0"
                class="mt-1"
              >
                <div class="flex flex-wrap gap-1">
                  <Badge
                    v-for="service in task.selected_services.slice(0, 8)"
                    :key="service"
                    variant="default"
                    class="text-[0.65rem]"
                  >
                    {{ service }}
                  </Badge>
                  <Badge
                    v-if="task.selected_services.length > 8"
                    variant="default"
                    class="text-[0.65rem]"
                    :title="task.selected_services.slice(8).join(', ')"
                  >
                    +{{ task.selected_services.length - 8 }}
                  </Badge>
                </div>
              </div>
            </div>
          </TableCell>
          <TableCell>
            <div>
              <div v-if="task.branch" class="mb-1">
                <Badge variant="default" class="text-[0.75rem]">
                  <i class="fas fa-code-branch mr-1"></i> {{ task.branch }}
                </Badge>
              </div>
              <div v-if="task.tag">
                <Badge variant="info" class="text-[0.75rem]">
                  <i class="fas fa-tag mr-1"></i> {{ task.tag }}
                </Badge>
              </div>
              <span v-if="!task.branch && !task.tag" class="text-sm text-slate-400">-</span>
            </div>
          </TableCell>
          <TableCell class="hidden xl:table-cell">
            <Badge
              v-if="task.task_category === 'deploy' && (task.trigger_source === 'webhook' || task.source === 'Webhook')"
              variant="success"
            >
              <i class="fas fa-link mr-1"></i> Webhook
            </Badge>
            <Badge v-else-if="task.task_category === 'deploy'" variant="success">
              <i class="fas fa-hand-pointer mr-1"></i> 手动
            </Badge>
            <Badge v-else-if="task.source === '流水线'" variant="default">
              <i class="fas fa-project-diagram mr-1"></i> 流水线
            </Badge>
            <Badge v-else-if="task.source === 'Git源码'" variant="info">
              <i class="fas fa-code-branch mr-1"></i> Git源码
            </Badge>
            <Badge v-else-if="task.source === '文件上传'" variant="success">
              <i class="fas fa-upload mr-1"></i> 文件上传
            </Badge>
            <Badge
              v-else-if="task.source === '镜像构建' || task.source === '分步构建'"
              variant="warning"
            >
              <i class="fas fa-list-ol mr-1"></i> 镜像构建
            </Badge>
            <Badge v-else-if="task.source === '手动部署'" variant="success">
              <i class="fas fa-rocket mr-1"></i> 手动部署
            </Badge>
            <Badge v-else-if="task.source === 'Webhook'" variant="success">
              <i class="fas fa-link mr-1"></i> Webhook
            </Badge>
            <Badge v-else-if="task.source === '手动'" variant="success">
              <i class="fas fa-rocket mr-1"></i> 手动
            </Badge>
            <Badge v-else variant="default">
              <i class="fas fa-hammer mr-1"></i> {{ task.source || "手动构建" }}
            </Badge>
          </TableCell>
          <TableCell>
            <div class="flex flex-col gap-1">
              <Badge v-if="task.status === 'pending'" variant="default">
                <i class="fas fa-clock mr-1"></i> 等待中
              </Badge>
              <Badge v-else-if="task.status === 'running'" variant="default">
                <i class="fas fa-spinner fa-spin mr-1"></i>
                进行中
              </Badge>
              <Badge v-else-if="task.status === 'stopped'" variant="warning">
                <i class="fas fa-stop-circle mr-1"></i> 已停止
              </Badge>
              <Badge v-else-if="task.status === 'completed'" variant="success">
                <i class="fas fa-check-circle mr-1"></i> 已完成
              </Badge>
              <Badge v-else-if="task.status === 'failed'" variant="danger">
                <i class="fas fa-times-circle mr-1"></i> 失败
              </Badge>
              <small
                v-if="task.selected_services && task.selected_services.length > 0 && task.status === 'running'"
                class="text-[0.7rem] text-slate-500"
              >
                <i class="fas fa-cog fa-spin mr-1"></i> 构建中...
              </small>
              <small
                v-else-if="task.selected_services && task.selected_services.length > 0 && task.status === 'completed'"
                class="text-[0.7rem] text-green-600"
              >
                <i class="fas fa-check mr-1"></i>
                {{ task.selected_services.length }} 个服务已完成
              </small>
            </div>
          </TableCell>
          <TableCell class="text-sm text-slate-500">{{ formatTime(task.created_at) }}</TableCell>
          <TableCell class="hidden text-sm lg:table-cell">
            <span v-if="task.status === 'running'" class="text-blue-600">
              <i class="fas fa-spinner fa-spin mr-1 text-xs"></i>
              {{ calculateDuration(task.started_at || task.created_at, null) }}
            </span>
            <span
              v-else-if="task.completed_at"
              :class="{
                'text-green-600': task.status === 'completed',
                'text-red-600': task.status === 'failed',
              }"
            >
              {{ calculateDuration(task.started_at || task.created_at, task.completed_at) }}
            </span>
            <span v-else class="text-slate-400">-</span>
          </TableCell>
          <TableCell class="text-sm">
            <span v-if="task.file_size">{{ formatFileSize(task.file_size) }}</span>
            <span v-else>-</span>
          </TableCell>
          <TableCell class="text-end">
            <div class="flex flex-wrap justify-end gap-1">
              <template v-if="task.task_category === 'build'">
                <Button
                  variant="outline"
                  size="sm"
                  title="查看构建日志"
                  :disabled="buildTaskLogs.isViewingLog(task.task_id)"
                  @click="buildTaskLogs.viewLogs(task)"
                >
                  <i class="fas fa-terminal"></i>
                </Button>
                <Button
                  v-if="task.source !== '流水线' && !task.pipeline_id"
                  variant="outline"
                  size="sm"
                  title="另存为流水线"
                  @click="saveAsPipeline(task)"
                >
                  <i class="fas fa-save"></i>
                </Button>
                <Button
                  v-if="task.status === 'completed' || task.status === 'failed' || task.status === 'stopped'"
                  variant="outline"
                  size="sm"
                  title="重新构建"
                  :disabled="rebuilding === task.task_id"
                  @click="rebuildTask(task)"
                >
                  <i class="fas fa-redo"></i>
                  <i v-if="rebuilding === task.task_id" class="fas fa-spinner fa-spin"></i>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  title="查看配置JSON"
                  @click="viewTaskConfig(task)"
                >
                  <i class="fas fa-code"></i>
                </Button>
              </template>

              <template v-if="task.task_category === 'deploy'">
                <Button
                  variant="outline"
                  size="sm"
                  title="查看部署日志"
                  :disabled="buildTaskLogs.isViewingLog(task.task_id)"
                  @click="buildTaskLogs.viewLogs(task)"
                >
                  <i class="fas fa-terminal"></i>
                </Button>
                <Button
                  v-if="task.status === 'failed' || task.status === 'stopped' || task.status === 'completed'"
                  variant="outline"
                  size="sm"
                  title="重试部署"
                  :disabled="retryingDeploy === task.task_id"
                  @click="retryDeployTask(task)"
                >
                  <i class="fas fa-redo"></i>
                  <i v-if="retryingDeploy === task.task_id" class="fas fa-spinner fa-spin"></i>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  title="查看部署配置"
                  @click="viewDeployConfig(task)"
                >
                  <i class="fas fa-code"></i>
                </Button>
              </template>

              <template v-if="task.task_category === 'export'">
                <Button
                  v-if="task.status === 'completed'"
                  size="sm"
                  title="下载导出文件"
                  :disabled="downloading === task.task_id"
                  @click="downloadTask(task)"
                >
                  <i class="fas fa-download"></i>
                  <i v-if="downloading === task.task_id" class="fas fa-spinner fa-spin"></i>
                </Button>
                <Button
                  v-if="task.status === 'failed' || task.status === 'stopped'"
                  variant="outline"
                  size="sm"
                  title="重试导出"
                  :disabled="retrying === task.task_id"
                  @click="retryExportTask(task)"
                >
                  <i class="fas fa-redo"></i>
                  <i v-if="retrying === task.task_id" class="fas fa-spinner fa-spin"></i>
                </Button>
              </template>

              <Button
                size="sm"
                :variant="task.status === 'running' || task.status === 'pending' ? 'outline' : 'destructive'"
                :title="task.status === 'running' || task.status === 'pending' ? '停止任务' : '删除任务'"
                :disabled="task.status === 'running' || task.status === 'pending' ? stopping === task.task_id : deleting === task.task_id"
                @click="task.status === 'running' || task.status === 'pending' ? stopTask(task) : deleteTask(task)"
              >
                <i
                  :class="task.status === 'running' || task.status === 'pending' ? 'fas fa-stop' : 'fas fa-trash'"
                ></i>
                <i
                  v-if="(task.status === 'running' || task.status === 'pending') && stopping === task.task_id"
                  class="fas fa-spinner fa-spin"
                ></i>
                <i
                  v-if="task.status !== 'running' && task.status !== 'pending' && deleting === task.task_id"
                  class="fas fa-spinner fa-spin"
                ></i>
              </Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
    </div>
    </template>

    <PaginationBar
      v-if="!loading && !filtering && totalTasks > 0"
      :page="currentPage"
      :page-size="pageSize"
      :total="totalTasks"
      :total-pages="totalPages"
      @update:page="changePage"
    />

    <AlertBanner :message="error || ''" />

    <BuildTaskLogModal
      :controller="buildTaskLogs"
      @task-status-updated="onTaskStatusUpdated"
    />

    <FormDialog
      v-model="showConfigModal"
      title="任务配置JSON"
      icon="fa-code"
      size="lg"
    >
      <div class="mb-3 flex justify-end">
        <Button variant="outline" size="sm" @click="copyTaskConfigJson">
          <i class="fas fa-copy"></i>
          复制JSON
        </Button>
      </div>
      <codemirror
        v-model="taskConfigJsonText"
        :style="{ height: 'min(500px, 60vh)', fontSize: '13px' }"
        :disabled="true"
        :extensions="jsonEditorExtensions"
      />
      <template #footer>
        <Button variant="outline" type="button" @click="showConfigModal = false">关闭</Button>
      </template>
    </FormDialog>

    <FormDialog
      v-model="showSaveAsPipelineModal"
      title="另存为流水线"
      icon="fa-save"
      size="lg"
    >
      <div class="space-y-4">
        <div class="space-y-2">
          <Label>流水线名称 <span class="text-red-500">*</span></Label>
          <Input v-model="pipelineForm.name" placeholder="请输入流水线名称" required />
        </div>
        <div class="space-y-2">
          <Label>描述</Label>
          <textarea
            v-model="pipelineForm.description"
            rows="2"
            class="flex min-h-[80px] w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            placeholder="请输入描述（可选）"
          ></textarea>
        </div>
        <AlertBanner
          variant="info"
          message="流水线将使用任务的完整配置，包括Git地址、分支、镜像名称、构建参数等。"
        />
      </div>
      <template #footer>
        <Button variant="outline" type="button" @click="showSaveAsPipelineModal = false"
          >取消</Button
        >
        <Button type="button" :disabled="saving" @click="savePipelineFromTask">
          <i v-if="saving" class="fas fa-spinner fa-spin"></i>
          {{ saving ? "保存中..." : "保存" }}
        </Button>
      </template>
    </FormDialog>

    <FormDialog v-model="showConcurrentModal" title="并发设置" icon="fa-sliders-h" size="sm">
      <div class="space-y-2">
        <Label>全局最大并发任务数</Label>
        <Input
          v-model="concurrentInput"
          type="number"
          min="1"
          step="1"
          :disabled="savingSystemSettings"
          @keydown.enter="submitConcurrentSetting"
        />
        <p class="text-xs text-slate-500">当前值：{{ maxConcurrentTasks }}</p>
      </div>
      <template #footer>
        <Button
          variant="outline"
          type="button"
          :disabled="savingSystemSettings"
          @click="closeConcurrentModal"
          >取消</Button
        >
        <Button type="button" :disabled="savingSystemSettings" @click="submitConcurrentSetting">
          <i v-if="savingSystemSettings" class="fas fa-spinner fa-spin"></i>
          保存
        </Button>
      </template>
    </FormDialog>
  </div>

</template>

<script setup>
import { StreamLanguage } from "@codemirror/language";
import { javascript } from "@codemirror/legacy-modes/mode/javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import axios from "axios";
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { copyToClipboard } from "../utils/clipboard.js";
import { Codemirror } from "vue-codemirror";
import BuildTaskLogModal from "@/components/BuildTaskLogModal.vue";
import { useBuildTaskLogs } from "@/composables/useBuildTaskLogs";
import { registerTask } from "@/composables/useTaskCompletionWatcher";
import { useTeamStore } from "@/stores/team";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import StatCard from "@/components/ui/StatCard.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const tasks = ref([]);
const loading = ref(false);
const filtering = ref(false); // 筛选中的状态（轻量级loading）
const error = ref(null);
const statusFilter = ref("");
const categoryFilter = ref("");
const deployConfigFilterId = ref(null);
let filterDebounceTimer = null; // 防抖定时器
const downloading = ref(null);
const deleting = ref(null);
const rebuilding = ref(null); // 重建中的任务ID
const retrying = ref(null); // 重试中的任务ID
const retryingDeploy = ref(null); // 重试部署中的任务ID
const stopping = ref(null); // 停止中的任务ID
const teamStore = useTeamStore();
const buildTaskLogs = useBuildTaskLogs();
// 错误弹窗已移除，错误信息现在显示在日志顶部
const currentPage = ref(1); // 当前页码
const pageSize = ref(10); // 每页显示数量（默认10）
const totalTasks = ref(0); // 总任务数（从后台获取）
const totalPages = ref(0); // 总页数（从后台获取）
const cleaning = ref(false); // 清理中状态
const buildDirSize = ref("0 MB"); // 编译目录容量
const buildDirCount = ref(0); // 编译目录数量
const exportDirSize = ref("0 MB"); // 下载目录容量
const exportDirCount = ref(0); // 下载目录文件数量
const saving = ref(false); // 保存中状态
const showConfigModal = ref(false); // 任务配置JSON模态框
const taskConfigJson = ref(""); // 任务配置JSON
const taskConfigJsonText = ref(""); // JSON文本内容（用于CodeMirror）
const maxConcurrentTasks = ref(15);
const queueRunningCount = ref(0);
const queuePendingCount = ref(0);
const savingSystemSettings = ref(false);
const showConcurrentModal = ref(false);
const concurrentInput = ref("");

// CodeMirror 扩展配置（JSON模式，使用JavaScript模式）
const jsonEditorExtensions = [StreamLanguage.define(javascript), oneDark];

const showSaveAsPipelineModal = ref(false); // 另存为流水线模态框
const cleanupDropdownWrap = ref(null);
const cleanupDropdownMenu = ref(null);
const cleanupMenuOpen = ref(false);
const cleanupMenuStyle = ref({});
const pipelineForm = ref({
  name: "",
  description: "",
  git_url: "",
  branch: "",
  image_name: "",
  tag: "",
  project_type: "",
  template: "",
  template_params: {},
  sub_path: "",
  use_project_dockerfile: true,
  dockerfile_name: "Dockerfile",
  source_id: null,
  push: false,
  selected_services: null,
  service_push_config: null,
  service_template_params: null,
  push_mode: "multi",
  resource_package_configs: null,
  trigger_webhook: true,
  trigger_schedule: false,
  cron_expression: "",
  webhook_branch_filter: false,
  webhook_use_push_branch: true,
  branch_tag_mapping: null,
  enabled: true,
});
let refreshInterval = null;

function toggleCleanupMenu() {
  if (cleaning.value) return;
  cleanupMenuOpen.value = !cleanupMenuOpen.value;
  if (cleanupMenuOpen.value) {
    nextTick(() => {
      adjustCleanupMenuPosition();
    });
  }
}

function closeCleanupMenu() {
  cleanupMenuOpen.value = false;
}

function handleCleanupOutsideClick(event) {
  const wrap = cleanupDropdownWrap.value;
  if (!wrap) return;
  if (!wrap.contains(event.target)) {
    closeCleanupMenu();
  }
}

function adjustCleanupMenuPosition() {
  const menu = cleanupDropdownMenu.value;
  if (!menu) return;

  const gap = 8;
  const rect = menu.getBoundingClientRect();
  const style = {
    maxHeight: "60vh",
    overflowY: "auto",
  };

  // 默认右对齐向下展开，超边界时自动纠正
  if (rect.right > window.innerWidth - gap) {
    style.right = "0";
    style.left = "auto";
  }
  if (rect.left < gap) {
    style.left = "0";
    style.right = "auto";
  }

  if (rect.bottom > window.innerHeight - gap) {
    style.top = "auto";
    style.bottom = "100%";
    style.marginBottom = "0.25rem";
    style.marginTop = "0";
  } else {
    style.top = "100%";
    style.bottom = "auto";
    style.marginTop = "0.25rem";
    style.marginBottom = "0";
  }

  cleanupMenuStyle.value = style;
}

// 启动定时刷新（只在有运行中任务时启动）
function startRefreshInterval() {
  // 先清除现有定时器
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }

  // 检查是否有运行中的任务
  const hasRunningTasks = tasks.value.some(
    (t) => t.status === "running" || t.status === "pending"
  );

  if (hasRunningTasks) {
    // 每3秒自动刷新一次（只更新运行中任务的状态，不刷新整个页面）
    refreshInterval = setInterval(() => {
      refreshRunningTasks();
    }, 3000);
  }
}

// 当前页的任务列表（后台已分页，直接使用）
const paginatedTasks = computed(() => {
  return tasks.value;
});

// 任务统计信息（基于当前页的任务）
const taskStats = computed(() => {
  const stats = {
    total: totalTasks.value, // 使用后台返回的总数
    pending: 0,
    running: 0,
    completed: 0,
    failed: 0,
    stopped: 0,
    build: 0,
    export: 0,
    deploy: 0,
    successRate: 0,
  };

  // 只统计当前页的任务（用于显示当前页的分布情况）
  tasks.value.forEach((task) => {
    // 统计状态
    const status = task.status || "pending";
    if (stats.hasOwnProperty(status)) {
      stats[status]++;
    }

    // 统计类型
    const category = task.task_category || "build";
    if (category === "build") stats.build++;
    else if (category === "export") stats.export++;
    else if (category === "deploy") stats.deploy++;
  });

  // 计算成功率（已完成任务 / 已完成+失败+停止的任务）
  const finishedTasks = stats.completed + stats.failed + stats.stopped;
  if (finishedTasks > 0) {
    stats.successRate = Math.round((stats.completed / finishedTasks) * 100);
  } else if (stats.total === 0) {
    stats.successRate = 0;
  } else {
    // 如果没有已完成的任务，显示0%
    stats.successRate = 0;
  }

  return stats;
});

// 可见的页码列表
const visiblePages = computed(() => {
  const total = totalPages.value || 0;
  const current = currentPage.value;
  const pages = [];

  if (total <= 7) {
    // 总页数小于7，显示所有页码
    for (let i = 1; i <= total; i++) {
      pages.push(i);
    }
  } else {
    // 总页数大于7，智能显示
    if (current <= 4) {
      // 前部：1 2 3 4 5 ... 最后页
      for (let i = 1; i <= 5; i++) pages.push(i);
      pages.push("...");
      pages.push(total);
    } else if (current >= total - 3) {
      // 后部：1 ... 倍数第5页 倍数第4页 倍数第3页 倍数第2页 最后页
      pages.push(1);
      pages.push("...");
      for (let i = total - 4; i <= total; i++) pages.push(i);
    } else {
      // 中间：1 ... current-1 current current+1 ... 最后页
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

// 切换页码
function changePage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  currentPage.value = page;
  // 切换页码时重新加载数据
  loadTasks(false);
}

// 重置到第1页（切换过滤条件时）
function resetPage() {
  if (currentPage.value !== 1) {
    currentPage.value = 1;
  }
}

// handleLogsOrError 函数已移除，统一使用 viewLogs 函数
// 错误弹窗相关函数已移除，错误信息现在显示在日志顶部

function formatTime(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString);

  // 显示完整精确时间（包括年月日时分秒）
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatFileSize(bytes) {
  if (!bytes) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

function calculateDuration(startTime, endTime) {
  if (!startTime) return "-";

  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();

  const diffMs = end - start;
  if (diffMs < 0) return "-";

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}小时${minutes % 60}分`;
  } else if (minutes > 0) {
    return `${minutes}分${seconds % 60}秒`;
  } else {
    return `${seconds}秒`;
  }
}

// 加载编译目录统计信息
async function loadBuildDirStats() {
  try {
    const res = await axios.get("/api/docker-build/stats");
    if (res.data.success) {
      buildDirSize.value =
        res.data.total_size_mb > 0 ? `${res.data.total_size_mb} MB` : "0 MB";
      buildDirCount.value = res.data.dir_count || 0;
    }
  } catch (err) {
    console.error("获取编译目录统计失败:", err);
    buildDirSize.value = "0 MB";
    buildDirCount.value = 0;
  }
}

// 加载下载目录统计信息
async function loadExportDirStats() {
  try {
    const res = await axios.get("/api/exports/stats");
    if (res.data.success) {
      exportDirSize.value =
        res.data.total_size_mb > 0 ? `${res.data.total_size_mb} MB` : "0 MB";
      exportDirCount.value = res.data.file_count || 0;
    }
  } catch (err) {
    console.error("获取下载目录统计失败:", err);
    exportDirSize.value = "0 MB";
    exportDirCount.value = 0;
  }
}

async function loadTasks(includeStats = true) {
  loading.value = true;
  error.value = null;

  try {
    // 构建请求参数，在后端进行筛选和分页
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    };
    const teamId = teamStore.activeTeamIdForApi;
    if (teamId) params.team_id = teamId;
    if (statusFilter.value) params.status = statusFilter.value;
    if (categoryFilter.value) params.task_type = categoryFilter.value;
    if (deployConfigFilterId.value) params.deploy_config_id = deployConfigFilterId.value;

    // 根据是否需要统计信息决定是否并行加载
    if (includeStats) {
      // 同时加载编译目录和下载目录统计
      await Promise.all([
        loadBuildDirStats(),
        loadExportDirStats(),
        loadSystemQueueSettings(),
      ]);
    }

    const res = await axios.get("/api/tasks", { params });
    tasks.value = res.data.tasks || [];
    totalTasks.value = res.data.total || 0;
    totalPages.value = res.data.total_pages || 0;

    // 加载任务后，检查是否需要启动定时刷新
    startRefreshInterval();
  } catch (err) {
    error.value =
      err.response?.data?.error || err.message || "加载任务列表失败";
    console.error("加载任务列表失败:", err);
    tasks.value = [];
    totalTasks.value = 0;
    totalPages.value = 0;
  } finally {
    loading.value = false;
    filtering.value = false;
  }
}

async function loadSystemQueueSettings() {
  try {
    const res = await axios.get("/api/system-settings");
    maxConcurrentTasks.value = res.data.max_concurrent_tasks || 15;
    queueRunningCount.value = res.data.running_count || 0;
    queuePendingCount.value = res.data.pending_count || 0;
  } catch (err) {
    console.error("获取系统并发设置失败:", err);
  }
}

function openConcurrentModal() {
  concurrentInput.value = String(maxConcurrentTasks.value || 15);
  showConcurrentModal.value = true;
}

function closeConcurrentModal() {
  if (savingSystemSettings.value) return;
  showConcurrentModal.value = false;
}

async function submitConcurrentSetting() {
  if (savingSystemSettings.value) return;
  const value = Number(concurrentInput.value);
  if (!Number.isInteger(value) || value < 1) {
    alert("请输入大于等于 1 的整数");
    return;
  }
  savingSystemSettings.value = true;
  try {
    await axios.put("/api/system-settings", { max_concurrent_tasks: value });
    await loadSystemQueueSettings();
    await loadTasks(false);
    showConcurrentModal.value = false;
  } catch (err) {
    const errorMsg =
      err.response?.data?.detail || err.message || "更新系统设置失败";
    alert(errorMsg);
  } finally {
    savingSystemSettings.value = false;
  }
}

// 筛选条件改变时的处理函数（使用防抖优化）
function handleFilterChange() {
  resetPage();

  // 清除之前的定时器
  if (filterDebounceTimer) {
    clearTimeout(filterDebounceTimer);
  }

  // 显示轻量级筛选状态
  filtering.value = true;

  // 防抖：300ms后执行，避免频繁请求
  filterDebounceTimer = setTimeout(() => {
    // 筛选时不需要重新加载统计信息，提升速度
    loadTasks(false);
  }, 300);
}

const terminalFetchInFlight = new Set();

async function fetchTaskTerminalStatus(taskId, index) {
  if (terminalFetchInFlight.has(taskId)) return;
  terminalFetchInFlight.add(taskId);
  try {
    const res = await axios.get(`/api/build-tasks/${taskId}`);
    const data = res.data;
    if (index >= 0 && index < tasks.value.length && tasks.value[index].task_id === taskId) {
      tasks.value[index].status = data.status ?? tasks.value[index].status;
      if (data.completed_at !== undefined) {
        tasks.value[index].completed_at = data.completed_at;
      }
      if (data.error !== undefined) {
        tasks.value[index].error = data.error;
      }
      if (data.file_size !== undefined) {
        tasks.value[index].file_size = data.file_size;
      }
      if (data.started_at !== undefined) {
        tasks.value[index].started_at = data.started_at;
      }
    }
  } catch (err) {
    if (err.response?.status !== 404) {
      console.error("刷新任务终态失败:", taskId, err);
    }
  } finally {
    terminalFetchInFlight.delete(taskId);
  }
}

// 只刷新运行中任务的状态（不刷新整个页面）
async function refreshRunningTasks() {
  try {
    const res = await axios.get("/api/tasks/running");
    const runningTasks = res.data.tasks || [];
    const runningTasksMap = new Map();
    runningTasks.forEach((task) => {
      runningTasksMap.set(task.task_id, task);
    });

    tasks.value.forEach((task, index) => {
      const taskId = task.task_id;
      const updatedTask = runningTasksMap.get(taskId);

      if (updatedTask) {
        tasks.value[index].status = updatedTask.status;
        if (updatedTask.completed_at !== undefined) {
          tasks.value[index].completed_at = updatedTask.completed_at;
        }
        if (updatedTask.error !== undefined) {
          tasks.value[index].error = updatedTask.error;
        }
        if (updatedTask.file_size !== undefined) {
          tasks.value[index].file_size = updatedTask.file_size;
        }
        if (updatedTask.started_at !== undefined) {
          tasks.value[index].started_at = updatedTask.started_at;
        }
      } else if (task.status === "running" || task.status === "pending") {
        fetchTaskTerminalStatus(taskId, index);
      }
    });

    const stillRunning = tasks.value.some(
      (t) => t.status === "running" || t.status === "pending"
    );
    if (!stillRunning && refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  } catch (err) {
    console.error("刷新运行中任务状态失败:", err);
  }
}

// 任务状态更新处理（不刷新整个页面，只更新当前任务状态）
function onTaskStatusUpdated(newStatus) {
  const task = buildTaskLogs.selectedTask.value;
  if (!task?.task_id) return;
  // 更新任务列表中的对应任务状态，不刷新整个列表
  const index = tasks.value.findIndex((t) => t.task_id === task.task_id);
  if (index !== -1) {
    tasks.value[index].status = newStatus;
  }
}

// 查看任务配置JSON
async function viewTaskConfig(task) {
  try {
    const res = await axios.get(`/api/build-tasks/${task.task_id}/config`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    });

    taskConfigJson.value = JSON.stringify(res.data, null, 2);
    taskConfigJsonText.value = taskConfigJson.value;
    showConfigModal.value = true;
  } catch (err) {
    console.error("获取任务配置失败:", err);
    const errorMsg =
      err.response?.data?.detail || err.message || "获取任务配置失败";
    alert(`获取任务配置失败: ${errorMsg}`);
  }
}

// 复制JSON到剪贴板（带降级方案）
async function copyTaskConfigJson() {
  const text = taskConfigJson.value;
  const success = await copyToClipboard(text);
  if (success) {
    alert("JSON配置已复制到剪贴板");
  } else {
    alert("自动复制失败，请手动选择并复制文本（已自动选中）");
    nextTick(() => {
      const editor = document.querySelector(".cm-editor");
      if (editor) {
        const range = document.createRange();
        range.selectNodeContents(editor);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
    });
  }
}

// 另存为流水线
async function saveAsPipeline(task) {
  try {
    // 获取任务配置
    const res = await axios.get(`/api/build-tasks/${task.task_id}/config`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    });

    const config = res.data;

    // 填充流水线表单
    pipelineForm.value = {
      name: `${task.image || "任务"}_${task.tag || "latest"}_${new Date()
        .toISOString()
        .slice(0, 10)}`,
      description: `从任务 ${task.task_id.slice(0, 8)} 创建${
        task.source === "流水线" ? "（流水线触发）" : ""
      }`,
      git_url: config.git_url || "",
      branch: config.branch || "",
      image_name: config.image_name || task.image || "",
      tag: config.tag || task.tag || "latest",
      project_type: config.project_type || "jar",
      template: config.template || "",
      template_params: config.template_params || {},
      sub_path: config.sub_path || "",
      use_project_dockerfile: config.use_project_dockerfile !== false,
      dockerfile_name: config.dockerfile_name || "Dockerfile",
      source_id: config.source_id || null,
      push: config.should_push || config.push || false,
      selected_services: config.selected_services || null,
      service_push_config: config.service_push_config || null,
      service_template_params: config.service_template_params || null,
      push_mode: config.push_mode || "multi",
      resource_package_configs:
        config.resource_package_configs || config.resource_package_ids || null,
      trigger_webhook: true,
      trigger_schedule: false,
      cron_expression: "",
      webhook_branch_filter: false,
      webhook_use_push_branch: true,
      branch_tag_mapping: null,
      enabled: true,
    };

    showSaveAsPipelineModal.value = true;
  } catch (err) {
    console.error("获取任务配置失败:", err);
    const errorMsg =
      err.response?.data?.detail || err.message || "获取任务配置失败";
    alert(`获取任务配置失败: ${errorMsg}`);
  }
}

async function downloadTask(task) {
  if (downloading.value) return;

  downloading.value = task.task_id;

  try {
    // 直接通过URL触发浏览器下载
    const downloadUrl = `/api/export-tasks/${task.task_id}/download`;

    // 生成文件名
    const image = task.image.replace(/\//g, "_");
    const tag = task.tag || "latest";
    const isCompressed =
      task.compress &&
      ["gzip", "gz", "tgz", "1", "true", "yes"].includes(
        task.compress.toLowerCase()
      );
    const ext = isCompressed ? ".tar.gz" : ".tar";
    const filename = `${image}-${tag}${ext}`;

    // 创建临时a标签，直接指向下载URL，让浏览器原生处理下载
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename; // 设置下载文件名
    a.style.display = "none";

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // 下载完成后清除loading状态（延迟一下确保下载已开始）
    setTimeout(() => {
      downloading.value = null;
    }, 500);
  } catch (err) {
    console.error("下载失败:", err);
    const errorMsg = err.message || "下载失败";
    error.value = `下载失败: ${errorMsg}`;
    // 3秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("下载失败")) {
        error.value = null;
      }
    }, 3000);
    downloading.value = null;
  }
}

async function stopTask(task) {
  if (stopping.value) return;

  // 确认对话框
  const taskName = task.image || task.task_type || "未知任务";
  const taskTag = task.tag || "latest";
  if (!confirm(`确定要停止任务 "${taskName}:${taskTag}" 吗？`)) {
    return;
  }

  stopping.value = task.task_id;
  error.value = null;

  try {
    if (task.task_category === "build") {
      await axios.post(`/api/build-tasks/${task.task_id}/stop`);
    } else if (task.task_category === "deploy") {
      // 部署任务使用构建任务管理器的stop接口（因为部署任务现在也在BuildTaskManager中）
      await axios.post(`/api/build-tasks/${task.task_id}/stop`);
    } else {
      await axios.post(`/api/export-tasks/${task.task_id}/stop`);
    }

    // 刷新任务列表
    await loadTasks();
  } catch (err) {
    console.error("停止任务失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      "停止失败";
    error.value = `停止任务失败: ${errorMsg}`;
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("停止任务失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    stopping.value = null;
  }
}

async function deleteTask(task) {
  const taskName = task.image || task.task_type || "未知任务";
  const taskTag = task.tag || "-";
  const status = task.status;

  // 检查任务状态
  if (status === "running" || status === "pending") {
    alert(
      `无法删除任务：只有停止、完成或失败的任务才能删除（当前状态: ${
        status === "running" ? "进行中" : "等待中"
      }）\n\n请先停止任务。`
    );
    return;
  }

  if (!confirm(`确定要删除任务 "${taskName}:${taskTag}" 吗？`)) {
    return;
  }

  deleting.value = task.task_id;
  try {
    if (task.task_category === "build") {
      await axios.delete(`/api/build-tasks/${task.task_id}`);
    } else if (task.task_category === "deploy") {
      await axios.delete(`/api/deploy-tasks/${task.task_id}`);
    } else {
      await axios.delete(`/api/export-tasks/${task.task_id}`);
    }
    // 成功删除后刷新列表
    await loadTasks();
  } catch (err) {
    console.error("删除任务失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      "删除失败";
    error.value = `删除任务失败: ${errorMsg}`;
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("删除任务失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    deleting.value = null;
  }
}

async function cleanupAll() {
  closeCleanupMenu();
  if (cleaning.value) return;

  if (
    !confirm(
      `确定要清理所有非运行中的任务吗？\n\n这将清理所有已完成、失败、已停止的任务，清理后的任务无法恢复，请谨慎操作！`
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    const res = await axios.post("/api/tasks/cleanup", {});

    alert(`成功清理 ${res.data.removed_count} 个任务`);
    await loadTasks();
  } catch (err) {
    console.error("清理全部任务失败:", err);
    alert(err.response?.data?.detail || "清理失败");
  } finally {
    cleaning.value = false;
  }
}

async function cleanupByStatus(status) {
  closeCleanupMenu();
  if (cleaning.value) return;

  const statusText = status === "completed" ? "已完成" : "失败";
  if (
    !confirm(
      `确定要清理所有${statusText}的任务吗？\n\n清理后的任务无法恢复，请谨慎操作！`
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    const res = await axios.post("/api/tasks/cleanup", {
      status: status,
    });

    alert(`成功清理 ${res.data.removed_count} 个任务`);
    await loadTasks();
  } catch (err) {
    console.error("清理任务失败:", err);
    alert(err.response?.data?.detail || "清理失败");
  } finally {
    cleaning.value = false;
  }
}

const DEFAULT_CLEANUP_DAYS = 7;

async function cleanupByDays(days) {
  closeCleanupMenu();
  if (cleaning.value) return;

  if (
    !confirm(
      `确定要清理 ${days} 天前的所有任务吗？\n\n清理后的任务无法恢复，请谨慎操作！`
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    const res = await axios.post("/api/tasks/cleanup", {
      days: days,
    });

    alert(`成功清理 ${res.data.removed_count} 个任务`);
    await loadTasks();
  } catch (err) {
    console.error("清理任务失败:", err);
    alert(err.response?.data?.detail || "清理失败");
  } finally {
    cleaning.value = false;
  }
}

async function cleanupByDaysPrompt() {
  closeCleanupMenu();
  if (cleaning.value) return;

  const daysInput = prompt(
    `请输入要清理的天数（默认 ${DEFAULT_CLEANUP_DAYS} 天）：`,
    String(DEFAULT_CLEANUP_DAYS)
  );
  if (!daysInput) {
    return;
  }

  const days = parseInt(daysInput, 10);
  if (isNaN(days) || days < 1) {
    alert("请输入有效的天数（必须大于0）");
    return;
  }

  await cleanupByDays(days);
}

async function cleanupOrphanDirs() {
  closeCleanupMenu();
  if (cleaning.value) return;

  if (
    !confirm(
      "确定要清理所有异常目录吗？\n\n此操作将删除所有没有对应任务的构建上下文目录，无法恢复，请谨慎操作！"
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    console.log("开始清理异常目录...");
    const res = await axios.post("/api/docker-build/cleanup", {
      cleanup_orphans_only: true,
    });

    console.log("清理异常目录响应:", res);
    console.log("响应数据:", res.data);

    // 检查响应数据
    if (res.data) {
      if (res.data.success === true) {
        const removedCount = res.data.removed_count || 0;
        const freedSpace = res.data.freed_space_mb || 0;
        let message =
          res.data.message ||
          `成功清理 ${removedCount} 个异常目录，释放空间 ${freedSpace} MB`;

        if (res.data.errors && res.data.errors.length > 0) {
          message += `\n\n部分目录清理失败: ${res.data.errors.length} 个`;
        }

        alert(message);

        // 刷新统计信息
        await Promise.all([loadBuildDirStats(), loadExportDirStats()]);
      } else {
        const errorMsg = res.data.message || res.data.detail || "清理失败";
        alert(typeof errorMsg === "string" ? errorMsg : String(errorMsg));
      }
    } else {
      console.warn("响应数据为空");
      alert("清理完成，但未收到响应数据");
      await Promise.all([loadBuildDirStats(), loadExportDirStats()]);
    }
  } catch (err) {
    console.error("清理异常目录失败:", err);
    let errorMsg = "清理失败";
    if (err.response) {
      if (err.response.data) {
        if (typeof err.response.data.detail === "string") {
          errorMsg = err.response.data.detail;
        } else if (typeof err.response.data.message === "string") {
          errorMsg = err.response.data.message;
        } else if (err.response.data.detail) {
          errorMsg = String(err.response.data.detail);
        } else {
          errorMsg = `清理失败: ${err.response.status} ${
            err.response.statusText || ""
          }`;
        }
      } else {
        errorMsg = `清理失败: ${err.response.status} ${
          err.response.statusText || ""
        }`;
      }
    } else if (err.message) {
      errorMsg = `清理失败: ${err.message}`;
    }

    alert(errorMsg);
  } finally {
    cleaning.value = false;
  }
}

async function cleanupBuildDir() {
  closeCleanupMenu();
  if (cleaning.value) return;

  if (
    !confirm(
      "确定要清空所有编译目录吗？\n\n此操作将删除所有构建上下文目录，无法恢复，请谨慎操作！"
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    console.log("开始清理编译目录...");
    const res = await axios.post("/api/docker-build/cleanup", {
      keep_days: 0,
    });

    console.log("清理目录响应:", res);
    console.log("响应数据:", res.data);

    // 检查响应数据
    if (res.data) {
      if (res.data.success === true) {
        // 成功情况
        const removedCount = res.data.removed_count || 0;
        const freedSpace = res.data.freed_space_mb || 0;
        let message =
          res.data.message ||
          `成功清空编译目录，删除了 ${removedCount} 个目录，释放空间 ${freedSpace} MB`;

        // 如果有错误信息，也显示出来
        if (res.data.errors && res.data.errors.length > 0) {
          message += `\n\n部分目录清理失败: ${res.data.errors.length} 个`;
        }

        alert(message);

        // 刷新统计信息
        await Promise.all([loadBuildDirStats(), loadExportDirStats()]);
      } else {
        // 失败情况
        const errorMsg = res.data.message || res.data.detail || "清理失败";
        alert(typeof errorMsg === "string" ? errorMsg : String(errorMsg));
      }
    } else {
      console.warn("响应数据为空");
      alert("清理完成，但未收到响应数据");
      // 仍然刷新统计信息
      await loadBuildDirStats();
    }
  } catch (err) {
    console.error("清理编译目录失败:", err);
    console.error("错误对象:", err);
    console.error("错误响应:", err.response);
    console.error("错误数据:", err.response?.data);

    let errorMsg = "清理失败";
    if (err.response) {
      if (err.response.data) {
        if (typeof err.response.data.detail === "string") {
          errorMsg = err.response.data.detail;
        } else if (typeof err.response.data.message === "string") {
          errorMsg = err.response.data.message;
        } else if (err.response.data.detail) {
          errorMsg = String(err.response.data.detail);
        } else {
          errorMsg = `清理失败: ${err.response.status} ${
            err.response.statusText || ""
          }`;
        }
      } else {
        errorMsg = `清理失败: ${err.response.status} ${
          err.response.statusText || ""
        }`;
      }
    } else if (err.message) {
      errorMsg = `清理失败: ${err.message}`;
    }

    alert(errorMsg);
  } finally {
    cleaning.value = false;
  }
}

// 清理下载目录
async function cleanupExportDir() {
  closeCleanupMenu();
  if (cleaning.value) return;

  if (
    !confirm(
      "确定要清空所有下载文件吗？\n\n此操作将删除所有导出文件，无法恢复，请谨慎操作！"
    )
  ) {
    return;
  }

  cleaning.value = true;

  try {
    const res = await axios.post("/api/exports/cleanup", {
      keep_tasks: true, // 保留任务元数据
    });

    if (res.data.success) {
      const removedCount = res.data.removed_count || 0;
      const freedSpace = res.data.freed_space_mb || 0;
      const message =
        res.data.message ||
        `成功清理了 ${removedCount} 个文件，释放空间 ${freedSpace} MB`;
      alert(message);
      await loadExportDirStats(); // 重新加载统计
    } else {
      alert(res.data.message || res.data.detail || "清理失败");
    }
  } catch (err) {
    console.error("清理下载目录失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      "清理失败";
    alert(errorMsg);
  } finally {
    cleaning.value = false;
  }
}

// 清理N天前的下载文件
async function cleanupExportDirDays() {
  closeCleanupMenu();
  if (cleaning.value) return;

  const days = prompt(
    "请输入要清理多少天前的文件（例如：7 表示清理7天前的文件）："
  );
  if (!days || isNaN(days) || parseInt(days) <= 0) {
    return;
  }

  if (
    !confirm(
      `确定要清理 ${days} 天前的下载文件吗？\n\n此操作不可恢复，请谨慎操作！`
    )
  ) {
    return;
  }

  cleaning.value = true;

  try {
    const res = await axios.post("/api/exports/cleanup", {
      days: parseInt(days),
      keep_tasks: true, // 保留任务元数据
    });

    if (res.data.success) {
      const removedCount = res.data.removed_count || 0;
      const freedSpace = res.data.freed_space_mb || 0;
      const message =
        res.data.message ||
        `成功清理了 ${removedCount} 个文件，释放空间 ${freedSpace} MB`;
      alert(message);
      await loadExportDirStats(); // 重新加载统计
    } else {
      alert(res.data.message || res.data.detail || "清理失败");
    }
  } catch (err) {
    console.error("清理下载目录失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      "清理失败";
    alert(errorMsg);
  } finally {
    cleaning.value = false;
  }
}

// 从任务保存为流水线
async function savePipelineFromTask() {
  if (saving.value) return;

  if (!pipelineForm.value.name) {
    alert("请输入流水线名称");
    return;
  }

  if (!pipelineForm.value.git_url) {
    alert("Git 仓库地址不能为空");
    return;
  }

  saving.value = true;
  error.value = null;

  try {
    const payload = {
      name: pipelineForm.value.name,
      description: pipelineForm.value.description,
      git_url: pipelineForm.value.git_url,
      branch: pipelineForm.value.branch,
      project_type: pipelineForm.value.project_type,
      template: pipelineForm.value.template,
      image_name: pipelineForm.value.image_name,
      tag: pipelineForm.value.tag,
      push: pipelineForm.value.push,
      template_params: pipelineForm.value.template_params,
      sub_path: pipelineForm.value.sub_path,
      use_project_dockerfile: pipelineForm.value.use_project_dockerfile,
      dockerfile_name: pipelineForm.value.dockerfile_name || "Dockerfile",
      source_id: pipelineForm.value.source_id || null,
      selected_services: pipelineForm.value.selected_services || null,
      service_push_config: pipelineForm.value.service_push_config || null,
      service_template_params:
        pipelineForm.value.service_template_params || null,
      push_mode: pipelineForm.value.push_mode || "multi",
      resource_package_configs:
        pipelineForm.value.resource_package_configs || null,
      enabled: pipelineForm.value.enabled,
      cron_expression: pipelineForm.value.trigger_schedule
        ? pipelineForm.value.cron_expression
        : null,
      webhook_branch_filter: pipelineForm.value.webhook_branch_filter || false,
      webhook_use_push_branch:
        pipelineForm.value.webhook_use_push_branch !== false,
      branch_tag_mapping: pipelineForm.value.branch_tag_mapping || null,
    };

    await axios.post("/api/pipelines", payload, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    });

    alert("流水线创建成功！");
    showSaveAsPipelineModal.value = false;
    // 可以跳转到流水线页面或刷新
  } catch (err) {
    console.error("保存流水线失败:", err);
    const errorMsg =
      err.response?.data?.detail || err.message || "保存流水线失败";
    error.value = `保存流水线失败: ${errorMsg}`;
    alert(`保存流水线失败: ${errorMsg}`);
  } finally {
    saving.value = false;
  }
}

// 重新构建任务
async function rebuildTask(task) {
  if (rebuilding.value) return;

  // 确认对话框
  const taskName = task.image || task.task_type || "未知任务";
  const taskTag = task.tag || "latest";
  if (!confirm(`确定要重新构建任务 "${taskName}:${taskTag}" 吗？`)) {
    return;
  }

  rebuilding.value = task.task_id;
  error.value = null;

  try {
    // 优先使用后端重试API，它会使用任务保存的完整JSON配置
    const res = await axios.post(
      `/api/build-tasks/${task.task_id}/retry`,
      {},
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      }
    );

    if (res.data && res.data.new_task_id) {
      registerTask(res.data.new_task_id, {
        task_type: "build",
        image: task.image,
        tag: task.tag || "latest",
      });
      alert(`任务重试成功！\n新任务 ID: ${res.data.new_task_id}`);
      await loadTasks(); // 刷新任务列表
    } else {
      throw new Error("重试响应格式错误");
    }
  } catch (err) {
    console.error("重新构建失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      "重新构建失败";
    error.value = `重新构建失败: ${errorMsg}`;
    alert(`重新构建失败: ${errorMsg}`);
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("重新构建失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    rebuilding.value = null;
  }
}

// 重试导出任务
async function retryExportTask(task) {
  if (retrying.value) return;

  // 检查任务状态，只有失败或停止的任务才能重试
  if (task.status !== "failed" && task.status !== "stopped") {
    alert(`无法重试：只有失败或停止的任务才能重试（当前状态: ${task.status}）`);
    return;
  }

  // 确认对话框
  const taskName = task.image || "未知任务";
  const taskTag = task.tag || "latest";
  if (!confirm(`确定要重试导出任务 "${taskName}:${taskTag}" 吗？`)) {
    return;
  }

  retrying.value = task.task_id;
  error.value = null;

  try {
    // 从任务信息中提取导出参数
    const config = {
      image: task.image,
      tag: task.tag || "latest",
      compress: task.compress || "none",
      registry: task.registry || null,
      use_local: task.use_local || false,
    };

    // 验证必要参数
    if (!config.image) {
      throw new Error("任务缺少镜像名称，无法重试导出");
    }

    console.log("🔄 重试导出任务:", task.task_id);

    // 调用重试 API（使用任务 ID 重试，而不是创建新任务）
    const res = await axios.post(`/api/export-tasks/${task.task_id}/retry`);

    if (res.data.success) {
      registerTask(task.task_id, {
        task_type: "export",
        image: task.image,
        tag: task.tag || "latest",
      });
      alert(`重试导出任务已启动！\n任务 ID: ${task.task_id}`);
      // 刷新任务列表
      await loadTasks();
    } else {
      throw new Error(res.data.message || "重试导出失败");
    }
  } catch (err) {
    console.error("重试导出失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      "重试导出失败";
    // 显示错误提示
    alert(`重试导出失败: ${errorMsg}`);
    error.value = `重试导出失败: ${errorMsg}`;
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("重试导出失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    retrying.value = null;
  }
}

// 重试部署任务
async function retryDeployTask(task) {
  if (retryingDeploy.value) return;

  // 检查任务状态，只有失败、停止或已完成的任务才能重试
  if (
    task.status !== "failed" &&
    task.status !== "stopped" &&
    task.status !== "completed"
  ) {
    alert(
      `无法重试：只有失败、停止或已完成的任务才能重试（当前状态: ${task.status}）`
    );
    return;
  }

  // 确认对话框
  const taskName = task.image || task.task_id.substring(0, 8);
  if (!confirm(`确定要重试部署任务 "${taskName}" 吗？`)) {
    return;
  }

  retryingDeploy.value = task.task_id;
  error.value = null;

  try {
    const res = await axios.post(`/api/deploy-tasks/${task.task_id}/retry`);
    if (res.data.success) {
      registerTask(task.task_id, {
        task_type: "deploy",
        image: task.image,
      });
      alert("部署任务已重新启动");
      await loadTasks();
    } else {
      throw new Error(res.data.message || "重试失败");
    }
  } catch (err) {
    console.error("重试部署任务失败:", err);
    const errorMsg = err.response?.data?.detail || err.message || "重试失败";
    error.value = `重试部署任务失败: ${errorMsg}`;
    alert(`重试部署任务失败: ${errorMsg}`);
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("重试部署任务失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    retryingDeploy.value = null;
  }
}

// 查看部署配置
async function viewDeployConfig(task) {
  try {
    const res = await axios.get(`/api/deploy-tasks/${task.task_id}`);
    const taskData = res.data.task;
    const configContent =
      taskData.config_content ||
      (taskData.task_config && taskData.task_config.config_content) ||
      "";

    taskConfigJson.value = configContent;
    taskConfigJsonText.value = configContent;
    showConfigModal.value = true;
  } catch (err) {
    console.error("获取部署配置失败:", err);
    const errorMsg =
      err.response?.data?.detail || err.message || "获取配置失败";
    alert(`获取部署配置失败: ${errorMsg}`);
  }
}

// 监听任务创建事件
function handleTaskCreated(event) {
  console.log("收到任务创建事件，刷新任务列表:", event.detail);
  // 延迟一下再刷新，确保后端任务已创建完成
  setTimeout(() => {
    loadTasks();
  }, 500);
}

function handleTaskFinished() {
  setTimeout(() => {
    loadTasks(false);
  }, 400);
}

onMounted(async () => {
  document.addEventListener("click", handleCleanupOutsideClick);
  window.addEventListener("resize", adjustCleanupMenuPosition);

  // 监听任务创建事件
  window.addEventListener("taskCreated", handleTaskCreated);
  window.addEventListener("taskFinished", handleTaskFinished);
  // 检查是否有从仪表盘传递过来的筛选条件
  const statusFilterFromStorage = sessionStorage.getItem("taskStatusFilter");
  if (statusFilterFromStorage) {
    statusFilter.value = statusFilterFromStorage;
    sessionStorage.removeItem("taskStatusFilter"); // 使用后清除
  }
  // 检查是否有从部署配置管理传递过来的筛选条件
  const deployConfigId = sessionStorage.getItem("deployConfigFilter");
  if (deployConfigId) {
    deployConfigFilterId.value = deployConfigId;
    categoryFilter.value = "deploy";
    sessionStorage.removeItem("deployConfigFilter");
  }
  if (sessionStorage.getItem("tasksNeedRefresh")) {
    sessionStorage.removeItem("tasksNeedRefresh");
  }
  const highlightId = sessionStorage.getItem("highlightTaskId");
  if (highlightId) {
    sessionStorage.removeItem("highlightTaskId");
    categoryFilter.value = "";
    statusFilter.value = "";
  }
  await loadTasks();
  if (highlightId) {
    const found = tasks.value.find((t) => t.task_id === highlightId);
    if (found) {
      nextTick(() => buildTaskLogs.viewLogs(found));
    }
  }
  loadSystemQueueSettings();
  // 启动定时刷新（如果有运行中的任务）
  startRefreshInterval();
});

onUnmounted(() => {
  document.removeEventListener("click", handleCleanupOutsideClick);
  window.removeEventListener("resize", adjustCleanupMenuPosition);

  // 移除任务创建事件监听器
  window.removeEventListener("taskCreated", handleTaskCreated);
  window.removeEventListener("taskFinished", handleTaskFinished);

  if (refreshInterval) {
    clearInterval(refreshInterval);
  }

  // 清除防抖定时器
  if (filterDebounceTimer) {
    clearTimeout(filterDebounceTimer);
  }
});
</script>

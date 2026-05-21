<template>
  <div class="pipeline-panel">
    <div class="pipeline-toolbar flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-3">
      <h5 class="mb-0"><i class="fas fa-project-diagram"></i> 流水线管理</h5>
      <div class="pipeline-toolbar-actions flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center">
        <Button
          variant="outline" size="sm"
          @click="loadPipelines"
          :disabled="loading"
          title="刷新列表"
        >
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i> 刷新
        </Button>
        <Button size="sm" @click="goToCreate">
          <i class="fas fa-plus"></i> 新建流水线
        </Button>
        <Button size="sm" @click="openJsonCreateModal">
          <i class="fas fa-code"></i> 通过JSON创建
        </Button>
      </div>
    </div>

    <div
      class="mb-3 flex flex-col gap-3 rounded-lg border border-slate-200 bg-slate-50/50 p-3 sm:flex-row sm:flex-wrap sm:items-end"
    >
      <div class="min-w-[12rem] flex-1">
        <label class="mb-1 block text-xs font-medium text-slate-600">名称搜索</label>
        <Input
          v-model="searchQuery"
          placeholder="搜索流水线名称或描述"
          @input="onSearchInput"
        />
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-slate-500">启用状态</span>
        <div class="flex flex-wrap gap-1 rounded-md border border-slate-200 bg-white p-0.5">
          <Button
            size="sm"
            :variant="enabledFilter === '' ? 'default' : 'ghost'"
            @click="setEnabledFilter('')"
          >
            全部
          </Button>
          <Button
            size="sm"
            :variant="enabledFilter === 'enabled' ? 'default' : 'ghost'"
            @click="setEnabledFilter('enabled')"
          >
            已启用
          </Button>
          <Button
            size="sm"
            :variant="enabledFilter === 'disabled' ? 'default' : 'ghost'"
            @click="setEnabledFilter('disabled')"
          >
            已禁用
          </Button>
        </div>
      </div>
      <div class="flex flex-col gap-1">
        <label class="text-xs text-slate-500">项目类型</label>
        <select
          v-model="projectTypeFilter"
          class="h-9 min-w-[8rem] rounded-md border border-slate-200 bg-white px-2 text-sm"
          @change="handleFilterChange"
        >
          <option value="">全部类型</option>
          <option
            v-for="pt in projectTypesList"
            :key="pt.value"
            :value="pt.value"
          >
            {{ pt.label }}
          </option>
        </select>
      </div>
    </div>

    <!-- 流水线列表 - 卡片式布局 -->
    <div v-if="loading" class="text-center py-12">
      <i class="fas fa-spinner fa-spin"></i> 加载中...
    </div>
    <div v-else-if="pipelines.length === 0" class="text-center py-12 text-slate-500">
      <i class="fas fa-inbox text-4xl mb-3"></i>
      <p class="mb-0">
        {{ hasActiveFilters ? "暂无符合筛选条件的流水线" : "暂无流水线配置" }}
      </p>
    </div>
    <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div
        v-for="pipeline in pipelines"
        :key="pipeline.pipeline_id"
        >
        <div class="card h-full shadow-sm">
          <!-- 卡片头部 -->
          <div class="card-header relative bg-white">
            <div class="mb-2">
              <h5 class="card-title mb-2">
                <strong class="break-words cursor-pointer text-blue-600 hover:underline" @click="goToDetail(pipeline)">{{ pipeline.name }}</strong>
              </h5>
              <!-- 徽章行 -->
              <div
                class="pipeline-card-badges flex items-center justify-between mb-1"
              >
                <div>
                  <span v-if="pipeline.enabled" class="badge bg-success">
                    <i class="fas fa-check-circle"></i> 已启用
                  </span>
                  <span v-else class="badge bg-secondary">
                    <i class="fas fa-times-circle"></i> 已禁用
                  </span>
                </div>
                <span
                  class="badge"
                  :class="getProjectTypeBadgeClass(pipeline.project_type)"
                  style="font-size: 0.8rem; padding: 0.3rem 0.6rem"
                >
                  <i :class="getProjectTypeIcon(pipeline.project_type)"></i>
                  {{ getProjectTypeLabel(pipeline.project_type) }}
                </span>
              </div>
              <p
                class="text-slate-500 mb-0 mt-1"
                v-if="pipeline.description"
                style="font-size: 0.9rem"
              >
                {{ pipeline.description }}
              </p>
            </div>
            <!-- 操作按钮行 -->
            <div class="pipeline-card-actions btn-group btn-group-sm w-full flex flex-wrap gap-1">
              <Button
                variant="outline" size="sm"
                @click="runPipeline(pipeline)"
                title="手动运行"
              >
                <i class="fas fa-play"></i>
                <span
                  v-if="running === pipeline.pipeline_id"
                  class="fas fa-spinner fa-spin ml-1"
                ></span>
                <span
                  v-else-if="pipeline.queue_length && pipeline.queue_length > 0"
                  class="badge bg-info ml-1"
                >
                  {{ pipeline.queue_length }}个排队
                </span>
                <span
                  v-else-if="
                    pipeline.current_task_status === 'running' ||
                    pipeline.current_task_status === 'pending'
                  "
                  class="badge bg-primary ml-1"
                >
                  运行中
                </span>
              </Button>
              <Button
                variant="outline" size="sm"
                @click="showHistory(pipeline)"
                title="历史构建"
              >
                <i class="fas fa-history"></i>
              </Button>
              <Button
                variant="outline" size="sm"
                @click="openPipelinePermission(pipeline)"
                title="成员授权"
              >
                <i class="fas fa-user-shield"></i>
              </Button>
              <Button
                variant="outline" size="sm"
                @click="goToDetail(pipeline)"
                title="配置流水线"
              >
                <i class="fas fa-cog"></i> 配置
              </Button>
            </div>
          </div>

          <!-- 卡片内容 -->
          <div class="card-body">
            <!-- Git 信息 -->
            <div class="mb-3" style="min-height: 60px">
              <div class="flex items-center mb-2">
                <i
                  class="fas fa-code-branch text-slate-500 mr-2"
                  style="width: 18px; flex-shrink: 0"
                ></i>
                <small
                  class="font-mono truncate flex-1"
                  :title="pipeline.git_url"
                  style="font-size: 0.9rem; min-width: 0"
                >
                  {{ formatGitUrl(pipeline.git_url) }}
                </small>
                <Button
                  variant="outline" size="sm"
                  style="
                    width: 24px;
                    height: 24px;
                    line-height: 1;
                    flex-shrink: 0;
                  "
                  @click="copyTextWithFeedback(pipeline.git_url, 'Git 地址', $event)"
                  title="复制 Git 地址"
                >
                  <i class="fas fa-copy" style="font-size: 0.7rem"></i>
                </Button>
              </div>
              <div
                class="flex items-center flex-wrap gap-2 ml-4"
                style="min-height: 24px"
              >
                <span class="badge bg-secondary" style="font-size: 0.75rem">
                  <i class="fas fa-code-branch"></i>
                  {{ pipeline.branch || "默认" }}
                </span>
                <span
                  v-if="pipeline.webhook_branch_filter"
                  class="badge bg-warning"
                  title="启用分支过滤"
                  style="font-size: 0.75rem"
                >
                  <i class="fas fa-filter"></i> 分支过滤
                </span>
                <span
                  v-if="pipeline.webhook_token"
                  class="badge bg-primary"
                  title="Webhook 触发"
                  style="font-size: 0.75rem"
                >
                  <i class="fas fa-link"></i> Webhook
                </span>
                <span
                  v-if="pipeline.cron_expression"
                  class="badge bg-info"
                  :title="pipeline.cron_expression"
                  style="font-size: 0.75rem"
                >
                  <i class="fas fa-clock"></i> 定时
                </span>
              </div>
            </div>

            <!-- 镜像信息 -->
            <div class="mb-3" style="min-height: 24px">
              <div class="flex items-center">
                <i
                  class="fab fa-docker text-slate-500 mr-2"
                  style="width: 18px; flex-shrink: 0"
                ></i>
                <small
                  class="font-mono truncate flex-1"
                  :title="`${pipeline.image_name}:${pipeline.tag}`"
                  style="font-size: 0.9rem; min-width: 0"
                >
                  {{ pipeline.image_name }}:{{ pipeline.tag }}
                </small>
                <Button
                  variant="outline" size="sm"
                  style="
                    width: 24px;
                    height: 24px;
                    line-height: 1;
                    flex-shrink: 0;
                  "
                  @click="
                    copyTextWithFeedback(
                      `${pipeline.image_name}:${pipeline.tag}`,
                      '镜像名称',
                      $event
                    )
                  "
                  title="复制镜像名称"
                >
                  <i class="fas fa-copy" style="font-size: 0.7rem"></i>
                </Button>
              </div>
              <!-- 多服务信息 -->
              <div
                v-if="
                  pipeline.selected_services &&
                  pipeline.selected_services.length > 0
                "
                class="flex items-center flex-wrap gap-2 ml-4 mt-2"
              >
                <span class="badge bg-info" style="font-size: 0.75rem">
                  <i class="fas fa-layer-group"></i>
                  {{ pipeline.selected_services.length }} 个服务
                </span>
                <span
                  class="badge"
                  :class="
                    pipeline.push_mode === 'multi'
                      ? 'bg-success'
                      : 'bg-secondary'
                  "
                  style="font-size: 0.75rem"
                >
                  <i
                    class="fas"
                    :class="
                      pipeline.push_mode === 'multi' ? 'fa-sitemap' : 'fa-cube'
                    "
                  ></i>
                  {{ pipeline.push_mode === "multi" ? "多阶段" : "单一" }}推送
                </span>
              </div>
              <!-- 子路径 -->
              <div v-if="pipeline.sub_path" class="ml-4 mt-1">
                <small class="text-slate-500" style="font-size: 0.8rem">
                  <i class="fas fa-folder"></i> 子路径: {{ pipeline.sub_path }}
                </small>
              </div>
              <!-- 资源包信息 -->
              <div
                v-if="
                  pipeline.resource_package_configs &&
                  pipeline.resource_package_configs.length > 0
                "
                class="ml-4 mt-1"
              >
                <small class="text-slate-500" style="font-size: 0.8rem">
                  <i class="fas fa-archive"></i>
                  {{ pipeline.resource_package_configs.length }} 个资源包
                </small>
              </div>
              <!-- Dockerfile 信息 -->
              <div v-if="pipeline.use_project_dockerfile" class="ml-4 mt-1">
                <small class="text-slate-500" style="font-size: 0.8rem">
                  <i class="fas fa-file-code"></i>
                  {{ pipeline.dockerfile_name || "Dockerfile" }}
                </small>
              </div>
            </div>

            <!-- 构建状态区域 -->
            <div class="border-t border-slate-200 pt-3 mt-3">
              <!-- 最后构建状态 -->
              <div class="mb-3">
                <div
                  class="pipeline-build-header flex items-center justify-between mb-2"
                >
                  <span
                    class="text-slate-500 fw-semibold"
                    style="font-size: 0.9rem"
                  >
                    <i class="fas fa-hammer mr-1"></i>
                    {{ isLastBuildRunning(pipeline) ? "当前任务" : "最后构建" }}
                  </span>
                  <!-- 如果最后构建是运行中或等待中，显示为当前任务 -->
                  <div
                    v-if="
                      pipeline.last_build &&
                      (pipeline.last_build.status === 'running' ||
                        pipeline.last_build.status === 'pending')
                    "
                    class="flex items-center gap-2"
                  >
                    <span
                      v-if="pipeline.last_build.status === 'running'"
                      class="badge bg-primary"
                    >
                      <span
                        class="fas fa-spinner fa-spin mr-1"
                        style="width: 0.7rem; height: 0.7rem"
                      ></span>
                      运行中
                    </span>
                    <span
                      v-else-if="pipeline.last_build.status === 'pending'"
                      class="badge bg-warning"
                    >
                      <i class="fas fa-clock"></i> 等待中
                    </span>
                    <span
                      v-else-if="
                        pipeline.queue_length && pipeline.queue_length > 0
                      "
                      class="badge bg-info"
                    >
                      <i class="fas fa-list"></i>
                      {{ pipeline.queue_length }}个排队
                    </span>
                    <Button
                      v-if="
                        pipeline.last_build &&
                        pipeline.last_build.task_id &&
                        pipeline.last_build.status !== 'deleted'
                      "
                      variant="outline" size="sm"
                      style="width: 24px; height: 24px; line-height: 1"
                      @click.stop="
                        buildTaskLogs.viewTaskLogs(
                          pipeline.last_build.task_id,
                          pipeline.last_build
                        )
                      "
                      title="查看日志"
                    >
                      <i class="fas fa-terminal" style="font-size: 0.75rem"></i>
                    </Button>
                  </div>
                  <!-- 如果最后构建已完成或失败，显示为历史构建 -->
                  <div
                    v-else-if="
                      pipeline.last_build &&
                      (pipeline.last_build.status === 'completed' ||
                        pipeline.last_build.status === 'failed')
                    "
                    class="flex items-center gap-2"
                  >
                    <span
                      :class="{
                        badge: true,
                        'bg-success':
                          pipeline.last_build.status === 'completed',
                        'bg-danger': pipeline.last_build.status === 'failed',
                      }"
                    >
                      <i
                        v-if="pipeline.last_build.status === 'completed'"
                        class="fas fa-check-circle"
                      ></i>
                      <i
                        v-else-if="pipeline.last_build.status === 'failed'"
                        class="fas fa-times-circle"
                      ></i>
                      {{
                        pipeline.last_build.status === "completed"
                          ? "成功"
                          : "失败"
                      }}
                    </span>
                    <Button
                      v-if="
                        pipeline.last_build &&
                        pipeline.last_build.task_id &&
                        pipeline.last_build.status !== 'deleted'
                      "
                      variant="outline" size="sm"
                      style="width: 24px; height: 24px; line-height: 1"
                      @click.stop="
                        buildTaskLogs.viewTaskLogs(
                          pipeline.last_build.task_id,
                          pipeline.last_build
                        )
                      "
                      title="查看日志"
                    >
                      <i class="fas fa-terminal" style="font-size: 0.75rem"></i>
                    </Button>
                  </div>
                  <span v-else class="text-slate-500" style="font-size: 0.85rem"
                    >暂无构建</span
                  >
                </div>
                <!-- 构建详情 -->
                <div
                  v-if="pipeline.last_build"
                  class="pipeline-build-meta flex justify-between items-center ml-3 mb-2"
                >
                  <small
                    class="text-slate-500"
                    :title="
                      formatDateTime(
                        pipeline.last_build.completed_at ||
                          pipeline.last_build.created_at
                      )
                    "
                    style="font-size: 0.8rem"
                  >
                    <i class="fas fa-calendar-alt mr-1"></i>
                    {{
                      formatDateTime(
                        pipeline.last_build.completed_at ||
                          pipeline.last_build.created_at
                      )
                    }}
                  </small>
                  <small class="text-slate-500">
                    <i class="fas fa-hashtag mr-1"></i>
                    <code style="font-size: 0.8rem">{{
                      pipeline.last_build.task_id?.substring(0, 8) || "-"
                    }}</code>
                  </small>
                </div>
              </div>

              <!-- 统计指标 -->
              <div class="pipeline-stats row g-2">
                <div class="col-4">
                  <div class="bg-light rounded p-2 text-center">
                    <div class="text-slate-500 mb-1" style="font-size: 0.75rem">
                      <i class="fas fa-chart-line"></i> 触发次数
                    </div>
                    <div
                      class="fw-bold"
                      style="font-size: 1.1rem; color: #0d6efd"
                    >
                      {{ pipeline.trigger_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-4">
                  <div class="bg-light rounded p-2 text-center">
                    <div class="text-slate-500 mb-1" style="font-size: 0.75rem">
                      <i class="fas fa-check-circle"></i> 成功
                    </div>
                    <div
                      class="fw-bold"
                      style="font-size: 1.1rem; color: #198754"
                    >
                      {{ pipeline.success_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-4">
                  <div class="bg-light rounded p-2 text-center">
                    <div class="text-slate-500 mb-1" style="font-size: 0.75rem">
                      <i class="fas fa-times-circle"></i> 失败
                    </div>
                    <div
                      class="fw-bold"
                      style="font-size: 1.1rem; color: #dc3545"
                    >
                      {{ pipeline.failed_count || 0 }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <PaginationBar
      v-if="!loading && totalPages > 1"
      :page="currentPage"
      :page-size="pageSize"
      :total="totalPipelines"
      :total-pages="totalPages"
      @update:page="changePage"
    />

<!-- 手动触发分支选择模态框 -->
    <div
      v-if="showManualRunModal"
      class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"
      @click.self="showManualRunModal = false"
      >
      <div class="relative z-10 mx-auto w-full max-w-lg">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="modal-title">
              <i class="fas fa-play text-green-600"></i> 手动触发流水线 -
              {{ manualRunPipeline?.name }}
            </h5>
            <button
              type="button"
              class="rounded-md p-2 text-slate-500 hover:bg-slate-100"
              @click="closeManualRunModal"
            ><i class="fas fa-times"></i></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700">
                <strong>选择分支</strong>
                <span class="text-red-500">*</span>
              </label>
              <div
                v-if="loadingManualRunBranches"
                class="alert alert-info py-2"
              >
                <i class="fas fa-spinner fa-spin"></i> 正在加载分支列表...
              </div>
              <div
                v-else-if="manualRunBranches.length === 0"
                class="alert alert-warning py-2"
              >
                <i class="fas fa-exclamation-triangle"></i>
                未找到可用分支，请点击刷新按钮重新加载
              </div>
              <div v-else class="input-group">
                <select
                  v-model="manualRunSelectedBranch"
                  class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                  required
                  @change="handleBranchChange"
                >
                  <option value="">-- 请选择分支 --</option>
                  <option
                    v-for="branch in manualRunBranches"
                    :key="branch"
                    :value="branch"
                  >
                    {{ branch }}
                  </option>
                </select>
                <Button
                  variant="outline" size="sm"
                  type="button"
                  @click="refreshManualRunBranches"
                  :disabled="loadingManualRunBranches"
                  title="刷新分支列表"
                >
                  <i
                    v-if="loadingManualRunBranches"
                    class="fas fa-spinner fa-spin"
                  ></i>
                  <i v-else class="fas fa-sync-alt"></i>
                </Button>
              </div>
              <small class="text-slate-500 block mt-1">
                <i class="fas fa-info-circle"></i>
                选择要用于构建的分支，点击刷新按钮可重新加载分支列表
              </small>
            </div>
          </div>
          <div class="pipeline-modal-footer flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3">
            <Button
              type="button"
              variant="outline" size="sm"
              @click="closeManualRunModal"
            >
              取消
            </Button>
            <Button
              type="button"
              size="sm"
              @click="confirmManualRun"
              :disabled="!manualRunSelectedBranch"
            >
              <i class="fas fa-play"></i> 确认触发
            </Button>
          </div>
        </div>
      </div>
    </div>
<!-- 通过JSON创建流水线模态框 -->
    <div
      v-if="showJsonCreateModal"
      class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"
      @click.self="showJsonCreateModal = false"
      >
      <div class="relative z-10 mx-auto w-full max-w-3xl">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="modal-title">
              <i class="fas fa-code"></i> 通过JSON创建流水线
            </h5>
            <button
              type="button"
              class="rounded-md p-2 text-slate-500 hover:bg-slate-100"
              @click="closeJsonCreateModal"
            ><i class="fas fa-times"></i></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <div class="alert alert-info">
              <i class="fas fa-info-circle"></i>
              <strong>提示：</strong
              >填写必要参数后，可在下方JSON中继续编辑完整配置。字段定义与"任务中另存为流水线"一致。
            </div>

            <!-- 必要参数输入框 -->
            <div class="card mb-3">
              <div class="card-header bg-light">
                <strong>必要参数</strong>
              </div>
              <div class="card-body">
                <div class="mb-3">
                  <label class="block text-sm font-medium text-slate-700"
                    >流水线名称 <span class="text-red-500">*</span></label
                  >
                  <input
                    type="text"
                    v-model="jsonFormData.name"
                    class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                    placeholder="请输入流水线名称"
                    @input="updateJsonFromForm"
                    required
                  />
                </div>
                <div class="mb-3">
                  <label class="block text-sm font-medium text-slate-700"
                    >Git 仓库地址 <span class="text-red-500">*</span></label
                  >
                  <input
                    type="text"
                    v-model="jsonFormData.git_url"
                    class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                    placeholder="https://github.com/example/repo.git"
                    @input="updateJsonFromForm"
                    required
                  />
                </div>
              </div>
            </div>

            <!-- JSON输入框 -->
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700">流水线配置JSON：</label>
              <textarea
                v-model="jsonInput"
                class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 font-mono text-sm"
                rows="15"
                placeholder='{"name": "my_pipeline", "git_url": "https://github.com/example/repo.git", "branch": "main", ...}'
                style="font-size: 0.9rem"
              ></textarea>
            </div>

            <div v-if="jsonError" class="alert alert-danger">
              <i class="fas fa-exclamation-circle"></i> {{ jsonError }}
            </div>
          </div>
          <div class="pipeline-modal-footer flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3">
            <Button
              type="button"
              variant="outline" size="sm"
              @click="closeJsonCreateModal"
              :disabled="savingJson"
            >
              取消
            </Button>
            <Button
              type="button"
              size="sm"
              @click="createPipelineFromJson"
              :disabled="savingJson || (!jsonFormData.name && !jsonInput)"
            >
              <span
                v-if="savingJson"
                class="fas fa-spinner fa-spin mr-1"
              ></span>
              <i v-else class="fas fa-save"></i> 创建流水线
            </Button>
          </div>
        </div>
      </div>
    </div>

    <ResourceMemberPermissionDialog
      v-model="permissionDialogOpen"
      resource-type="pipeline"
      :resource-id="permissionPipeline?.pipeline_id"
      :team-id="teamStore.activeTeamId"
      :resource-name="permissionPipeline?.name || ''"
    />
    <BuildTaskLogModal :controller="buildTaskLogs" />
  </div>
</template>
<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import BuildTaskLogModal from "@/components/BuildTaskLogModal.vue";
import ResourceMemberPermissionDialog from "@/components/team/ResourceMemberPermissionDialog.vue";
import { useBuildTaskLogs } from "@/composables/useBuildTaskLogs";
import { useTeamStore } from "@/stores/team";
import { StreamLanguage } from "@codemirror/language";
import { javascript } from "@codemirror/legacy-modes/mode/javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import axios from "axios";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { goToPipelineList } from "@/utils/pipelineNavigation.js";
import { copyToClipboard } from "../utils/clipboard.js";
import { Codemirror } from "vue-codemirror";
import { getDockerfilesWithCache } from "../utils/dockerfileCache.js";
import {
  clearGitCache,
  getGitCache,
  getGitInfoWithCache,
  setGitCache,
} from "../utils/gitCache.js";
import { getServiceAnalysisWithCache } from "../utils/serviceAnalysisCache.js";
import { 
  getProjectTypes, 
  getProjectTypesSync,
  getProjectTypeLabel, 
  getProjectTypeIcon,
  getProjectTypeBadgeClass 
} from '../utils/projectTypes.js';

/** 分隔列表时仅使用半角逗号：输入中的全角逗号自动转为半角 */
function normalizeAsciiCommaSeparators(s) {
  return String(s ?? "").replace(/\uFF0C/g, ",");
}

function onPostBuildWebhookBranchesInput(webhook, e) {
  const raw = normalizeAsciiCommaSeparators(e.target.value);
  webhook.branches = raw.split(",").map((b) => b.trim()).filter(Boolean);
}

// 项目类型相关
const projectTypesList = ref(getProjectTypesSync()); // 从缓存获取项目类型列表

const teamStore = useTeamStore();
const router = useRouter();
const route = useRoute();

const buildTaskLogs = useBuildTaskLogs({
  onTaskFinished: () => loadPipelines(),
});

function goToCreate() {
  router.push("/app/pipeline/new");
}

function goToDetail(pipeline, tab = "basic") {
  router.push({
    name: "pipeline-detail",
    params: { pipelineId: pipeline.pipeline_id },
    query: { tab },
  });
}

const pipelines = ref([]);
const currentPage = ref(1);
const pageSize = ref(12);
const totalPipelines = ref(0);
const totalPages = ref(0);
const searchQuery = ref("");
const enabledFilter = ref("");
const projectTypeFilter = ref("");
const searchDebounceTimer = ref(null);

const hasActiveFilters = computed(() =>
  Boolean(
    searchQuery.value.trim() ||
      enabledFilter.value ||
      projectTypeFilter.value
  )
);

const templates = ref([]);
const registries = ref([]);
const gitSources = ref([]);
const loading = ref(false);
const saving = ref(false); // 正在保存流水线
const running = ref(null); // 正在运行的流水线ID
const debounceTimers = ref({}); // 防抖定时器
const queuedPipelines = ref(new Set()); // 排队中的流水线ID集合
const loadingServicesTimer = ref(null); // 加载服务的防抖定时器
const loadingServicesKey = ref(""); // 当前加载服务的唯一标识（用于去重）
const isVerifyingServices = ref(false); // 是否正在验证服务列表（编辑模式下防止重复验证）
const showModal = ref(false);
const showWebhookModal = ref(false);
const permissionDialogOpen = ref(false);
const permissionPipeline = ref(null);
const showMultiServiceConfigModal = ref(false);
const showManualRunModal = ref(false); // 手动触发分支选择模态框
const manualRunPipeline = ref(null); // 要手动触发的流水线
const manualRunSelectedBranch = ref(""); // 手动触发选择的分支
const manualRunBranches = ref([]); // 手动触发可用的分支列表
const loadingManualRunBranches = ref(false); // 正在加载分支列表
const multiServiceConfigPipeline = ref(null);
const savingMultiServiceConfig = ref(false);
const parsingDockerfileForMultiService = ref(false);
const multiServiceFormData = ref({
  push_mode: "multi",
  selected_services: [],
  service_push_config: {},
  global_image_name: "",
  global_tag: "latest",
});
// 临时存储多服务模式下的服务数据（用于单服务/多服务切换时恢复）
const multiServiceBackup = ref({
  selected_services: [],
  service_push_config: {},
});
const webhookUrl = ref("");
const webhookUrlInput = ref(null);
const deployTaskList = ref([]); // 部署任务列表（用于构建后Webhook快捷选择）
const editingPipeline = ref(null);
const showResourcePackageModal = ref(false);
const resourcePackages = ref([]); // 资源包列表
const showJsonCreateModal = ref(false); // JSON创建流水线模态框
const jsonInput = ref(""); // JSON输入内容
const jsonError = ref(""); // JSON错误信息
const savingJson = ref(false); // 正在保存JSON
const jsonFormData = ref({
  // JSON表单数据（只包含必要参数）
  name: "",
  git_url: "",
});

// 多服务相关
const services = ref([]); // 服务列表
const loadingServices = ref(false); // 加载服务中
const servicesError = ref(""); // 服务加载错误

// 分支和 Dockerfile 相关
const branchesAndTags = ref({
  branches: [],
  tags: [],
  default_branch: null,
});
const refreshingBranches = ref(false); // 正在刷新分支
const availableDockerfiles = ref([]); // 可用的 Dockerfile 列表
const scanningDockerfiles = ref(false); // 正在扫描 Dockerfile
const dockerfilesError = ref(""); // Dockerfile 扫描错误
const repoVerified = ref(false); // 仓库是否已验证

const activeTab = ref("basic"); // 当前激活的Tab
const showBuildConfigJsonModal = ref(false); // 显示构建配置JSON模态框
const buildConfigJsonText = ref(""); // JSON文本内容（用于CodeMirror）
const buildConfigJsonError = ref(""); // JSON验证错误
const dockerfileContentText = ref(""); // Dockerfile文本内容（用于CodeMirror）
const loadingDockerfile = ref(false); // 正在从仓库加载Dockerfile

// CodeMirror 扩展配置（JSON模式，使用JavaScript模式）
const jsonEditorExtensions = [StreamLanguage.define(javascript), oneDark];

// CodeMirror 扩展配置（Dockerfile模式，使用JavaScript模式）
const dockerfileEditorExtensions = [StreamLanguage.define(javascript), oneDark];

const formData = ref({
  name: "",
  description: "",
  git_url: "",
  branch: "",
  sub_path: "",
  project_type: "jar",
  template: "",
  image_name: "",
  tag: "latest",
  push: false,
  webhook_token: "", // Webhook Token（用于 URL）
  webhook_secret: "", // Webhook 密钥
  webhook_branch_strategy: "use_push", // Webhook分支策略
  webhook_allowed_branches: [], // 允许触发的分支列表（用于选择分支触发策略）
  branch_tag_mapping: [], // 分支标签映射
  post_build_webhooks: [], // 构建完成后触发的webhook列表
  enabled: true,
  trigger_schedule: false, // 是否启用定时触发
  cron_expression: "", // Cron 表达式
  dockerfile_name: "Dockerfile", // Dockerfile文件名，默认Dockerfile
  use_project_dockerfile: true, // 是否使用项目中的 Dockerfile
  dockerfile_content: "", // Dockerfile内容（用于直接编辑）
  source_id: "", // 数据源ID
  // 多服务配置
  push_mode: "multi", // 推送模式：'single' 或 'multi'
  selected_service: "", // 单服务模式选中的服务
  selected_services: [], // 多服务模式选中的服务列表
  service_push_config: {}, // 服务推送配置 {服务名: {imageName, tag, push}}
  service_template_params: {}, // 服务模板参数
  resource_package_configs: [], // 资源包配置
});

watch(
  () => teamStore.activeTeamId,
  () => {
    loadPipelines({ resetPage: true });
  }
);

watch(
  () =>
    route.name === "admin" &&
    route.params.tab === "pipeline" &&
    !route.params.pipelineId,
  (onList) => {
    if (onList) {
      loadPipelines({ resetPage: true });
    }
  }
);

onMounted(() => {
  loadProjectTypes();
  loadPipelines();
  loadTemplates();
  loadRegistries();
  loadGitSources();
  loadResourcePackages();
  loadDeployTasks();

  // 监听构建配置保存事件
  window.addEventListener("buildConfigSaved", () => {
    const configStr = localStorage.getItem("buildConfigEdited");
    if (configStr) {
      try {
        const config = JSON.parse(configStr);
        localStorage.removeItem("buildConfigEdited");

        // 将配置填充回表单
        if (config.git_url) formData.value.git_url = config.git_url;
        if (config.branch !== undefined) formData.value.branch = config.branch;
        if (config.source_id) formData.value.source_id = config.source_id;
        if (config.project_type)
          formData.value.project_type = config.project_type;
        if (config.template !== undefined)
          formData.value.template = config.template || "";
        if (config.use_project_dockerfile !== undefined)
          formData.value.use_project_dockerfile = config.use_project_dockerfile;
        if (config.dockerfile_name)
          formData.value.dockerfile_name = config.dockerfile_name;
        if (config.template_params)
          formData.value.template_params = config.template_params;
        if (config.image_name) formData.value.image_name = config.image_name;
        if (config.tag) formData.value.tag = config.tag;
        if (config.push_mode) formData.value.push_mode = config.push_mode;
        if (config.should_push !== undefined)
          formData.value.push = config.should_push;
        if (config.selected_services)
          formData.value.selected_services = config.selected_services;
        if (config.service_push_config)
          formData.value.service_push_config = config.service_push_config;
        if (config.service_template_params)
          formData.value.service_template_params =
            config.service_template_params;
        if (config.resource_package_ids)
          formData.value.resource_package_ids = config.resource_package_ids;

        toastSuccess("构建配置已更新");
      } catch (error) {
        console.error("解析构建配置失败:", error);
      }
    }
  });
});

async function loadGitSources() {
  try {
    const res = await axios.get("/api/git-sources");
    gitSources.value = res.data.sources || [];
  } catch (error) {
    console.error("加载数据源列表失败:", error);
  }
}

async function onSourceSelected() {
  const sourceId = formData.value.source_id;
  if (!sourceId) {
    // 如果清空数据源选择，重置分支
    formData.value.source_id = "";
    formData.value.branch = "";
    repoVerified.value = false;
    branchesAndTags.value = { branches: [], tags: [], default_branch: null };
    availableDockerfiles.value = [];
    return;
  }

  const source = gitSources.value.find((s) => s.source_id === sourceId);
  if (source) {
    formData.value.git_url = source.git_url;
    formData.value.source_id = source.source_id;

    // 先尝试从缓存获取
    const cached = getGitCache(source.git_url, sourceId);
    if (cached) {
      branchesAndTags.value = cached;
      repoVerified.value = true;

      // 设置默认分支（如果当前没有选择分支，或选择的分支不在列表中）
      if (
        !formData.value.branch ||
        !cached.branches.includes(formData.value.branch)
      ) {
        formData.value.branch =
          cached.default_branch || cached.branches[0] || "";
      }

      // 如果使用项目 Dockerfile，自动扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles();
        loadServices();
      }
      return;
    }

    // 如果数据源有分支信息，使用数据源的分支列表和默认分支
    if (source.branches && source.branches.length > 0) {
      branchesAndTags.value = {
        branches: source.branches || [],
        tags: source.tags || [],
        default_branch: source.default_branch || null,
      };
      repoVerified.value = true;

      // 设置默认分支（如果当前没有选择分支，或选择的分支不在列表中）
      if (
        !formData.value.branch ||
        !source.branches.includes(formData.value.branch)
      ) {
        formData.value.branch =
          source.default_branch || source.branches[0] || "";
      }

      // 如果使用项目 Dockerfile，自动扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles();
        loadServices();
      }
    } else if (source.default_branch && !formData.value.branch) {
      formData.value.branch = source.default_branch;
      // 尝试从缓存获取（如果API数据源没有缓存，尝试从URL缓存获取）
      const urlCached = getGitCache(source.git_url, null);
      if (urlCached) {
        branchesAndTags.value = urlCached;
        repoVerified.value = true;
      }
    }
  }
}

// 监听 Git URL 变化，自动匹配数据源
watch(
  () => formData.value.git_url,
  () => {
    if (!formData.value.git_url) {
      return;
    }

    // 查找匹配的数据源
    const source = gitSources.value.find(
      (s) => s.git_url === formData.value.git_url
    );
    if (source) {
      // 如果还没有设置 source_id，自动设置
      if (!formData.value.source_id) {
        formData.value.source_id = source.source_id;
      }

      // 先尝试从缓存获取
      const cached = getGitCache(source.git_url, source.source_id);
      if (cached) {
        branchesAndTags.value = cached;
        repoVerified.value = true;

        // 如果数据源有默认分支且当前没有选择分支，设置默认分支
        if (
          !formData.value.branch ||
          !cached.branches.includes(formData.value.branch)
        ) {
          formData.value.branch =
            cached.default_branch || cached.branches[0] || "";
        }

        // 如果使用项目 Dockerfile 且有分支，自动扫描 Dockerfile
        if (formData.value.use_project_dockerfile && formData.value.branch) {
          scanDockerfiles();
        }
      } else if (source.branches && source.branches.length > 0) {
        // 如果数据源有分支信息，加载分支列表
        branchesAndTags.value = {
          branches: source.branches || [],
          tags: source.tags || [],
          default_branch: source.default_branch || null,
        };
        repoVerified.value = true;

        // 如果数据源有默认分支且当前没有选择分支，设置默认分支
        if (source.default_branch && !formData.value.branch) {
          formData.value.branch = source.default_branch;
        }

        // 如果使用项目 Dockerfile 且有分支，自动扫描 Dockerfile
        if (formData.value.use_project_dockerfile && formData.value.branch) {
          scanDockerfiles();
        }
      } else if (source.default_branch && !formData.value.branch) {
        formData.value.branch = source.default_branch;
      }

      // 如果使用项目 Dockerfile 且有分支，重新加载服务（数据源变化不是切换 Dockerfile）
      // 注意：这里不立即调用 loadServices，因为 scanDockerfiles 完成后会自动调用
      // 避免重复触发
    }
  }
);

// 监听分支变化（onBranchChanged 已处理 Dockerfile 扫描）

// 监听 Dockerfile 名称变化，如果使用项目 Dockerfile，重新加载服务
watch(
  () => formData.value.dockerfile_name,
  (newName, oldName) => {
    // 只有当 Dockerfile 名称真正改变且使用项目 Dockerfile 时才重新加载服务
    if (
      newName !== oldName &&
      formData.value.use_project_dockerfile &&
      formData.value.git_url &&
      formData.value.branch &&
      newName && // 确保新名称不为空
      oldName
    ) {
      // 确保是真正的变化（不是初始化）
      // #region agent log (disabled - causes connection errors)
      // fetch(
      //   "http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e",
      //   {
      //     method: "POST",
      //     headers: { "Content-Type": "application/json" },
      //     body: JSON.stringify({
      //       location: "PipelinePanel.vue:1834",
      //       message: "Dockerfile name changed, reloading services",
      //       data: { old: oldName, newValue: newName },
      //       timestamp: Date.now(),
      //       sessionId: "debug-session",
      //       runId: "run1",
      //       hypothesisId: "D",
      //     }),
      //   }
      // ).catch(() => {});
      // #endregion
      // Dockerfile 名称变化是用户主动切换，需要重新识别服务
      loadServices(true);
    }
  }
);

// 监听模态框显示，确保内容同步（只在显示时更新，避免递归）
watch(showBuildConfigJsonModal, (isVisible) => {
  if (isVisible) {
    // 使用 nextTick 确保在模态框完全显示后再更新
    nextTick(() => {
      buildConfigJsonText.value = buildConfigJson.value;
      buildConfigJsonError.value = "";
    });
  }
});

// 监听activeTab变化，当切换到build Tab时（新建或编辑模式），更新JSON内容
// 当切换到service Tab时，自动加载服务列表（如果还没有加载）
watch(activeTab, (newTab) => {
  if (newTab === "build") {
    nextTick(() => {
      buildConfigJsonText.value = buildConfigJson.value;
      buildConfigJsonError.value = "";
    });
  }
  // 编辑模式下不自动加载服务列表，需要用户手动点击加载按钮
  // 这样可以避免编辑时卡死的问题
  // 移除了切换到 service tab 时的自动加载逻辑
});

// 监听JSON文本变化，实时验证（新建和编辑模式下）
watch(buildConfigJsonText, (newText) => {
  if (activeTab.value !== "build") return;

  buildConfigJsonError.value = "";
  if (!newText || !newText.trim()) {
    buildConfigJsonError.value = "JSON不能为空";
    return;
  }

  try {
    const parsed = JSON.parse(newText);
    // 基本验证：确保是对象
    if (typeof parsed !== "object" || Array.isArray(parsed)) {
      buildConfigJsonError.value = "JSON必须是对象格式";
      return;
    }
  } catch (e) {
    buildConfigJsonError.value = `JSON格式错误: ${e.message}`;
  }
});

// 关闭构建配置JSON模态框
function closeBuildConfigJsonModal() {
  showBuildConfigJsonModal.value = false;
  buildConfigJsonError.value = "";
}

// 重置构建配置JSON（恢复到原始值）
async function resetBuildConfigJson() {
  if (await showConfirm({ message: "确定要重置构建配置JSON吗？未保存的修改将丢失。" })) {
    buildConfigJsonText.value = buildConfigJson.value;
    buildConfigJsonError.value = "";
  }
}

// 应用构建配置JSON到formData（不保存到后端）
function applyBuildConfigJson() {
  if (buildConfigJsonError.value) {
    toastError("请先修复JSON错误");
    return;
  }

  try {
    const config = JSON.parse(buildConfigJsonText.value);

    // 更新formData中的相关字段
    if (config.git_url !== undefined) formData.value.git_url = config.git_url;
    if (config.image_name !== undefined)
      formData.value.image_name = config.image_name;
    if (config.tag !== undefined) formData.value.tag = config.tag;
    if (config.branch !== undefined && config.branch !== null)
      formData.value.branch = config.branch;
    if (config.project_type !== undefined)
      formData.value.project_type = config.project_type;
    if (config.template !== undefined)
      formData.value.template = config.template;
    if (config.template_params !== undefined)
      formData.value.template_params = config.template_params;
    if (config.should_push !== undefined)
      formData.value.push = config.should_push;
    if (config.sub_path !== undefined && config.sub_path !== null)
      formData.value.sub_path = config.sub_path;
    if (config.use_project_dockerfile !== undefined)
      formData.value.use_project_dockerfile = config.use_project_dockerfile;
    if (config.dockerfile_name !== undefined)
      formData.value.dockerfile_name = config.dockerfile_name;
    if (
      config.dockerfile_content !== undefined &&
      config.dockerfile_content !== null
    ) {
      formData.value.dockerfile_content = config.dockerfile_content;
      dockerfileContentText.value = config.dockerfile_content;
    }
    if (config.source_id !== undefined && config.source_id !== null)
      formData.value.source_id = config.source_id;
    if (config.selected_services !== undefined)
      formData.value.selected_services = config.selected_services || [];
    if (config.service_push_config !== undefined)
      formData.value.service_push_config = config.service_push_config || {};
    if (config.service_template_params !== undefined)
      formData.value.service_template_params =
        config.service_template_params || {};
    if (config.push_mode !== undefined)
      formData.value.push_mode = config.push_mode || "multi";
    if (config.resource_package_configs !== undefined) {
      // 直接使用resource_package_configs配置（包含package_id和target_path）
      formData.value.resource_package_configs =
        config.resource_package_configs || [];
    } else if (config.resource_package_ids !== undefined) {
      // 兼容旧格式：如果只有resource_package_ids数组，转换为resource_package_configs格式
      formData.value.resource_package_configs = (
        config.resource_package_ids || []
      ).map((pkgId) => ({
        package_id: pkgId,
        target_path: "", // 旧格式没有target_path，留空
      }));
    }

    // 如果push_mode是single，设置selected_service
    if (
      config.push_mode === "single" &&
      config.selected_services &&
      config.selected_services.length > 0
    ) {
      formData.value.selected_service = config.selected_services[0];
    }

    // 更新JSON文本以反映formData的变化
    buildConfigJsonText.value = buildConfigJson.value;
    buildConfigJsonError.value = "";

    // 不显示alert，静默应用，用户需要点击外部保存按钮才能真正保存
  } catch (e) {
    toastError(`应用失败: ${e.message}`);
  }
}

// 从仓库加载Dockerfile内容
async function loadDockerfileFromRepo() {
  if (!formData.value.source_id) {
    toastError("请先选择数据源");
    return;
  }

  if (!formData.value.dockerfile_name) {
    toastError("请先选择或输入Dockerfile文件名");
    return;
  }

  if (!formData.value.branch) {
    toastError("请先选择分支");
    return;
  }

  loadingDockerfile.value = true;
  try {
    const response = await axios.get(
      `/api/git-sources/${
        formData.value.source_id
      }/dockerfiles/${encodeURIComponent(formData.value.dockerfile_name)}`
    );

    if (response.data && response.data.content) {
      dockerfileContentText.value = response.data.content;
      toastInfo("Dockerfile已从仓库加载");
    } else {
      toastError("未找到Dockerfile内容");
    }
  } catch (error) {
    console.error("加载Dockerfile失败:", error);
    toastApiError(error, "加载Dockerfile失败");
  } finally {
    loadingDockerfile.value = false;
  }
}

// 应用Dockerfile内容到formData
function applyDockerfileContent() {
  if (!dockerfileContentText.value.trim()) {
    toastError("Dockerfile内容不能为空");
    return;
  }

  formData.value.dockerfile_content = dockerfileContentText.value;
  toastInfo("Dockerfile内容已应用");
}

// 监听项目类型变化，如果当前选择的模板不再匹配新的项目类型，则清除模板选择
watch(
  () => formData.value.project_type,
  (newType, oldType) => {
    if (newType !== oldType && formData.value.template) {
      // 检查当前选择的模板是否匹配新的项目类型
      const currentTemplate = templates.value.find(
        (t) => t.name === formData.value.template
      );
      if (!currentTemplate || currentTemplate.project_type !== newType) {
        // 模板不匹配新的项目类型，清除模板选择并重新加载服务（项目类型变化不是切换 Dockerfile）
        formData.value.template = "";
        if (
          formData.value.use_project_dockerfile &&
          formData.value.git_url &&
          formData.value.branch
        ) {
          loadServices(false);
        }
      }
    }
  }
);

function handleFilterChange() {
  currentPage.value = 1;
  loadPipelines();
}

function setEnabledFilter(value) {
  enabledFilter.value = value;
  handleFilterChange();
}

function onSearchInput() {
  if (searchDebounceTimer.value) {
    clearTimeout(searchDebounceTimer.value);
  }
  searchDebounceTimer.value = setTimeout(() => {
    handleFilterChange();
  }, 300);
}

function changePage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  currentPage.value = page;
  loadPipelines();
}

async function loadPipelines(options = {}) {
  const { resetPage = false } = options;
  if (resetPage) {
    currentPage.value = 1;
  }
  loading.value = true;
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    };
    if (searchQuery.value.trim()) {
      params.query = searchQuery.value.trim();
    }
    if (enabledFilter.value === "enabled") {
      params.enabled = true;
    } else if (enabledFilter.value === "disabled") {
      params.enabled = false;
    }
    if (projectTypeFilter.value) {
      params.project_type = projectTypeFilter.value;
    }
    if (teamStore.activeTeamId) {
      params.team_id = teamStore.activeTeamId;
    }

    const res = await axios.get("/api/pipelines", { params });
    pipelines.value = res.data.pipelines || [];
    totalPipelines.value = res.data.total ?? 0;
    totalPages.value = res.data.total_pages ?? 0;

    if (
      pipelines.value.length === 0 &&
      currentPage.value > 1 &&
      totalPages.value > 0
    ) {
      currentPage.value = totalPages.value;
      return loadPipelines();
    }

    queuedPipelines.value.clear();
    pipelines.value.forEach((pipeline) => {
      if (
        pipeline.has_queued_tasks ||
        (pipeline.queue_length && pipeline.queue_length > 0)
      ) {
        queuedPipelines.value.add(pipeline.pipeline_id);
      }
    });
  } catch (error) {
    console.error("加载流水线列表失败:", error);
    toastError("加载流水线列表失败");
    pipelines.value = [];
    totalPipelines.value = 0;
    totalPages.value = 0;
  } finally {
    loading.value = false;
  }
}

async function loadTemplates() {
  try {
    const res = await axios.get("/api/list-templates");
    templates.value = res.data || [];
  } catch (error) {
    console.error("加载模板列表失败:", error);
  }
}

async function loadRegistries() {
  try {
    const res = await axios.get("/api/registries");
    registries.value = res.data.registries || [];
  } catch (error) {
    console.error("加载仓库列表失败:", error);
  }
}

async function loadDeployTasks() {
  try {
    const res = await axios.get("/api/deploy-tasks");
    deployTaskList.value = res.data.tasks || [];
  } catch (error) {
    console.error("加载部署任务列表失败:", error);
  }
}

function getDeployWebhookUrl(token) {
  const baseUrl = window.location.origin
    .replace(":3000", ":8000")
    .replace(":5173", ":8000");
  return `${baseUrl}/api/webhook/deploy/${token}`;
}

function onDeployTaskSelected(webhook, configId) {
  const task = deployTaskList.value.find((t) => t.task_id === configId);
  if (!task) return;
  let token = task.webhook_token;
  if (!token) {
    // 部署配置没有 webhook_token，自动生成一个
    token = crypto.randomUUID();
    task.webhook_token = token;
    // 异步回写到后端，确保下次也能使用
    axios.put(`/api/deploy-tasks/${configId}`, {
      config_content: task.config_content,
      webhook_token: token,
    }).catch(() => {});
  }
  webhook.url = getDeployWebhookUrl(token);
  webhook.method = "POST";
}

function showCreateModal() {
  editingPipeline.value = null;
  formData.value = {
    name: "",
    description: "",
    git_url: "",
    branch: "",
    sub_path: "",
    project_type: "jar",
    template: "",
    image_name: "",
    tag: "latest",
    push: false,
    webhook_secret: "",
    webhook_branch_strategy: "use_push",
    webhook_allowed_branches: [],
    branch_tag_mapping: [],
    post_build_webhooks: [],
    enabled: true,
    trigger_schedule: false,
    cron_expression: "",
    dockerfile_name: "Dockerfile",
    dockerfile_content: "", // Dockerfile内容
    source_id: "",
    use_project_dockerfile: true,
    push_mode: "multi",
    selected_service: "",
    selected_services: [],
    service_push_config: {},
    service_template_params: {},
    resource_package_configs: [],
  };
  services.value = [];
  loadingServices.value = false;
  servicesError.value = "";
  // 初始化Dockerfile编辑器内容
  dockerfileContentText.value = "";
  showModal.value = true;
  // 初始化JSON编辑器内容（新建模式）
  nextTick(() => {
    if (activeTab.value === "build") {
      buildConfigJsonText.value = buildConfigJson.value;
      buildConfigJsonError.value = "";
    }
  });
}

function editPipeline(pipeline) {
  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:1918",
  //     message: "editPipeline started",
  //     data: {
  //       pipeline_id: pipeline.id,
  //       pipeline_name: pipeline.name,
  //       dockerfile_name: pipeline.dockerfile_name,
  //       template: pipeline.template,
  //       use_project_dockerfile: pipeline.use_project_dockerfile,
  //       project_type: pipeline.project_type,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "B",
  //   }),
  // }).catch(() => {});
  // #endregion

  // 先重置Tab，确保显示基本信息Tab，而不是自动跳转到build Tab
  activeTab.value = "basic";
  // 然后设置编辑模式
  editingPipeline.value = pipeline;

  // 查找对应的数据源
  const source = gitSources.value.find(
    (s) => s.source_id === pipeline.source_id || s.git_url === pipeline.git_url
  );

  // 保存原始配置，避免被扫描覆盖
  const savedDockerfileName = pipeline.dockerfile_name || "Dockerfile";
  const savedTemplate = pipeline.template || "";
  // 优先使用后端返回的 use_project_dockerfile，如果没有则根据 template 推断
  const savedUseProjectDockerfile =
    pipeline.use_project_dockerfile !== undefined
      ? pipeline.use_project_dockerfile
      : !pipeline.template; // 有模板则 false，无模板则 true

  const normalizedPipelineSpc = normalizeServicePushConfig(
    pipeline.service_push_config || {}
  );

  formData.value = {
    name: pipeline.name,
    description: pipeline.description || "",
    git_url: pipeline.git_url,
    branch: pipeline.branch || "",
    sub_path: pipeline.sub_path || "",
    project_type: pipeline.project_type || "jar",
    template: savedTemplate,
    image_name: pipeline.image_name || "",
    tag: pipeline.tag || "latest",
    push:
      pipeline.push_mode === "multi"
        ? anyServicePushEnabled(normalizedPipelineSpc) || !!pipeline.push
        : pipeline.push || false,
    webhook_token: pipeline.webhook_token || "",
    webhook_secret: pipeline.webhook_secret || "",
    webhook_branch_strategy: getWebhookBranchStrategy(pipeline),
    webhook_allowed_branches: pipeline.webhook_allowed_branches
      ? [...pipeline.webhook_allowed_branches]
      : [],
    branch_tag_mapping: pipeline.branch_tag_mapping
      ? Object.entries(pipeline.branch_tag_mapping).map(([branch, tag]) => ({
          branch,
          tag: Array.isArray(tag) ? tag.join(",") : tag, // 如果是数组，转换为逗号分隔的字符串
        }))
      : [],
    post_build_webhooks: (() => {
      if (
        !pipeline.post_build_webhooks ||
        pipeline.post_build_webhooks.length === 0
      ) {
        return [];
      }
      // 将headers对象转换为headers_json字符串
      return pipeline.post_build_webhooks.map((webhook) => ({
        url: webhook.url || "",
        method: webhook.method || "POST",
        headers: webhook.headers || {},
        headers_json: JSON.stringify(webhook.headers || {}, null, 2),
        body_template: webhook.body_template || "{}",
        enabled: webhook.enabled !== false,
        branch_strategy: webhook.branch_strategy || "all",
        branches: webhook.branches || [],
      }));
    })(),
    enabled: pipeline.enabled !== false,
    trigger_schedule: !!pipeline.cron_expression, // 如果有cron表达式则启用
    cron_expression: pipeline.cron_expression || "",
    dockerfile_name: savedDockerfileName,
    use_project_dockerfile: savedUseProjectDockerfile,
    dockerfile_content: pipeline.dockerfile_content || "", // Dockerfile内容
    source_id: pipeline.source_id || (source ? source.source_id : ""),
    push_mode: pipeline.push_mode || "multi",
    selected_service:
      pipeline.selected_services && pipeline.selected_services.length === 1
        ? pipeline.selected_services[0]
        : "",
    selected_services: pipeline.selected_services || [],
    service_push_config: normalizedPipelineSpc,
    service_template_params: pipeline.service_template_params || {},
    resource_package_configs: pipeline.resource_package_configs || [],
  };

  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:1956",
  //     message: "formData initialized",
  //     data: {
  //       dockerfile_name: formData.value.dockerfile_name,
  //       template: formData.value.template,
  //       use_project_dockerfile: formData.value.use_project_dockerfile,
  //       branch: formData.value.branch,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "B",
  //   }),
  // }).catch(() => {});
  // #endregion

  // 如果数据源有分支信息，加载分支列表
  if (source && source.branches && source.branches.length > 0) {
    branchesAndTags.value = {
      branches: source.branches || [],
      tags: source.tags || [],
      default_branch: source.default_branch || null,
    };
    repoVerified.value = true;

    // 如果当前分支为空或不在分支列表中，使用默认分支
    if (
      !formData.value.branch ||
      !source.branches.includes(formData.value.branch)
    ) {
      formData.value.branch =
        source.default_branch ||
        source.branches[0] ||
        formData.value.branch ||
        "";
    }

    // 编辑模式下：不自动扫描 Dockerfile 和加载服务列表
    // 用户需要手动在服务配置 tab 中点击加载按钮
    // 这样可以避免编辑时卡死的问题
  }

  // 编辑模式下：不加载服务列表，避免卡死问题
  // 服务管理功能已移除

  // 初始化Dockerfile编辑器内容
  dockerfileContentText.value = formData.value.dockerfile_content || "";

  showModal.value = true;

  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:1980",
  //     message: "editPipeline completed",
  //     data: {
  //       final_dockerfile_name: formData.value.dockerfile_name,
  //       final_template: formData.value.template,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "B",
  //   }),
  // }).catch(() => {});
  // #endregion
}

// 添加分支标签映射
function addBranchTagMapping() {
  if (!formData.value.branch_tag_mapping) {
    formData.value.branch_tag_mapping = [];
  }
  formData.value.branch_tag_mapping.push({ branch: "", tag: "" });
}

// 删除分支标签映射
function addPostBuildWebhook() {
  if (!formData.value.post_build_webhooks) {
    formData.value.post_build_webhooks = [];
  }
  formData.value.post_build_webhooks.push({
    url: "",
    method: "POST",
    headers: {},
    headers_json: "{}",
    body_template:
      '{"task_id": "{task_id}", "image": "{image}", "tag": "{tag}", "status": "{status}"}',
    enabled: true,
    branch_strategy: "all",
    branches: [],
  });
}

function removePostBuildWebhook(index) {
  if (formData.value.post_build_webhooks) {
    formData.value.post_build_webhooks.splice(index, 1);
  }
}

function removeBranchTagMapping(index) {
  formData.value.branch_tag_mapping.splice(index, 1);
}

// 全选/取消全选分支
function toggleAllBranches(event) {
  if (event.target.checked) {
    // 全选：添加所有分支
    formData.value.webhook_allowed_branches = [
      ...(branchesAndTags.value.branches || []),
    ];
  } else {
    // 取消全选：清空选择
    formData.value.webhook_allowed_branches = [];
  }
}

// 计算是否全选分支
const isAllBranchesSelected = computed(() => {
  const branches = branchesAndTags.value.branches || [];
  if (branches.length === 0) return false;
  const selected = formData.value.webhook_allowed_branches || [];
  return (
    branches.length === selected.length &&
    branches.every((branch) => selected.includes(branch))
  );
});

// 根据旧配置获取新的分支策略
function getWebhookBranchStrategy(pipeline) {
  // 如果流水线有webhook_allowed_branches字段且不为空，说明是选择分支触发策略
  if (
    pipeline.webhook_allowed_branches &&
    Array.isArray(pipeline.webhook_allowed_branches) &&
    pipeline.webhook_allowed_branches.length > 0
  ) {
    return "select_branches";
  }

  const webhook_branch_filter = pipeline.webhook_branch_filter || false;
  const webhook_use_push_branch = pipeline.webhook_use_push_branch !== false; // 默认为true

  if (webhook_branch_filter) {
    return "filter_match";
  } else if (webhook_use_push_branch) {
    return "use_push";
  } else {
    return "use_configured";
  }
}

async function savePipeline() {
  // 防止重复提交
  if (saving.value) {
    return;
  }

  saving.value = true;
  try {
    // 将分支标签映射从数组转换为对象
    // 支持一个分支对应多个标签（用逗号分隔，转换为数组）
    const branch_tag_mapping = {};
    if (
      formData.value.branch_tag_mapping &&
      formData.value.branch_tag_mapping.length > 0
    ) {
      formData.value.branch_tag_mapping.forEach((mapping) => {
        if (mapping.branch && mapping.tag) {
          // 如果标签包含逗号，转换为数组；否则保持字符串
          const tagValue = mapping.tag.trim().replace(/，/g, ',');
          if (tagValue.includes(",")) {
            // 多个标签，转换为数组
            branch_tag_mapping[mapping.branch] = tagValue
              .split(",")
              .map((t) => t.trim())
              .filter((t) => t);
          } else {
            // 单个标签，保持字符串（向后兼容）
            branch_tag_mapping[mapping.branch] = tagValue;
          }
        }
      });
    }

    // 根据分支策略设置webhook_branch_filter和webhook_use_push_branch
    let webhook_branch_filter = false;
    let webhook_use_push_branch = true;

    if (formData.value.webhook_branch_strategy === "filter_match") {
      webhook_branch_filter = true;
      webhook_use_push_branch = true;
    } else if (formData.value.webhook_branch_strategy === "use_push") {
      webhook_branch_filter = false;
      webhook_use_push_branch = true;
    } else if (formData.value.webhook_branch_strategy === "select_branches") {
      // 选择分支触发策略：验证是否选择了分支
      if (
        !formData.value.webhook_allowed_branches ||
        formData.value.webhook_allowed_branches.length === 0
      ) {
        toastError("请至少选择一个允许触发的分支");
        saving.value = false;
        return;
      }
      webhook_branch_filter = true;
      webhook_use_push_branch = true;
    } else {
      // use_configured
      webhook_branch_filter = false;
      webhook_use_push_branch = false;
    }

    // 确保 template 和 use_project_dockerfile 的一致性
    // 如果使用项目 Dockerfile，则清空 template
    // 如果使用模板，则确保 use_project_dockerfile 为 false
    if (formData.value.use_project_dockerfile) {
      formData.value.template = "";
    } else {
      // 使用模板时，确保选择了模板
      if (!formData.value.template) {
        toastError("请选择 Dockerfile 模板");
        saving.value = false;
        return;
      }
    }

    // 准备提交数据
    const payload = {
      ...formData.value,
      // 确保 use_project_dockerfile 和 template 的一致性
      use_project_dockerfile: formData.value.use_project_dockerfile,
      // 如果使用项目 Dockerfile，template 应该为空字符串
      // 如果使用模板，template 必须有值（不能为空）
      template: formData.value.use_project_dockerfile
        ? ""
        : formData.value.template || "",
      // 将分支策略转换为旧格式（向后兼容）
      webhook_branch_filter: webhook_branch_filter,
      webhook_use_push_branch: webhook_use_push_branch,
      // 将分支标签映射转换为对象格式
      branch_tag_mapping:
        Object.keys(branch_tag_mapping).length > 0 ? branch_tag_mapping : null,
      // 如果未启用定时触发，则cron_expression为null
      cron_expression: formData.value.trigger_schedule
        ? formData.value.cron_expression
        : null,
      // 传递数据源ID
      source_id: formData.value.source_id || null,
      // 多服务配置：根据推送模式处理
      // 编辑模式下，如果formData中没有多阶段配置，从原始流水线数据中保留
      selected_services: (() => {
        const fromForm =
          formData.value.push_mode === "single" &&
          formData.value.selected_service
            ? [formData.value.selected_service]
            : formData.value.selected_services &&
              formData.value.selected_services.length > 0
            ? formData.value.selected_services
            : null;

        // 如果formData中有配置，使用formData的配置
        if (fromForm && fromForm.length > 0) {
          return fromForm;
        }

        // 编辑模式下，如果formData中没有配置，从原始流水线数据中保留
        if (
          editingPipeline.value &&
          editingPipeline.value.selected_services &&
          editingPipeline.value.selected_services.length > 0
        ) {
          return editingPipeline.value.selected_services;
        }

        return null;
      })(),
      // 规范化服务推送配置（确保所有配置都是对象格式，包含 push、imageName 和 tag 字段）
      service_push_config: (() => {
        // 只处理已选择的服务
        const selectedServices =
          formData.value.push_mode === "single" &&
          formData.value.selected_service
            ? [formData.value.selected_service]
            : formData.value.selected_services || [];

        // 如果formData中没有服务，但编辑模式下原始流水线有服务，使用原始流水线的服务
        if (
          selectedServices.length === 0 &&
          editingPipeline.value &&
          editingPipeline.value.selected_services &&
          editingPipeline.value.selected_services.length > 0
        ) {
          selectedServices.push(...editingPipeline.value.selected_services);
        }

        if (selectedServices.length === 0) {
          // 编辑模式下，如果formData中没有配置，从原始流水线数据中保留
          if (
            editingPipeline.value &&
            editingPipeline.value.service_push_config &&
            Object.keys(editingPipeline.value.service_push_config).length > 0
          ) {
            return editingPipeline.value.service_push_config;
          }
          return null;
        }

        const config = formData.value.service_push_config || {};
        // 编辑模式下，如果formData中没有配置，尝试从原始流水线数据中获取
        if (
          Object.keys(config).length === 0 &&
          editingPipeline.value &&
          editingPipeline.value.service_push_config
        ) {
          Object.assign(config, editingPipeline.value.service_push_config);
        }

        const normalized = {};

        selectedServices.forEach((serviceName) => {
          const value = config[serviceName];
          if (typeof value === "boolean") {
            // 旧格式：只有push字段
            normalized[serviceName] = {
              push: value,
              imageName: getServiceDefaultImageName(serviceName),
              tag: formData.value.tag || "latest",
            };
          } else if (value && typeof value === "object") {
            // 获取最终镜像名（自定义或默认）
            const customImageName = value.imageName && value.imageName.trim();
            const finalImageName =
              customImageName || getServiceDefaultImageName(serviceName);
            // 获取最终标签（自定义或全局）
            const finalTag =
              (value.tag && value.tag.trim()) || formData.value.tag || "latest";

            normalized[serviceName] = {
              push: value.push !== undefined ? value.push : false,
              imageName: finalImageName,
              tag: finalTag,
            };
          } else {
            // 新服务，使用默认值
            normalized[serviceName] = {
              push: false,
              imageName: getServiceDefaultImageName(serviceName),
              tag: formData.value.tag || "latest",
            };
          }
        });

        return Object.keys(normalized).length > 0 ? normalized : null;
      })(),
      service_template_params: (() => {
        const fromForm =
          formData.value.service_template_params &&
          Object.keys(formData.value.service_template_params).length > 0
            ? formData.value.service_template_params
            : null;

        // 如果formData中有配置，使用formData的配置
        if (fromForm) {
          return fromForm;
        }

        // 编辑模式下，如果formData中没有配置，从原始流水线数据中保留
        if (
          editingPipeline.value &&
          editingPipeline.value.service_template_params &&
          Object.keys(editingPipeline.value.service_template_params).length > 0
        ) {
          return editingPipeline.value.service_template_params;
        }

        return null;
      })(),
      // 确保push_mode被保留（编辑模式下，如果formData中没有，从原始流水线数据中保留）
      push_mode:
        formData.value.push_mode ||
        (editingPipeline.value && editingPipeline.value.push_mode) ||
        "multi",
      resource_package_configs:
        formData.value.resource_package_configs &&
        formData.value.resource_package_configs.length > 0
          ? formData.value.resource_package_configs
          : null,
      // Webhook 配置：如果为空字符串，传递 null 让后端自动生成
      webhook_token:
        formData.value.webhook_token && formData.value.webhook_token.trim()
          ? formData.value.webhook_token.trim()
          : null,
      webhook_secret:
        formData.value.webhook_secret && formData.value.webhook_secret.trim()
          ? formData.value.webhook_secret.trim()
          : null,
      // 选择分支触发：只在策略为select_branches时传递
      webhook_allowed_branches:
        formData.value.webhook_branch_strategy === "select_branches"
          ? formData.value.webhook_allowed_branches || []
          : null,
      // 构建后webhook配置
      post_build_webhooks: (() => {
        if (
          !formData.value.post_build_webhooks ||
          formData.value.post_build_webhooks.length === 0
        ) {
          return null;
        }
        // 处理每个webhook，将headers_json转换为headers对象
        return formData.value.post_build_webhooks.map((webhook) => {
          const processed = {
            url: webhook.url,
            method: webhook.method || "POST",
            body_template: webhook.body_template || "{}",
            enabled: webhook.enabled !== false,
            branch_strategy: webhook.branch_strategy || "all",
            branches: webhook.branches || [],
          };
          // 解析headers_json为对象
          if (webhook.headers_json) {
            try {
              processed.headers = JSON.parse(webhook.headers_json);
            } catch (e) {
              console.warn("解析webhook headers失败，使用空对象:", e);
              processed.headers = {};
            }
          } else {
            processed.headers = webhook.headers || {};
          }
          return processed;
        });
      })(),
    };
    // 多阶段模式：顶层 push 与分服务推送开关同步（否则仅保存 service_push_config 时 DB 仍为 false）
    if (payload.push_mode === "multi" && payload.service_push_config) {
      payload.push = anyServicePushEnabled(payload.service_push_config);
    }
    // 移除webhook_branch_strategy，因为后端不需要这个字段
    delete payload.webhook_branch_strategy;
    delete payload.selected_service; // 移除单服务字段，后端不需要
    delete payload.trigger_schedule; // 移除前端字段

    // 验证：如果启用定时触发，必须填写cron表达式
    if (payload.trigger_schedule && !payload.cron_expression) {
      toastError("请填写 Cron 表达式");
      saving.value = false;
      return;
    }

    // 验证：如果使用模板，必须选择了模板
    if (!payload.use_project_dockerfile && !payload.template) {
      toastError("使用模板时必须选择 Dockerfile 模板");
      saving.value = false;
      return;
    }

    // 验证流水线名字不能重复
    const pipelineName = payload.name && payload.name.trim();
    if (!pipelineName) {
      toastError("请输入流水线名称");
      saving.value = false;
      return;
    }

    // 调试信息
    console.log("保存流水线参数:", {
      use_project_dockerfile: payload.use_project_dockerfile,
      template: payload.template,
      project_type: payload.project_type,
    });

    const isEdit = !!editingPipeline.value;
    if (isEdit) {
      await axios.put(
        `/api/pipelines/${editingPipeline.value.pipeline_id}`,
        payload
      );
      toastSuccess("流水线更新成功");
    } else {
      await axios.post("/api/pipelines", payload);
      toastSuccess("流水线创建成功");
    }
    closeModal();
    loadPipelines({ resetPage: !isEdit });
  } catch (error) {
    console.error("保存流水线失败:", error);
    toastApiError(error, "保存流水线失败");
  } finally {
    saving.value = false;
  }
}

function closeModal() {
  // 如果正在保存，不允许关闭
  if (saving.value) {
    return;
  }
  showModal.value = false;
  editingPipeline.value = null;
  services.value = [];
  loadingServices.value = false;
  servicesError.value = "";
  saving.value = false; // 重置保存状态
  // 重置分支和 Dockerfile 相关状态
  branchesAndTags.value = { branches: [], tags: [], default_branch: null };
  availableDockerfiles.value = [];
  refreshingBranches.value = false;
  scanningDockerfiles.value = false;
  dockerfilesError.value = "";
  repoVerified.value = false;
}

function openJsonCreateModal() {
  jsonInput.value = "";
  jsonError.value = "";
  jsonFormData.value = {
    name: "",
    git_url: "",
  };
  showJsonCreateModal.value = true;
}

// 从表单数据更新JSON
function updateJsonFromForm() {
  try {
    // 如果JSON输入框为空或无效，则从表单生成
    let currentJson = {};
    if (jsonInput.value && jsonInput.value.trim()) {
      try {
        currentJson = JSON.parse(jsonInput.value.trim());
      } catch (e) {
        // JSON无效，使用表单数据
        currentJson = {};
      }
    }

    // 只更新必要字段
    if (jsonFormData.value.name) {
      currentJson.name = jsonFormData.value.name;
    }
    if (jsonFormData.value.git_url) {
      currentJson.git_url = jsonFormData.value.git_url;
    }

    // 设置默认值（如果字段不存在）
    if (!currentJson.enabled) {
      currentJson.enabled = true;
    }
    if (currentJson.push === undefined) {
      currentJson.push = false;
    }
    if (currentJson.use_project_dockerfile === undefined) {
      currentJson.use_project_dockerfile = true;
    }
    if (!currentJson.dockerfile_name) {
      currentJson.dockerfile_name = "Dockerfile";
    }
    if (currentJson.webhook_branch_filter === undefined) {
      currentJson.webhook_branch_filter = false;
    }
    if (currentJson.webhook_use_push_branch === undefined) {
      currentJson.webhook_use_push_branch = true;
    }
    if (!currentJson.push_mode) {
      currentJson.push_mode = "multi";
    }
    if (!currentJson.tag) {
      currentJson.tag = "latest";
    }
    if (!currentJson.project_type) {
      currentJson.project_type = "jar";
    }

    // 更新JSON输入框
    jsonInput.value = JSON.stringify(currentJson, null, 2);
  } catch (e) {
    console.error("更新JSON失败:", e);
  }
}

function closeJsonCreateModal() {
  if (savingJson.value) {
    return;
  }
  showJsonCreateModal.value = false;
  jsonInput.value = "";
  jsonError.value = "";
}

async function createPipelineFromJson() {
  savingJson.value = true;
  jsonError.value = "";

  try {
    let pipelineData;

    // 优先使用JSON输入框的内容
    if (jsonInput.value && jsonInput.value.trim()) {
      try {
        pipelineData = JSON.parse(jsonInput.value.trim());
      } catch (e) {
        jsonError.value = `JSON格式错误: ${e.message}`;
        savingJson.value = false;
        return;
      }
    } else {
      // 如果JSON为空，从表单数据生成
      if (!jsonFormData.value.name) {
        jsonError.value = "流水线名称不能为空";
        savingJson.value = false;
        return;
      }

      if (!jsonFormData.value.git_url) {
        jsonError.value = "Git 仓库地址不能为空";
        savingJson.value = false;
        return;
      }

      // 构建完整的流水线配置
      pipelineData = {
        name: jsonFormData.value.name,
        git_url: jsonFormData.value.git_url,
        branch: jsonFormData.value.branch || null,
        image_name: jsonFormData.value.image_name || null,
        tag: jsonFormData.value.tag || "latest",
        project_type: jsonFormData.value.project_type || "jar",
        description: jsonFormData.value.description || "",
        enabled: true,
        push: false,
        use_project_dockerfile: true,
        dockerfile_name: "Dockerfile",
        webhook_branch_filter: false,
        webhook_use_push_branch: true,
        push_mode: "multi",
      };
    }

    // 验证必填字段
    if (!pipelineData.name) {
      jsonError.value = "流水线名称(name)不能为空";
      savingJson.value = false;
      return;
    }

    if (!pipelineData.git_url && !pipelineData.source_id) {
      jsonError.value = "必须提供 git_url 或 source_id";
      savingJson.value = false;
      return;
    }

    // 调用API创建流水线
    const response = await axios.post("/api/pipelines/json", pipelineData);

    toastSuccess("流水线创建成功！");
    closeJsonCreateModal();
    loadPipelines({ resetPage: true });
  } catch (error) {
    console.error("通过JSON创建流水线失败:", error);
    const errorMsg =
      error.response?.data?.detail || error.message || "创建流水线失败";
    jsonError.value = errorMsg;
  } finally {
    savingJson.value = false;
  }
}

// 刷新分支列表
async function refreshBranches(forceRefresh = true) {
  const sourceId = formData.value.source_id;
  if (!sourceId) {
    if (!formData.value.git_url) {
      toastError("请先选择数据源或填写 Git 仓库地址");
      return;
    }
    // 如果没有数据源但有 Git URL，使用 verify-git-repo API
    try {
      refreshingBranches.value = true;

      // 如果强制刷新，先清除缓存
      if (forceRefresh) {
        clearGitCache(formData.value.git_url, null);
      }

      // 使用缓存机制获取Git信息
      const data = await getGitInfoWithCache(
        async () => {
          const response = await axios.post("/api/verify-git-repo", {
            git_url: formData.value.git_url,
            source_id: null,
          });
          return response.data;
        },
        formData.value.git_url,
        null,
        forceRefresh
      );

      if (data && data.branches) {
        branchesAndTags.value = {
          branches: data.branches || [],
          tags: data.tags || [],
          default_branch: data.default_branch || null,
        };
        repoVerified.value = true;

        // 如果当前选择的分支不在新列表中，重置为默认分支
        const currentBranch = formData.value.branch;
        if (
          currentBranch &&
          !branchesAndTags.value.branches.includes(currentBranch) &&
          !branchesAndTags.value.tags.includes(currentBranch)
        ) {
          formData.value.branch = branchesAndTags.value.default_branch || "";
        }
      }
    } catch (error) {
      console.error("刷新分支列表失败:", error);
      toastApiError(error, "刷新分支列表失败，请稍后重试");
    } finally {
      refreshingBranches.value = false;
    }
    return;
  }

  const source = gitSources.value.find((s) => s.source_id === sourceId);
  if (!source) {
    return;
  }

  refreshingBranches.value = true;
  try {
    // 如果强制刷新，先清除缓存
    if (forceRefresh) {
      clearGitCache(source.git_url, sourceId);
    }

    // 使用缓存机制获取Git信息
    const data = await getGitInfoWithCache(
      async () => {
        const response = await axios.post("/api/verify-git-repo", {
          git_url: source.git_url,
          source_id: sourceId,
        });
        return response.data;
      },
      source.git_url,
      sourceId,
      forceRefresh
    );

    if (data && data.branches) {
      // 更新分支和标签列表
      branchesAndTags.value = {
        branches: data.branches || [],
        tags: data.tags || [],
        default_branch: data.default_branch || null,
      };
      repoVerified.value = true;

      // 如果当前选择的分支不在新列表中，重置为默认分支
      const currentBranch = formData.value.branch;
      if (
        currentBranch &&
        !branchesAndTags.value.branches.includes(currentBranch) &&
        !branchesAndTags.value.tags.includes(currentBranch)
      ) {
        formData.value.branch = branchesAndTags.value.default_branch || "";
      }

      // 如果使用项目 Dockerfile，重新扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles();
      }
    }
  } catch (error) {
    console.error("刷新分支列表失败:", error);
    toastApiError(error, "刷新分支列表失败，请稍后重试");
  } finally {
    refreshingBranches.value = false;
  }
}

// 扫描项目中的 Dockerfile
async function scanDockerfiles(
  keepCurrentSelection = true,
  forceRefresh = false
) {
  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:2316",
  //     message: "scanDockerfiles started",
  //     data: {
  //       source_id: formData.value.source_id,
  //       git_url: formData.value.git_url,
  //       dockerfile_name: formData.value.dockerfile_name,
  //       branch: formData.value.branch,
  //       keep_current_selection: keepCurrentSelection,
  //       editing: !!editingPipeline.value,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "A",
  //   }),
  // }).catch(() => {});
  // #endregion
  const sourceId = formData.value.source_id;
  if (!sourceId && !formData.value.git_url) {
    dockerfilesError.value = "请先选择数据源或填写 Git 仓库地址";
    return;
  }

  // 保存当前的 dockerfile_name，避免被覆盖（编辑模式下必须保持）
  const savedDockerfileName = formData.value.dockerfile_name;
  // 判断是否是编辑模式（正在编辑已有流水线）
  const isEditing = !!editingPipeline.value || keepCurrentSelection;
  // 保存当前已扫描的列表，以便在扫描失败时恢复
  const previousDockerfiles = [...availableDockerfiles.value];

  scanningDockerfiles.value = true;
  dockerfilesError.value = "";
  // 注意：不要立即清空 availableDockerfiles，这样下拉框可以继续显示已保存的值
  // 只有在扫描成功后才更新列表

  try {
    // 获取 Git URL 和分支
    let gitUrl = formData.value.git_url;
    if (sourceId) {
      const source = gitSources.value.find((s) => s.source_id === sourceId);
      if (source) {
        gitUrl = source.git_url;
      }
    }

    if (!gitUrl) {
      dockerfilesError.value = "无法获取 Git 仓库地址";
      return;
    }

    const branch =
      formData.value.branch || branchesAndTags.value.default_branch || "main";

    if (!branch) {
      dockerfilesError.value = "请先选择分支";
      return;
    }

    // 使用缓存机制获取 Dockerfile 列表
    const dockerfilePaths = await getDockerfilesWithCache(
      async () => {
        // 调用 API 扫描 Dockerfile
        const response = await axios.post("/api/git-sources/scan-dockerfiles", {
          git_url: gitUrl,
          branch: branch,
          source_id: sourceId || null,
        });
        return response;
      },
      gitUrl,
      branch,
      sourceId || null,
      forceRefresh // 根据参数决定是否强制刷新
    );

    if (dockerfilePaths && dockerfilePaths.length > 0) {
      // 保存完整路径信息（包含路径和文件名）
      const dockerfileList = dockerfilePaths.map((path) => {
        const parts = path.split("/");
        return {
          path: path, // 完整路径，如 "frontend/Dockerfile"
          name: parts[parts.length - 1], // 文件名，如 "Dockerfile"
        };
      });

      // 按路径排序
      dockerfileList.sort((a, b) => {
        // 根目录的 Dockerfile 优先
        if (a.path === "Dockerfile") return -1;
        if (b.path === "Dockerfile") return 1;
        return a.path.localeCompare(b.path);
      });

      // 只有在成功扫描到结果时才更新列表
      availableDockerfiles.value = dockerfileList;
    } else {
      // 如果 API 返回成功但没有 dockerfiles，保持原列表（如果有）或设为空数组
      // 这样可以保留之前扫描的结果，或者如果是首次扫描则设为空
      if (availableDockerfiles.value.length === 0) {
        // 如果是首次扫描且没有结果，设为空数组
        availableDockerfiles.value = [];
      }
      // 否则保持原列表不变
    }

    // #region agent log (disabled - causes connection errors)
    // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({
    //     location: "PipelinePanel.vue:2402",
    //     message: "Dockerfiles scanned",
    //     data: {
    //       count: availableDockerfiles.value.length,
    //       saved_dockerfile_name: savedDockerfileName,
    //       available_paths: availableDockerfiles.value.map((df) => df.path),
    //       is_editing: isEditing,
    //       keep_current_selection: keepCurrentSelection,
    //     },
    //     timestamp: Date.now(),
    //     sessionId: "debug-session",
    //     runId: "run1",
    //     hypothesisId: "A",
    //   }),
    // }).catch(() => {});
    // #endregion

    // 在编辑模式下，始终保持原有的 dockerfile_name，不进行任何自动选择
    // 在新建模式下，只有在当前没有选择时才自动设置
    if (keepCurrentSelection && savedDockerfileName) {
      // 编辑模式或有已保存的选择：始终保持原选择（即使不在新扫描的列表中，下拉框也会显示它）
      formData.value.dockerfile_name = savedDockerfileName;
      const currentInList = availableDockerfiles.value.some(
        (df) => df.path === savedDockerfileName
      );
      // #region agent log (disabled - causes connection errors)
      // fetch(
      //   "http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e",
      //   {
      //     method: "POST",
      //     headers: { "Content-Type": "application/json" },
      //     body: JSON.stringify({
      //       location: "PipelinePanel.vue:2412",
      //       message:
      //         "Dockerfile name preserved (editing mode or has saved selection)",
      //       data: {
      //         dockerfile_name: savedDockerfileName,
      //         in_list: currentInList,
      //         is_editing: isEditing,
      //       },
      //       timestamp: Date.now(),
      //       sessionId: "debug-session",
      //       runId: "run1",
      //       hypothesisId: "A",
      //     }),
      //   }
      // ).catch(() => {});
      // #endregion
    } else if (availableDockerfiles.value.length > 0) {
      // 新建模式且没有保存的选择：自动选择第一个
      if (
        !savedDockerfileName ||
        savedDockerfileName === "" ||
        savedDockerfileName === "Dockerfile"
      ) {
        // 当前没有选择或只有默认值，自动选择第一个（优先选择根目录的 Dockerfile）
        const rootDockerfile = availableDockerfiles.value.find(
          (df) => df.path === "Dockerfile"
        );
        formData.value.dockerfile_name = rootDockerfile
          ? "Dockerfile"
          : availableDockerfiles.value[0].path;
        // #region agent log (disabled - causes connection errors)
        // fetch(
        //   "http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e",
        //   {
        //     method: "POST",
        //     headers: { "Content-Type": "application/json" },
        //     body: JSON.stringify({
        //       location: "PipelinePanel.vue:2420",
        //       message:
        //         "Dockerfile name auto-selected (new mode, no previous selection)",
        //       data: {
        //         new: formData.value.dockerfile_name,
        //         old: savedDockerfileName,
        //       },
        //       timestamp: Date.now(),
        //       sessionId: "debug-session",
        //       runId: "run1",
        //       hypothesisId: "A",
        //     }),
        //   }
        // ).catch(() => {});
        // #endregion
      } else {
        // 有保存的选择（非编辑模式），检查是否在新列表中，如果在则保持，否则选择第一个
        const currentInList = availableDockerfiles.value.some(
          (df) => df.path === savedDockerfileName
        );
        if (currentInList) {
          formData.value.dockerfile_name = savedDockerfileName;
        } else {
          const rootDockerfile = availableDockerfiles.value.find(
            (df) => df.path === "Dockerfile"
          );
          formData.value.dockerfile_name = rootDockerfile
            ? "Dockerfile"
            : availableDockerfiles.value[0].path;
        }
        // #region agent log (disabled - causes connection errors)
        // fetch(
        //   "http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e",
        //   {
        //     method: "POST",
        //     headers: { "Content-Type": "application/json" },
        //     body: JSON.stringify({
        //       location: "PipelinePanel.vue:2430",
        //       message:
        //         "Dockerfile name handled (new mode with previous selection)",
        //       data: {
        //         saved: savedDockerfileName,
        //         final: formData.value.dockerfile_name,
        //         in_list: currentInList,
        //       },
        //       timestamp: Date.now(),
        //       sessionId: "debug-session",
        //       runId: "run1",
        //       hypothesisId: "A",
        //     }),
        //   }
        // ).catch(() => {});
        // #endregion
      }
      // 扫描后重新加载服务（如果是用户主动切换 Dockerfile，传入 true）
      if (formData.value.use_project_dockerfile) {
        // 这里是在扫描 Dockerfile 后，可能是用户切换了 Dockerfile，传入 true 表示需要重新识别
        loadServices(true);
      }
    } else {
      // 没有扫描到 Dockerfile，如果当前选择不为空，保持原选择，否则设为默认值
      if (!savedDockerfileName) {
        formData.value.dockerfile_name = "Dockerfile";
      }
    }
  } catch (error) {
    console.error("扫描 Dockerfile 失败:", error);
    dockerfilesError.value =
      error.response?.data?.detail || "扫描 Dockerfile 失败";
    // 扫描失败时不清空列表，保持之前的列表（如果有），这样已保存的值还能显示
    // availableDockerfiles.value 保持原值
    // #region agent log (disabled - causes connection errors)
    // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({
    //     location: "PipelinePanel.vue:2404",
    //     message: "scanDockerfiles error",
    //     data: {
    //       error: error.message,
    //       response: error.response?.data,
    //       preserved_list_count: availableDockerfiles.value.length,
    //     },
    //     timestamp: Date.now(),
    //     sessionId: "debug-session",
    //     runId: "run1",
    //     hypothesisId: "A",
    //   }),
    // }).catch(() => {});
    // #endregion
  } finally {
    scanningDockerfiles.value = false;
    // #region agent log (disabled - causes connection errors)
    // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({
    //     location: "PipelinePanel.vue:2320",
    //     message: "scanDockerfiles completed",
    //     data: { final_dockerfile_name: formData.value.dockerfile_name },
    //     timestamp: Date.now(),
    //     sessionId: "debug-session",
    //     runId: "run1",
    //     hypothesisId: "A",
    //   }),
    // }).catch(() => {});
    // #endregion
  }
}

// 分支变化处理
function onBranchChanged() {
  // 如果切换到新分支且使用项目 Dockerfile，重新扫描 Dockerfile
  if (
    formData.value.use_project_dockerfile &&
    formData.value.branch &&
    formData.value.git_url
  ) {
    scanDockerfiles();
  }
}

// 加载服务列表（带防抖和去重）
async function loadServices(isDockerfileChanged = false) {
  if (!formData.value.git_url) {
    services.value = [];
    return Promise.resolve();
  }

  // 生成唯一标识，用于去重
  const currentKey = `${formData.value.git_url}_${formData.value.branch}_${
    formData.value.dockerfile_name
  }_${formData.value.source_id || ""}`;

  // 如果正在加载相同的服务配置，直接返回
  if (loadingServices.value && loadingServicesKey.value === currentKey) {
    console.log("服务正在加载中，跳过重复请求:", currentKey);
    return Promise.resolve();
  }

  // 清除之前的防抖定时器
  if (loadingServicesTimer.value) {
    clearTimeout(loadingServicesTimer.value);
    loadingServicesTimer.value = null;
  }

  // 判断是否是编辑模式
  const isEditing = !!editingPipeline.value;

  // 编辑模式下且未切换 Dockerfile：不显示加载状态，直接返回（已保存的配置会直接显示）
  if (isEditing && !isDockerfileChanged) {
    // 如果正在验证，直接返回，避免重复验证
    if (isVerifyingServices.value) {
      return Promise.resolve();
    }

    // 在后台异步加载服务列表进行验证，但不阻塞界面
    // 先返回，让界面立即显示已保存的配置
    setTimeout(async () => {
      // 防止重复验证
      if (isVerifyingServices.value) {
        return;
      }
      isVerifyingServices.value = true;

      try {
        await loadServicesInternal(isDockerfileChanged, currentKey);
        // 加载完成后验证已保存的服务是否还存在（只验证一次）
        if (
          formData.value.push_mode === "multi" &&
          formData.value.selected_services
        ) {
          const validServices = formData.value.selected_services.filter(
            (serviceName) => services.value.some((s) => s.name === serviceName)
          );
          if (
            validServices.length !== formData.value.selected_services.length
          ) {
            formData.value.selected_services = validServices;
            Object.keys(formData.value.service_push_config || {}).forEach(
              (serviceName) => {
                if (!services.value.some((s) => s.name === serviceName)) {
                  delete formData.value.service_push_config[serviceName];
                }
              }
            );
          }
        } else if (
          formData.value.push_mode === "single" &&
          formData.value.selected_service
        ) {
          if (
            !services.value.some(
              (s) => s.name === formData.value.selected_service
            )
          ) {
            formData.value.selected_service = "";
          }
        }
      } catch (error) {
        // 后台验证失败不影响已保存的配置显示
        console.warn("后台验证服务列表失败，但已保存的配置仍然有效:", error);
      } finally {
        isVerifyingServices.value = false;
      }
    }, 100);
    return Promise.resolve();
  }

  // 新建模式或切换 Dockerfile：使用防抖延迟加载，避免重复触发
  return new Promise((resolve) => {
    loadingServicesTimer.value = setTimeout(async () => {
      loadingServicesTimer.value = null;
      try {
        await loadServicesInternal(isDockerfileChanged, currentKey);
        resolve();
      } catch (error) {
        resolve(); // 即使出错也 resolve，避免阻塞
      }
    }, 300); // 300ms 防抖延迟
  });
}

// 内部加载服务列表函数
async function loadServicesInternal(
  isDockerfileChanged = false,
  currentKey = ""
) {
  if (!formData.value.git_url) {
    services.value = [];
    return Promise.resolve();
  }

  // 生成唯一标识
  const key =
    currentKey ||
    `${formData.value.git_url}_${formData.value.branch}_${
      formData.value.dockerfile_name
    }_${formData.value.source_id || ""}`;

  // 如果正在加载相同的服务配置，直接返回
  if (loadingServices.value && loadingServicesKey.value === key) {
    console.log("服务正在加载中，跳过重复请求:", key);
    return Promise.resolve();
  }

  // 判断是否是编辑模式
  const isEditing = !!editingPipeline.value;

  loadingServices.value = true;
  loadingServicesKey.value = key;
  servicesError.value = "";

  try {
    if (formData.value.use_project_dockerfile) {
      // 使用项目 Dockerfile
      const gitUrl = formData.value.git_url;
      const branch = formData.value.branch || null;
      const dockerfileName = formData.value.dockerfile_name || "Dockerfile";
      const sourceId = formData.value.source_id || null;

      // 使用缓存机制获取服务分析结果
      const servicesList = await getServiceAnalysisWithCache(
        async () => {
          const payload = {
            git_url: gitUrl,
            branch: branch,
            dockerfile_name: dockerfileName,
            source_id: sourceId,
          };
          return await axios.post("/api/parse-dockerfile-services", payload);
        },
        gitUrl,
        branch || "main",
        dockerfileName,
        sourceId,
        false // 不强制刷新，使用缓存
      );

      if (servicesList && servicesList.length > 0) {
        services.value = servicesList;

        // 编辑模式下：保持原有的服务选择和推送模式，只有在切换 Dockerfile 时才重新识别
        if (isEditing && !isDockerfileChanged) {
          // 编辑模式且未切换 Dockerfile：保持原有配置，不做任何自动初始化
          // 注意：服务验证已经在 loadServices 函数中完成，这里不再重复验证
          // 避免重复更新导致卡死
        } else {
          // 新建模式或切换 Dockerfile：自动初始化服务选择
          if (
            !formData.value.selected_services ||
            formData.value.selected_services.length === 0
          ) {
            if (formData.value.push_mode === "multi") {
              formData.value.selected_services = services.value.map(
                (s) => s.name
              );
              initializeServiceConfigs();
            }
          }
        }
      } else {
        services.value = [];
        // 如果没有服务，清空选择（但编辑模式下保持推送模式）
        if (!isEditing || isDockerfileChanged) {
          formData.value.selected_services = [];
          formData.value.selected_service = "";
        }
      }
    } else if (formData.value.template) {
      // 使用模板
      const res = await axios.get("/api/template-params", {
        params: {
          template: formData.value.template,
          project_type: formData.value.project_type,
        },
      });
      const templateServices = res.data.services || [];
      if (templateServices.length > 0) {
        services.value = templateServices;

        // 编辑模式下：保持原有的服务选择和推送模式
        if (isEditing && !isDockerfileChanged) {
          // 编辑模式且未切换模板：保持原有配置
          // 注意：服务验证已经在 loadServices 函数中完成，这里不再重复验证
          // 避免重复更新导致卡死
        } else {
          // 新建模式或切换模板：根据推送模式初始化
          if (
            !formData.value.selected_services ||
            formData.value.selected_services.length === 0
          ) {
            if (formData.value.push_mode === "single") {
              formData.value.selected_services = [];
            } else {
              formData.value.selected_services = services.value.map(
                (s) => s.name
              );
              initializeServiceConfigs();
            }
          }
        }
      } else {
        services.value = [];
        // 如果没有服务，清空选择（但编辑模式下保持推送模式）
        if (!isEditing || isDockerfileChanged) {
          formData.value.selected_services = [];
          formData.value.selected_service = "";
        }
      }
    } else {
      services.value = [];
    }
  } catch (error) {
    console.error("加载服务列表失败:", error);
    servicesError.value = error.response?.data?.detail || "加载服务列表失败";
    services.value = [];
    return Promise.reject(error);
  } finally {
    loadingServices.value = false;
    loadingServicesKey.value = ""; // 清除加载标识
  }

  return Promise.resolve();
}

// 初始化服务配置
function initializeServiceConfigs() {
  if (!formData.value.service_push_config) {
    formData.value.service_push_config = {};
  }
  formData.value.selected_services.forEach((serviceName) => {
    if (
      formData.value.service_push_config[serviceName] === undefined ||
      typeof formData.value.service_push_config[serviceName] === "boolean"
    ) {
      // 如果是布尔值（旧格式），转换为对象格式
      const oldValue = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === "boolean" ? oldValue : false,
        imageName: "",
        tag: "",
      };
    } else if (
      formData.value.service_push_config[serviceName] &&
      typeof formData.value.service_push_config[serviceName] === "object"
    ) {
      // 确保对象格式包含所有字段
      const config = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : "",
        tag: config.tag !== undefined ? config.tag : "",
      };
    }
  });
}

// 推送模式变化
function onPushModeChange() {
  if (formData.value.push_mode === "single") {
    formData.value.selected_services = [];
    formData.value.selected_service = "";
  } else {
    formData.value.selected_service = "";
    if (
      services.value.length > 0 &&
      (!formData.value.selected_services ||
        formData.value.selected_services.length === 0)
    ) {
      formData.value.selected_services = services.value.map((s) => s.name);
      initializeServiceConfigs();
    }
  }
}

// 切换服务选择
function toggleService(serviceName) {
  if (!formData.value.selected_services) {
    formData.value.selected_services = [];
  }
  const index = formData.value.selected_services.indexOf(serviceName);
  if (index > -1) {
    formData.value.selected_services.splice(index, 1);
    delete formData.value.service_push_config[serviceName];
  } else {
    formData.value.selected_services.push(serviceName);
    if (
      formData.value.service_push_config[serviceName] === undefined ||
      typeof formData.value.service_push_config[serviceName] === "boolean"
    ) {
      const oldValue = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === "boolean" ? oldValue : false,
        imageName: "",
        tag: "",
      };
    } else if (
      formData.value.service_push_config[serviceName] &&
      typeof formData.value.service_push_config[serviceName] === "object"
    ) {
      // 确保包含所有字段
      const config = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : "",
        tag: config.tag !== undefined ? config.tag : "",
      };
    }
  }
}

// 服务选择变化
function onServiceSelectionChange() {
  // 移除未选中服务的配置
  Object.keys(formData.value.service_push_config).forEach((serviceName) => {
    if (!formData.value.selected_services.includes(serviceName)) {
      delete formData.value.service_push_config[serviceName];
    }
  });
  // 为新选中的服务初始化配置
  formData.value.selected_services.forEach((serviceName) => {
    if (
      formData.value.service_push_config[serviceName] === undefined ||
      typeof formData.value.service_push_config[serviceName] === "boolean"
    ) {
      const oldValue = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === "boolean" ? oldValue : false,
        imageName: "",
        tag: "",
      };
    } else if (
      formData.value.service_push_config[serviceName] &&
      typeof formData.value.service_push_config[serviceName] === "object"
    ) {
      // 确保包含所有字段
      const config = formData.value.service_push_config[serviceName];
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : "",
        tag: config.tag !== undefined ? config.tag : "",
      };
    }
  });
}

// 全选服务
function selectAllServices() {
  if (services.value.length > 0) {
    formData.value.selected_services = services.value.map((s) => s.name);
    initializeServiceConfigs();
  }
}

// 全不选服务
function deselectAllServices() {
  formData.value.selected_services = [];
  formData.value.service_push_config = {};
}

// 移除服务
function removeService(serviceName) {
  const index = formData.value.selected_services.indexOf(serviceName);
  if (index > -1) {
    formData.value.selected_services.splice(index, 1);
    delete formData.value.service_push_config[serviceName];
  }
}

// 获取服务配置对象（确保返回对象格式，包含 push、imageName 和 tag 字段）
function getServiceConfig(serviceName) {
  if (!formData.value.service_push_config) {
    formData.value.service_push_config = {};
  }
  // 如果是布尔值（旧格式），转换为对象格式
  if (
    formData.value.service_push_config[serviceName] === undefined ||
    typeof formData.value.service_push_config[serviceName] === "boolean"
  ) {
    const oldValue = formData.value.service_push_config[serviceName];
    formData.value.service_push_config[serviceName] = {
      push: typeof oldValue === "boolean" ? oldValue : false,
      imageName: "",
      tag: "",
    };
  } else if (
    formData.value.service_push_config[serviceName] &&
    typeof formData.value.service_push_config[serviceName] === "object"
  ) {
    // 确保包含所有字段
    const config = formData.value.service_push_config[serviceName];
    formData.value.service_push_config[serviceName] = {
      push: config.push !== undefined ? config.push : false,
      imageName: config.imageName !== undefined ? config.imageName : "",
      tag: config.tag !== undefined ? config.tag : "",
    };
  }
  return formData.value.service_push_config[serviceName];
}

// 获取服务的默认镜像名称（基于全局镜像名称前缀 + 服务名）
function getServiceDefaultImageName(serviceName) {
  if (!serviceName) {
    return formData.value.image_name || "myapp/demo";
  }

  let prefix = formData.value.image_name || "myapp/demo";

  // 去除前缀末尾的斜杠，避免出现双斜杠
  prefix = prefix.replace(/\/+$/, "");

  // 如果前缀已经以服务名结尾，直接返回前缀（避免重复拼接）
  // 检查格式：prefix/serviceName 或 prefix//serviceName 等
  const normalizedPrefix = prefix.replace(/\/+$/, "");
  if (
    normalizedPrefix.endsWith(`/${serviceName}`) ||
    normalizedPrefix === serviceName
  ) {
    return normalizedPrefix;
  }

  // 如果前缀就是服务名本身，直接返回
  if (prefix === serviceName) {
    return prefix;
  }

  // 否则拼接服务名（确保只有一个斜杠）
  return `${prefix}/${serviceName}`;
}

// 服务镜像名输入框失焦处理
function onServiceImageNameBlur(serviceName) {
  const config = getServiceConfig(serviceName);
  // 如果用户清空了自定义镜像名，确保使用默认值
  if (!config.imageName || !config.imageName.trim()) {
    config.imageName = "";
  }
}

// 恢复默认镜像名
function resetServiceImageName(serviceName) {
  const config = getServiceConfig(serviceName);
  config.imageName = "";
}

// 规范化服务推送配置（将旧格式的布尔值转换为新格式的对象，保留 push、imageName 和 tag 字段）
function normalizeServicePushConfig(config) {
  if (!config || typeof config !== "object") {
    return {};
  }
  const normalized = {};
  Object.keys(config).forEach((serviceName) => {
    const value = config[serviceName];
    // 如果是布尔值（旧格式），转换为对象格式
    if (typeof value === "boolean") {
      normalized[serviceName] = {
        push: value,
        imageName: "",
        tag: "",
      };
    } else if (value && typeof value === "object") {
      // 已经是对象格式，保留所有字段
      normalized[serviceName] = {
        push: value.push !== undefined ? value.push : false,
        imageName: value.imageName !== undefined ? value.imageName : "",
        tag: value.tag !== undefined ? value.tag : "",
      };
    }
  });
  return normalized;
}

/** 多阶段模式下任一分服务是否开启推送（用于同步顶层 pipeline.push） */
function anyServicePushEnabled(servicePushConfig) {
  if (!servicePushConfig || typeof servicePushConfig !== "object") {
    return false;
  }
  return Object.values(servicePushConfig).some(
    (cfg) => cfg && typeof cfg === "object" && cfg.push === true
  );
}

// 加载资源包列表
async function loadResourcePackages() {
  try {
    const res = await axios.get("/api/resource-packages");
    resourcePackages.value = res.data.packages || [];

    // 编辑模式下：确保已保存的资源包配置中的 target_path 有默认值
    // 如果某个已保存的资源包配置没有 target_path 或为空，使用资源包名称作为默认值（与分步构建一致）
    if (editingPipeline.value && formData.value.resource_package_configs) {
      formData.value.resource_package_configs.forEach((config) => {
        if (!config.target_path || config.target_path.trim() === "") {
          const pkg = resourcePackages.value.find(
            (p) => p.package_id === config.package_id
          );
          if (pkg && pkg.name) {
            // 如果路径为空，使用资源包名称（与分步构建一致）
            config.target_path = pkg.name;
          } else {
            config.target_path = "resources";
          }
        }
      });
    }
  } catch (error) {
    console.error("加载资源包列表失败:", error);
  }
}

// 获取资源包名称
function getResourcePackageName(packageId) {
  const pkg = resourcePackages.value.find((p) => p.package_id === packageId);
  return pkg ? pkg.name : packageId;
}

// 移除资源包
function removeResourcePackage(index) {
  formData.value.resource_package_configs.splice(index, 1);
}

// 检查资源包是否已选择
function isResourcePackageSelected(packageId) {
  return formData.value.resource_package_configs.some(
    (pkg) => pkg.package_id === packageId
  );
}

// 切换资源包选择
function toggleResourcePackage(pkg) {
  const index = formData.value.resource_package_configs.findIndex(
    (p) => p.package_id === pkg.package_id
  );
  if (index > -1) {
    // 取消选择：移除配置
    formData.value.resource_package_configs.splice(index, 1);
  } else {
    // 选择：添加配置，使用默认路径（资源包名称，与分步构建一致）
    const defaultPath = pkg.name || "resources";
    formData.value.resource_package_configs.push({
      package_id: pkg.package_id,
      target_path: defaultPath, // 默认使用资源包名称作为路径，与分步构建一致
    });
  }
}

// 获取资源包配置
function getResourcePackageConfig(packageId) {
  let config = formData.value.resource_package_configs.find(
    (p) => p.package_id === packageId
  );
  if (!config) {
    // 如果配置不存在，根据资源包信息创建默认配置
    const pkg = resourcePackages.value.find((p) => p.package_id === packageId);
    // 编辑模式下，如果已有保存的配置，不应该自动创建新配置
    // 只有在用户主动选择资源包时才创建配置
    // 这里返回一个临时对象，但不添加到列表中（由 toggleResourcePackage 处理）
    return {
      package_id: packageId,
      target_path: pkg ? pkg.name || "resources" : "resources", // 默认使用资源包名称作为路径
    };
  }
  return config;
}

// 更新资源包目标路径
function updateResourcePackagePath(packageId, targetPath) {
  const config = formData.value.resource_package_configs.find(
    (p) => p.package_id === packageId
  );
  if (config) {
    config.target_path = targetPath || "";
  } else {
    // 如果配置不存在，创建新配置
    formData.value.resource_package_configs.push({
      package_id: packageId,
      target_path: targetPath || "",
    });
  }
}

// Dockerfile 来源变化处理
async function onDockerfileSourceChange() {
  // #region agent log (disabled - causes connection errors)
  // fetch("http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({
  //     location: "PipelinePanel.vue:2744",
  //     message: "Dockerfile source changed",
  //     data: {
  //       use_project_dockerfile: formData.value.use_project_dockerfile,
  //       template: formData.value.template,
  //       dockerfile_name: formData.value.dockerfile_name,
  //       git_url: formData.value.git_url,
  //       branch: formData.value.branch,
  //     },
  //     timestamp: Date.now(),
  //     sessionId: "debug-session",
  //     runId: "run1",
  //     hypothesisId: "D",
  //   }),
  // }).catch(() => {});
  // #endregion
  if (formData.value.use_project_dockerfile) {
    // 使用项目 Dockerfile 时，清空模板
    formData.value.template = "";
    // 如果有数据源、分支和 Dockerfile，尝试加载 Dockerfile 内容
    if (
      formData.value.source_id &&
      formData.value.branch &&
      formData.value.dockerfile_name
    ) {
      try {
        await loadDockerfileFromRepo();
      } catch (error) {
        // 如果加载失败，清空编辑器
        dockerfileContentText.value = "";
      }
    } else {
      // 如果没有完整信息，清空编辑器
      dockerfileContentText.value = "";
    }
    // 如果有分支和 Dockerfile，重新加载服务（服务列表依赖于 Dockerfile）
    if (
      formData.value.git_url &&
      formData.value.branch &&
      formData.value.dockerfile_name
    ) {
      // Dockerfile 来源变化是用户主动切换，需要重新识别服务
      loadServices(true);
    } else if (formData.value.git_url && formData.value.branch) {
      // 如果有分支但没有 Dockerfile，先扫描 Dockerfile（扫描完成后会自动加载服务）
      scanDockerfiles();
    }
  } else {
    // 使用模板时，清空 Dockerfile 名称和内容
    formData.value.dockerfile_name = "Dockerfile";
    dockerfileContentText.value = "";
    // 如果选择了模板，加载模板内容并重新加载服务（切换到模板是用户主动切换）
    if (formData.value.template) {
      await onTemplateChange();
    }
  }
}

// 模板变化处理
async function onTemplateChange() {
  // 选择模板时，确保 use_project_dockerfile 为 false
  if (formData.value.template) {
    formData.value.use_project_dockerfile = false;
    // 加载模板的 Dockerfile 内容
    try {
      const res = await axios.get("/api/templates", {
        params: {
          name: formData.value.template,
          project_type: formData.value.project_type,
        },
      });
      if (res.data && res.data.content) {
        dockerfileContentText.value = res.data.content;
      }
    } catch (error) {
      console.error("加载模板内容失败:", error);
      // 如果加载失败，清空编辑器
      dockerfileContentText.value = "";
    }
    // 编辑模式下不自动加载，需要用户手动点击加载按钮
    // 新建模式下可以自动加载（通过判断 editingPipeline）
    if (!editingPipeline.value) {
      loadServices(true);
    }
  } else {
    // 清空模板时，清空 Dockerfile 内容
    dockerfileContentText.value = "";
    // 清空模板时，如果使用项目 Dockerfile 且有分支，重新加载服务（切换到项目 Dockerfile 是用户主动切换）
    // 编辑模式下不自动加载，需要用户手动点击加载按钮
    if (
      formData.value.use_project_dockerfile &&
      formData.value.git_url &&
      formData.value.branch &&
      !editingPipeline.value
    ) {
      loadServices(true);
    }
  }
}

// 根据项目类型过滤模板
const filteredTemplates = computed(() => {
  if (!formData.value.project_type) {
    return [];
  }
  return templates.value.filter(
    (t) => t.project_type === formData.value.project_type
  );
});

// 构建配置JSON（基于统一的任务配置结构）
const buildConfigJson = computed(() => {
  // 构建服务推送配置（与StepBuildPanel格式一致）
  const servicePushConfig = {};
  if (
    formData.value.selected_services &&
    formData.value.selected_services.length > 0
  ) {
    if (formData.value.push_mode === "multi") {
      // 多服务模式：处理所有启用的服务
      formData.value.selected_services.forEach((serviceName) => {
        const config = getServiceConfig(serviceName);
        const customImageName = config.imageName && config.imageName.trim();
        const finalImageName =
          customImageName || getServiceDefaultImageName(serviceName);
        const finalTag =
          (config.tag && config.tag.trim()) || formData.value.tag || "latest";

        servicePushConfig[serviceName] = {
          push: config.push || false,
          imageName: finalImageName,
          tag: finalTag,
        };
      });
    } else if (formData.value.push_mode === "single") {
      // 单服务模式：只处理第一个服务
      const firstService = formData.value.selected_services[0];
      if (firstService) {
        const config = getServiceConfig(firstService);
        // 单服务模式使用全局镜像名和标签
        servicePushConfig[firstService] = {
          push: config.push || false,
          imageName: formData.value.image_name || "",
          tag: formData.value.tag || "latest",
        };
      }
    }
  }

  const config = {
    git_url: formData.value.git_url || "",
    image_name: formData.value.image_name || "",
    tag: formData.value.tag || "latest",
    branch: formData.value.branch || null,
    project_type: formData.value.project_type || "jar",
    template: formData.value.template || "",
    template_params: formData.value.template_params || {},
    should_push: formData.value.push || false,
    sub_path: formData.value.sub_path || null,
    use_project_dockerfile: formData.value.use_project_dockerfile !== false,
    dockerfile_name: formData.value.dockerfile_name || "Dockerfile",
    dockerfile_content: formData.value.dockerfile_content || null,
    source_id: formData.value.source_id || null,
    selected_services: formData.value.selected_services || [],
    service_push_config:
      Object.keys(servicePushConfig).length > 0
        ? servicePushConfig
        : formData.value.service_push_config || {},
    service_template_params: formData.value.service_template_params || {},
    push_mode: formData.value.push_mode || "multi",
    resource_package_configs: formData.value.resource_package_configs || [],
  };

  // 移除null值和空值（保留false和0）
  // 注意：多阶段相关配置（push_mode、selected_services、service_push_config、service_template_params）需要保留
  const multiStageKeys = [
    "push_mode",
    "selected_services",
    "service_push_config",
    "service_template_params",
  ];
  Object.keys(config).forEach((key) => {
    // 多阶段相关配置始终保留
    if (multiStageKeys.includes(key)) {
      return;
    }

    if (
      config[key] === null ||
      config[key] === "" ||
      (Array.isArray(config[key]) && config[key].length === 0) ||
      (typeof config[key] === "object" &&
        !Array.isArray(config[key]) &&
        Object.keys(config[key]).length === 0)
    ) {
      delete config[key];
    }
  });

  return JSON.stringify(config, null, 2);
});

async function copyBuildConfigJson() {
  const text = buildConfigJson.value;
  const success = await copyToClipboard(text);
  if (success) {
    toastSuccess("构建配置JSON已复制到剪贴板");
  } else {
    toastError("自动复制失败，请手动选择并复制文本（已自动选中）");
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

async function deletePipeline(pipeline) {
  if (!(await showConfirm({ message: `确定要删除流水线"${pipeline.name}"吗？`, danger: true }))) {
    return;
  }

  try {
    await axios.delete(`/api/pipelines/${pipeline.pipeline_id}`);
    const onDetailOfDeleted =
      route.name === "pipeline-detail" &&
      route.params.pipelineId === pipeline.pipeline_id;
    if (onDetailOfDeleted) {
      await goToPipelineList(router);
    } else {
      loadPipelines();
    }
    toastSuccess("流水线已删除");
  } catch (error) {
    console.error("删除流水线失败:", error);
    toastApiError(error, "删除流水线失败");
  }
}

// 手动运行流水线（带防抖）
async function runPipeline(pipeline) {
  const pipelineId = pipeline.pipeline_id;

  // 清除之前的防抖定时器
  if (debounceTimers.value[pipelineId]) {
    clearTimeout(debounceTimers.value[pipelineId]);
  }

  // 设置防抖定时器（500ms）
  debounceTimers.value[pipelineId] = setTimeout(async () => {
    // 保存要触发的流水线
    manualRunPipeline.value = pipeline;
    manualRunSelectedBranch.value = pipeline.branch || ""; // 默认使用配置的分支

    // 调试日志：初始化时的值
    console.log("🔍 runPipeline 初始化:");
    console.log("   - pipeline.branch:", pipeline.branch);
    console.log(
      "   - manualRunSelectedBranch.value:",
      manualRunSelectedBranch.value
    );

    // 加载可用分支列表
    await loadBranchesForManualRun(pipeline);

    // 调试日志：加载分支列表后的值
    console.log("🔍 加载分支列表后:");
    console.log(
      "   - manualRunSelectedBranch.value:",
      manualRunSelectedBranch.value
    );
    console.log("   - manualRunBranches.value:", manualRunBranches.value);

    // 显示分支选择模态框
    showManualRunModal.value = true;

    delete debounceTimers.value[pipelineId];
  }, 500);
}

// 加载手动触发可用的分支列表
async function loadBranchesForManualRun(pipeline, forceRefresh = false) {
  loadingManualRunBranches.value = true;

  try {
    // 如果不是强制刷新，优先从gitSources中获取分支列表
    if (!forceRefresh) {
      if (pipeline.source_id) {
        const source = gitSources.value.find(
          (s) => s.source_id === pipeline.source_id
        );
        if (source && source.branches && source.branches.length > 0) {
          manualRunBranches.value = [...source.branches];
          loadingManualRunBranches.value = false;
          return;
        }
      }

      // 如果没有source_id，尝试通过git_url查找
      if (pipeline.git_url) {
        const source = gitSources.value.find(
          (s) => s.git_url === pipeline.git_url
        );
        if (source && source.branches && source.branches.length > 0) {
          manualRunBranches.value = [...source.branches];
          loadingManualRunBranches.value = false;
          return;
        }
      }
    }

    // 强制刷新或缓存中没有时，从API获取分支列表
    if (pipeline.source_id) {
      // 强制刷新时，添加refresh参数从Git仓库拉取最新分支
      const params = forceRefresh ? { refresh: true } : {};
      const res = await axios.get(
        `/api/git-sources/${pipeline.source_id}/branches`,
        { params }
      );
      if (res.data && res.data.branches) {
        manualRunBranches.value = res.data.branches;
        // 更新gitSources中的分支列表
        const source = gitSources.value.find(
          (s) => s.source_id === pipeline.source_id
        );
        if (source) {
          source.branches = res.data.branches;
        }
      }
    } else if (pipeline.git_url) {
      // 如果没有source_id但有git_url，尝试通过git_url获取
      try {
        const params = forceRefresh
          ? { git_url: pipeline.git_url, refresh: true }
          : { git_url: pipeline.git_url };
        const res = await axios.get("/api/git-sources", { params });
        if (res.data && res.data.length > 0 && res.data[0].branches) {
          manualRunBranches.value = res.data[0].branches;
        }
      } catch (error) {
        console.error("通过git_url获取分支列表失败:", error);
      }
    }

    // 如果还是没有分支，至少显示配置的分支
    if (manualRunBranches.value.length === 0 && pipeline.branch) {
      manualRunBranches.value = [pipeline.branch];
    }
  } catch (error) {
    console.error("加载分支列表失败:", error);
    // 如果加载失败，至少显示配置的分支
    if (pipeline.branch) {
      manualRunBranches.value = [pipeline.branch];
    }
  } finally {
    loadingManualRunBranches.value = false;
  }
}

// 刷新手动触发的分支列表（从Git仓库拉取最新分支）
async function refreshManualRunBranches() {
  if (!manualRunPipeline.value) {
    return;
  }

  loadingManualRunBranches.value = true;

  try {
    const pipeline = manualRunPipeline.value;

    // 使用 verify-git-repo API 获取最新分支列表（强制刷新）
    const gitUrl = pipeline.git_url;
    const sourceId = pipeline.source_id || null;

    // 清除缓存，强制从Git仓库拉取
    if (sourceId) {
      clearGitCache(gitUrl, sourceId);
    } else {
      clearGitCache(gitUrl, null);
    }

    // 调用 verify-git-repo API 获取最新分支列表
    const response = await axios.post("/api/verify-git-repo", {
      git_url: gitUrl,
      source_id: sourceId,
    });

    if (response.data && response.data.branches) {
      manualRunBranches.value = response.data.branches || [];

      // 更新gitSources中的分支列表缓存
      if (sourceId) {
        const source = gitSources.value.find((s) => s.source_id === sourceId);
        if (source) {
          source.branches = response.data.branches;
          source.tags = response.data.tags || [];
          source.default_branch = response.data.default_branch || null;
        }
      }

      // 更新本地缓存
      if (response.data.branches || response.data.tags) {
        setGitCache(gitUrl, sourceId, {
          branches: response.data.branches || [],
          tags: response.data.tags || [],
          default_branch: response.data.default_branch || null,
        });
      }
    } else {
      // 如果API返回没有分支，至少显示配置的分支
      if (pipeline.branch) {
        manualRunBranches.value = [pipeline.branch];
      } else {
        manualRunBranches.value = [];
      }
    }
  } catch (error) {
    console.error("刷新分支列表失败:", error);
    const errorMsg =
      error.response?.data?.detail ||
      error.message ||
      "刷新分支列表失败，请稍后重试";
    toastInfo(errorMsg);

    // 如果刷新失败，至少显示配置的分支
    if (manualRunPipeline.value && manualRunPipeline.value.branch) {
      manualRunBranches.value = [manualRunPipeline.value.branch];
    } else {
      manualRunBranches.value = [];
    }
  } finally {
    loadingManualRunBranches.value = false;
  }
}

// 确认手动触发
async function confirmManualRun() {
  // 调试日志：检查选择的分支
  console.log("🔍 confirmManualRun 开始:");
  console.log(
    "   - manualRunSelectedBranch.value:",
    manualRunSelectedBranch.value
  );
  console.log(
    "   - manualRunSelectedBranch.value类型:",
    typeof manualRunSelectedBranch.value
  );
  console.log(
    "   - manualRunSelectedBranch.value长度:",
    manualRunSelectedBranch.value?.length
  );
  console.log("   - manualRunPipeline.value:", manualRunPipeline.value);
  console.log(
    "   - manualRunPipeline.value.branch:",
    manualRunPipeline.value?.branch
  );

  if (!manualRunSelectedBranch.value) {
    toastError("请选择分支");
    return;
  }

  const pipeline = manualRunPipeline.value;
  const pipelineId = pipeline.pipeline_id;

  // 重要：在关闭模态框之前，先保存选择的分支值
  const selectedBranch = manualRunSelectedBranch.value;

  // 调试日志：确认要发送的分支
  console.log("🔍 准备发送请求:");
  console.log("   - 选择的分支:", selectedBranch);
  console.log("   - 流水线默认分支:", pipeline.branch);
  console.log("   - 是否相同:", selectedBranch === pipeline.branch);

  // 显示确认对话框，提示排队信息
  const queueInfo =
    pipeline.queue_length > 0
      ? `\n当前已有 ${pipeline.queue_length} 个任务在排队`
      : "";
  const runningInfo =
    pipeline.current_task_status === "running" ||
    pipeline.current_task_status === "pending"
      ? "\n当前有任务正在运行，新任务将加入队列"
      : "";

  if (!(await showConfirm({ message: `确定要运行流水线 "${pipeline.name}" 吗？\n分支: ${selectedBranch}${queueInfo}${runningInfo}` }))) {
    return;
  }

  // 关闭模态框（会清空 manualRunSelectedBranch.value，所以要先保存）
  closeManualRunModal();

  running.value = pipelineId;
  try {
    // 调试日志：检查前端发送的分支参数
    console.log("🔍 前端发送请求:");
    console.log("   - 保存的分支值:", selectedBranch);
    console.log(
      "   - manualRunSelectedBranch.value (已清空):",
      manualRunSelectedBranch.value
    );
    console.log("   - pipelineId:", pipelineId);
    console.log("   - 请求体:", { branch: selectedBranch });

    // 调用API时传递分支参数（使用保存的值，而不是 manualRunSelectedBranch.value）
    const res = await axios.post(`/api/pipelines/${pipelineId}/run`, {
      branch: selectedBranch,
    });

    // 调试日志：检查后端返回的分支
    console.log("🔍 后端返回响应:");
    console.log("   - res.data.branch:", res.data.branch);
    console.log("   - res.data:", res.data);

    // 检查任务状态
    if (res.data.status === "queued") {
      // 任务已加入队列
      const queueInfo = res.data.queue_length
        ? `（队列位置: ${res.data.queue_length}）`
        : "";
      toastSuccess(`流水线已加入队列！${queueInfo}\n分支: ${
          res.data.branch || selectedBranch
        }`);
      // 发送事件通知任务管理页面刷新（队列中的任务也会创建pending状态的任务）
      if (res.data.task_id) {
        window.dispatchEvent(
          new CustomEvent("taskCreated", {
            detail: {
              task_id: res.data.task_id,
              task_type: "pipeline",
              pipeline_name: pipeline.name,
            },
          })
        );
      }
    } else if (res.data.task_id) {
      // 任务立即运行
      toastSuccess(`流水线已启动！\n任务 ID: ${res.data.task_id}\n分支: ${
          res.data.branch || selectedBranch
        }`);
      // 发送事件通知任务管理页面刷新
      window.dispatchEvent(
        new CustomEvent("taskCreated", {
          detail: {
            task_id: res.data.task_id,
            task_type: "pipeline",
            pipeline_name: pipeline.name,
          },
        })
      );
    }
    // 刷新流水线列表（更新触发次数和时间）
    loadPipelines();
  } catch (error) {
    console.error("运行流水线失败:", error);
    const errorMsg = error.response?.data?.detail || "运行流水线失败";

    // 如果是409冲突（已有任务运行），说明任务已加入队列
    if (error.response?.status === 409) {
      toastSuccess(`流水线已加入队列！\n${errorMsg}`);
      loadPipelines();
    } else {
      toastInfo(errorMsg);
    }
  } finally {
    running.value = null;
  }
}

// 处理分支选择变化
function handleBranchChange(e) {
  const newValue = e.target.value;
  console.log("🔍 选择框change事件:");
  console.log("   - 新值:", newValue);
  console.log(
    "   - manualRunSelectedBranch (ref对象):",
    manualRunSelectedBranch
  );
  // v-model 已经自动更新了 manualRunSelectedBranch.value，这里只记录日志
  // 使用 nextTick 确保 v-model 已经更新
  setTimeout(() => {
    console.log(
      "   - manualRunSelectedBranch.value (更新后):",
      manualRunSelectedBranch.value
    );
  }, 0);
}

// 关闭手动触发模态框
function closeManualRunModal() {
  showManualRunModal.value = false;
  manualRunPipeline.value = null;
  manualRunSelectedBranch.value = "";
  manualRunBranches.value = [];
  loadingManualRunBranches.value = false;
}

function showWebhookUrl(pipeline) {
  const baseUrl = window.location.origin;
  const token = pipeline.webhook_token || "未设置";
  webhookUrl.value =
    token !== "未设置"
      ? `${baseUrl}/api/webhook/${token}`
      : "请先设置 Webhook Token";
  showWebhookModal.value = true;
}

// 重新生成 Webhook Token
async function regenerateWebhookToken() {
  if (await showConfirm({ message: "确定要重新生成 Webhook Token 吗？重新生成后需要更新 Git 平台的 Webhook URL。" })) {
    // 生成新的 UUID
    formData.value.webhook_token = generateUUID();
  }
}

// 重新生成 Webhook Secret
async function regenerateWebhookSecret() {
  if (await showConfirm({ message: "确定要重新生成 Webhook 密钥吗？重新生成后需要更新 Git 平台的 Webhook Secret。" })) {
    // 生成新的 UUID
    formData.value.webhook_secret = generateUUID();
  }
}

// 生成 UUID（简单版本）
function generateUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

async function copyWebhookUrl() {
  const el = webhookUrlInput.value;
  if (el) {
    const url = typeof el === 'string' ? el : el.value;
    const success = await copyToClipboard(url);
    if (success) {
      toastSuccess("Webhook URL 已复制到剪贴板");
    } else {
      toastError("Webhook URL 复制失败");
    }
  }
}

async function copyTextWithFeedback(text, label, event) {
  if (!text) return;

  const success = await copyToClipboard(text);
  if (success) {
    const btn = event?.target?.closest?.("button");
    if (btn) {
      const originalHTML = btn.innerHTML;
      btn.innerHTML =
        '<i class="fas fa-check" style="font-size: 0.7rem; color: green;"></i>';
      setTimeout(() => {
        btn.innerHTML = originalHTML;
      }, 1000);
    }
  } else {
    console.error("复制失败");
    toastError(`复制${label}失败`);
  }
}

// 项目类型处理（从缓存加载，如果没有则从API加载）
async function loadProjectTypes() {
  projectTypesList.value = await getProjectTypes();
}

function formatGitUrl(url) {
  if (!url) return "";
  // 简化显示
  return url.replace("https://", "").replace("http://", "").replace(".git", "");
}

function formatTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  const now = new Date();
  const diff = (now - date) / 1000; // 秒

  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;

  return date.toLocaleDateString("zh-CN");
}

function formatDateTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);

  // 格式：YYYY-MM-DD HH:mm:ss
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

function openPipelinePermission(pipeline) {
  permissionPipeline.value = pipeline;
  permissionDialogOpen.value = true;
}

function showHistory(pipeline) {
  const id = pipeline.pipeline_id || pipeline.id;
  if (!id) {
    toastError("无法获取流水线 ID");
    return;
  }
  router.push({
    name: "pipeline-history",
    params: { pipelineId: id },
  });
}

// 判断最后构建是否正在运行
function isLastBuildRunning(pipeline) {
  return (
    pipeline.last_build &&
    (pipeline.last_build.status === "running" ||
      pipeline.last_build.status === "pending")
  );
}

// 显示多服务配置模态框
async function showMultiServiceConfig(pipeline) {
  let pipelineToUse = pipeline;
  try {
    const res = await axios.get(`/api/pipelines/${pipeline.pipeline_id}`);
    if (res.data) {
      pipelineToUse = res.data;
    }
  } catch (error) {
    console.warn("获取流水线详情失败，使用列表数据:", error);
  }

  console.log("showMultiServiceConfig - pipelineToUse:", {
    pipeline_id: pipelineToUse.pipeline_id,
    push_mode: pipelineToUse.push_mode,
    selected_services: pipelineToUse.selected_services,
    service_push_config: pipelineToUse.service_push_config,
  });

  multiServiceConfigPipeline.value = pipelineToUse;

  // 初始化表单数据
  multiServiceFormData.value = {
    push_mode: pipelineToUse.push_mode || "multi",
    selected_services: pipelineToUse.selected_services
      ? [...pipelineToUse.selected_services]
      : [],
    service_push_config: pipelineToUse.service_push_config
      ? JSON.parse(JSON.stringify(pipelineToUse.service_push_config))
      : {},
    global_image_name: pipelineToUse.image_name || "",
    global_tag: pipelineToUse.tag || "latest",
  };

  // 确保每个服务都有配置对象
  const isSingleMode = multiServiceFormData.value.push_mode === "single";

  // 如果是单服务模式但没有服务，自动添加一个默认服务
  if (
    isSingleMode &&
    multiServiceFormData.value.selected_services.length === 0
  ) {
    const defaultServiceName = "service1";
    multiServiceFormData.value.selected_services.push(defaultServiceName);
    if (!multiServiceFormData.value.service_push_config[defaultServiceName]) {
      multiServiceFormData.value.service_push_config[defaultServiceName] = {
        enabled: false, // 单服务模式下默认禁用
        push: false,
        imageName: "",
        tag: "",
      };
    }
  }

  multiServiceFormData.value.selected_services.forEach((serviceName) => {
    if (!multiServiceFormData.value.service_push_config[serviceName]) {
      multiServiceFormData.value.service_push_config[serviceName] = {
        enabled: isSingleMode ? false : true, // 单服务模式下默认禁用
        push: false,
        imageName: "",
        tag: "",
      };
    } else if (
      typeof multiServiceFormData.value.service_push_config[serviceName] ===
      "boolean"
    ) {
      // 兼容旧格式
      const oldValue =
        multiServiceFormData.value.service_push_config[serviceName];
      multiServiceFormData.value.service_push_config[serviceName] = {
        enabled: isSingleMode ? false : true, // 单服务模式下默认禁用
        push: oldValue,
        imageName: "",
        tag: "",
      };
    } else {
      // 确保enabled字段存在
      if (
        multiServiceFormData.value.service_push_config[serviceName].enabled ===
        undefined
      ) {
        multiServiceFormData.value.service_push_config[serviceName].enabled =
          isSingleMode ? false : true;
      } else if (isSingleMode) {
        // 单服务模式下，强制设置为禁用状态
        multiServiceFormData.value.service_push_config[
          serviceName
        ].enabled = false;
      }
    }
  });

  showMultiServiceConfigModal.value = true;
}

// 监听推送模式变化
watch(
  () => multiServiceFormData.value.push_mode,
  (newMode, oldMode) => {
    if (newMode === "single") {
      // 单服务模式下，保留所有服务但将所有服务设置为禁用状态
      if (multiServiceFormData.value.selected_services.length === 0) {
        // 如果没有服务，添加一个默认服务
        const defaultServiceName = "service1";
        multiServiceFormData.value.selected_services.push(defaultServiceName);
        if (
          !multiServiceFormData.value.service_push_config[defaultServiceName]
        ) {
          multiServiceFormData.value.service_push_config[defaultServiceName] = {
            enabled: false, // 单服务模式下默认禁用
            push: false,
            imageName: "",
            tag: "",
          };
        } else {
          // 确保设置为禁用状态
          multiServiceFormData.value.service_push_config[
            defaultServiceName
          ].enabled = false;
        }
      } else {
        // 保留所有服务，但将所有服务设置为禁用状态
        multiServiceFormData.value.selected_services.forEach((serviceName) => {
          if (!multiServiceFormData.value.service_push_config[serviceName]) {
            multiServiceFormData.value.service_push_config[serviceName] = {
              enabled: false, // 单服务模式下禁用
              push: false,
              imageName: "",
              tag: "",
            };
          } else {
            // 设置为禁用状态，保留其他配置
            multiServiceFormData.value.service_push_config[
              serviceName
            ].enabled = false;
          }
        });
      }
    } else if (newMode === "multi" && oldMode === "single") {
      // 从单服务模式切换到多服务模式，保留所有服务，但保持禁用状态（用户可以手动启用）
      // 确保每个服务都有配置对象，enabled字段保持当前状态（禁用）
      multiServiceFormData.value.selected_services.forEach((serviceName) => {
        if (!multiServiceFormData.value.service_push_config[serviceName]) {
          multiServiceFormData.value.service_push_config[serviceName] = {
            enabled: false, // 从单服务切换过来时保持禁用，用户需要手动启用
            push: false,
            imageName: "",
            tag: "",
          };
        } else {
          // 确保enabled字段存在，如果不存在则设置为false（保持禁用状态）
          if (
            multiServiceFormData.value.service_push_config[serviceName]
              .enabled === undefined
          ) {
            multiServiceFormData.value.service_push_config[
              serviceName
            ].enabled = false;
          }
          // 保持当前的enabled状态（可能是false，用户需要手动启用）
        }
      });
    }
  }
);

// 关闭多服务配置模态框
function closeMultiServiceConfigModal() {
  if (savingMultiServiceConfig.value) {
    return;
  }
  showMultiServiceConfigModal.value = false;
  multiServiceConfigPipeline.value = null;
  multiServiceFormData.value = {
    push_mode: "multi",
    selected_services: [],
    service_push_config: {},
    global_image_name: "",
    global_tag: "latest",
  };
  // 清空备份数据
  multiServiceBackup.value = {
    selected_services: [],
    service_push_config: {},
  };
}

// 识别dockerfile并解析多服务
async function parseDockerfileForMultiService() {
  if (!multiServiceConfigPipeline.value) {
    toastError("无法获取流水线信息");
    return;
  }

  const pipeline = multiServiceConfigPipeline.value;

  // 检查必要的字段
  if (!pipeline.git_url) {
    toastError("流水线未配置 Git 地址，无法识别 Dockerfile");
    return;
  }

  if (!pipeline.branch) {
    toastError("流水线未配置分支，无法识别 Dockerfile");
    return;
  }

  parsingDockerfileForMultiService.value = true;

  try {
    const payload = {
      git_url: pipeline.git_url,
      branch: pipeline.branch,
      dockerfile_name: pipeline.dockerfile_name || "Dockerfile",
      source_id: pipeline.source_id || null,
    };

    const res = await axios.post("/api/parse-dockerfile-services", payload);
    const servicesList = res.data.services || [];

    if (servicesList.length === 0) {
      toastInfo("未从 Dockerfile 中识别到服务");
      return;
    }

    // 将解析出的服务填充到表单中
    // 如果已有服务，询问是否覆盖
    if (multiServiceFormData.value.selected_services.length > 0) {
      const confirmed = await showConfirm({ message: `已识别到 ${servicesList.length} 个服务，是否覆盖现有服务列表？` });
      if (!confirmed) {
        return;
      }
    }

    // 清空现有服务
    multiServiceFormData.value.selected_services = [];
    multiServiceFormData.value.service_push_config = {};

    // 添加解析出的服务
    servicesList.forEach((service) => {
      const serviceName = service.name;
      multiServiceFormData.value.selected_services.push(serviceName);

      // 初始化服务配置
      multiServiceFormData.value.service_push_config[serviceName] = {
        enabled: true, // 默认启用
        push: false,
        imageName: "", // 留空使用全局前缀拼接
        tag: multiServiceFormData.value.global_tag || "latest",
      };
    });

    // 如果全局镜像名称前缀为空，尝试从 Git URL 生成
    if (
      !multiServiceFormData.value.global_image_name ||
      !multiServiceFormData.value.global_image_name.trim()
    ) {
      const gitUrl = pipeline.git_url;
      // 尝试从 Git URL 提取项目名
      const match = gitUrl.match(/\/([^\/]+?)(?:\.git)?$/);
      if (match && match[1]) {
        multiServiceFormData.value.global_image_name = match[1];
      }
    }

    toastSuccess(`成功识别 ${servicesList.length} 个服务`);
  } catch (error) {
    console.error("解析 Dockerfile 失败:", error);
    const errorMsg = error.response?.data?.detail || "解析 Dockerfile 失败";
    toastError(`识别失败: ${errorMsg}`);
  } finally {
    parsingDockerfileForMultiService.value = false;
  }
}

// 添加服务到多服务配置
function addServiceToMultiConfig() {
  const newServiceName = `service${
    multiServiceFormData.value.selected_services.length + 1
  }`;
  multiServiceFormData.value.selected_services.push(newServiceName);
  multiServiceFormData.value.service_push_config[newServiceName] = {
    enabled: true,
    push: false,
    imageName: "",
    tag: "",
  };
}

// 从多服务配置中移除服务
function removeServiceFromMultiConfig(index) {
  const serviceName = multiServiceFormData.value.selected_services[index];
  multiServiceFormData.value.selected_services.splice(index, 1);
  if (multiServiceFormData.value.service_push_config[serviceName]) {
    delete multiServiceFormData.value.service_push_config[serviceName];
  }
}

// 更新服务名称
function updateServiceName(index, newName) {
  const oldName = multiServiceFormData.value.selected_services[index];
  if (oldName === newName) {
    return;
  }

  // 更新服务名称数组
  multiServiceFormData.value.selected_services[index] = newName;

  // 更新配置对象的key
  if (multiServiceFormData.value.service_push_config[oldName]) {
    multiServiceFormData.value.service_push_config[newName] =
      multiServiceFormData.value.service_push_config[oldName];
    delete multiServiceFormData.value.service_push_config[oldName];
  } else {
    // 如果旧名称没有配置，创建新配置
    multiServiceFormData.value.service_push_config[newName] = {
      enabled: true,
      push: false,
      imageName: "",
      tag: "",
    };
  }
}

// 更新服务镜像名称
function updateServiceImageName(serviceName, imageName) {
  if (!multiServiceFormData.value.service_push_config[serviceName]) {
    multiServiceFormData.value.service_push_config[serviceName] = {
      enabled: true,
      push: false,
      imageName: "",
      tag: "",
    };
  }
  multiServiceFormData.value.service_push_config[serviceName].imageName =
    imageName;
}

// 更新服务标签
function updateServiceTag(serviceName, tag) {
  if (!multiServiceFormData.value.service_push_config[serviceName]) {
    multiServiceFormData.value.service_push_config[serviceName] = {
      enabled: true,
      push: false,
      imageName: "",
      tag: "",
    };
  }
  multiServiceFormData.value.service_push_config[serviceName].tag = tag;
}

// 更新服务推送设置
function updateServicePush(serviceName, push) {
  if (!multiServiceFormData.value.service_push_config[serviceName]) {
    multiServiceFormData.value.service_push_config[serviceName] = {
      enabled: true,
      push: false,
      imageName: "",
      tag: "",
    };
  }
  multiServiceFormData.value.service_push_config[serviceName].push = push;
}

// 获取单服务模式下的推送状态
function getSingleServicePush() {
  if (multiServiceFormData.value.push_mode !== "single") {
    return false;
  }
  const firstService =
    multiServiceFormData.value.selected_services &&
    multiServiceFormData.value.selected_services.length > 0
      ? multiServiceFormData.value.selected_services[0]
      : null;
  if (!firstService) {
    return false;
  }
  const config = multiServiceFormData.value.service_push_config[firstService];
  return config && config.push !== undefined ? config.push : false;
}

// 更新单服务模式下的推送状态
function updateSingleServicePush(push) {
  if (multiServiceFormData.value.push_mode !== "single") {
    return;
  }
  const firstService =
    multiServiceFormData.value.selected_services &&
    multiServiceFormData.value.selected_services.length > 0
      ? multiServiceFormData.value.selected_services[0]
      : null;
  if (!firstService) {
    return;
  }
  updateServicePush(firstService, push);
}

// 更新服务启用状态
function updateServiceEnabled(serviceName, enabled) {
  if (!multiServiceFormData.value.service_push_config[serviceName]) {
    multiServiceFormData.value.service_push_config[serviceName] = {
      enabled: true,
      push: false,
      imageName: "",
      tag: "",
    };
  }
  multiServiceFormData.value.service_push_config[serviceName].enabled = enabled;
}

// 全部启用服务
function enableAllServices() {
  multiServiceFormData.value.selected_services.forEach((serviceName) => {
    updateServiceEnabled(serviceName, true);
  });
}

// 全部禁用服务
function disableAllServices() {
  multiServiceFormData.value.selected_services.forEach((serviceName) => {
    updateServiceEnabled(serviceName, false);
  });
}

// 获取多服务默认镜像名称
function getMultiServiceDefaultImageName(serviceName) {
  if (!serviceName) {
    return multiServiceFormData.value.global_image_name || "myapp/demo";
  }

  let prefix = multiServiceFormData.value.global_image_name || "myapp/demo";
  prefix = prefix.replace(/\/+$/, "");

  const normalizedPrefix = prefix.replace(/\/+$/, "");
  if (
    normalizedPrefix.endsWith(`/${serviceName}`) ||
    normalizedPrefix === serviceName
  ) {
    return normalizedPrefix;
  }

  if (prefix === serviceName) {
    return prefix;
  }

  return `${prefix}/${serviceName}`;
}

// 保存多服务配置
async function saveMultiServiceConfig() {
  if (savingMultiServiceConfig.value) {
    return;
  }

  // 验证服务名称
  const serviceNames = multiServiceFormData.value.selected_services.filter(
    (name) => name && name.trim()
  );
  if (
    serviceNames.length === 0 &&
    multiServiceFormData.value.push_mode === "multi"
  ) {
    toastInfo("多服务模式下至少需要添加一个服务");
    return;
  }

  // 检查是否有重复的服务名称
  const uniqueNames = new Set(serviceNames);
  if (uniqueNames.size !== serviceNames.length) {
    toastError("服务名称不能重复");
    return;
  }

  savingMultiServiceConfig.value = true;

  try {
    if (multiServiceFormData.value.push_mode === "single") {
      // 单服务模式：使用全局配置，但保留所有服务配置（设置为禁用状态）
      // 如果没有服务，自动添加一个默认服务
      if (serviceNames.length === 0) {
        const defaultServiceName = "service1";
        serviceNames.push(defaultServiceName);
        // 同时更新 multiServiceFormData，确保数据一致性
        if (
          !multiServiceFormData.value.selected_services.includes(
            defaultServiceName
          )
        ) {
          multiServiceFormData.value.selected_services.push(defaultServiceName);
        }
        if (
          !multiServiceFormData.value.service_push_config[defaultServiceName]
        ) {
          multiServiceFormData.value.service_push_config[defaultServiceName] = {
            enabled: false,
            push: false,
            imageName: "",
            tag: "",
          };
        }
      }

      // 保留所有服务，但将所有服务的配置设置为禁用状态
      const normalizedServicePushConfig = {};
      serviceNames.forEach((serviceName) => {
        const config =
          multiServiceFormData.value.service_push_config[serviceName];
        if (config) {
          // 保留配置，但确保enabled为false
          normalizedServicePushConfig[serviceName] = {
            enabled: false, // 单服务模式下所有服务都禁用
            push: config.push !== undefined ? config.push : false,
            imageName: config.imageName || "",
            tag: config.tag || "",
          };
        } else {
          normalizedServicePushConfig[serviceName] = {
            enabled: false, // 单服务模式下所有服务都禁用
            push: false,
            imageName: "",
            tag: "",
          };
        }
      });

      const firstName = serviceNames[0];
      const firstCfg = firstName
        ? normalizedServicePushConfig[firstName]
        : null;
      const payload = {
        push_mode: "single",
        selected_services: serviceNames, // 保留所有服务
        service_push_config: normalizedServicePushConfig, // 保留所有服务配置，但enabled都是false
        image_name:
          multiServiceFormData.value.global_image_name ||
          multiServiceConfigPipeline.value.image_name ||
          "",
        tag:
          multiServiceFormData.value.global_tag ||
          multiServiceConfigPipeline.value.tag ||
          "latest",
        push: !!(firstCfg && firstCfg.push),
      };

      console.log("保存单服务模式配置:", payload);
      await axios.put(
        `/api/pipelines/${multiServiceConfigPipeline.value.pipeline_id}`,
        payload
      );
    } else {
      // 多服务模式：只保存启用的服务，使用各服务的独立配置
      const enabledServices = serviceNames.filter((serviceName) => {
        const config =
          multiServiceFormData.value.service_push_config[serviceName];
        return config?.enabled !== false; // enabled默认为true，只有显式设置为false才禁用
      });

      if (enabledServices.length === 0) {
        toastInfo("多服务模式下至少需要启用一个服务");
        savingMultiServiceConfig.value = false;
        return;
      }

      // 规范化服务推送配置（只包含启用的服务）
      const normalizedServicePushConfig = {};
      enabledServices.forEach((serviceName) => {
        const config =
          multiServiceFormData.value.service_push_config[serviceName];
        if (config) {
          const customImageName = config.imageName && config.imageName.trim();
          const finalImageName =
            customImageName || getMultiServiceDefaultImageName(serviceName);
          const finalTag =
            (config.tag && config.tag.trim()) ||
            multiServiceFormData.value.global_tag ||
            "latest";

          normalizedServicePushConfig[serviceName] = {
            push: config.push !== undefined ? config.push : false,
            imageName: finalImageName,
            tag: finalTag,
          };
        } else {
          normalizedServicePushConfig[serviceName] = {
            push: false,
            imageName: getMultiServiceDefaultImageName(serviceName),
            tag: multiServiceFormData.value.global_tag || "latest",
          };
        }
      });

      const payload = {
        push_mode: "multi",
        selected_services: enabledServices,
        service_push_config: normalizedServicePushConfig,
        image_name:
          multiServiceFormData.value.global_image_name ||
          multiServiceConfigPipeline.value.image_name ||
          "",
        tag:
          multiServiceFormData.value.global_tag ||
          multiServiceConfigPipeline.value.tag ||
          "latest",
        push: anyServicePushEnabled(normalizedServicePushConfig),
      };

      await axios.put(
        `/api/pipelines/${multiServiceConfigPipeline.value.pipeline_id}`,
        payload
      );
    }

    toastSuccess("多服务配置已保存");

    await loadPipelines();

    try {
      const res = await axios.get(
        `/api/pipelines/${multiServiceConfigPipeline.value.pipeline_id}`
      );
      if (res.data) {
        multiServiceConfigPipeline.value = res.data;
      }
    } catch (error) {
      console.warn("刷新流水线详情失败:", error);
    }

    // 如果当前正在编辑这个流水线，需要更新 editingPipeline 和 formData
    if (
      editingPipeline.value &&
      editingPipeline.value.pipeline_id ===
        multiServiceConfigPipeline.value.pipeline_id
    ) {
      if (updatedPipeline) {
        // 更新 editingPipeline
        editingPipeline.value = updatedPipeline;

        // 更新 formData 中相关的字段（多服务配置相关的字段）
        formData.value.push_mode = updatedPipeline.push_mode || "multi";
        formData.value.selected_service =
          updatedPipeline.selected_services &&
          updatedPipeline.selected_services.length === 1
            ? updatedPipeline.selected_services[0]
            : "";
        formData.value.selected_services =
          updatedPipeline.selected_services || [];
        formData.value.service_push_config = normalizeServicePushConfig(
          updatedPipeline.service_push_config || {}
        );
        formData.value.image_name = updatedPipeline.image_name || "";
        formData.value.tag = updatedPipeline.tag || "latest";
        formData.value.push =
          updatedPipeline.push_mode === "multi"
            ? anyServicePushEnabled(
                normalizeServicePushConfig(
                  updatedPipeline.service_push_config || {}
                )
              ) || !!updatedPipeline.push
            : updatedPipeline.push || false;

        // 更新 buildConfigJsonText（如果JSON模态框是打开的）
        if (showBuildConfigJsonModal.value) {
          buildConfigJsonText.value = buildConfigJson.value;
        }
      }
    }

    // 关闭模态框（在更新数据之后关闭，确保数据已更新）
    closeMultiServiceConfigModal();
  } catch (error) {
    console.error("保存多服务配置失败:", error);
    toastApiError(error, "保存多服务配置失败");
  } finally {
    savingMultiServiceConfig.value = false;
  }
}
</script>

<style scoped>
.pipeline-panel {
  padding: 1rem;
  max-width: 100%;
  min-width: 0;
  overflow-x: hidden;
  box-sizing: border-box;
}

.card {
  transition: transform 0.2s, box-shadow 0.2s;
  border: 1px solid rgba(0, 0, 0, 0.125);
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15) !important;
}

.card-header {
  border-bottom: 1px solid rgba(0, 0, 0, 0.125);
  padding: 1rem 1.25rem;
  background-color: #f8f9fa;
}

.card-title {
  font-size: 1.1rem;
  margin: 0;
  font-weight: 600;
  line-height: 1.5;
}

.card-body {
  padding: 1.25rem;
  line-height: 1.6;
}

/* 卡片操作按钮：桌面单行，移动端可换行 */
.pipeline-panel .card-header .btn-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.pipeline-panel .card-header .btn-group > * {
  flex: 1 1 calc(33.333% - 0.25rem);
  min-width: 2.5rem;
}

.pipeline-stats .col-4 {
  flex: 0 0 33.333333%;
  width: 33.333333%;
  max-width: 33.333333%;
}

/* 响应式调整 */
@media (max-width: 767px) {
  .pipeline-panel .row > [class*="col-md-"] {
    flex: 0 0 100%;
    width: 100%;
    max-width: 100%;
  }

  .pipeline-panel {
    padding: 0;
  }

  .pipeline-toolbar h5 {
    font-size: 1rem;
  }

  .pipeline-toolbar-actions {
    width: 100%;
  }

  .pipeline-toolbar-actions > * {
    flex: 1 1 100%;
    min-width: 0;
    justify-content: center;
  }

  .pipeline-panel .card-header,
  .pipeline-panel .card-body {
    padding: 0.75rem;
  }

  .pipeline-panel .card:hover {
    transform: none;
    box-shadow: 0 1px 2px rgb(0 0 0 / 0.05) !important;
  }

  .pipeline-card-badges {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.375rem;
  }

  .pipeline-panel .card-body .ml-4 {
    margin-left: 0.25rem !important;
  }

  .pipeline-build-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.375rem;
  }

  .pipeline-build-header > div {
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .pipeline-build-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.25rem;
    margin-left: 0 !important;
  }

  .pipeline-stats.row {
    flex-direction: column;
    margin-left: 0;
    margin-right: 0;
  }

  .pipeline-stats .col-4 {
    flex: 0 0 100%;
    width: 100%;
    max-width: 100%;
    padding-left: 0;
    padding-right: 0;
  }

  .pipeline-panel .card-header .btn-group > * {
    flex: 1 1 calc(33.333% - 0.25rem);
    min-height: 2.25rem;
    padding-left: 0.25rem;
    padding-right: 0.25rem;
  }

  .pipeline-panel > .fixed.inset-0 {
    padding: 0.5rem;
    align-items: flex-end;
  }

  .pipeline-panel > .fixed.inset-0 > .relative {
    max-width: 100%;
  }

  .pipeline-panel .modal-title {
    font-size: 0.9375rem;
    line-height: 1.35;
    word-break: break-word;
  }

  .pipeline-panel .nav-tabs {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
    margin-left: -0.25rem;
    margin-right: -0.25rem;
    padding-bottom: 0.25rem;
  }

  .pipeline-panel .nav-tabs .nav-link {
    white-space: nowrap;
    font-size: 0.75rem;
    padding: 0.375rem 0.5rem;
  }

  .pipeline-modal-footer {
    flex-direction: column-reverse;
    align-items: stretch;
  }

  .pipeline-modal-footer > * {
    width: 100%;
    justify-content: center;
  }

  .pipeline-panel .flex.justify-between.items-center {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .pipeline-panel .flex.justify-between.items-center .btn-group {
    width: 100%;
    flex-wrap: wrap;
  }

  .pipeline-panel .input-group {
    flex-direction: column;
    align-items: stretch;
  }

  .pipeline-panel .input-group > .btn,
  .pipeline-panel .input-group > button {
    width: 100%;
    border-radius: 0.375rem !important;
    margin-top: 0.375rem;
  }

  .pipeline-panel .input-group > input,
  .pipeline-panel .input-group > select {
    border-radius: 0.375rem !important;
    width: 100%;
  }

  .pipeline-panel .btn-group.w-full {
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .pipeline-panel .btn-group.w-full > .btn,
  .pipeline-panel .btn-group.w-full > button,
  .pipeline-panel .btn-group.w-full > label {
    flex: 1 1 calc(50% - 0.25rem);
    min-width: 0;
    white-space: normal;
    line-height: 1.25;
  }

  .pipeline-branch-mapping-row .col-md-1.text-center {
    padding-top: 0.125rem;
    padding-bottom: 0.125rem;
  }

  .pipeline-json-editor :deep(.cm-editor) {
    height: min(500px, 42vh) !important;
    min-height: 220px;
  }

  .pipeline-json-editor :deep(.cm-scroller) {
    max-height: 42vh;
  }
}
</style>

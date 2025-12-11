<template>
  <div class="pipeline-panel">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0">
        <i class="fas fa-project-diagram"></i> 流水线管理
      </h5>
      <div class="d-flex gap-2">
        <button 
          class="btn btn-outline-secondary btn-sm" 
          @click="loadPipelines"
          :disabled="loading"
          title="刷新列表"
        >
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i> 刷新
        </button>
        <button class="btn btn-primary btn-sm" @click="showCreateModal">
          <i class="fas fa-plus"></i> 新建流水线
        </button>
      </div>
    </div>

    <!-- 流水线列表 - 卡片式布局 -->
    <div v-if="loading" class="text-center py-5">
      <span class="spinner-border spinner-border-sm"></span> 加载中...
    </div>
    <div v-else-if="pipelines.length === 0" class="text-center py-5 text-muted">
      <i class="fas fa-inbox fa-3x mb-3"></i>
      <p class="mb-0">暂无流水线配置</p>
    </div>
    <div v-else class="row g-4">
      <div v-for="pipeline in pipelines" :key="pipeline.pipeline_id" class="col-12 col-md-6 col-xl-4">
        <div class="card h-100 shadow-sm">
          <!-- 卡片头部 -->
          <div class="card-header bg-white">
            <!-- 标题行 -->
            <div class="mb-2">
              <!-- 流水线名字单独一行 -->
              <h5 class="card-title mb-2">
                <strong>{{ pipeline.name }}</strong>
              </h5>
              <!-- 徽章行 -->
              <div class="d-flex align-items-center justify-content-between mb-1">
                <div>
                  <span v-if="pipeline.enabled" class="badge bg-success">
                    <i class="fas fa-check-circle"></i> 已启用
                  </span>
                  <span v-else class="badge bg-secondary">
                    <i class="fas fa-times-circle"></i> 已禁用
                  </span>
                </div>
                <span class="badge" :class="getProjectTypeBadgeClass(pipeline.project_type)" style="font-size: 0.8rem; padding: 0.3rem 0.6rem;">
                  <i :class="getProjectTypeIcon(pipeline.project_type)"></i>
                  {{ getProjectTypeLabel(pipeline.project_type) }}
                </span>
              </div>
              <p class="text-muted mb-0 mt-1" v-if="pipeline.description" style="font-size: 0.9rem;">{{ pipeline.description }}</p>
            </div>
            <!-- 操作按钮行 -->
            <div class="btn-group btn-group-sm w-100">
              <button 
                class="btn btn-outline-success" 
                @click="runPipeline(pipeline)"
                :disabled="running === pipeline.pipeline_id || queuedPipelines.has(pipeline.pipeline_id)"
                title="手动运行"
              >
                <i class="fas fa-play"></i>
                <span v-if="running === pipeline.pipeline_id" class="spinner-border spinner-border-sm ms-1"></span>
                <span v-else-if="queuedPipelines.has(pipeline.pipeline_id)" class="badge bg-warning ms-1">排队中</span>
              </button>
              <button 
                class="btn btn-outline-secondary" 
                @click="showHistory(pipeline)"
                title="查看历史构建"
              >
                <i class="fas fa-history"></i>
              </button>
              <button 
                class="btn btn-outline-info" 
                @click="showWebhookUrl(pipeline)"
                title="查看 Webhook URL"
              >
                <i class="fas fa-link"></i>
              </button>
              <button 
                class="btn btn-outline-primary" 
                @click="editPipeline(pipeline)"
                title="编辑"
              >
                <i class="fas fa-edit"></i>
              </button>
              <button 
                class="btn btn-outline-danger" 
                @click="deletePipeline(pipeline)"
                title="删除"
              >
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
          
          <!-- 卡片内容 -->
          <div class="card-body">
            <!-- Git 信息 -->
            <div class="mb-3" style="min-height: 60px;">
              <div class="d-flex align-items-center mb-2">
                <i class="fas fa-code-branch text-muted me-2" style="width: 18px; flex-shrink: 0;"></i>
                <small class="font-monospace text-truncate flex-grow-1" :title="pipeline.git_url" style="font-size: 0.9rem; min-width: 0;">
                  {{ formatGitUrl(pipeline.git_url) }}
                </small>
                <button 
                  class="btn btn-sm btn-outline-secondary p-1 ms-2" 
                  style="width: 24px; height: 24px; line-height: 1; flex-shrink: 0;"
                  @click="copyToClipboard(pipeline.git_url, 'Git 地址')"
                  title="复制 Git 地址"
                >
                  <i class="fas fa-copy" style="font-size: 0.7rem;"></i>
                </button>
              </div>
              <div class="d-flex align-items-center flex-wrap gap-2 ms-4" style="min-height: 24px;">
                <span class="badge bg-secondary" style="font-size: 0.75rem;">
                  <i class="fas fa-code-branch"></i> {{ pipeline.branch || '默认' }}
                </span>
                <span v-if="pipeline.webhook_branch_filter" class="badge bg-warning" title="启用分支过滤" style="font-size: 0.75rem;">
                  <i class="fas fa-filter"></i> 分支过滤
                </span>
                <span v-if="pipeline.webhook_token" class="badge bg-primary" title="Webhook 触发" style="font-size: 0.75rem;">
                  <i class="fas fa-link"></i> Webhook
                </span>
                <span v-if="pipeline.cron_expression" class="badge bg-info" :title="pipeline.cron_expression" style="font-size: 0.75rem;">
                  <i class="fas fa-clock"></i> 定时
                </span>
              </div>
            </div>
            
            <!-- 镜像信息 -->
            <div class="mb-3" style="min-height: 24px;">
              <div class="d-flex align-items-center">
                <i class="fab fa-docker text-muted me-2" style="width: 18px; flex-shrink: 0;"></i>
                <small class="font-monospace text-truncate flex-grow-1" :title="`${pipeline.image_name}:${pipeline.tag}`" style="font-size: 0.9rem; min-width: 0;">
                  {{ pipeline.image_name }}:{{ pipeline.tag }}
                </small>
                <button 
                  class="btn btn-sm btn-outline-secondary p-1 ms-2" 
                  style="width: 24px; height: 24px; line-height: 1; flex-shrink: 0;"
                  @click="copyToClipboard(`${pipeline.image_name}:${pipeline.tag}`, '镜像名称')"
                  title="复制镜像名称"
                >
                  <i class="fas fa-copy" style="font-size: 0.7rem;"></i>
                </button>
              </div>
              <!-- 多服务信息 -->
              <div v-if="pipeline.selected_services && pipeline.selected_services.length > 0" class="d-flex align-items-center flex-wrap gap-2 ms-4 mt-2">
                <span class="badge bg-info" style="font-size: 0.75rem;">
                  <i class="fas fa-layer-group"></i> {{ pipeline.selected_services.length }} 个服务
                </span>
                <span class="badge" :class="pipeline.push_mode === 'multi' ? 'bg-success' : 'bg-secondary'" style="font-size: 0.75rem;">
                  <i class="fas" :class="pipeline.push_mode === 'multi' ? 'fa-sitemap' : 'fa-cube'"></i> {{ pipeline.push_mode === 'multi' ? '多阶段' : '单一' }}推送
                </span>
              </div>
              <!-- 子路径 -->
              <div v-if="pipeline.sub_path" class="ms-4 mt-1">
                <small class="text-muted" style="font-size: 0.8rem;">
                  <i class="fas fa-folder"></i> 子路径: {{ pipeline.sub_path }}
                </small>
              </div>
              <!-- 资源包信息 -->
              <div v-if="pipeline.resource_package_configs && pipeline.resource_package_configs.length > 0" class="ms-4 mt-1">
                <small class="text-muted" style="font-size: 0.8rem;">
                  <i class="fas fa-archive"></i> {{ pipeline.resource_package_configs.length }} 个资源包
                </small>
              </div>
              <!-- Dockerfile 信息 -->
              <div v-if="pipeline.use_project_dockerfile" class="ms-4 mt-1">
                <small class="text-muted" style="font-size: 0.8rem;">
                  <i class="fas fa-file-code"></i> {{ pipeline.dockerfile_name || 'Dockerfile' }}
                </small>
              </div>
            </div>
            
            <!-- 构建状态区域 -->
            <div class="border-top pt-3 mt-3">
              <!-- 最后构建状态 -->
              <div class="mb-3">
                <div class="d-flex align-items-center justify-content-between mb-2">
                  <span class="text-muted fw-semibold" style="font-size: 0.9rem;">
                    <i class="fas fa-hammer me-1"></i>
                    {{ isLastBuildRunning(pipeline) ? '当前任务' : '最后构建' }}
                  </span>
                  <!-- 如果最后构建是运行中或等待中，显示为当前任务 -->
                  <div v-if="pipeline.last_build && (pipeline.last_build.status === 'running' || pipeline.last_build.status === 'pending')" class="d-flex align-items-center gap-2">
                    <span v-if="pipeline.last_build.status === 'running'" class="badge bg-primary">
                      <span class="spinner-border spinner-border-sm me-1" style="width: 0.7rem; height: 0.7rem;"></span> 运行中
                    </span>
                    <span v-else-if="pipeline.last_build.status === 'pending'" class="badge bg-warning">
                      <i class="fas fa-clock"></i> 等待中
                    </span>
                    <span v-else-if="queuedPipelines.has(pipeline.pipeline_id)" class="badge bg-info">
                      <i class="fas fa-list"></i> 排队中
                    </span>
                    <button 
                      v-if="pipeline.last_build && pipeline.last_build.task_id && pipeline.last_build.status !== 'deleted'"
                      class="btn btn-sm btn-outline-info p-1" 
                      style="width: 24px; height: 24px; line-height: 1;"
                      @click.stop="viewTaskLogs(pipeline.last_build.task_id, pipeline.last_build)"
                      title="查看日志"
                    >
                      <i class="fas fa-terminal" style="font-size: 0.75rem;"></i>
                    </button>
                  </div>
                  <!-- 如果最后构建已完成或失败，显示为历史构建 -->
                  <div v-else-if="pipeline.last_build && (pipeline.last_build.status === 'completed' || pipeline.last_build.status === 'failed')" class="d-flex align-items-center gap-2">
                    <span 
                      :class="{
                        'badge': true,
                        'bg-success': pipeline.last_build.status === 'completed',
                        'bg-danger': pipeline.last_build.status === 'failed',
                      }"
                    >
                      <i v-if="pipeline.last_build.status === 'completed'" class="fas fa-check-circle"></i>
                      <i v-else-if="pipeline.last_build.status === 'failed'" class="fas fa-times-circle"></i>
                      {{ pipeline.last_build.status === 'completed' ? '成功' : '失败' }}
                    </span>
                    <button 
                      v-if="pipeline.last_build && pipeline.last_build.task_id && pipeline.last_build.status !== 'deleted'"
                      class="btn btn-sm btn-outline-info p-1" 
                      style="width: 24px; height: 24px; line-height: 1;"
                      @click.stop="viewTaskLogs(pipeline.last_build.task_id, pipeline.last_build)"
                      title="查看日志"
                    >
                      <i class="fas fa-terminal" style="font-size: 0.75rem;"></i>
                    </button>
                  </div>
                  <span v-else class="text-muted" style="font-size: 0.85rem;">暂无构建</span>
                </div>
                <!-- 构建详情 -->
                <div v-if="pipeline.last_build" class="d-flex justify-content-between align-items-center ms-3 mb-2">
                  <small class="text-muted" :title="formatDateTime(pipeline.last_build.completed_at || pipeline.last_build.created_at)" style="font-size: 0.8rem;">
                    <i class="fas fa-calendar-alt me-1"></i>
                    {{ formatDateTime(pipeline.last_build.completed_at || pipeline.last_build.created_at) }}
                  </small>
                  <small class="text-muted">
                    <i class="fas fa-hashtag me-1"></i>
                    <code style="font-size: 0.8rem;">{{ pipeline.last_build.task_id?.substring(0, 8) || '-' }}</code>
                  </small>
                </div>
              </div>
              
              <!-- 统计指标 -->
              <div class="row g-2">
                <div class="col-4">
                  <div class="bg-light rounded p-2 text-center">
                    <div class="text-muted mb-1" style="font-size: 0.75rem;">
                      <i class="fas fa-chart-line"></i> 触发次数
                    </div>
                    <div class="fw-bold" style="font-size: 1.1rem; color: #0d6efd;">
                      {{ pipeline.trigger_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-4">
                  <div class="bg-light rounded p-2 text-center">
                    <div class="text-muted mb-1" style="font-size: 0.75rem;">
                      <i class="fas fa-check-circle"></i> 成功
                    </div>
                    <div class="fw-bold" style="font-size: 1.1rem; color: #198754;">
                      {{ pipeline.success_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-4">
                  <div class="bg-light rounded p-2 text-center">
                    <div class="text-muted mb-1" style="font-size: 0.75rem;">
                      <i class="fas fa-times-circle"></i> 失败
                    </div>
                    <div class="fw-bold" style="font-size: 1.1rem; color: #dc3545;">
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

    <!-- 创建/编辑流水线模态框 -->
    <div v-if="showModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ editingPipeline ? '编辑流水线' : '新建流水线' }}
            </h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
            <form @submit.prevent="savePipeline">
              <!-- Tab 导航 -->
              <ul class="nav nav-tabs mb-3" role="tablist">
                <li class="nav-item" role="presentation">
                  <button 
                    class="nav-link" 
                    :class="{ active: activeTab === 'basic' }"
                    type="button"
                    @click="activeTab = 'basic'"
                    id="basic-tab"
                  >
                    <i class="fas fa-info-circle"></i> 基本信息
                  </button>
                </li>
                <li class="nav-item" role="presentation">
                  <button 
                    class="nav-link" 
                    :class="{ active: activeTab === 'git' }"
                    type="button"
                    @click="activeTab = 'git'"
                    id="git-tab"
                  >
                    <i class="fas fa-code-branch"></i> Git 配置
                  </button>
                </li>
                <li class="nav-item" role="presentation">
                  <button 
                    class="nav-link" 
                    :class="{ active: activeTab === 'build' }"
                    type="button"
                    @click="activeTab = 'build'"
                    id="build-tab"
                  >
                    <i class="fas fa-cogs"></i> Dockerfile & 镜像配置
                  </button>
                </li>
                <li class="nav-item" role="presentation">
                  <button 
                    class="nav-link" 
                    :class="{ active: activeTab === 'resource' }"
                    type="button"
                    @click="activeTab = 'resource'"
                    id="resource-tab"
                  >
                    <i class="fas fa-archive"></i> 资源包配置
                  </button>
                </li>
                <li class="nav-item" role="presentation">
                  <button 
                    class="nav-link" 
                    :class="{ active: activeTab === 'webhook' }"
                    type="button"
                    @click="activeTab = 'webhook'"
                    id="webhook-tab"
                  >
                    <i class="fas fa-link"></i> Webhook 设置
                  </button>
                </li>
                <li class="nav-item" role="presentation">
                  <button 
                    class="nav-link" 
                    :class="{ active: activeTab === 'other' }"
                    type="button"
                    @click="activeTab = 'other'"
                    id="other-tab"
                  >
                    <i class="fas fa-sliders-h"></i> 其他选项
                  </button>
                </li>
              </ul>

              <!-- Tab 内容 -->
              <div class="tab-content">
                <!-- 基本信息 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'basic' }"
                  role="tabpanel"
                  id="basic-pane"
                >
                  <div class="mb-3">
                    <label class="form-label">流水线名称 <span class="text-danger">*</span></label>
                    <input 
                      v-model="formData.name" 
                      type="text" 
                      class="form-control form-control-sm" 
                      required
                      placeholder="例如：主分支自动构建"
                    >
                  </div>
                  <div class="mb-3">
                    <label class="form-label">描述</label>
                    <input 
                      v-model="formData.description" 
                      type="text" 
                      class="form-control form-control-sm"
                      placeholder="流水线描述（可选）"
                    >
                  </div>
                </div>

                <!-- Git 配置 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'git' }"
                  role="tabpanel"
                  id="git-pane"
                >
                  <div class="card">
                    <div class="card-header bg-light">
                      <h6 class="mb-0">
                        <i class="fas fa-code-branch text-primary"></i> Git 配置
                      </h6>
                    </div>
                    <div class="card-body">
                      <div class="row g-3">
                        <div class="col-md-6">
                          <label class="form-label">Git 数据源</label>
                          <select v-model="formData.source_id" class="form-select form-select-sm" @change="onSourceSelected">
                            <option value="">-- 选择数据源或手动输入 --</option>
                            <option v-for="source in gitSources" :key="source.source_id" :value="source.source_id">
                              {{ source.name }} ({{ formatGitUrl(source.git_url) }})
                            </option>
                          </select>
                          <div class="form-text small text-muted mt-1">
                            <i class="fas fa-info-circle"></i> 
                            可以从已保存的数据源中选择，或手动输入 Git 仓库地址
                          </div>
                        </div>
                        <div class="col-md-6">
                          <label class="form-label">Git 仓库地址 <span class="text-danger">*</span></label>
                          <input 
                            v-model="formData.git_url" 
                            type="text" 
                            class="form-control form-control-sm" 
                            required
                            placeholder="https://github.com/user/repo.git"
                          >
                        </div>
                        <div class="col-md-6">
                          <label class="form-label">分支名称</label>
                          <div class="input-group">
                            <select 
                              v-if="repoVerified || formData.source_id || formData.git_url"
                              v-model="formData.branch" 
                              class="form-select form-select-sm"
                              :disabled="refreshingBranches || (!repoVerified && !formData.source_id && !formData.git_url)"
                              @change="onBranchChanged"
                            >
                              <option value="">
                                使用默认分支 ({{ branchesAndTags.default_branch || "main" }})
                              </option>
                              <optgroup v-if="branchesAndTags.branches.length > 0" label="分支">
                                <option
                                  v-for="branch in branchesAndTags.branches"
                                  :key="branch"
                                  :value="branch"
                                >
                                  {{ branch }}
                                </option>
                              </optgroup>
                              <optgroup v-if="branchesAndTags.tags.length > 0" label="标签">
                                <option
                                  v-for="tag in branchesAndTags.tags"
                                  :key="tag"
                                  :value="tag"
                                >
                                  {{ tag }}
                                </option>
                              </optgroup>
                            </select>
                            <input
                              v-else
                              type="text"
                              class="form-control form-control-sm"
                              placeholder="请先选择数据源"
                              disabled
                            >
                            <button 
                              v-if="formData.source_id || formData.git_url"
                              class="btn btn-outline-secondary btn-sm" 
                              type="button"
                              @click="refreshBranches(true)"
                              :disabled="refreshingBranches"
                              title="刷新分支列表"
                            >
                              <i v-if="refreshingBranches" class="fas fa-spinner fa-spin"></i>
                              <i v-else class="fas fa-sync-alt"></i>
                            </button>
                          </div>
                          <small class="text-muted">
                            <span v-if="refreshingBranches">正在刷新分支列表...</span>
                            <span v-else-if="repoVerified && branchesAndTags.branches.length > 0">
                              已加载 {{ branchesAndTags.branches.length }} 个分支、{{ branchesAndTags.tags.length }} 个标签
                            </span>
                            <span v-else-if="formData.source_id || formData.git_url">
                              点击刷新按钮加载分支列表，或留空使用推送的分支
                            </span>
                            <span v-else>请先选择数据源</span>
                          </small>
                        </div>
                        <div class="col-md-6">
                          <label class="form-label">项目类型 <span class="text-danger">*</span></label>
                          <select v-model="formData.project_type" class="form-select form-select-sm">
                            <option value="jar">Java 应用（JAR）</option>
                            <option value="nodejs">Node.js 应用</option>
                            <option value="python">Python 应用</option>
                            <option value="go">Go 应用</option>
                            <option value="web">静态网站</option>
                          </select>
                        </div>
                        <div class="col-md-6">
                          <label class="form-label">子路径</label>
                          <input 
                            v-model="formData.sub_path" 
                            type="text" 
                            class="form-control form-control-sm"
                            placeholder="留空表示根目录"
                          >
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Dockerfile & 镜像配置 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'build' }"
                  role="tabpanel"
                  id="build-pane"
                >
                  <!-- 视图切换和查看JSON按钮 -->
                  <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">
                      <i class="fas fa-cogs"></i> Dockerfile & 镜像配置
                    </h6>
                    <div class="btn-group btn-group-sm" role="group">
                      <button 
                        type="button"
                        class="btn btn-outline-info"
                        @click="showBuildConfigJsonModal = true"
                      >
                        <i class="fas fa-code"></i> 查看JSON
                      </button>
                    </div>
                  </div>


                  <!-- Dockerfile 配置模块 -->
                  <div class="card mb-4">
                    <div class="card-header bg-light">
                      <h6 class="mb-0">
                        <i class="fas fa-file-code text-primary"></i> Dockerfile 配置
                      </h6>
                    </div>
                    <div class="card-body">
                      <div class="row g-3">
                        <div class="col-12">
                          <label class="form-label">Dockerfile 来源</label>
                          <div class="btn-group w-100 mb-2" role="group">
                            <input 
                              type="radio" 
                              class="btn-check" 
                              id="use-project-dockerfile" 
                              :value="true"
                              v-model="formData.use_project_dockerfile"
                              @change="onDockerfileSourceChange"
                            >
                            <label class="btn btn-outline-primary" for="use-project-dockerfile">
                              <i class="fas fa-file-code"></i> 项目Dockerfile
                            </label>
                            
                            <input 
                              type="radio" 
                              class="btn-check" 
                              id="use-template" 
                              :value="false"
                              v-model="formData.use_project_dockerfile"
                              @change="onDockerfileSourceChange"
                            >
                            <label class="btn btn-outline-primary" for="use-template">
                              <i class="fas fa-layer-group"></i> 使用模板
                            </label>
                          </div>
                        </div>
                        <div v-if="formData.use_project_dockerfile" class="col-md-6">
                          <label class="form-label">Dockerfile 文件名</label>
                          <div v-if="scanningDockerfiles" class="mb-2">
                            <span class="spinner-border spinner-border-sm me-2"></span>
                            <small class="text-muted">正在扫描项目中的 Dockerfile...</small>
                          </div>
                          <div class="input-group">
                            <select
                              v-model="formData.dockerfile_name" 
                              class="form-select form-select-sm"
                              :disabled="scanningDockerfiles || !formData.branch"
                              required
                            >
                              <option value="">-- 请先选择分支 --</option>
                              <option value="Dockerfile">Dockerfile（默认，根目录）</option>
                              <!-- 如果当前选择不在扫描列表中，也要显示出来 -->
                              <option
                                v-if="formData.dockerfile_name && 
                                      formData.dockerfile_name !== 'Dockerfile' && 
                                      !availableDockerfiles.some(df => df.path === formData.dockerfile_name)"
                                :value="formData.dockerfile_name"
                                :key="'current-' + formData.dockerfile_name"
                              >
                                {{ formData.dockerfile_name }} (当前选择)
                              </option>
                              <option
                                v-for="dockerfile in availableDockerfiles"
                                :key="dockerfile.path"
                                :value="dockerfile.path"
                              >
                                {{ dockerfile.path }} {{ dockerfile.path !== dockerfile.name ? `(${dockerfile.name})` : '' }}
                              </option>
                            </select>
                            <button 
                              class="btn btn-outline-secondary btn-sm" 
                              type="button"
                              @click="scanDockerfiles(true, true)"
                              :disabled="scanningDockerfiles || (!formData.branch && !branchesAndTags.default_branch)"
                              title="刷新 Dockerfile 列表（强制刷新）"
                            >
                              <i v-if="scanningDockerfiles" class="fas fa-spinner fa-spin"></i>
                              <i v-else class="fas fa-sync-alt"></i>
                            </button>
                          </div>
                          <small v-if="dockerfilesError" class="text-danger d-block mt-1">
                            <i class="fas fa-exclamation-triangle"></i> {{ dockerfilesError }}
                          </small>
                          <small v-else-if="availableDockerfiles.length > 0" class="text-muted d-block mt-1">
                            <i class="fas fa-check-circle"></i> 已扫描到 {{ availableDockerfiles.length }} 个 Dockerfile
                          </small>
                          <small v-else-if="formData.branch" class="text-muted d-block mt-1">
                            <i class="fas fa-info-circle"></i> 请先选择分支，然后点击刷新按钮扫描项目中的 Dockerfile
                          </small>
                          <small v-else class="text-muted d-block mt-1">
                            <i class="fas fa-info-circle"></i> 请先选择分支
                          </small>
                        </div>
                        <div v-else class="col-md-6">
                          <label class="form-label">模板名称</label>
                          
                          <!-- 当前选择提示 -->
                          <div v-if="formData.template && formData.template !== ''" class="alert alert-success alert-sm py-2 mb-2">
                            <i class="fas fa-check-circle me-2"></i>
                            <strong>当前选择：</strong>{{ formData.template }}
                            <span v-if="filteredTemplates.find(t => t.name === formData.template)">
                              ({{ filteredTemplates.find(t => t.name === formData.template).project_type }})
                            </span>
                          </div>
                          
                          <select 
                            v-model="formData.template" 
                            class="form-select form-select-sm" 
                            @change="onTemplateChange"
                            :disabled="!formData.project_type"
                          >
                            <option value="">-- 请先选择项目类型 --</option>
                            <option v-for="tpl in filteredTemplates" :key="tpl.name" :value="tpl.name">
                              {{ tpl.name }} ({{ tpl.project_type }})
                            </option>
                          </select>
                          <small v-if="formData.project_type && filteredTemplates.length === 0" class="text-muted d-block mt-1">
                            <i class="fas fa-info-circle"></i> 当前项目类型没有可用的模板
                          </small>
                          <small v-else-if="formData.project_type && filteredTemplates.length > 0" class="text-muted d-block mt-1">
                            <i class="fas fa-check-circle"></i> 已按项目类型过滤，共 {{ filteredTemplates.length }} 个模板
                          </small>
                          <small v-else class="text-muted d-block mt-1">
                            <i class="fas fa-info-circle"></i> 请先在 Git 配置中选择项目类型
                          </small>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- 服务配置（包含镜像配置） -->
                  <div class="card mb-4">
                    <div class="card-header bg-light">
                      <h6 class="mb-0">
                        <i class="fas fa-layer-group text-primary"></i> 服务配置
                      </h6>
                    </div>
                    <div class="card-body">
                      <!-- 镜像配置部分 -->
                      <div class="border-bottom pb-3 mb-3">
                        <h6 class="mb-3">
                          <i class="fab fa-docker text-primary"></i> 镜像配置
                        </h6>
                        <div class="row g-3">
                          <div class="col-md-6">
                            <label class="form-label">推送模式</label>
                            <select v-model="formData.push_mode" class="form-select form-select-sm" @change="onPushModeChange">
                              <option value="single">单服务推送</option>
                              <option value="multi">多服务推送</option>
                            </select>
                          </div>
                          <div class="col-md-6">
                            <div class="form-check mt-4">
                              <input 
                                v-model="formData.push" 
                                class="form-check-input" 
                                type="checkbox" 
                                id="pushCheck"
                              >
                              <label class="form-check-label" for="pushCheck">
                                构建完成后推送到仓库
                              </label>
                            </div>
                          </div>
                          <div class="col-md-6">
                            <label class="form-label">镜像名称 <span class="text-danger">*</span></label>
                            <input 
                              v-model="formData.image_name" 
                              type="text" 
                              class="form-control form-control-sm" 
                              required
                              placeholder="myapp/demo"
                            >
                            <small class="text-muted d-block mt-1">
                              <span v-if="formData.push_mode === 'single'">
                                <i class="fas fa-info-circle"></i> 单服务模式：直接使用此镜像名称
                              </span>
                              <span v-else>
                                <i class="fas fa-info-circle"></i> 多服务模式：作为镜像名称前缀，每个服务会自动拼接服务名
                              </span>
                            </small>
                          </div>
                          <div class="col-md-6">
                            <label class="form-label">镜像标签</label>
                            <input 
                              v-model="formData.tag" 
                              type="text" 
                              class="form-control form-control-sm"
                              placeholder="latest"
                            >
                            <small class="text-muted d-block mt-1">
                              <i class="fas fa-info-circle"></i> 所有服务使用此标签
                            </small>
                          </div>
                        </div>
                        <div v-if="formData.push_mode === 'single'" class="alert alert-info mt-3 mb-0">
                          <i class="fas fa-info-circle"></i> 
                          <strong>单服务模式：</strong>使用上方配置的镜像名称和标签
                        </div>
                        <div v-else-if="formData.push_mode === 'multi'" class="alert alert-info mt-3 mb-0">
                          <i class="fas fa-info-circle"></i> 
                          <strong>多服务模式：</strong>每个服务的镜像名称将自动生成为 <code>{{ formData.image_name || 'myapp/demo' }}/服务名</code>，标签使用上方配置的全局标签
                        </div>
                      </div>

                      <!-- 服务列表加载 -->
                      <div v-if="loadingServices" class="text-center py-3">
                        <span class="spinner-border spinner-border-sm"></span> 正在加载服务列表...
                      </div>
                      <div v-else-if="servicesError" class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle"></i> {{ servicesError }}
                      </div>
                      
                      <!-- 单服务推送模式 -->
                      <!-- 编辑模式下，即使服务列表为空，也显示已保存的服务选择 -->
                      <div v-else-if="formData.push_mode === 'single' && (services.length > 0 || (editingPipeline && formData.selected_service))" class="mb-3">
                        <label class="form-label">选择服务 <span class="text-danger">*</span></label>
                        <div class="list-group">
                          <label
                            v-for="service in services"
                            :key="service.name"
                            class="list-group-item list-group-item-action"
                            :class="{ active: formData.selected_service === service.name }"
                            style="cursor: pointer"
                          >
                            <div class="d-flex align-items-center">
                              <input
                                type="radio"
                                :value="service.name"
                                v-model="formData.selected_service"
                                class="form-check-input me-3"
                              />
                              <div class="flex-grow-1">
                                <div class="fw-bold">
                                  <code>{{ service.name }}</code>
                                </div>
                                <small class="text-muted">
                                  <span v-if="service.port">端口: {{ service.port }}</span>
                                  <span v-if="service.port && service.user"> | </span>
                                  <span v-if="service.user">用户: {{ service.user }}</span>
                                </small>
                              </div>
                            </div>
                          </label>
                        </div>
                      </div>

                      <!-- 多服务推送模式 -->
                      <!-- 编辑模式下，即使服务列表为空，也显示已保存的服务选择 -->
                      <div v-else-if="formData.push_mode === 'multi' && (services.length > 0 || (editingPipeline && formData.selected_services && formData.selected_services.length > 0))" class="mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                          <div>
                            <span class="badge bg-info">{{ services.length }} 个服务</span>
                          </div>
                          <div>
                            <button
                              type="button"
                              class="btn btn-sm btn-outline-info me-2"
                              @click="selectAllServices"
                            >
                              <i class="fas fa-check-square"></i> 全选
                            </button>
                            <button
                              type="button"
                              class="btn btn-sm btn-outline-info"
                              @click="deselectAllServices"
                            >
                              <i class="fas fa-square"></i> 全不选
                            </button>
                          </div>
                        </div>
                        
                        <!-- 服务列表 -->
                        <!-- 编辑模式下，如果服务列表为空但已保存了服务选择，显示提示信息 -->
                        <div v-if="services.length === 0 && editingPipeline && formData.selected_services && formData.selected_services.length > 0" class="alert alert-info mb-3">
                          <i class="fas fa-info-circle"></i> 正在后台验证服务列表，已保存的服务选择将显示在下方
                        </div>
                        <div v-if="services.length > 0" class="row g-2 mb-3">
                          <div
                            v-for="service in services"
                            :key="service.name"
                            class="col-md-6 col-lg-4"
                          >
                            <div
                              class="card h-100"
                              :class="{
                                'border-success': formData.selected_services?.includes(service.name),
                                'border-secondary': !formData.selected_services?.includes(service.name)
                              }"
                              style="cursor: pointer"
                              @click="toggleService(service.name)"
                            >
                              <div class="card-body p-2">
                                <div class="form-check">
                                  <input
                                    type="checkbox"
                                    :value="service.name"
                                    v-model="formData.selected_services"
                                    class="form-check-input"
                                    @change="onServiceSelectionChange"
                                  />
                                  <label class="form-check-label fw-bold">
                                    <code>{{ service.name }}</code>
                                  </label>
                                </div>
                                <small class="text-muted d-block">
                                  <span v-if="service.port">端口: {{ service.port }}</span>
                                  <span v-if="service.port && service.user"> | </span>
                                  <span v-if="service.user">用户: {{ service.user }}</span>
                                </small>
                              </div>
                            </div>
                          </div>
                        </div>

                        <!-- 服务推送配置 -->
                        <div v-if="formData.selected_services && formData.selected_services.length > 0" class="border-top pt-3">
                          <h6 class="mb-3">
                            <i class="fas fa-cog"></i> 服务推送配置
                            <small class="text-muted">(已选择 {{ formData.selected_services.length }} 个服务)</small>
                          </h6>
                          <div class="alert alert-info mb-3">
                            <i class="fas fa-info-circle"></i> 
                            <strong>多服务模式：</strong>可以为每个服务设置独立的镜像名称和标签。留空时，镜像名称将自动生成为 <code>{{ formData.image_name || 'myapp/demo' }}/服务名</code>，标签使用全局标签 <code>{{ formData.tag || 'latest' }}</code>
                          </div>
                          <div class="table-responsive">
                            <table class="table table-sm table-bordered">
                              <thead>
                                <tr>
                                  <th style="width: 20%">服务名</th>
                                  <th style="width: 35%">镜像名称</th>
                                  <th style="width: 15%">标签</th>
                                  <th style="width: 10%">推送</th>
                                  <th style="width: 20%">操作</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr v-for="serviceName in formData.selected_services" :key="serviceName">
                                  <td><code>{{ serviceName }}</code></td>
                                  <td>
                                    <div class="d-flex align-items-center gap-1">
                                      <input
                                        type="text"
                                        v-model="getServiceConfig(serviceName).imageName"
                                        :placeholder="getServiceDefaultImageName(serviceName)"
                                        class="form-control form-control-sm"
                                        @blur="onServiceImageNameBlur(serviceName)"
                                      />
                                      <button
                                        v-if="getServiceConfig(serviceName).imageName"
                                        type="button"
                                        class="btn btn-link btn-sm p-0"
                                        style="font-size: 0.75rem; flex-shrink: 0"
                                        @click="resetServiceImageName(serviceName)"
                                        title="恢复默认"
                                      >
                                        <i class="fas fa-undo"></i>
                                      </button>
                                    </div>
                                    <small class="text-muted d-block mt-1" style="font-size: 0.7rem;">
                                      <i class="fas fa-info-circle"></i> 默认: {{ getServiceDefaultImageName(serviceName) }}
                                    </small>
                                  </td>
                                  <td>
                                    <input
                                      type="text"
                                      v-model="getServiceConfig(serviceName).tag"
                                      :placeholder="formData.tag || 'latest'"
                                      class="form-control form-control-sm"
                                    />
                                  </td>
                                  <td class="text-center">
                                    <input
                                      type="checkbox"
                                      v-model="getServiceConfig(serviceName).push"
                                      class="form-check-input"
                                    />
                                  </td>
                                  <td>
                                    <button
                                      type="button"
                                      class="btn btn-sm btn-outline-danger"
                                      @click="removeService(serviceName)"
                                    >
                                      <i class="fas fa-times"></i> 移除
                                    </button>
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </div>

                      <div v-else-if="!formData.template && !formData.use_project_dockerfile" class="alert alert-info">
                        <i class="fas fa-info-circle"></i> 请先选择 Dockerfile 模板或启用"使用项目中的 Dockerfile"以加载服务列表
                      </div>
                      <div v-else-if="services.length === 0" class="alert alert-info">
                        <i class="fas fa-info-circle"></i> 未检测到多服务配置，将使用单服务模式
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 资源包配置 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'resource' }"
                  role="tabpanel"
                  id="resource-pane"
                >
                  <div class="card">
                    <div class="card-header bg-light d-flex justify-content-between align-items-center">
                      <h6 class="mb-0">
                        <i class="fas fa-archive text-primary"></i> 资源包配置
                      </h6>
                      <button 
                        type="button" 
                        class="btn btn-sm btn-outline-success" 
                        @click="showResourcePackageModal = true"
                        title="添加资源包"
                      >
                        <i class="fas fa-plus"></i> 添加
                      </button>
                    </div>
                    <div class="card-body">
                      <div v-if="formData.resource_package_configs && formData.resource_package_configs.length > 0" class="border rounded p-2">
                        <div 
                          v-for="(pkg, index) in formData.resource_package_configs" 
                          :key="index" 
                          class="d-flex align-items-center justify-content-between mb-2 p-2 bg-light rounded"
                        >
                          <div class="flex-grow-1">
                            <strong>{{ getResourcePackageName(pkg.package_id) }}</strong>
                            <small class="text-muted ms-2">→ {{ pkg.target_path || 'resources' }}</small>
                          </div>
                          <button 
                            type="button" 
                            class="btn btn-sm btn-outline-danger" 
                            @click="removeResourcePackage(index)"
                          >
                            <i class="fas fa-trash"></i>
                          </button>
                        </div>
                      </div>
                      <div v-else class="text-muted small">
                        暂无资源包，点击"添加"按钮添加资源包
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Webhook 设置 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'webhook' }"
                  role="tabpanel"
                  id="webhook-pane"
                >
                  <div class="mb-3">
                    <label class="form-label">Webhook Token（用于 URL）</label>
                    <div class="input-group input-group-sm">
                      <input 
                        v-model="formData.webhook_token" 
                        type="text" 
                        class="form-control font-monospace"
                        placeholder="留空自动生成"
                      >
                      <button 
                        class="btn btn-outline-secondary" 
                        type="button"
                        @click="regenerateWebhookToken"
                        title="重新生成 Token"
                      >
                        <i class="fas fa-sync-alt"></i> 重新生成
                      </button>
                    </div>
                    <small class="text-muted">用于构建 Webhook URL，留空将自动生成 UUID</small>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Webhook 密钥</label>
                    <div class="input-group input-group-sm">
                      <input 
                        v-model="formData.webhook_secret" 
                        type="text" 
                        class="form-control font-monospace"
                        placeholder="留空自动生成"
                      >
                      <button 
                        class="btn btn-outline-secondary" 
                        type="button"
                        @click="regenerateWebhookSecret"
                        title="重新生成密钥"
                      >
                        <i class="fas fa-sync-alt"></i> 重新生成
                      </button>
                    </div>
                    <small class="text-muted">用于验证 Webhook 签名（可选）</small>
                  </div>
                  <div class="mb-3">
                    <label class="form-label"><strong>Webhook 分支策略</strong></label>
                    <div class="btn-group w-100 d-flex" role="group">
                      <input 
                        type="radio" 
                        class="btn-check" 
                        id="strategy-use-push" 
                        value="use_push"
                        v-model="formData.webhook_branch_strategy"
                      >
                      <label class="btn btn-outline-primary flex-fill" for="strategy-use-push" style="white-space: normal; padding: 0.5rem;">
                        <i class="fas fa-code-branch d-block mb-1"></i>
                        <small class="d-block fw-bold">使用推送分支</small>
                        <small class="text-muted d-block" style="font-size: 0.7rem;">所有分支都触发</small>
                      </label>
                      
                      <input 
                        type="radio" 
                        class="btn-check" 
                        id="strategy-filter-match" 
                        value="filter_match"
                        v-model="formData.webhook_branch_strategy"
                      >
                      <label class="btn btn-outline-primary flex-fill" for="strategy-filter-match" style="white-space: normal; padding: 0.5rem;">
                        <i class="fas fa-filter d-block mb-1"></i>
                        <small class="d-block fw-bold">只允许匹配分支</small>
                        <small class="text-muted d-block" style="font-size: 0.7rem;">使用推送分支构建</small>
                      </label>
                      
                      <input 
                        type="radio" 
                        class="btn-check" 
                        id="strategy-use-configured" 
                        value="use_configured"
                        v-model="formData.webhook_branch_strategy"
                      >
                      <label class="btn btn-outline-primary flex-fill" for="strategy-use-configured" style="white-space: normal; padding: 0.5rem;">
                        <i class="fas fa-cog d-block mb-1"></i>
                        <small class="d-block fw-bold">使用配置分支</small>
                        <small class="text-muted d-block" style="font-size: 0.7rem;">所有分支都触发</small>
                      </label>
                    </div>
                    <small class="text-muted d-block mt-2">
                      <span v-if="formData.webhook_branch_strategy === 'use_push'">
                        <i class="fas fa-info-circle"></i> 任何分支推送都会触发，使用推送的分支进行构建
                      </span>
                      <span v-else-if="formData.webhook_branch_strategy === 'filter_match'">
                        <i class="fas fa-info-circle"></i> 只有推送的分支与上方配置的分支一致时才会触发，使用推送的分支构建
                      </span>
                      <span v-else>
                        <i class="fas fa-info-circle"></i> 任何分支推送都会触发，但使用配置的分支进行构建
                      </span>
                    </small>
                  </div>
                
                <!-- 分支标签映射 -->
                <div class="mb-3">
                  <label class="form-label">
                    <strong>分支标签映射</strong>
                    <button 
                      type="button" 
                      class="btn btn-sm btn-outline-success ms-2" 
                      @click="addBranchTagMapping"
                      title="添加映射"
                    >
                      <i class="fas fa-plus"></i> 添加
                    </button>
                  </label>
                  <small class="text-muted d-block mb-2">
                    为不同分支设置不同的镜像标签，支持通配符（如 feature/*）
                  </small>
                  <div v-if="formData.branch_tag_mapping && formData.branch_tag_mapping.length > 0" class="border rounded p-2">
                    <div 
                      v-for="(mapping, index) in formData.branch_tag_mapping" 
                      :key="index" 
                      class="row g-2 mb-2 align-items-center"
                    >
                      <div class="col-md-5">
                        <input 
                          v-model="mapping.branch" 
                          type="text" 
                          class="form-control form-control-sm"
                          placeholder="分支名（如：main 或 feature/*）"
                        >
                      </div>
                      <div class="col-md-1 text-center">
                        <i class="fas fa-arrow-right text-muted"></i>
                      </div>
                      <div class="col-md-5">
                        <input 
                          v-model="mapping.tag" 
                          type="text" 
                          class="form-control form-control-sm"
                          placeholder="标签（如：latest）"
                        >
                      </div>
                      <div class="col-md-1">
                        <button 
                          type="button" 
                          class="btn btn-sm btn-outline-danger" 
                          @click="removeBranchTagMapping(index)"
                          title="删除"
                        >
                          <i class="fas fa-trash"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-muted small">
                    暂无映射，点击"添加"按钮添加分支标签映射
                  </div>
                </div>
                </div>

                <!-- 其他选项 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'other' }"
                  role="tabpanel"
                  id="other-pane"
                >
                <div class="form-check mb-3">
                  <input 
                    v-model="formData.enabled" 
                    class="form-check-input" 
                    type="checkbox" 
                    id="enabledCheck"
                    checked
                  >
                  <label class="form-check-label" for="enabledCheck">
                    启用流水线
                  </label>
                </div>
                <div class="mb-3">
                  <div class="form-check mb-2">
                    <input 
                      v-model="formData.trigger_schedule" 
                      class="form-check-input" 
                      type="checkbox" 
                      id="triggerScheduleCheck"
                    >
                    <label class="form-check-label" for="triggerScheduleCheck">
                      启用定时触发
                    </label>
                  </div>
                  <div v-if="formData.trigger_schedule" class="ms-4">
                    <label class="form-label small">Cron 表达式 <span class="text-danger">*</span></label>
                    <input 
                      v-model="formData.cron_expression" 
                      type="text" 
                      class="form-control form-control-sm font-monospace"
                      placeholder="0 0 * * *"
                      :required="formData.trigger_schedule"
                    >
                    <small class="text-muted">
                      <code>0 0 * * *</code> 每天零点 | 
                      <code>0 */2 * * *</code> 每2小时 | 
                      <code>*/30 * * * *</code> 每30分钟
                    </small>
                  </div>
                </div>
                </div>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeModal" :disabled="saving">取消</button>
            <button type="button" class="btn btn-primary btn-sm" @click="savePipeline" :disabled="saving">
              <span v-if="saving" class="spinner-border spinner-border-sm me-1" style="width: 0.8rem; height: 0.8rem;"></span>
              <i v-else class="fas fa-save"></i> {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>

    <!-- Webhook URL 模态框 -->
    <div v-if="showWebhookModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-link"></i> Webhook URL
            </h5>
            <button type="button" class="btn-close" @click="showWebhookModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Webhook URL</label>
              <div class="input-group">
                <input 
                  :value="webhookUrl" 
                  type="text" 
                  class="form-control form-control-sm font-monospace" 
                  readonly
                  ref="webhookUrlInput"
                >
                <button class="btn btn-outline-secondary btn-sm" @click="copyWebhookUrl">
                  <i class="fas fa-copy"></i> 复制
                </button>
              </div>
            </div>
            <div class="alert alert-info small mb-0">
              <strong>使用说明：</strong><br>
              1. 在 Git 平台（GitHub/GitLab/Gitee）的仓库设置中添加 Webhook<br>
              2. 将上述 URL 粘贴到 Payload URL 中<br>
              3. Content Type 选择 <code>application/json</code><br>
              4. Secret 填写流水线配置的 Webhook 密钥（如果有）<br>
              5. 选择触发事件（通常是 Push events）
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showWebhookModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>

    <!-- 日志查看模态框 -->
    <div v-if="showLogModal" class="modal fade show d-block" style="z-index: 1070;" tabindex="-1">
      <div class="modal-dialog modal-xl" style="max-width: 90%;">
        <div class="modal-content">
          <div class="modal-header" :class="getLogStatusHeaderClass(selectedTask?.status)">
            <h5 class="modal-title">
              <i :class="getLogStatusIcon(selectedTask?.status)"></i>
              任务日志 - {{ selectedTask?.image || '未知' }}:{{ selectedTask?.tag || 'latest' }}
              <span v-if="isLogTaskRunning" class="badge bg-primary ms-2">
                <span class="spinner-border spinner-border-sm me-1" style="width: 0.7rem; height: 0.7rem;"></span> 运行中
              </span>
            </h5>
            <button type="button" class="btn-close" :class="selectedTask?.status === 'failed' ? 'btn-close-white' : ''" @click="closeLogModal"></button>
          </div>
          <div class="modal-body" style="display: flex; flex-direction: column; padding: 0; max-height: 80vh;">
            <!-- 任务信息 -->
            <div v-if="selectedTask" class="p-3 border-bottom">
              <div class="text-muted small">
                任务ID: <code>{{ selectedTask.task_id?.substring(0, 8) || '未知' }}</code>
              </div>
            </div>
            
            <!-- 任务概况（仅已完成/失败/停止时显示） -->
            <div 
              v-if="selectedTask && (selectedTask.status === 'failed' || selectedTask.status === 'completed' || selectedTask.status === 'stopped')" 
              class="p-3 border-bottom" 
              :class="getLogStatusSummaryClass(selectedTask.status)"
            >
              <div class="d-flex align-items-center mb-2">
                <i :class="getLogStatusIcon(selectedTask.status)" class="me-2"></i>
                <strong>{{ getLogStatusText(selectedTask.status) }}</strong>
              </div>
              <div v-if="selectedTask.status === 'failed' && selectedTask.error" class="mt-2">
                <strong>错误信息：</strong>
                <pre class="mb-0 mt-1 p-2 bg-dark text-light rounded" style="font-size: 0.85rem; max-height: 150px; overflow-y: auto;">{{ selectedTask.error }}</pre>
              </div>
              <div v-if="selectedTask.status === 'completed'" class="mt-2 small">
                <div><strong>创建时间：</strong>{{ formatLogTime(selectedTask.created_at) }}</div>
                <div v-if="selectedTask.completed_at"><strong>完成时间：</strong>{{ formatLogTime(selectedTask.completed_at) }}</div>
                <div v-if="selectedTask.completed_at"><strong>耗时：</strong>{{ calculateLogDuration(selectedTask.created_at, selectedTask.completed_at) }}</div>
              </div>
              <div v-if="selectedTask.status === 'stopped'" class="mt-2 small">
                <div><strong>创建时间：</strong>{{ formatLogTime(selectedTask.created_at) }}</div>
                <div v-if="selectedTask.completed_at"><strong>停止时间：</strong>{{ formatLogTime(selectedTask.completed_at) }}</div>
              </div>
            </div>
            
            <!-- 日志内容 -->
            <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column;">
              <div class="p-2 border-bottom d-flex justify-content-between align-items-center">
                <div>
                  <button type="button" class="btn btn-sm btn-outline-secondary" @click="refreshLogs" :disabled="refreshingLogs">
                    <i class="fas fa-sync-alt" :class="{ 'fa-spin': refreshingLogs }"></i> 刷新
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-secondary ms-2" @click="toggleAutoScroll">
                    <i class="fas" :class="autoScroll ? 'fa-pause' : 'fa-play'"></i> {{ autoScroll ? '暂停自动滚动' : '启用自动滚动' }}
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-secondary ms-2" @click="copyLogs">
                    <i class="fas fa-copy"></i> 复制日志
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-info ms-2" @click="scrollLogToTop" title="滚动到顶部">
                    <i class="fas fa-arrow-up"></i> 到顶
                  </button>
                  <button type="button" class="btn btn-sm btn-outline-info ms-2" @click="scrollLogToBottom" title="滚动到底部">
                    <i class="fas fa-arrow-down"></i> 到底
                  </button>
                </div>
              </div>
              <pre 
                ref="logContainer"
                class="bg-dark text-light p-3 mb-0" 
                style="flex: 1; overflow-y: auto; overflow-x: hidden; font-size: 0.85rem; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', monospace; line-height: 1.5; min-height: 0; max-height: 80vh;"
              >{{ taskLogs || '暂无日志' }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeLogModal">关闭</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showLogModal" class="modal-backdrop fade show" style="z-index: 1065;"></div>

    <!-- 历史构建模态框 -->
    <div v-if="showHistoryModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-history"></i> 历史构建 - {{ currentPipeline?.name }}
            </h5>
            <button type="button" class="btn-close" @click="closeHistoryModal"></button>
          </div>
          <div class="modal-body">
            <!-- 过滤选项 -->
            <div class="row mb-3">
              <div class="col-md-4">
                <label class="form-label small">触发来源</label>
                <select v-model="historyFilter.trigger_source" class="form-select form-select-sm" @change="() => { historyPagination.currentPage = 1; loadHistory(); }">
                  <option value="">全部</option>
                  <option value="webhook">Webhook</option>
                  <option value="manual">手动</option>
                  <option value="cron">定时</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label small">任务状态</label>
                <select v-model="historyFilter.status" class="form-select form-select-sm" @change="() => { historyPagination.currentPage = 1; loadHistory(); }">
                  <option value="">全部</option>
                  <option value="pending">等待中</option>
                  <option value="running">进行中</option>
                  <option value="completed">已完成</option>
                  <option value="failed">失败</option>
                </select>
              </div>
              <div class="col-md-4 d-flex align-items-end">
                <button class="btn btn-sm btn-outline-primary" @click="() => { historyPagination.currentPage = 1; loadHistory(); }">
                  <i class="fas fa-sync-alt"></i> 刷新
                </button>
              </div>
            </div>

            <!-- 历史列表 -->
            <div v-if="historyLoading" class="text-center py-4">
              <span class="spinner-border spinner-border-sm"></span> 加载中...
            </div>
            <div v-else-if="historyTasks.length === 0" class="text-center py-4 text-muted">
              <i class="fas fa-inbox fa-2x mb-2"></i>
              <p class="mb-0">暂无历史构建记录</p>
            </div>
            <div v-else class="table-responsive" style="overflow-x: hidden;">
              <table class="table table-sm table-hover" style="table-layout: fixed; width: 100%;">
                <thead>
                  <tr>
                    <th style="width: 9%;">任务ID</th>
                    <th style="width: 9%;">触发来源</th>
                    <th style="width: 9%;">状态</th>
                    <th style="width: 13%;">镜像</th>
                    <th style="width: 12%;">触发时间</th>
                    <th style="width: 12%;">完成时间</th>
                    <th style="width: 18%;">分支/信息</th>
                    <th style="width: 16%;">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="task in historyTasks" :key="task.task_id">
                    <td>
                      <code class="small">{{ task.task_id.substring(0, 8) }}</code>
                    </td>
                    <td>
                      <span v-if="task.trigger_source === 'webhook'" class="badge bg-info">
                        <i class="fas fa-link"></i> Webhook
                      </span>
                      <span v-else-if="task.trigger_source === 'manual'" class="badge bg-success">
                        <i class="fas fa-hand-pointer"></i> 手动
                      </span>
                      <span v-else-if="task.trigger_source === 'cron'" class="badge bg-warning">
                        <i class="fas fa-clock"></i> 定时
                      </span>
                      <span v-else class="badge bg-secondary">未知</span>
                    </td>
                    <td>
                      <span v-if="task.status === 'pending'" class="badge bg-secondary">
                        <i class="fas fa-clock"></i> 等待中
                      </span>
                      <span v-else-if="task.status === 'running'" class="badge bg-primary">
                        <span class="spinner-border spinner-border-sm me-1" style="width: 0.65rem; height: 0.65rem;"></span> 进行中
                      </span>
                      <span v-else-if="task.status === 'completed'" class="badge bg-success">
                        <i class="fas fa-check-circle"></i> 已完成
                      </span>
                      <span v-else-if="task.status === 'failed'" class="badge bg-danger">
                        <i class="fas fa-times-circle"></i> 失败
                      </span>
                      <span v-else-if="task.status === 'deleted'" class="badge bg-secondary">
                        <i class="fas fa-trash"></i> 已删除
                      </span>
                    </td>
                    <td>
                      <small class="font-monospace text-truncate d-block" :title="`${task.image}:${task.tag}`">
                        {{ task.image }}:{{ task.tag }}
                      </small>
                    </td>
                    <td>
                      <small class="text-muted" :title="formatDateTime(task.triggered_at)">
                        {{ formatDateTime(task.triggered_at) }}
                      </small>
                    </td>
                    <td>
                      <small v-if="task.completed_at" class="text-muted" :title="formatDateTime(task.completed_at)">
                        {{ formatDateTime(task.completed_at) }}
                      </small>
                      <small v-else class="text-muted">-</small>
                    </td>
                    <td>
                      <div v-if="task.trigger_info">
                        <span v-if="task.trigger_info.branch" class="badge bg-secondary mb-1">
                          {{ task.trigger_info.branch }}
                        </span>
                        <div v-if="task.trigger_info.platform" class="text-muted small">
                          {{ task.trigger_info.platform }}
                        </div>
                        <div v-if="task.trigger_info.last_commit" class="text-muted small text-truncate" :title="task.trigger_info.last_commit">
                          {{ task.trigger_info.last_commit.substring(0, 40) }}{{ task.trigger_info.last_commit.length > 40 ? '...' : '' }}
                        </div>
                      </div>
                      <small v-else class="text-muted">-</small>
                    </td>
                    <td>
                      <button 
                        v-if="task.status !== 'deleted' && task.task_id"
                        class="btn btn-sm btn-outline-info" 
                        @click.stop="viewTaskLogs(task.task_id, task)"
                        :disabled="viewingLogs === task.task_id"
                        title="查看日志"
                      >
                        <i class="fas fa-terminal"></i> 日志
                        <span v-if="viewingLogs === task.task_id" class="spinner-border spinner-border-sm ms-1"></span>
                      </button>
                      <span v-else class="text-muted small">-</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer">
            <div class="text-muted small me-auto">
              共 {{ historyPagination.total }} 条记录
              <span v-if="historyPagination.total > 0">
                ，第 {{ historyPagination.currentPage }} / {{ Math.ceil(historyPagination.total / historyPagination.pageSize) }} 页
              </span>
            </div>
            <!-- 分页控件 -->
            <nav v-if="historyPagination.total > 0">
              <ul class="pagination pagination-sm mb-0">
                <li class="page-item" :class="{ disabled: historyPagination.currentPage === 1 }">
                  <a class="page-link" href="#" @click.prevent="changeHistoryPage(1)" title="首页">
                    <i class="fas fa-angle-double-left"></i>
                  </a>
                </li>
                <li class="page-item" :class="{ disabled: historyPagination.currentPage === 1 }">
                  <a class="page-link" href="#" @click.prevent="changeHistoryPage(historyPagination.currentPage - 1)" title="上一页">
                    <i class="fas fa-angle-left"></i>
                  </a>
                </li>
                <li class="page-item active">
                  <span class="page-link">{{ historyPagination.currentPage }}</span>
                </li>
                <li class="page-item" :class="{ disabled: historyPagination.currentPage >= Math.ceil(historyPagination.total / historyPagination.pageSize) }">
                  <a class="page-link" href="#" @click.prevent="changeHistoryPage(historyPagination.currentPage + 1)" title="下一页">
                    <i class="fas fa-angle-right"></i>
                  </a>
                </li>
                <li class="page-item" :class="{ disabled: historyPagination.currentPage >= Math.ceil(historyPagination.total / historyPagination.pageSize) }">
                  <a class="page-link" href="#" @click.prevent="changeHistoryPage(Math.ceil(historyPagination.total / historyPagination.pageSize))" title="末页">
                    <i class="fas fa-angle-double-right"></i>
                  </a>
                </li>
              </ul>
            </nav>
            <button type="button" class="btn btn-secondary btn-sm ms-2" @click="closeHistoryModal">关闭</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showHistoryModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>

    <!-- 资源包选择模态框 -->
    <div v-if="showResourcePackageModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-archive"></i> 选择资源包
            </h5>
            <button type="button" class="btn-close" @click="showResourcePackageModal = false"></button>
          </div>
          <div class="modal-body" style="max-height: 60vh; overflow-y: auto;">
            <div v-if="resourcePackages.length === 0" class="text-center py-4 text-muted">
              <i class="fas fa-inbox fa-2x mb-2"></i>
              <p class="mb-0">暂无资源包</p>
              <small class="text-muted">请先在"资源包"标签页上传资源包</small>
            </div>
            <div v-else class="row g-3">
              <div v-for="pkg in resourcePackages" :key="pkg.package_id" class="col-md-6">
                <div class="card h-100" :class="{ 'border-primary': isResourcePackageSelected(pkg.package_id) }">
                  <div class="card-body">
                    <div class="form-check">
                      <input
                        type="checkbox"
                        :value="pkg.package_id"
                        :checked="isResourcePackageSelected(pkg.package_id)"
                        @change="toggleResourcePackage(pkg)"
                        class="form-check-input"
                      />
                      <label class="form-check-label fw-bold">
                        {{ pkg.name }}
                      </label>
                    </div>
                    <small class="text-muted d-block mt-1">{{ pkg.description || '无描述' }}</small>
                    <div v-if="isResourcePackageSelected(pkg.package_id)" class="mt-2">
                      <label class="form-label small">目标路径</label>
                      <input
                        type="text"
                        :value="getResourcePackageConfig(pkg.package_id).target_path"
                        @input="updateResourcePackagePath(pkg.package_id, $event.target.value)"
                        class="form-control form-control-sm"
                        placeholder="resources"
                      />
                      <small class="text-muted d-block mt-1">
                        <i class="fas fa-info-circle"></i>
                        相对路径，如：<code>test/b.txt</code> 或 <code>config/app.conf</code>
                      </small>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="showResourcePackageModal = false">完成</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showResourcePackageModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>

    <!-- 构建配置JSON模态框 -->
    <div v-if="showBuildConfigJsonModal" class="modal fade show" style="display: block; z-index: 1055;" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-code"></i> 构建配置JSON
            </h5>
            <button type="button" class="btn-close" @click="showBuildConfigJsonModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="d-flex justify-content-end mb-2">
              <button 
                type="button"
                class="btn btn-sm btn-outline-primary"
                @click="copyBuildConfigJson"
              >
                <i class="fas fa-copy"></i> 复制JSON
              </button>
            </div>
            <codemirror
              v-model="buildConfigJsonText"
              :style="{ height: '500px', fontSize: '13px' }"
              :disabled="true"
              :extensions="jsonEditorExtensions"
            />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="showBuildConfigJsonModal = false">关闭</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showBuildConfigJsonModal" class="modal-backdrop fade show" style="z-index: 1050;"></div>
  </div>
</template>

<script setup>
import { StreamLanguage } from '@codemirror/language'
import { javascript } from '@codemirror/legacy-modes/mode/javascript'
import { oneDark } from '@codemirror/theme-one-dark'
import axios from 'axios'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { getDockerfilesWithCache } from '../utils/dockerfileCache.js'
import { clearGitCache, getGitCache, getGitInfoWithCache } from '../utils/gitCache.js'
import { getServiceAnalysisWithCache } from '../utils/serviceAnalysisCache.js'

const pipelines = ref([])
const templates = ref([])
const registries = ref([])
const gitSources = ref([])
const loading = ref(false)
const saving = ref(false)  // 正在保存流水线
const running = ref(null)  // 正在运行的流水线ID
const debounceTimers = ref({})  // 防抖定时器
const queuedPipelines = ref(new Set())  // 排队中的流水线ID集合
const loadingServicesTimer = ref(null)  // 加载服务的防抖定时器
const loadingServicesKey = ref('')  // 当前加载服务的唯一标识（用于去重）
const showModal = ref(false)
const showWebhookModal = ref(false)
const showHistoryModal = ref(false)
const webhookUrl = ref('')
const webhookUrlInput = ref(null)
const editingPipeline = ref(null)
const currentPipeline = ref(null)
const historyTasks = ref([])
const historyLoading = ref(false)
const historyFilter = ref({
  trigger_source: '',
  status: ''
})
const historyPagination = ref({
  currentPage: 1,
  pageSize: 20,
  total: 0,
  hasMore: false
})
const showLogModal = ref(false)
const selectedTask = ref(null)
const viewingLogs = ref(null)
const taskLogs = ref('')
const logContainer = ref(null)
const logPollingInterval = ref(null)
const autoScroll = ref(true)
const refreshingLogs = ref(false)
const showResourcePackageModal = ref(false)
const resourcePackages = ref([])  // 资源包列表

// 多服务相关
const services = ref([])  // 服务列表
const loadingServices = ref(false)  // 加载服务中
const servicesError = ref('')  // 服务加载错误

// 分支和 Dockerfile 相关
const branchesAndTags = ref({
  branches: [],
  tags: [],
  default_branch: null,
})
const refreshingBranches = ref(false)  // 正在刷新分支
const availableDockerfiles = ref([])  // 可用的 Dockerfile 列表
const scanningDockerfiles = ref(false)  // 正在扫描 Dockerfile
const dockerfilesError = ref('')  // Dockerfile 扫描错误
const repoVerified = ref(false)  // 仓库是否已验证

const activeTab = ref('basic')  // 当前激活的Tab
const showBuildConfigJsonModal = ref(false)  // 显示构建配置JSON模态框
const buildConfigJsonText = ref('')  // JSON文本内容（用于CodeMirror）

// CodeMirror 扩展配置（JSON模式，使用JavaScript模式）
const jsonEditorExtensions = [
  StreamLanguage.define(javascript),
  oneDark
]

const formData = ref({
  name: '',
  description: '',
  git_url: '',
  branch: '',
  sub_path: '',
  project_type: 'jar',
  template: '',
  image_name: '',
  tag: 'latest',
  push: false,
  webhook_token: '',  // Webhook Token（用于 URL）
  webhook_secret: '',  // Webhook 密钥
  webhook_branch_strategy: 'use_push',  // Webhook分支策略
  branch_tag_mapping: [],  // 分支标签映射
  enabled: true,
  trigger_schedule: false,  // 是否启用定时触发
  cron_expression: '',  // Cron 表达式
  dockerfile_name: 'Dockerfile',  // Dockerfile文件名，默认Dockerfile
  use_project_dockerfile: true,  // 是否使用项目中的 Dockerfile
  source_id: '',  // 数据源ID
  // 多服务配置
  push_mode: 'multi',  // 推送模式：'single' 或 'multi'
  selected_service: '',  // 单服务模式选中的服务
  selected_services: [],  // 多服务模式选中的服务列表
  service_push_config: {},  // 服务推送配置 {服务名: {imageName, tag, push}}
  service_template_params: {},  // 服务模板参数
  resource_package_configs: [],  // 资源包配置
})

onMounted(() => {
  loadPipelines()
  loadTemplates()
  loadRegistries()
  loadGitSources()
  loadResourcePackages()
  
  // 监听构建配置保存事件
  window.addEventListener('buildConfigSaved', () => {
    const configStr = localStorage.getItem('buildConfigEdited')
    if (configStr) {
      try {
        const config = JSON.parse(configStr)
        localStorage.removeItem('buildConfigEdited')
        
        // 将配置填充回表单
        if (config.git_url) formData.value.git_url = config.git_url
        if (config.branch !== undefined) formData.value.branch = config.branch
        if (config.source_id) formData.value.source_id = config.source_id
        if (config.project_type) formData.value.project_type = config.project_type
        if (config.template !== undefined) formData.value.template = config.template || ''
        if (config.use_project_dockerfile !== undefined) formData.value.use_project_dockerfile = config.use_project_dockerfile
        if (config.dockerfile_name) formData.value.dockerfile_name = config.dockerfile_name
        if (config.template_params) formData.value.template_params = config.template_params
        if (config.image_name) formData.value.image_name = config.image_name
        if (config.tag) formData.value.tag = config.tag
        if (config.push_mode) formData.value.push_mode = config.push_mode
        if (config.should_push !== undefined) formData.value.should_push = config.should_push
        if (config.selected_services) formData.value.selected_services = config.selected_services
        if (config.service_push_config) formData.value.service_push_config = config.service_push_config
        if (config.service_template_params) formData.value.service_template_params = config.service_template_params
        if (config.resource_package_ids) formData.value.resource_package_ids = config.resource_package_ids
        
        alert('构建配置已更新')
      } catch (error) {
        console.error('解析构建配置失败:', error)
      }
    }
  })
})

async function loadGitSources() {
  try {
    const res = await axios.get('/api/git-sources')
    gitSources.value = res.data.sources || []
  } catch (error) {
    console.error('加载数据源列表失败:', error)
  }
}

async function onSourceSelected() {
  const sourceId = formData.value.source_id
  if (!sourceId) {
    // 如果清空数据源选择，重置分支
    formData.value.source_id = ''
    formData.value.branch = ''
    repoVerified.value = false
    branchesAndTags.value = { branches: [], tags: [], default_branch: null }
    availableDockerfiles.value = []
    return
  }
  
  const source = gitSources.value.find(s => s.source_id === sourceId)
  if (source) {
    formData.value.git_url = source.git_url
    formData.value.source_id = source.source_id
    
    // 先尝试从缓存获取
    const cached = getGitCache(source.git_url, sourceId)
    if (cached) {
      branchesAndTags.value = cached
      repoVerified.value = true
      
      // 设置默认分支（如果当前没有选择分支，或选择的分支不在列表中）
      if (!formData.value.branch || !cached.branches.includes(formData.value.branch)) {
        formData.value.branch = cached.default_branch || cached.branches[0] || ''
      }
      
      // 如果使用项目 Dockerfile，自动扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles()
        loadServices()
      }
      return
    }
    
    // 如果数据源有分支信息，使用数据源的分支列表和默认分支
    if (source.branches && source.branches.length > 0) {
      branchesAndTags.value = {
        branches: source.branches || [],
        tags: source.tags || [],
        default_branch: source.default_branch || null,
      }
      repoVerified.value = true
      
      // 设置默认分支（如果当前没有选择分支，或选择的分支不在列表中）
      if (!formData.value.branch || !source.branches.includes(formData.value.branch)) {
        formData.value.branch = source.default_branch || source.branches[0] || ''
      }
      
      // 如果使用项目 Dockerfile，自动扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles()
        loadServices()
      }
    } else if (source.default_branch && !formData.value.branch) {
      formData.value.branch = source.default_branch
      // 尝试从缓存获取（如果API数据源没有缓存，尝试从URL缓存获取）
      const urlCached = getGitCache(source.git_url, null)
      if (urlCached) {
        branchesAndTags.value = urlCached
        repoVerified.value = true
      }
    }
  }
}

// 监听 Git URL 变化，自动匹配数据源
watch(() => formData.value.git_url, () => {
  if (!formData.value.git_url) {
    return
  }
  
  // 查找匹配的数据源
  const source = gitSources.value.find(s => s.git_url === formData.value.git_url)
  if (source) {
    // 如果还没有设置 source_id，自动设置
    if (!formData.value.source_id) {
      formData.value.source_id = source.source_id
    }
    
    // 先尝试从缓存获取
    const cached = getGitCache(source.git_url, source.source_id)
    if (cached) {
      branchesAndTags.value = cached
      repoVerified.value = true
      
      // 如果数据源有默认分支且当前没有选择分支，设置默认分支
      if (!formData.value.branch || !cached.branches.includes(formData.value.branch)) {
        formData.value.branch = cached.default_branch || cached.branches[0] || ''
      }
      
      // 如果使用项目 Dockerfile 且有分支，自动扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles()
      }
    } else if (source.branches && source.branches.length > 0) {
      // 如果数据源有分支信息，加载分支列表
      branchesAndTags.value = {
        branches: source.branches || [],
        tags: source.tags || [],
        default_branch: source.default_branch || null,
      }
      repoVerified.value = true
      
      // 如果数据源有默认分支且当前没有选择分支，设置默认分支
      if (source.default_branch && !formData.value.branch) {
        formData.value.branch = source.default_branch
      }
      
      // 如果使用项目 Dockerfile 且有分支，自动扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles()
      }
    } else if (source.default_branch && !formData.value.branch) {
      formData.value.branch = source.default_branch
    }
    
    // 如果使用项目 Dockerfile 且有分支，重新加载服务（数据源变化不是切换 Dockerfile）
    // 注意：这里不立即调用 loadServices，因为 scanDockerfiles 完成后会自动调用
    // 避免重复触发
  }
})

// 监听分支变化（onBranchChanged 已处理 Dockerfile 扫描）

// 监听 Dockerfile 名称变化，如果使用项目 Dockerfile，重新加载服务
watch(() => formData.value.dockerfile_name, (newName, oldName) => {
  // 只有当 Dockerfile 名称真正改变且使用项目 Dockerfile 时才重新加载服务
  if (newName !== oldName && 
      formData.value.use_project_dockerfile && 
      formData.value.git_url && 
      formData.value.branch &&
      newName && // 确保新名称不为空
      oldName) { // 确保是真正的变化（不是初始化）
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:1834',message:'Dockerfile name changed, reloading services',data:{old:oldName,new:newName},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
    // #endregion
    // Dockerfile 名称变化是用户主动切换，需要重新识别服务
    loadServices(true)
  }
})

// 监听模态框显示，确保内容同步（只在显示时更新，避免递归）
watch(showBuildConfigJsonModal, (isVisible) => {
  if (isVisible) {
    // 使用 nextTick 确保在模态框完全显示后再更新
    nextTick(() => {
      buildConfigJsonText.value = buildConfigJson.value
    })
  }
})

// 监听项目类型变化，如果当前选择的模板不再匹配新的项目类型，则清除模板选择
watch(() => formData.value.project_type, (newType, oldType) => {
  if (newType !== oldType && formData.value.template) {
    // 检查当前选择的模板是否匹配新的项目类型
    const currentTemplate = templates.value.find(t => t.name === formData.value.template)
    if (!currentTemplate || currentTemplate.project_type !== newType) {
      // 模板不匹配新的项目类型，清除模板选择并重新加载服务（项目类型变化不是切换 Dockerfile）
      formData.value.template = ''
      if (formData.value.use_project_dockerfile && formData.value.git_url && formData.value.branch) {
        loadServices(false)
      }
    }
  }
})

async function loadPipelines() {
  loading.value = true
  try {
    const res = await axios.get('/api/pipelines')
    pipelines.value = res.data.pipelines || []
    
    // 更新排队状态：检查每个流水线的任务状态
    queuedPipelines.value.clear()
    pipelines.value.forEach(pipeline => {
      // 使用后端返回的队列信息
      if (pipeline.has_queued_tasks || (pipeline.queue_length && pipeline.queue_length > 0)) {
        queuedPipelines.value.add(pipeline.pipeline_id)
      } else if (pipeline.last_build && pipeline.last_build.status === 'pending') {
        // 如果最后构建是 pending，且有正在运行的任务，说明在排队
        const currentTaskStatus = pipeline.current_task_status
        if (currentTaskStatus === 'running' || currentTaskStatus === 'pending') {
          // 有任务正在运行，pending 的任务在排队
          queuedPipelines.value.add(pipeline.pipeline_id)
        }
      }
    })
  } catch (error) {
    console.error('加载流水线列表失败:', error)
    alert('加载流水线列表失败')
  } finally {
    loading.value = false
  }
}

async function loadTemplates() {
  try {
    const res = await axios.get('/api/list-templates')
    templates.value = res.data || []
  } catch (error) {
    console.error('加载模板列表失败:', error)
  }
}

async function loadRegistries() {
  try {
    const res = await axios.get('/api/registries')
    registries.value = res.data.registries || []
  } catch (error) {
    console.error('加载仓库列表失败:', error)
  }
}

function showCreateModal() {
  editingPipeline.value = null
  formData.value = {
    name: '',
    description: '',
    git_url: '',
    branch: '',
    sub_path: '',
    project_type: 'jar',
    template: '',
    image_name: '',
    tag: 'latest',
    push: false,
    webhook_secret: '',
    webhook_branch_strategy: 'use_push',
    branch_tag_mapping: [],
    enabled: true,
    trigger_schedule: false,
    cron_expression: '',
    dockerfile_name: 'Dockerfile',
    source_id: '',
    use_project_dockerfile: true,
    push_mode: 'multi',
    selected_service: '',
    selected_services: [],
    service_push_config: {},
    service_template_params: {},
    resource_package_configs: []
  }
  services.value = []
  loadingServices.value = false
  servicesError.value = ''
  showModal.value = true
}

function editPipeline(pipeline) {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:1918',message:'editPipeline started',data:{pipeline_id:pipeline.id,pipeline_name:pipeline.name,dockerfile_name:pipeline.dockerfile_name,template:pipeline.template,use_project_dockerfile:pipeline.use_project_dockerfile,project_type:pipeline.project_type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion
  editingPipeline.value = pipeline
  activeTab.value = 'basic'  // 重置到第一个Tab
  
  // 查找对应的数据源
  const source = gitSources.value.find(s => 
    s.source_id === pipeline.source_id || s.git_url === pipeline.git_url
  )
  
  // 保存原始配置，避免被扫描覆盖
  const savedDockerfileName = pipeline.dockerfile_name || 'Dockerfile'
  const savedTemplate = pipeline.template || ''
  // 优先使用后端返回的 use_project_dockerfile，如果没有则根据 template 推断
  const savedUseProjectDockerfile = pipeline.use_project_dockerfile !== undefined 
    ? pipeline.use_project_dockerfile 
    : !pipeline.template  // 有模板则 false，无模板则 true
  
  formData.value = {
    name: pipeline.name,
    description: pipeline.description || '',
    git_url: pipeline.git_url,
    branch: pipeline.branch || '',
    sub_path: pipeline.sub_path || '',
    project_type: pipeline.project_type || 'jar',
    template: savedTemplate,
    image_name: pipeline.image_name || '',
    tag: pipeline.tag || 'latest',
    push: pipeline.push || false,
    webhook_token: pipeline.webhook_token || '',
    webhook_secret: pipeline.webhook_secret || '',
    webhook_branch_strategy: getWebhookBranchStrategy(pipeline),
    branch_tag_mapping: pipeline.branch_tag_mapping ? Object.entries(pipeline.branch_tag_mapping).map(([branch, tag]) => ({ branch, tag })) : [],
    enabled: pipeline.enabled !== false,
    trigger_schedule: !!pipeline.cron_expression,  // 如果有cron表达式则启用
    cron_expression: pipeline.cron_expression || '',
    dockerfile_name: savedDockerfileName,
    use_project_dockerfile: savedUseProjectDockerfile,
    source_id: pipeline.source_id || (source ? source.source_id : ''),
    push_mode: pipeline.push_mode || 'multi',
    selected_service: pipeline.selected_services && pipeline.selected_services.length === 1 ? pipeline.selected_services[0] : '',
    selected_services: pipeline.selected_services || [],
    service_push_config: normalizeServicePushConfig(pipeline.service_push_config || {}),
    service_template_params: pipeline.service_template_params || {},
    resource_package_configs: pipeline.resource_package_configs || []
  }
  
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:1956',message:'formData initialized',data:{dockerfile_name:formData.value.dockerfile_name,template:formData.value.template,use_project_dockerfile:formData.value.use_project_dockerfile,branch:formData.value.branch},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion
  
  // 如果数据源有分支信息，加载分支列表
  if (source && source.branches && source.branches.length > 0) {
    branchesAndTags.value = {
      branches: source.branches || [],
      tags: source.tags || [],
      default_branch: source.default_branch || null,
    }
    repoVerified.value = true
    
    // 如果当前分支为空或不在分支列表中，使用默认分支
    if (!formData.value.branch || !source.branches.includes(formData.value.branch)) {
      formData.value.branch = source.default_branch || source.branches[0] || formData.value.branch || ''
    }
    
    // 如果使用项目 Dockerfile，自动扫描 Dockerfile（编辑模式下不会覆盖已保存的配置）
    // 注意：scanDockerfiles(true) 会保持已保存的 dockerfile_name
    if (formData.value.use_project_dockerfile && formData.value.branch) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2015',message:'About to scan Dockerfiles in editPipeline',data:{dockerfile_name:formData.value.dockerfile_name,branch:formData.value.branch,use_project_dockerfile:formData.value.use_project_dockerfile,editing:true},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
      // #endregion
      // 编辑模式下传入 true，确保保持已保存的配置
      scanDockerfiles(true)
    }
  }
  
  // 编辑模式下：先不加载服务列表，直接显示已保存的配置（秒加载）
  // 服务列表在后台异步加载，仅用于验证服务是否还存在，不阻塞界面显示
  if (pipeline.template || pipeline.use_project_dockerfile) {
    // 编辑模式下，先设置一个空的服务列表，避免显示加载状态
    // 已保存的服务选择会直接显示（即使服务列表为空，已选择的也会显示）
    services.value = []
    loadingServices.value = false
    
    // 在后台异步加载服务列表进行验证（不阻塞界面）
    // 使用 setTimeout 确保界面先渲染
    setTimeout(() => {
      loadServices(false).then(() => {
        // 加载完成后，验证已保存的服务是否还存在
        if (formData.value.push_mode === 'multi' && formData.value.selected_services) {
          // 过滤掉不存在的服务
          const validServices = formData.value.selected_services.filter(
            serviceName => services.value.some(s => s.name === serviceName)
          )
          if (validServices.length !== formData.value.selected_services.length) {
            // 有服务不存在，更新选择
            formData.value.selected_services = validServices
            // 清理不存在的服务的配置
            Object.keys(formData.value.service_push_config || {}).forEach(serviceName => {
              if (!services.value.some(s => s.name === serviceName)) {
                delete formData.value.service_push_config[serviceName]
              }
            })
          }
        } else if (formData.value.push_mode === 'single' && formData.value.selected_service) {
          // 单服务模式：检查选中的服务是否还存在
          if (!services.value.some(s => s.name === formData.value.selected_service)) {
            formData.value.selected_service = ''
          }
        }
      }).catch(() => {
        // 加载失败不影响已保存的配置显示
        console.warn('后台验证服务列表失败，但已保存的配置仍然有效')
      })
    }, 100)
  }
  showModal.value = true
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:1980',message:'editPipeline completed',data:{final_dockerfile_name:formData.value.dockerfile_name,final_template:formData.value.template},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
  // #endregion
}

// 添加分支标签映射
function addBranchTagMapping() {
  if (!formData.value.branch_tag_mapping) {
    formData.value.branch_tag_mapping = []
  }
  formData.value.branch_tag_mapping.push({ branch: '', tag: '' })
}

// 删除分支标签映射
function removeBranchTagMapping(index) {
  formData.value.branch_tag_mapping.splice(index, 1)
}

// 根据旧配置获取新的分支策略
function getWebhookBranchStrategy(pipeline) {
  const webhook_branch_filter = pipeline.webhook_branch_filter || false
  const webhook_use_push_branch = pipeline.webhook_use_push_branch !== false  // 默认为true
  
  if (webhook_branch_filter) {
    return 'filter_match'
  } else if (webhook_use_push_branch) {
    return 'use_push'
  } else {
    return 'use_configured'
  }
}

async function savePipeline() {
  // 防止重复提交
  if (saving.value) {
    return
  }
  
  saving.value = true
  try {
    // 将分支标签映射从数组转换为对象
    const branch_tag_mapping = {}
    if (formData.value.branch_tag_mapping && formData.value.branch_tag_mapping.length > 0) {
      formData.value.branch_tag_mapping.forEach(mapping => {
        if (mapping.branch && mapping.tag) {
          branch_tag_mapping[mapping.branch] = mapping.tag
        }
      })
    }
    
    // 根据分支策略设置webhook_branch_filter和webhook_use_push_branch
    let webhook_branch_filter = false
    let webhook_use_push_branch = true
    
    if (formData.value.webhook_branch_strategy === 'filter_match') {
      webhook_branch_filter = true
      webhook_use_push_branch = true
    } else if (formData.value.webhook_branch_strategy === 'use_push') {
      webhook_branch_filter = false
      webhook_use_push_branch = true
    } else {  // use_configured
      webhook_branch_filter = false
      webhook_use_push_branch = false
    }
    
    // 确保 template 和 use_project_dockerfile 的一致性
    // 如果使用项目 Dockerfile，则清空 template
    // 如果使用模板，则确保 use_project_dockerfile 为 false
    if (formData.value.use_project_dockerfile) {
      formData.value.template = ''
    } else {
      // 使用模板时，确保选择了模板
      if (!formData.value.template) {
        alert('请选择 Dockerfile 模板')
        saving.value = false
        return
      }
    }
    
    // 准备提交数据
    const payload = {
      ...formData.value,
      // 确保 use_project_dockerfile 和 template 的一致性
      use_project_dockerfile: formData.value.use_project_dockerfile,
      // 如果使用项目 Dockerfile，template 应该为空字符串
      // 如果使用模板，template 必须有值（不能为空）
      template: formData.value.use_project_dockerfile ? '' : (formData.value.template || ''),
      // 将分支策略转换为旧格式（向后兼容）
      webhook_branch_filter: webhook_branch_filter,
      webhook_use_push_branch: webhook_use_push_branch,
      // 将分支标签映射转换为对象格式
      branch_tag_mapping: Object.keys(branch_tag_mapping).length > 0 ? branch_tag_mapping : null,
      // 如果未启用定时触发，则cron_expression为null
      cron_expression: formData.value.trigger_schedule ? formData.value.cron_expression : null,
      // 传递数据源ID
      source_id: formData.value.source_id || null,
      // 多服务配置：根据推送模式处理
      selected_services: formData.value.push_mode === 'single' && formData.value.selected_service 
        ? [formData.value.selected_service] 
        : formData.value.selected_services && formData.value.selected_services.length > 0
        ? formData.value.selected_services
        : null,
      // 规范化服务推送配置（确保所有配置都是对象格式，包含 push、imageName 和 tag 字段）
      service_push_config: (() => {
        // 只处理已选择的服务
        const selectedServices = formData.value.push_mode === 'single' && formData.value.selected_service 
          ? [formData.value.selected_service] 
          : (formData.value.selected_services || [])
        
        if (selectedServices.length === 0) {
          return null
        }
        
        const config = formData.value.service_push_config || {}
        const normalized = {}
        
        selectedServices.forEach(serviceName => {
          const value = config[serviceName]
          if (typeof value === 'boolean') {
            // 旧格式：只有push字段
            normalized[serviceName] = {
              push: value,
              imageName: getServiceDefaultImageName(serviceName),
              tag: formData.value.tag || 'latest'
            }
          } else if (value && typeof value === 'object') {
            // 获取最终镜像名（自定义或默认）
            const customImageName = value.imageName && value.imageName.trim()
            const finalImageName = customImageName || getServiceDefaultImageName(serviceName)
            // 获取最终标签（自定义或全局）
            const finalTag = (value.tag && value.tag.trim()) || formData.value.tag || 'latest'
            
            normalized[serviceName] = {
              push: value.push !== undefined ? value.push : false,
              imageName: finalImageName,
              tag: finalTag
            }
          } else {
            // 新服务，使用默认值
            normalized[serviceName] = {
              push: false,
              imageName: getServiceDefaultImageName(serviceName),
              tag: formData.value.tag || 'latest'
            }
          }
        })
        
        return Object.keys(normalized).length > 0 ? normalized : null
      })(),
      service_template_params: formData.value.service_template_params && Object.keys(formData.value.service_template_params).length > 0
        ? formData.value.service_template_params
        : null,
      resource_package_configs: formData.value.resource_package_configs && formData.value.resource_package_configs.length > 0
        ? formData.value.resource_package_configs
        : null,
      // Webhook 配置：如果为空字符串，传递 null 让后端自动生成
      webhook_token: formData.value.webhook_token && formData.value.webhook_token.trim() 
        ? formData.value.webhook_token.trim() 
        : null,
      webhook_secret: formData.value.webhook_secret && formData.value.webhook_secret.trim() 
        ? formData.value.webhook_secret.trim() 
        : null
    }
    // 移除webhook_branch_strategy，因为后端不需要这个字段
    delete payload.webhook_branch_strategy
    delete payload.selected_service  // 移除单服务字段，后端不需要
    delete payload.trigger_schedule  // 移除前端字段
    
    // 验证：如果启用定时触发，必须填写cron表达式
    if (payload.trigger_schedule && !payload.cron_expression) {
      alert('请填写 Cron 表达式')
      saving.value = false
      return
    }
    
    // 验证：如果使用模板，必须选择了模板
    if (!payload.use_project_dockerfile && !payload.template) {
      alert('使用模板时必须选择 Dockerfile 模板')
      saving.value = false
      return
    }
    
    // 调试信息
    console.log('保存流水线参数:', {
      use_project_dockerfile: payload.use_project_dockerfile,
      template: payload.template,
      project_type: payload.project_type
    })
    
    if (editingPipeline.value) {
      // 更新
      await axios.put(`/api/pipelines/${editingPipeline.value.pipeline_id}`, payload)
      alert('流水线更新成功')
    } else {
      // 创建
      await axios.post('/api/pipelines', payload)
      alert('流水线创建成功')
    }
    closeModal()
    loadPipelines()
  } catch (error) {
    console.error('保存流水线失败:', error)
    alert(error.response?.data?.detail || '保存流水线失败')
  } finally {
    saving.value = false
  }
}

function closeModal() {
  // 如果正在保存，不允许关闭
  if (saving.value) {
    return
  }
  showModal.value = false
  editingPipeline.value = null
  services.value = []
  loadingServices.value = false
  servicesError.value = ''
  saving.value = false  // 重置保存状态
  // 重置分支和 Dockerfile 相关状态
  branchesAndTags.value = { branches: [], tags: [], default_branch: null }
  availableDockerfiles.value = []
  refreshingBranches.value = false
  scanningDockerfiles.value = false
  dockerfilesError.value = ''
  repoVerified.value = false
}

// 刷新分支列表
async function refreshBranches(forceRefresh = true) {
  const sourceId = formData.value.source_id
  if (!sourceId) {
    if (!formData.value.git_url) {
      alert('请先选择数据源或填写 Git 仓库地址')
      return
    }
    // 如果没有数据源但有 Git URL，使用 verify-git-repo API
    try {
      refreshingBranches.value = true
      
      // 如果强制刷新，先清除缓存
      if (forceRefresh) {
        clearGitCache(formData.value.git_url, null)
      }
      
      // 使用缓存机制获取Git信息
      const data = await getGitInfoWithCache(
        async () => {
          const response = await axios.post('/api/verify-git-repo', {
            git_url: formData.value.git_url,
            source_id: null
          })
          return response.data
        },
        formData.value.git_url,
        null,
        forceRefresh
      )
      
      if (data && data.branches) {
        branchesAndTags.value = {
          branches: data.branches || [],
          tags: data.tags || [],
          default_branch: data.default_branch || null,
        }
        repoVerified.value = true
        
        // 如果当前选择的分支不在新列表中，重置为默认分支
        const currentBranch = formData.value.branch
        if (currentBranch && 
            !branchesAndTags.value.branches.includes(currentBranch) &&
            !branchesAndTags.value.tags.includes(currentBranch)) {
          formData.value.branch = branchesAndTags.value.default_branch || ''
        }
      }
    } catch (error) {
      console.error('刷新分支列表失败:', error)
      alert(error.response?.data?.detail || error.message || '刷新分支列表失败，请稍后重试')
    } finally {
      refreshingBranches.value = false
    }
    return
  }

  const source = gitSources.value.find(s => s.source_id === sourceId)
  if (!source) {
    return
  }

  refreshingBranches.value = true
  try {
    // 如果强制刷新，先清除缓存
    if (forceRefresh) {
      clearGitCache(source.git_url, sourceId)
    }
    
    // 使用缓存机制获取Git信息
    const data = await getGitInfoWithCache(
      async () => {
        const response = await axios.post('/api/verify-git-repo', {
          git_url: source.git_url,
          source_id: sourceId,
        })
        return response.data
      },
      source.git_url,
      sourceId,
      forceRefresh
    )

    if (data && data.branches) {
      // 更新分支和标签列表
      branchesAndTags.value = {
        branches: data.branches || [],
        tags: data.tags || [],
        default_branch: data.default_branch || null,
      }
      repoVerified.value = true

      // 如果当前选择的分支不在新列表中，重置为默认分支
      const currentBranch = formData.value.branch
      if (currentBranch &&
          !branchesAndTags.value.branches.includes(currentBranch) &&
          !branchesAndTags.value.tags.includes(currentBranch)) {
        formData.value.branch = branchesAndTags.value.default_branch || ''
      }
      
      // 如果使用项目 Dockerfile，重新扫描 Dockerfile
      if (formData.value.use_project_dockerfile && formData.value.branch) {
        scanDockerfiles()
      }
    }
  } catch (error) {
    console.error('刷新分支列表失败:', error)
    alert(error.response?.data?.detail || error.message || '刷新分支列表失败，请稍后重试')
  } finally {
    refreshingBranches.value = false
  }
}

// 扫描项目中的 Dockerfile
async function scanDockerfiles(keepCurrentSelection = true, forceRefresh = false) {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2316',message:'scanDockerfiles started',data:{source_id:formData.value.source_id,git_url:formData.value.git_url,dockerfile_name:formData.value.dockerfile_name,branch:formData.value.branch,keep_current_selection:keepCurrentSelection,editing:!!editingPipeline.value},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  // #endregion
  const sourceId = formData.value.source_id
  if (!sourceId && !formData.value.git_url) {
    dockerfilesError.value = '请先选择数据源或填写 Git 仓库地址'
    return
  }

  // 保存当前的 dockerfile_name，避免被覆盖（编辑模式下必须保持）
  const savedDockerfileName = formData.value.dockerfile_name
  // 判断是否是编辑模式（正在编辑已有流水线）
  const isEditing = !!editingPipeline.value || keepCurrentSelection
  // 保存当前已扫描的列表，以便在扫描失败时恢复
  const previousDockerfiles = [...availableDockerfiles.value]

  scanningDockerfiles.value = true
  dockerfilesError.value = ''
  // 注意：不要立即清空 availableDockerfiles，这样下拉框可以继续显示已保存的值
  // 只有在扫描成功后才更新列表

  try {
    // 获取 Git URL 和分支
    let gitUrl = formData.value.git_url
    if (sourceId) {
      const source = gitSources.value.find(s => s.source_id === sourceId)
      if (source) {
        gitUrl = source.git_url
      }
    }
    
    if (!gitUrl) {
      dockerfilesError.value = '无法获取 Git 仓库地址'
      return
    }

    const branch = formData.value.branch || branchesAndTags.value.default_branch || 'main'

    if (!branch) {
      dockerfilesError.value = '请先选择分支'
      return
    }

    // 使用缓存机制获取 Dockerfile 列表
    const dockerfilePaths = await getDockerfilesWithCache(
      async () => {
        // 调用 API 扫描 Dockerfile
        const response = await axios.post('/api/git-sources/scan-dockerfiles', {
          git_url: gitUrl,
          branch: branch,
          source_id: sourceId || null
        })
        return response
      },
      gitUrl,
      branch,
      sourceId || null,
      forceRefresh // 根据参数决定是否强制刷新
    )

    if (dockerfilePaths && dockerfilePaths.length > 0) {
      // 保存完整路径信息（包含路径和文件名）
      const dockerfileList = dockerfilePaths.map(path => {
        const parts = path.split('/')
        return {
          path: path,  // 完整路径，如 "frontend/Dockerfile"
          name: parts[parts.length - 1]  // 文件名，如 "Dockerfile"
        }
      })
      
      // 按路径排序
      dockerfileList.sort((a, b) => {
        // 根目录的 Dockerfile 优先
        if (a.path === 'Dockerfile') return -1
        if (b.path === 'Dockerfile') return 1
        return a.path.localeCompare(b.path)
      })
      
      // 只有在成功扫描到结果时才更新列表
      availableDockerfiles.value = dockerfileList
    } else {
      // 如果 API 返回成功但没有 dockerfiles，保持原列表（如果有）或设为空数组
      // 这样可以保留之前扫描的结果，或者如果是首次扫描则设为空
      if (availableDockerfiles.value.length === 0) {
        // 如果是首次扫描且没有结果，设为空数组
        availableDockerfiles.value = []
      }
      // 否则保持原列表不变
    }
    
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2402',message:'Dockerfiles scanned',data:{count:availableDockerfiles.value.length,saved_dockerfile_name:savedDockerfileName,available_paths:availableDockerfiles.value.map(df=>df.path),is_editing:isEditing,keep_current_selection:keepCurrentSelection},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    
    // 在编辑模式下，始终保持原有的 dockerfile_name，不进行任何自动选择
    // 在新建模式下，只有在当前没有选择时才自动设置
    if (keepCurrentSelection && savedDockerfileName) {
      // 编辑模式或有已保存的选择：始终保持原选择（即使不在新扫描的列表中，下拉框也会显示它）
      formData.value.dockerfile_name = savedDockerfileName
      const currentInList = availableDockerfiles.value.some(df => df.path === savedDockerfileName)
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2412',message:'Dockerfile name preserved (editing mode or has saved selection)',data:{dockerfile_name:savedDockerfileName,in_list:currentInList,is_editing:isEditing},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
    } else if (availableDockerfiles.value.length > 0) {
      // 新建模式且没有保存的选择：自动选择第一个
      if (!savedDockerfileName || savedDockerfileName === '' || savedDockerfileName === 'Dockerfile') {
        // 当前没有选择或只有默认值，自动选择第一个（优先选择根目录的 Dockerfile）
        const rootDockerfile = availableDockerfiles.value.find(df => df.path === 'Dockerfile')
        formData.value.dockerfile_name = rootDockerfile ? 'Dockerfile' : availableDockerfiles.value[0].path
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2420',message:'Dockerfile name auto-selected (new mode, no previous selection)',data:{new:formData.value.dockerfile_name,old:savedDockerfileName},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
        // #endregion
      } else {
        // 有保存的选择（非编辑模式），检查是否在新列表中，如果在则保持，否则选择第一个
        const currentInList = availableDockerfiles.value.some(df => df.path === savedDockerfileName)
        if (currentInList) {
          formData.value.dockerfile_name = savedDockerfileName
        } else {
          const rootDockerfile = availableDockerfiles.value.find(df => df.path === 'Dockerfile')
          formData.value.dockerfile_name = rootDockerfile ? 'Dockerfile' : availableDockerfiles.value[0].path
        }
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2430',message:'Dockerfile name handled (new mode with previous selection)',data:{saved:savedDockerfileName,final:formData.value.dockerfile_name,in_list:currentInList},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
        // #endregion
      }
      // 扫描后重新加载服务（如果是用户主动切换 Dockerfile，传入 true）
      if (formData.value.use_project_dockerfile) {
        // 这里是在扫描 Dockerfile 后，可能是用户切换了 Dockerfile，传入 true 表示需要重新识别
        loadServices(true)
      }
    } else {
      // 没有扫描到 Dockerfile，如果当前选择不为空，保持原选择，否则设为默认值
      if (!savedDockerfileName) {
        formData.value.dockerfile_name = 'Dockerfile'
      }
    }
  } catch (error) {
    console.error('扫描 Dockerfile 失败:', error)
    dockerfilesError.value = error.response?.data?.detail || '扫描 Dockerfile 失败'
    // 扫描失败时不清空列表，保持之前的列表（如果有），这样已保存的值还能显示
    // availableDockerfiles.value 保持原值
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2404',message:'scanDockerfiles error',data:{error:error.message,response:error.response?.data,preserved_list_count:availableDockerfiles.value.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
  } finally {
    scanningDockerfiles.value = false
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2320',message:'scanDockerfiles completed',data:{final_dockerfile_name:formData.value.dockerfile_name},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
  }
}

// 分支变化处理
function onBranchChanged() {
  // 如果切换到新分支且使用项目 Dockerfile，重新扫描 Dockerfile
  if (formData.value.use_project_dockerfile && formData.value.branch && formData.value.git_url) {
    scanDockerfiles()
  }
}

// 加载服务列表（带防抖和去重）
async function loadServices(isDockerfileChanged = false) {
  if (!formData.value.git_url) {
    services.value = []
    return Promise.resolve()
  }

  // 生成唯一标识，用于去重
  const currentKey = `${formData.value.git_url}_${formData.value.branch}_${formData.value.dockerfile_name}_${formData.value.source_id || ''}`
  
  // 如果正在加载相同的服务配置，直接返回
  if (loadingServices.value && loadingServicesKey.value === currentKey) {
    console.log('服务正在加载中，跳过重复请求:', currentKey)
    return Promise.resolve()
  }

  // 清除之前的防抖定时器
  if (loadingServicesTimer.value) {
    clearTimeout(loadingServicesTimer.value)
    loadingServicesTimer.value = null
  }

  // 判断是否是编辑模式
  const isEditing = !!editingPipeline.value
  
  // 编辑模式下且未切换 Dockerfile：不显示加载状态，直接返回（已保存的配置会直接显示）
  if (isEditing && !isDockerfileChanged) {
    // 在后台异步加载服务列表进行验证，但不阻塞界面
    // 先返回，让界面立即显示已保存的配置
    setTimeout(async () => {
      try {
        await loadServicesInternal(isDockerfileChanged, currentKey)
        // 加载完成后验证已保存的服务是否还存在
        if (formData.value.push_mode === 'multi' && formData.value.selected_services) {
          const validServices = formData.value.selected_services.filter(
            serviceName => services.value.some(s => s.name === serviceName)
          )
          if (validServices.length !== formData.value.selected_services.length) {
            formData.value.selected_services = validServices
            Object.keys(formData.value.service_push_config || {}).forEach(serviceName => {
              if (!services.value.some(s => s.name === serviceName)) {
                delete formData.value.service_push_config[serviceName]
              }
            })
          }
        } else if (formData.value.push_mode === 'single' && formData.value.selected_service) {
          if (!services.value.some(s => s.name === formData.value.selected_service)) {
            formData.value.selected_service = ''
          }
        }
      } catch (error) {
        // 后台验证失败不影响已保存的配置显示
        console.warn('后台验证服务列表失败，但已保存的配置仍然有效:', error)
      }
    }, 100)
    return Promise.resolve()
  }
  
  // 新建模式或切换 Dockerfile：使用防抖延迟加载，避免重复触发
  return new Promise((resolve) => {
    loadingServicesTimer.value = setTimeout(async () => {
      loadingServicesTimer.value = null
      try {
        await loadServicesInternal(isDockerfileChanged, currentKey)
        resolve()
      } catch (error) {
        resolve() // 即使出错也 resolve，避免阻塞
      }
    }, 300) // 300ms 防抖延迟
  })
}

// 内部加载服务列表函数
async function loadServicesInternal(isDockerfileChanged = false, currentKey = '') {
  if (!formData.value.git_url) {
    services.value = []
    return Promise.resolve()
  }

  // 生成唯一标识
  const key = currentKey || `${formData.value.git_url}_${formData.value.branch}_${formData.value.dockerfile_name}_${formData.value.source_id || ''}`
  
  // 如果正在加载相同的服务配置，直接返回
  if (loadingServices.value && loadingServicesKey.value === key) {
    console.log('服务正在加载中，跳过重复请求:', key)
    return Promise.resolve()
  }

  // 判断是否是编辑模式
  const isEditing = !!editingPipeline.value
  
  loadingServices.value = true
  loadingServicesKey.value = key
  servicesError.value = ''

  try {
    if (formData.value.use_project_dockerfile) {
      // 使用项目 Dockerfile
      const gitUrl = formData.value.git_url
      const branch = formData.value.branch || null
      const dockerfileName = formData.value.dockerfile_name || 'Dockerfile'
      const sourceId = formData.value.source_id || null
      
      // 使用缓存机制获取服务分析结果
      const servicesList = await getServiceAnalysisWithCache(
        async () => {
          const payload = {
            git_url: gitUrl,
            branch: branch,
            dockerfile_name: dockerfileName,
            source_id: sourceId
          }
          return await axios.post('/api/parse-dockerfile-services', payload)
        },
        gitUrl,
        branch || 'main',
        dockerfileName,
        sourceId,
        false // 不强制刷新，使用缓存
      )
      
      if (servicesList && servicesList.length > 0) {
        services.value = servicesList
        
        // 编辑模式下：保持原有的服务选择和推送模式，只有在切换 Dockerfile 时才重新识别
        if (isEditing && !isDockerfileChanged) {
          // 编辑模式且未切换 Dockerfile：保持原有配置，不做任何自动初始化
          // 只确保已选择的服务在新服务列表中仍然有效
          if (formData.value.push_mode === 'multi' && formData.value.selected_services) {
            // 过滤掉不存在的服务
            formData.value.selected_services = formData.value.selected_services.filter(
              serviceName => services.value.some(s => s.name === serviceName)
            )
            // 清理不存在的服务的配置
            Object.keys(formData.value.service_push_config || {}).forEach(serviceName => {
              if (!services.value.some(s => s.name === serviceName)) {
                delete formData.value.service_push_config[serviceName]
              }
            })
          } else if (formData.value.push_mode === 'single' && formData.value.selected_service) {
            // 单服务模式：检查选中的服务是否还存在
            if (!services.value.some(s => s.name === formData.value.selected_service)) {
              formData.value.selected_service = ''
            }
          }
        } else {
          // 新建模式或切换 Dockerfile：自动初始化服务选择
          if (!formData.value.selected_services || formData.value.selected_services.length === 0) {
            if (formData.value.push_mode === 'multi') {
              formData.value.selected_services = services.value.map(s => s.name)
              initializeServiceConfigs()
            }
          }
        }
      } else {
        services.value = []
        // 如果没有服务，清空选择（但编辑模式下保持推送模式）
        if (!isEditing || isDockerfileChanged) {
          formData.value.selected_services = []
          formData.value.selected_service = ''
        }
      }
    } else if (formData.value.template) {
      // 使用模板
      const res = await axios.get('/api/template-params', {
        params: {
          template: formData.value.template,
          project_type: formData.value.project_type
        }
      })
      const templateServices = res.data.services || []
      if (templateServices.length > 0) {
        services.value = templateServices
        
        // 编辑模式下：保持原有的服务选择和推送模式
        if (isEditing && !isDockerfileChanged) {
          // 编辑模式且未切换模板：保持原有配置
          if (formData.value.push_mode === 'multi' && formData.value.selected_services) {
            // 过滤掉不存在的服务
            formData.value.selected_services = formData.value.selected_services.filter(
              serviceName => services.value.some(s => s.name === serviceName)
            )
            // 清理不存在的服务的配置
            Object.keys(formData.value.service_push_config || {}).forEach(serviceName => {
              if (!services.value.some(s => s.name === serviceName)) {
                delete formData.value.service_push_config[serviceName]
              }
            })
          } else if (formData.value.push_mode === 'single' && formData.value.selected_service) {
            // 单服务模式：检查选中的服务是否还存在
            if (!services.value.some(s => s.name === formData.value.selected_service)) {
              formData.value.selected_service = ''
            }
          }
        } else {
          // 新建模式或切换模板：根据推送模式初始化
          if (!formData.value.selected_services || formData.value.selected_services.length === 0) {
            if (formData.value.push_mode === 'single') {
              formData.value.selected_services = []
            } else {
              formData.value.selected_services = services.value.map(s => s.name)
              initializeServiceConfigs()
            }
          }
        }
      } else {
        services.value = []
        // 如果没有服务，清空选择（但编辑模式下保持推送模式）
        if (!isEditing || isDockerfileChanged) {
          formData.value.selected_services = []
          formData.value.selected_service = ''
        }
      }
    } else {
      services.value = []
    }
  } catch (error) {
    console.error('加载服务列表失败:', error)
    servicesError.value = error.response?.data?.detail || '加载服务列表失败'
    services.value = []
    return Promise.reject(error)
  } finally {
    loadingServices.value = false
    loadingServicesKey.value = '' // 清除加载标识
  }
  
  return Promise.resolve()
}

// 初始化服务配置
function initializeServiceConfigs() {
  if (!formData.value.service_push_config) {
    formData.value.service_push_config = {}
  }
  formData.value.selected_services.forEach(serviceName => {
    if (formData.value.service_push_config[serviceName] === undefined || 
        typeof formData.value.service_push_config[serviceName] === 'boolean') {
      // 如果是布尔值（旧格式），转换为对象格式
      const oldValue = formData.value.service_push_config[serviceName]
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === 'boolean' ? oldValue : false,
        imageName: '',
        tag: ''
      }
    } else if (formData.value.service_push_config[serviceName] && typeof formData.value.service_push_config[serviceName] === 'object') {
      // 确保对象格式包含所有字段
      const config = formData.value.service_push_config[serviceName]
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : '',
        tag: config.tag !== undefined ? config.tag : ''
      }
    }
  })
}

// 推送模式变化
function onPushModeChange() {
  if (formData.value.push_mode === 'single') {
    formData.value.selected_services = []
    formData.value.selected_service = ''
  } else {
    formData.value.selected_service = ''
    if (services.value.length > 0 && (!formData.value.selected_services || formData.value.selected_services.length === 0)) {
      formData.value.selected_services = services.value.map(s => s.name)
      initializeServiceConfigs()
    }
  }
}

// 切换服务选择
function toggleService(serviceName) {
  if (!formData.value.selected_services) {
    formData.value.selected_services = []
  }
  const index = formData.value.selected_services.indexOf(serviceName)
  if (index > -1) {
    formData.value.selected_services.splice(index, 1)
    delete formData.value.service_push_config[serviceName]
  } else {
    formData.value.selected_services.push(serviceName)
    if (formData.value.service_push_config[serviceName] === undefined || 
        typeof formData.value.service_push_config[serviceName] === 'boolean') {
      const oldValue = formData.value.service_push_config[serviceName]
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === 'boolean' ? oldValue : false,
        imageName: '',
        tag: ''
      }
    } else if (formData.value.service_push_config[serviceName] && typeof formData.value.service_push_config[serviceName] === 'object') {
      // 确保包含所有字段
      const config = formData.value.service_push_config[serviceName]
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : '',
        tag: config.tag !== undefined ? config.tag : ''
      }
    }
  }
}

// 服务选择变化
function onServiceSelectionChange() {
  // 移除未选中服务的配置
  Object.keys(formData.value.service_push_config).forEach(serviceName => {
    if (!formData.value.selected_services.includes(serviceName)) {
      delete formData.value.service_push_config[serviceName]
    }
  })
  // 为新选中的服务初始化配置
  formData.value.selected_services.forEach(serviceName => {
    if (formData.value.service_push_config[serviceName] === undefined || 
        typeof formData.value.service_push_config[serviceName] === 'boolean') {
      const oldValue = formData.value.service_push_config[serviceName]
      formData.value.service_push_config[serviceName] = {
        push: typeof oldValue === 'boolean' ? oldValue : false,
        imageName: '',
        tag: ''
      }
    } else if (formData.value.service_push_config[serviceName] && typeof formData.value.service_push_config[serviceName] === 'object') {
      // 确保包含所有字段
      const config = formData.value.service_push_config[serviceName]
      formData.value.service_push_config[serviceName] = {
        push: config.push !== undefined ? config.push : false,
        imageName: config.imageName !== undefined ? config.imageName : '',
        tag: config.tag !== undefined ? config.tag : ''
      }
    }
  })
}

// 全选服务
function selectAllServices() {
  if (services.value.length > 0) {
    formData.value.selected_services = services.value.map(s => s.name)
    initializeServiceConfigs()
  }
}

// 全不选服务
function deselectAllServices() {
  formData.value.selected_services = []
  formData.value.service_push_config = {}
}

// 移除服务
function removeService(serviceName) {
  const index = formData.value.selected_services.indexOf(serviceName)
  if (index > -1) {
    formData.value.selected_services.splice(index, 1)
    delete formData.value.service_push_config[serviceName]
  }
}

// 获取服务配置对象（确保返回对象格式，包含 push、imageName 和 tag 字段）
function getServiceConfig(serviceName) {
  if (!formData.value.service_push_config) {
    formData.value.service_push_config = {}
  }
  // 如果是布尔值（旧格式），转换为对象格式
  if (formData.value.service_push_config[serviceName] === undefined || 
      typeof formData.value.service_push_config[serviceName] === 'boolean') {
    const oldValue = formData.value.service_push_config[serviceName]
    formData.value.service_push_config[serviceName] = {
      push: typeof oldValue === 'boolean' ? oldValue : false,
      imageName: '',
      tag: ''
    }
  } else if (formData.value.service_push_config[serviceName] && typeof formData.value.service_push_config[serviceName] === 'object') {
    // 确保包含所有字段
    const config = formData.value.service_push_config[serviceName]
    formData.value.service_push_config[serviceName] = {
      push: config.push !== undefined ? config.push : false,
      imageName: config.imageName !== undefined ? config.imageName : '',
      tag: config.tag !== undefined ? config.tag : ''
    }
  }
  return formData.value.service_push_config[serviceName]
}

// 获取服务的默认镜像名称（基于全局镜像名称前缀 + 服务名）
function getServiceDefaultImageName(serviceName) {
  if (!serviceName) {
    return formData.value.image_name || 'myapp/demo'
  }
  
  let prefix = formData.value.image_name || 'myapp/demo'
  
  // 去除前缀末尾的斜杠，避免出现双斜杠
  prefix = prefix.replace(/\/+$/, '')
  
  // 如果前缀已经以服务名结尾，直接返回前缀（避免重复拼接）
  // 检查格式：prefix/serviceName 或 prefix//serviceName 等
  const normalizedPrefix = prefix.replace(/\/+$/, '')
  if (normalizedPrefix.endsWith(`/${serviceName}`) || normalizedPrefix === serviceName) {
    return normalizedPrefix
  }
  
  // 如果前缀就是服务名本身，直接返回
  if (prefix === serviceName) {
    return prefix
  }
  
  // 否则拼接服务名（确保只有一个斜杠）
  return `${prefix}/${serviceName}`
}

// 服务镜像名输入框失焦处理
function onServiceImageNameBlur(serviceName) {
  const config = getServiceConfig(serviceName)
  // 如果用户清空了自定义镜像名，确保使用默认值
  if (!config.imageName || !config.imageName.trim()) {
    config.imageName = ''
  }
}

// 恢复默认镜像名
function resetServiceImageName(serviceName) {
  const config = getServiceConfig(serviceName)
  config.imageName = ''
}

// 规范化服务推送配置（将旧格式的布尔值转换为新格式的对象，保留 push、imageName 和 tag 字段）
function normalizeServicePushConfig(config) {
  if (!config || typeof config !== 'object') {
    return {}
  }
  const normalized = {}
  Object.keys(config).forEach(serviceName => {
    const value = config[serviceName]
    // 如果是布尔值（旧格式），转换为对象格式
    if (typeof value === 'boolean') {
      normalized[serviceName] = {
        push: value,
        imageName: '',
        tag: ''
      }
    } else if (value && typeof value === 'object') {
      // 已经是对象格式，保留所有字段
      normalized[serviceName] = {
        push: value.push !== undefined ? value.push : false,
        imageName: value.imageName !== undefined ? value.imageName : '',
        tag: value.tag !== undefined ? value.tag : ''
      }
    }
  })
  return normalized
}


// 加载资源包列表
async function loadResourcePackages() {
  try {
    const res = await axios.get('/api/resource-packages')
    resourcePackages.value = res.data.packages || []
    
    // 编辑模式下：确保已保存的资源包配置中的 target_path 有默认值
    // 如果某个已保存的资源包配置没有 target_path 或为空，使用资源包名称作为默认值（与分步构建一致）
    if (editingPipeline.value && formData.value.resource_package_configs) {
      formData.value.resource_package_configs.forEach(config => {
        if (!config.target_path || config.target_path.trim() === '') {
          const pkg = resourcePackages.value.find(p => p.package_id === config.package_id)
          if (pkg && pkg.name) {
            // 如果路径为空，使用资源包名称（与分步构建一致）
            config.target_path = pkg.name
          } else {
            config.target_path = 'resources'
          }
        }
      })
    }
  } catch (error) {
    console.error('加载资源包列表失败:', error)
  }
}

// 获取资源包名称
function getResourcePackageName(packageId) {
  const pkg = resourcePackages.value.find(p => p.package_id === packageId)
  return pkg ? pkg.name : packageId
}

// 移除资源包
function removeResourcePackage(index) {
  formData.value.resource_package_configs.splice(index, 1)
}

// 检查资源包是否已选择
function isResourcePackageSelected(packageId) {
  return formData.value.resource_package_configs.some(pkg => pkg.package_id === packageId)
}

// 切换资源包选择
function toggleResourcePackage(pkg) {
  const index = formData.value.resource_package_configs.findIndex(p => p.package_id === pkg.package_id)
  if (index > -1) {
    // 取消选择：移除配置
    formData.value.resource_package_configs.splice(index, 1)
  } else {
    // 选择：添加配置，使用默认路径（资源包名称，与分步构建一致）
    const defaultPath = pkg.name || 'resources'
    formData.value.resource_package_configs.push({
      package_id: pkg.package_id,
      target_path: defaultPath  // 默认使用资源包名称作为路径，与分步构建一致
    })
  }
}

// 获取资源包配置
function getResourcePackageConfig(packageId) {
  let config = formData.value.resource_package_configs.find(p => p.package_id === packageId)
  if (!config) {
    // 如果配置不存在，根据资源包信息创建默认配置
    const pkg = resourcePackages.value.find(p => p.package_id === packageId)
    // 编辑模式下，如果已有保存的配置，不应该自动创建新配置
    // 只有在用户主动选择资源包时才创建配置
    // 这里返回一个临时对象，但不添加到列表中（由 toggleResourcePackage 处理）
    return {
      package_id: packageId,
      target_path: pkg ? (pkg.name || 'resources') : 'resources'  // 默认使用资源包名称作为路径
    }
  }
  return config
}

// Dockerfile 来源变化处理
function onDockerfileSourceChange() {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/eabdd98b-6281-463e-ab2f-b0646adc831e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'PipelinePanel.vue:2744',message:'Dockerfile source changed',data:{use_project_dockerfile:formData.value.use_project_dockerfile,template:formData.value.template,dockerfile_name:formData.value.dockerfile_name,git_url:formData.value.git_url,branch:formData.value.branch},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
  // #endregion
  if (formData.value.use_project_dockerfile) {
    // 使用项目 Dockerfile 时，清空模板
    formData.value.template = ''
    // 如果有分支和 Dockerfile，重新加载服务（服务列表依赖于 Dockerfile）
    if (formData.value.git_url && formData.value.branch && formData.value.dockerfile_name) {
      // Dockerfile 来源变化是用户主动切换，需要重新识别服务
      loadServices(true)
    } else if (formData.value.git_url && formData.value.branch) {
      // 如果有分支但没有 Dockerfile，先扫描 Dockerfile（扫描完成后会自动加载服务）
      scanDockerfiles()
    }
  } else {
    // 使用模板时，清空 Dockerfile 名称
    formData.value.dockerfile_name = 'Dockerfile'
    // 如果选择了模板，重新加载服务（切换到模板是用户主动切换）
    if (formData.value.template) {
      loadServices(true)
    }
  }
}

// 模板变化处理
function onTemplateChange() {
  // 选择模板时，确保 use_project_dockerfile 为 false
  if (formData.value.template) {
    formData.value.use_project_dockerfile = false
    // 重新加载服务（模板变化是用户主动切换）
    loadServices(true)
  } else {
    // 清空模板时，如果使用项目 Dockerfile 且有分支，重新加载服务（切换到项目 Dockerfile 是用户主动切换）
    if (formData.value.use_project_dockerfile && formData.value.git_url && formData.value.branch) {
      loadServices(true)
    }
  }
}

// 根据项目类型过滤模板
const filteredTemplates = computed(() => {
  if (!formData.value.project_type) {
    return []
  }
  return templates.value.filter(
    (t) => t.project_type === formData.value.project_type
  )
})

// 构建配置JSON（基于统一的任务配置结构）
const buildConfigJson = computed(() => {
  // 构建服务推送配置（与StepBuildPanel格式一致）
  const servicePushConfig = {}
  if (formData.value.push_mode === 'multi' && formData.value.selected_services && formData.value.selected_services.length > 0) {
    formData.value.selected_services.forEach(serviceName => {
      const config = getServiceConfig(serviceName)
      const customImageName = config.imageName && config.imageName.trim()
      const finalImageName = customImageName || getServiceDefaultImageName(serviceName)
      const finalTag = (config.tag && config.tag.trim()) || formData.value.tag || 'latest'
      
      servicePushConfig[serviceName] = {
        push: config.push || false,
        imageName: finalImageName,
        tag: finalTag
      }
    })
  }
  
  const config = {
    git_url: formData.value.git_url || '',
    image_name: formData.value.image_name || '',
    tag: formData.value.tag || 'latest',
    branch: formData.value.branch || null,
    project_type: formData.value.project_type || 'jar',
    template: formData.value.template || '',
    template_params: formData.value.template_params || {},
    should_push: formData.value.push || false,
    sub_path: formData.value.sub_path || null,
    use_project_dockerfile: formData.value.use_project_dockerfile !== false,
    dockerfile_name: formData.value.dockerfile_name || 'Dockerfile',
    source_id: formData.value.source_id || null,
    selected_services: formData.value.selected_services || [],
    service_push_config: Object.keys(servicePushConfig).length > 0 ? servicePushConfig : {},
    service_template_params: formData.value.service_template_params || {},
    push_mode: formData.value.push_mode || 'multi',
    resource_package_ids: (formData.value.resource_package_configs || []).map(pkg => pkg.package_id || pkg),
  }
  
  // 移除null值和空值（保留false和0）
  Object.keys(config).forEach(key => {
    if (config[key] === null || config[key] === '' || 
        (Array.isArray(config[key]) && config[key].length === 0) ||
        (typeof config[key] === 'object' && !Array.isArray(config[key]) && Object.keys(config[key]).length === 0)) {
      delete config[key]
    }
  })
  
  return JSON.stringify(config, null, 2)
})

// 复制构建配置JSON（带降级方案）
async function copyBuildConfigJson() {
  const text = buildConfigJson.value
  
  // 优先使用 Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      alert('构建配置JSON已复制到剪贴板')
      return
    } catch (err) {
      console.warn('Clipboard API 失败，尝试降级方案:', err)
    }
  }
  
  // 降级方案：使用传统的选择文本方式
  try {
    // 创建临时文本区域
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    textarea.setSelectionRange(0, text.length) // 兼容移动端
    
    // 执行复制
    const successful = document.execCommand('copy')
    document.body.removeChild(textarea)
    
    if (successful) {
      alert('构建配置JSON已复制到剪贴板')
    } else {
      throw new Error('execCommand 复制失败')
    }
  } catch (err) {
    console.error('复制失败:', err)
    // 最后的降级方案：提示用户手动复制
    alert('自动复制失败，请手动选择并复制文本（已自动选中）')
    // 尝试选中 CodeMirror 中的文本
    nextTick(() => {
      const editor = document.querySelector('.cm-editor')
      if (editor) {
        const range = document.createRange()
        range.selectNodeContents(editor)
        const selection = window.getSelection()
        selection.removeAllRanges()
        selection.addRange(range)
      }
    })
  }
}

async function deletePipeline(pipeline) {
  if (!confirm(`确定要删除流水线"${pipeline.name}"吗？`)) {
    return
  }
  
  try {
    await axios.delete(`/api/pipelines/${pipeline.pipeline_id}`)
    alert('流水线已删除')
    loadPipelines()
  } catch (error) {
    console.error('删除流水线失败:', error)
    alert(error.response?.data?.detail || '删除流水线失败')
  }
}

// 手动运行流水线（带防抖）
async function runPipeline(pipeline) {
  const pipelineId = pipeline.pipeline_id
  
  // 防抖：如果已经在处理中，直接返回
  if (running.value === pipelineId || queuedPipelines.value.has(pipelineId)) {
    return
  }
  
  // 清除之前的防抖定时器
  if (debounceTimers.value[pipelineId]) {
    clearTimeout(debounceTimers.value[pipelineId])
  }
  
  // 设置防抖定时器（500ms）
  debounceTimers.value[pipelineId] = setTimeout(async () => {
    // 再次检查是否已经在处理中
    if (running.value === pipelineId || queuedPipelines.value.has(pipelineId)) {
      return
    }
    
    if (!confirm(`确定要运行流水线 "${pipeline.name}" 吗？`)) {
      delete debounceTimers.value[pipelineId]
      return
    }
    
    running.value = pipelineId
    try {
      const res = await axios.post(`/api/pipelines/${pipelineId}/run`)
      
      // 检查任务状态
      if (res.data.status === 'queued') {
        // 任务已加入队列
        queuedPipelines.value.add(pipelineId)
        const queueInfo = res.data.queue_length ? `（队列位置: ${res.data.queue_length}）` : ''
        alert(`流水线已加入队列！${queueInfo}\n分支: ${res.data.branch || '默认'}`)
      } else if (res.data.task_id) {
        // 任务立即运行
        alert(`流水线已启动！\n任务 ID: ${res.data.task_id}\n分支: ${res.data.branch || '默认'}`)
      }
      // 刷新流水线列表（更新触发次数和时间）
      loadPipelines()
    } catch (error) {
      console.error('运行流水线失败:', error)
      const errorMsg = error.response?.data?.detail || '运行流水线失败'
      
      // 如果是409冲突（已有任务运行），说明任务已加入队列
      if (error.response?.status === 409) {
        queuedPipelines.value.add(pipelineId)
        alert(`流水线已加入队列！\n${errorMsg}`)
        loadPipelines()
      } else {
        alert(errorMsg)
      }
    } finally {
      running.value = null
      delete debounceTimers.value[pipelineId]
    }
  }, 500)
}

function showWebhookUrl(pipeline) {
  const baseUrl = window.location.origin
  const token = pipeline.webhook_token || '未设置'
  webhookUrl.value = token !== '未设置' ? `${baseUrl}/api/webhook/${token}` : '请先设置 Webhook Token'
  showWebhookModal.value = true
}

// 重新生成 Webhook Token
function regenerateWebhookToken() {
  if (confirm('确定要重新生成 Webhook Token 吗？重新生成后需要更新 Git 平台的 Webhook URL。')) {
    // 生成新的 UUID
    formData.value.webhook_token = generateUUID()
  }
}

// 重新生成 Webhook Secret
function regenerateWebhookSecret() {
  if (confirm('确定要重新生成 Webhook 密钥吗？重新生成后需要更新 Git 平台的 Webhook Secret。')) {
    // 生成新的 UUID
    formData.value.webhook_secret = generateUUID()
  }
}

// 生成 UUID（简单版本）
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

function copyWebhookUrl() {
  if (webhookUrlInput.value) {
    webhookUrlInput.value.select()
    document.execCommand('copy')
    alert('Webhook URL 已复制到剪贴板')
  }
}

function copyToClipboard(text, label) {
  if (!text) return
  
  // 使用现代 Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      // 显示成功提示
      const btn = event.target.closest('button')
      if (btn) {
        const originalHTML = btn.innerHTML
        btn.innerHTML = '<i class="fas fa-check" style="font-size: 0.7rem; color: green;"></i>'
        setTimeout(() => {
          btn.innerHTML = originalHTML
        }, 1000)
      }
    }).catch(err => {
      console.error('复制失败:', err)
      alert(`复制${label}失败`)
    })
  } else {
    // 降级方案：使用传统方法
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      const btn = event.target.closest('button')
      if (btn) {
        const originalHTML = btn.innerHTML
        btn.innerHTML = '<i class="fas fa-check" style="font-size: 0.7rem; color: green;"></i>'
        setTimeout(() => {
          btn.innerHTML = originalHTML
        }, 1000)
      }
    } catch (err) {
      console.error('复制失败:', err)
      alert(`复制${label}失败`)
    }
    document.body.removeChild(textarea)
  }
}

function getProjectTypeIcon(type) {
  const iconMap = {
    jar: "fab fa-java",
    nodejs: "fab fa-node-js",
    python: "fab fa-python",
    go: "fas fa-code",
    web: "fas fa-globe",
  };
  return iconMap[type] || "fas fa-cube";
}

function getProjectTypeLabel(type) {
  const labelMap = {
    jar: "Java 应用（JAR）",
    nodejs: "Node.js 应用",
    python: "Python 应用",
    go: "Go 应用",
    web: "静态网站",
  };
  return labelMap[type] || type;
}

function getProjectTypeBadgeClass(type) {
  const classes = {
    'jar': 'bg-danger',
    'nodejs': 'bg-success',
    'python': 'bg-info',
    'go': 'bg-primary',
    'web': 'bg-secondary'
  }
  return classes[type] || 'bg-secondary'
}

function formatGitUrl(url) {
  if (!url) return ''
  // 简化显示
  return url.replace('https://', '').replace('http://', '').replace('.git', '')
}

function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const now = new Date()
  const diff = (now - date) / 1000 // 秒
  
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`
  
  return date.toLocaleDateString('zh-CN')
}

function formatDateTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  
  // 格式：YYYY-MM-DD HH:mm:ss
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

function showHistory(pipeline) {
  currentPipeline.value = pipeline
  historyFilter.value = {
    trigger_source: '',
    status: ''
  }
  historyPagination.value = {
    currentPage: 1,
    pageSize: 20,
    total: 0,
    hasMore: false
  }
  showHistoryModal.value = true
  loadHistory()
}

function closeHistoryModal() {
  showHistoryModal.value = false
  currentPipeline.value = null
  historyTasks.value = []
  historyPagination.value = {
    currentPage: 1,
    pageSize: 20,
    total: 0,
    hasMore: false
  }
}

async function loadHistory(page = null) {
  if (!currentPipeline.value) return
  
  // 如果指定了页码，更新当前页
  if (page !== null) {
    historyPagination.value.currentPage = page
  }
  
  historyLoading.value = true
  try {
    const params = new URLSearchParams()
    if (historyFilter.value.trigger_source) {
      params.append('trigger_source', historyFilter.value.trigger_source)
    }
    if (historyFilter.value.status) {
      params.append('status', historyFilter.value.status)
    }
    
    const offset = (historyPagination.value.currentPage - 1) * historyPagination.value.pageSize
    params.append('limit', historyPagination.value.pageSize.toString())
    params.append('offset', offset.toString())
    
    const url = `/api/pipelines/${currentPipeline.value.pipeline_id}/tasks?${params.toString()}`
    const res = await axios.get(url)
    historyTasks.value = res.data.tasks || []
    
    // 更新分页信息
    historyPagination.value.total = res.data.total || 0
    historyPagination.value.hasMore = res.data.has_more || false
  } catch (error) {
    console.error('加载历史构建失败:', error)
    alert('加载历史构建失败')
    historyTasks.value = []
    historyPagination.value.total = 0
    historyPagination.value.hasMore = false
  } finally {
    historyLoading.value = false
  }
}

function changeHistoryPage(page) {
  if (page < 1) return
  const totalPages = Math.ceil(historyPagination.value.total / historyPagination.value.pageSize)
  if (page > totalPages) return
  loadHistory(page)
}

// 判断最后构建是否正在运行
function isLastBuildRunning(pipeline) {
  return pipeline.last_build && (pipeline.last_build.status === 'running' || pipeline.last_build.status === 'pending')
}

// 计算任务是否正在运行（用于日志模态框）
const isLogTaskRunning = computed(() => {
  if (!selectedTask.value) return false
  const status = selectedTask.value.status
  return status === 'running' || status === 'pending'
})

// 获取任务日志
async function fetchTaskLogs(taskId, silent = false) {
  if (!silent) {
    refreshingLogs.value = true
  }
  
  try {
    const res = await axios.get(`/api/build-tasks/${taskId}/logs`)
    const oldLength = taskLogs.value.length
    if (typeof res.data === 'string') {
      taskLogs.value = res.data || '暂无日志'
    } else {
      taskLogs.value = JSON.stringify(res.data, null, 2)
    }
    
    // 如果有新内容，自动滚动到底部
    if (taskLogs.value.length > oldLength && autoScroll.value) {
      setTimeout(() => {
        scrollLogToBottom()
      }, 50)
    }
  } catch (error) {
    console.error('获取任务日志失败:', error)
    taskLogs.value = `获取日志失败: ${error.message || '未知错误'}`
  } finally {
    refreshingLogs.value = false
  }
}

// 滚动日志到底部
// 滚动日志到顶部
function scrollLogToTop() {
  if (logContainer.value) {
    autoScroll.value = false  // 滚动到顶部时关闭自动滚动
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = 0
      }
    })
  }
}

function scrollLogToBottom() {
  if (logContainer.value) {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
}

// 开始日志轮询
function startLogPolling(taskId) {
  stopLogPolling()
  if (selectedTask.value && (selectedTask.value.status === 'running' || selectedTask.value.status === 'pending')) {
    logPollingInterval.value = setInterval(() => {
      fetchTaskLogs(taskId, true)
    }, 2000)
  }
}

// 停止日志轮询
function stopLogPolling() {
  if (logPollingInterval.value) {
    clearInterval(logPollingInterval.value)
    logPollingInterval.value = null
  }
}

// 刷新日志
function refreshLogs() {
  if (selectedTask.value?.task_id) {
    fetchTaskLogs(selectedTask.value.task_id)
  }
}

// 切换自动滚动
function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
  if (autoScroll.value) {
    scrollLogToBottom()
  }
}

// 复制日志
function copyLogs() {
  if (taskLogs.value) {
    navigator.clipboard.writeText(taskLogs.value).then(() => {
      alert('日志已复制到剪贴板')
    }).catch(err => {
      console.error('复制失败:', err)
      alert('复制失败')
    })
  }
}

// 关闭日志模态框
function closeLogModal() {
  showLogModal.value = false
  stopLogPolling()
  taskLogs.value = ''
  selectedTask.value = null
  viewingLogs.value = null
}

// 日志状态相关函数
function getLogStatusHeaderClass(status) {
  if (status === 'failed') return 'bg-danger text-white'
  if (status === 'completed') return 'bg-success text-white'
  if (status === 'stopped') return 'bg-warning text-dark'
  return 'bg-primary text-white'
}

function getLogStatusSummaryClass(status) {
  if (status === 'failed') return 'bg-danger-subtle'
  if (status === 'completed') return 'bg-success-subtle'
  if (status === 'stopped') return 'bg-warning-subtle'
  return ''
}

function getLogStatusIcon(status) {
  if (status === 'failed') return 'fas fa-times-circle'
  if (status === 'completed') return 'fas fa-check-circle'
  if (status === 'stopped') return 'fas fa-stop-circle'
  if (status === 'running') return 'fas fa-spinner fa-spin'
  if (status === 'pending') return 'fas fa-clock'
  return 'fas fa-info-circle'
}

function getLogStatusText(status) {
  if (status === 'failed') return '构建失败'
  if (status === 'completed') return '构建成功'
  if (status === 'stopped') return '构建已停止'
  if (status === 'running') return '构建中'
  if (status === 'pending') return '等待中'
  return '未知状态'
}

function formatLogTime(time) {
  if (!time) return '未知'
  return new Date(time).toLocaleString('zh-CN')
}

function calculateLogDuration(start, end) {
  if (!start || !end) return '未知'
  const startTime = new Date(start).getTime()
  const endTime = new Date(end).getTime()
  const duration = Math.floor((endTime - startTime) / 1000)
  const minutes = Math.floor(duration / 60)
  const seconds = duration % 60
  return `${minutes}分${seconds}秒`
}

function viewTaskLogs(taskId, task) {
  if (!taskId) {
    alert('任务ID不存在，无法查看日志')
    return
  }
  
  if (viewingLogs.value === taskId) {
    return
  }
  
  viewingLogs.value = taskId
  
  // 确保 task 对象有 task_id 属性
  if (task) {
    if (!task.task_id) {
      task = { ...task, task_id: taskId }
    }
    if (!task.image) {
      task.image = task.image_name || '未知'
    }
    if (!task.tag) {
      task.tag = 'latest'
    }
  } else {
    task = { 
      task_id: taskId, 
      status: 'unknown',
      image: '未知',
      tag: 'latest'
    }
  }
  
  selectedTask.value = task
  showLogModal.value = true
  taskLogs.value = '加载中...'
  
  // 加载日志
  fetchTaskLogs(taskId)
  
  // 如果任务正在运行，开始轮询
  if (task.status === 'running' || task.status === 'pending') {
    startLogPolling(taskId)
  }
  
  // 监听任务状态变化
  let statusCheckInterval = setInterval(async () => {
    try {
      const res = await axios.get(`/api/build-tasks/${taskId}`)
      if (res.data && res.data.status) {
        if (selectedTask.value && selectedTask.value.task_id === taskId) {
          selectedTask.value.status = res.data.status
          if (res.data.status === 'completed' || res.data.status === 'failed' || res.data.status === 'stopped') {
            stopLogPolling()
            clearInterval(statusCheckInterval)
            // 刷新一次日志
            fetchTaskLogs(taskId)
            // 刷新流水线列表
            loadPipelines()
          } else if (res.data.status === 'running' || res.data.status === 'pending') {
            startLogPolling(taskId)
          }
        }
      }
    } catch (error) {
      console.error('检查任务状态失败:', error)
    }
  }, 3000)
  
  // 当模态框关闭时，清理状态检查
  const unwatchStatus = watch(() => showLogModal.value, (newVal) => {
    if (!newVal) {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval)
      }
      unwatchStatus()
    }
  })
  
  // 延迟清除 viewingLogs
  setTimeout(() => {
    if (viewingLogs.value === taskId) {
      viewingLogs.value = null
    }
  }, 100)
}
</script>

<style scoped>
.pipeline-panel {
  padding: 1rem;
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

.font-monospace {
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
}

/* 确保操作按钮组不换行 */
.btn-group {
  flex-wrap: nowrap;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
  }
  
  .card-header .btn-group {
    width: 100%;
    margin-top: 0.5rem;
    justify-content: flex-start;
  }
  
  .card-header .btn-group .btn {
    flex: 1;
  }
}
</style>

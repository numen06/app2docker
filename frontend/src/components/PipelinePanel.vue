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
                :disabled="running === pipeline.pipeline_id"
                title="手动运行"
              >
                <i class="fas fa-play"></i>
                <span v-if="running === pipeline.pipeline_id" class="spinner-border spinner-border-sm ms-1"></span>
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
            
            <!-- 当前任务/最后构建（合并显示） -->
            <div class="mb-3" style="min-height: 48px;">
              <div class="d-flex align-items-center justify-content-between mb-1">
                <span class="text-muted" style="font-size: 0.9rem;">
                  {{ isLastBuildRunning(pipeline) ? '当前任务：' : '最后构建：' }}
                </span>
                <!-- 如果最后构建是运行中或等待中，显示为当前任务 -->
                <div v-if="pipeline.last_build && (pipeline.last_build.status === 'running' || pipeline.last_build.status === 'pending')" class="d-flex align-items-center gap-2">
                  <span v-if="pipeline.last_build.status === 'running'" class="badge bg-primary">
                    <span class="spinner-border spinner-border-sm me-1" style="width: 0.7rem; height: 0.7rem;"></span> 运行中
                  </span>
                  <span v-else-if="pipeline.last_build.status === 'pending'" class="badge bg-warning">
                    <i class="fas fa-clock"></i> 等待中
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
                <span v-else class="text-muted" style="font-size: 0.85rem;">暂无</span>
              </div>
              <!-- 显示任务详情 -->
              <div v-if="pipeline.last_build" class="d-flex justify-content-between align-items-center ms-4">
                <small class="text-muted" :title="formatDateTime(pipeline.last_build.completed_at || pipeline.last_build.created_at)" style="font-size: 0.85rem;">
                  {{ formatDateTime(pipeline.last_build.completed_at || pipeline.last_build.created_at) }}
                </small>
                <small class="text-muted">
                  <code style="font-size: 0.85rem;">{{ pipeline.last_build.task_id?.substring(0, 8) || '-' }}</code>
                </small>
              </div>
              <div v-else class="ms-4" style="height: 20px;"></div>
            </div>
            
            <!-- 统计信息 -->
            <div class="border-top pt-2 mt-2" style="min-height: 60px;">
              <div class="row text-center">
                <div class="col-6">
                  <div class="text-muted mb-1" style="font-size: 0.85rem;">触发次数</div>
                  <div class="fw-bold" style="font-size: 1.1rem; min-height: 24px;">{{ pipeline.trigger_count || 0 }}</div>
                </div>
                <div class="col-6">
                  <div class="text-muted mb-1" style="font-size: 0.85rem;">最后触发</div>
                  <div class="small" v-if="pipeline.last_triggered_at" :title="formatDateTime(pipeline.last_triggered_at)" style="font-size: 0.85rem; min-height: 24px;">
                    {{ formatDateTime(pipeline.last_triggered_at) }}
                  </div>
                  <div class="small text-muted" v-else style="font-size: 0.85rem; min-height: 24px;">-</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑流水线模态框 -->
    <div v-if="showModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1" @click.self="closeModal">
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
                    :class="{ active: activeTab === 'build' }"
                    type="button"
                    @click="activeTab = 'build'"
                    id="build-tab"
                  >
                    <i class="fas fa-cogs"></i> 构建配置
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
                    :class="{ active: activeTab === 'services' }"
                    type="button"
                    @click="activeTab = 'services'"
                    id="services-tab"
                  >
                    <i class="fas fa-layer-group"></i> 多服务配置
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
                  <div class="mb-3">
                    <label class="form-label">Git 数据源</label>
                    <select 
                      v-model="selectedSourceId" 
                      class="form-select form-select-sm mb-2"
                      @change="onSourceSelected"
                    >
                      <option value="">-- 选择数据源或手动输入 --</option>
                      <option v-for="source in gitSources" :key="source.source_id" :value="source.source_id">
                        {{ source.name }} ({{ formatGitUrl(source.git_url) }})
                      </option>
                    </select>
                    <div class="form-text small text-muted mb-2">
                      <i class="fas fa-info-circle"></i> 
                      可以从已保存的数据源中选择，或手动输入 Git 仓库地址
                    </div>
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Git 仓库地址 <span class="text-danger">*</span></label>
                    <input 
                      v-model="formData.git_url" 
                      type="text" 
                      class="form-control form-control-sm" 
                      required
                      placeholder="https://github.com/user/repo.git"
                    >
                  </div>
                </div>

                <!-- 构建配置 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'build' }"
                  role="tabpanel"
                  id="build-pane"
                >
                  <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">分支名称</label>
                    <input 
                      v-model="formData.branch" 
                      type="text" 
                      class="form-control form-control-sm"
                      placeholder="main（Webhook触发时使用推送的分支）"
                    >
                    <small class="text-muted">留空则使用推送的分支</small>
                  </div>
                  <div class="col-md-6 mb-3">
                    <label class="form-label">项目类型</label>
                    <select v-model="formData.project_type" class="form-select form-select-sm">
                      <option value="jar">Java (JAR)</option>
                      <option value="nodejs">Node.js</option>
                      <option value="python">Python</option>
                      <option value="go">Go</option>
                      <option value="web">静态网站</option>
                    </select>
                  </div>
                </div>
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">镜像名称 <span class="text-danger">*</span></label>
                    <input 
                      v-model="formData.image_name" 
                      type="text" 
                      class="form-control form-control-sm" 
                      required
                      placeholder="myapp/demo"
                    >
                  </div>
                  <div class="col-md-6 mb-3">
                    <label class="form-label">镜像标签</label>
                    <input 
                      v-model="formData.tag" 
                      type="text" 
                      class="form-control form-control-sm"
                      placeholder="latest"
                    >
                  </div>
                </div>
                <div class="mb-3">
                  <label class="form-label">Dockerfile 来源</label>
                  <div class="btn-group w-100 mb-2" role="group">
                    <input 
                      type="radio" 
                      class="btn-check" 
                      id="use-project-dockerfile" 
                      :value="true"
                      v-model="formData.use_project_dockerfile"
                    >
                    <label class="btn btn-outline-primary" for="use-project-dockerfile">
                      <i class="fas fa-file-code"></i> 使用项目中的 Dockerfile
                    </label>
                    
                    <input 
                      type="radio" 
                      class="btn-check" 
                      id="use-template" 
                      :value="false"
                      v-model="formData.use_project_dockerfile"
                    >
                    <label class="btn btn-outline-primary" for="use-template">
                      <i class="fas fa-layer-group"></i> 使用模板
                    </label>
                  </div>
                  
                  <!-- 使用项目中的 Dockerfile -->
                  <div v-if="formData.use_project_dockerfile" class="mt-2">
                    <label class="form-label">Dockerfile 文件名</label>
                    <input 
                      v-model="formData.dockerfile_name" 
                      type="text" 
                      class="form-control form-control-sm"
                      placeholder="Dockerfile"
                    >
                    <small class="text-muted">默认为 Dockerfile，可自定义文件名</small>
                  </div>
                  
                  <!-- 使用模板 -->
                  <div v-else class="mt-2">
                    <label class="form-label">Dockerfile 模板 <span class="text-danger">*</span></label>
                    <select 
                      v-model="formData.template" 
                      class="form-select form-select-sm" 
                      required
                      @change="onTemplateChange"
                    >
                      <option value="">-- 请选择模板 --</option>
                      <option v-for="tpl in templates" :key="tpl.name" :value="tpl.name">
                        {{ tpl.name }} ({{ tpl.project_type }})
                      </option>
                    </select>
                    <small class="text-muted">选择一个 Dockerfile 模板来生成 Dockerfile</small>
                  </div>
                </div>
                <div class="mb-3">
                  <label class="form-label">子路径</label>
                  <input 
                    v-model="formData.sub_path" 
                    type="text" 
                    class="form-control form-control-sm"
                    placeholder="留空表示根目录"
                  >
                </div>
                </div>

                <!-- 多服务配置 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'services' }"
                  role="tabpanel"
                  id="services-pane"
                >
                  <!-- 推送模式选择 -->
                  <div class="mb-3" v-if="!formData.use_project_dockerfile && formData.template">
                    <label class="form-label">推送模式 <span class="text-danger">*</span></label>
                    <div class="btn-group w-100" role="group">
                      <input 
                        type="radio" 
                        class="btn-check" 
                        id="push-mode-single" 
                        value="single"
                        v-model="formData.push_mode"
                        @change="onPushModeChange"
                      >
                      <label class="btn btn-outline-primary" for="push-mode-single">
                        <i class="fas fa-box"></i> 单服务推送
                      </label>
                      
                      <input 
                        type="radio" 
                        class="btn-check" 
                        id="push-mode-multi" 
                        value="multi"
                        v-model="formData.push_mode"
                        @change="onPushModeChange"
                      >
                      <label class="btn btn-outline-primary" for="push-mode-multi">
                        <i class="fas fa-boxes"></i> 多服务推送
                      </label>
                    </div>
                    <small class="text-muted d-block mt-2">
                      <i class="fas fa-info-circle"></i>
                      <span v-if="formData.push_mode === 'single'">
                        单服务推送：只能选择一个服务，定义镜像名和标签
                      </span>
                      <span v-else>
                        多服务推送：可以批量设置推送、镜像名和标签
                      </span>
                    </small>
                  </div>

                  <!-- 服务列表加载 -->
                  <div v-if="loadingServices" class="text-center py-3">
                    <span class="spinner-border spinner-border-sm"></span> 正在加载服务列表...
                  </div>
                  <div v-else-if="servicesError" class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> {{ servicesError }}
                  </div>
                  
                  <!-- 单服务推送模式 -->
                  <div v-else-if="formData.push_mode === 'single' && !formData.use_project_dockerfile && formData.template && services.length > 0" class="mb-3">
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
                  <div v-else-if="services.length > 0" class="mb-3">
                    <div class="card border-info">
                      <div class="card-header bg-info bg-opacity-10 d-flex justify-content-between align-items-center">
                        <div>
                          <i class="fas fa-server"></i> 服务选择
                          <span class="badge bg-info ms-2">{{ services.length }} 个服务</span>
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
                      <div class="card-body">
                        <!-- 服务列表 -->
                        <div class="row g-2 mb-3">
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

                        <!-- 服务配置 -->
                        <div v-if="formData.selected_services && formData.selected_services.length > 0" class="border-top pt-3">
                          <h6 class="mb-3">
                            <i class="fas fa-cog"></i> 服务推送配置
                            <small class="text-muted">(已选择 {{ formData.selected_services.length }} 个服务)</small>
                          </h6>
                          <div class="table-responsive">
                            <table class="table table-sm table-bordered">
                              <thead>
                                <tr>
                                  <th style="width: 30%">服务名</th>
                                  <th style="width: 20%">推送</th>
                                  <th style="width: 50%">操作</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr v-for="serviceName in formData.selected_services" :key="serviceName">
                                  <td><code>{{ serviceName }}</code></td>
                                  <td class="text-center">
                                    <input
                                      type="checkbox"
                                      v-model="formData.service_push_config[serviceName]"
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
                    </div>
                  </div>
                  <div v-else-if="!formData.template && !formData.use_project_dockerfile" class="alert alert-info">
                    <i class="fas fa-info-circle"></i> 请先选择 Dockerfile 模板或启用"使用项目中的 Dockerfile"以加载服务列表
                  </div>
                  <div v-else-if="services.length === 0" class="alert alert-info">
                    <i class="fas fa-info-circle"></i> 未检测到多服务配置，将使用单服务模式
                  </div>

                  <!-- 资源包配置 -->
                  <div class="mb-3">
                    <label class="form-label">
                      <i class="fas fa-archive"></i> 资源包配置
                      <button 
                        type="button" 
                        class="btn btn-sm btn-outline-success ms-2" 
                        @click="showResourcePackageModal = true"
                        title="添加资源包"
                      >
                        <i class="fas fa-plus"></i> 添加
                      </button>
                    </label>
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

                <!-- Webhook 设置 Tab -->
                <div 
                  class="tab-pane fade" 
                  :class="{ 'show active': activeTab === 'webhook' }"
                  role="tabpanel"
                  id="webhook-pane"
                >
                  <div class="mb-3">
                    <label class="form-label">Webhook 密钥</label>
                    <input 
                      v-model="formData.webhook_secret" 
                      type="text" 
                      class="form-control form-control-sm"
                      placeholder="留空自动生成"
                    >
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
                    v-model="formData.push" 
                    class="form-check-input" 
                    type="checkbox" 
                    id="pushCheck"
                  >
                  <label class="form-check-label" for="pushCheck">
                    构建完成后推送镜像
                  </label>
                </div>
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
            <button type="button" class="btn btn-secondary btn-sm" @click="closeModal">取消</button>
            <button type="button" class="btn btn-primary btn-sm" @click="savePipeline">
              <i class="fas fa-save"></i> 保存
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>

    <!-- Webhook URL 模态框 -->
    <div v-if="showWebhookModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1" @click.self="showWebhookModal = false">
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
    <TaskLogModal 
      v-model="showLogModal" 
      :task="selectedTask"
      @task-status-updated="onTaskStatusUpdated"
    />

    <!-- 历史构建模态框 -->
    <div v-if="showHistoryModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1" @click.self="closeHistoryModal">
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
                <li class="page-item" :class="{ disabled: !historyPagination.hasMore }">
                  <a class="page-link" href="#" @click.prevent="changeHistoryPage(historyPagination.currentPage + 1)" title="下一页">
                    <i class="fas fa-angle-right"></i>
                  </a>
                </li>
                <li class="page-item" :class="{ disabled: !historyPagination.hasMore }">
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
    <div v-if="showResourcePackageModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1" @click.self="showResourcePackageModal = false">
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
                        v-model="getResourcePackageConfig(pkg.package_id).target_path"
                        class="form-control form-control-sm"
                        placeholder="resources"
                      />
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
  </div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, ref, watch } from 'vue'

const pipelines = ref([])
const templates = ref([])
const registries = ref([])
const gitSources = ref([])
const selectedSourceId = ref('')
const loading = ref(false)
const running = ref(null)  // 正在运行的流水线ID
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
const showResourcePackageModal = ref(false)
const resourcePackages = ref([])  // 资源包列表

// 多服务相关
const services = ref([])  // 服务列表
const loadingServices = ref(false)  // 加载服务中
const servicesError = ref('')  // 服务加载错误

const activeTab = ref('basic')  // 当前激活的Tab

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
  webhook_secret: '',
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
})

async function loadGitSources() {
  try {
    const res = await axios.get('/api/git-sources')
    gitSources.value = res.data.sources || []
  } catch (error) {
    console.error('加载数据源列表失败:', error)
  }
}

function onSourceSelected() {
  if (!selectedSourceId.value) {
    return
  }
  
  const source = gitSources.value.find(s => s.source_id === selectedSourceId.value)
  if (source) {
    formData.value.git_url = source.git_url
    if (source.default_branch && !formData.value.branch) {
      formData.value.branch = source.default_branch
    }
  }
}

// 监听 Git URL 变化，自动匹配数据源
watch(() => formData.value.git_url, () => {
  if (!formData.value.git_url || selectedSourceId.value) {
    return
  }
  
  // 查找匹配的数据源
  const source = gitSources.value.find(s => s.git_url === formData.value.git_url)
  if (source) {
    selectedSourceId.value = source.source_id
    if (source.default_branch && !formData.value.branch) {
      formData.value.branch = source.default_branch
    }
  }
})

async function loadPipelines() {
  loading.value = true
  try {
    const res = await axios.get('/api/pipelines')
    pipelines.value = res.data.pipelines || []
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
  selectedSourceId.value = ''
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
  editingPipeline.value = pipeline
  activeTab.value = 'basic'  // 重置到第一个Tab
  // 查找对应的数据源
  const source = gitSources.value.find(s => s.git_url === pipeline.git_url)
  selectedSourceId.value = source ? source.source_id : ''
  
  formData.value = {
    name: pipeline.name,
    description: pipeline.description || '',
    git_url: pipeline.git_url,
    branch: pipeline.branch || '',
    sub_path: pipeline.sub_path || '',
    project_type: pipeline.project_type || 'jar',
    template: pipeline.template || '',
    image_name: pipeline.image_name || '',
    tag: pipeline.tag || 'latest',
    push: pipeline.push || false,
    webhook_secret: pipeline.webhook_secret || '',
    webhook_branch_strategy: getWebhookBranchStrategy(pipeline),
    branch_tag_mapping: pipeline.branch_tag_mapping ? Object.entries(pipeline.branch_tag_mapping).map(([branch, tag]) => ({ branch, tag })) : [],
    enabled: pipeline.enabled !== false,
    trigger_schedule: !!pipeline.cron_expression,  // 如果有cron表达式则启用
    cron_expression: pipeline.cron_expression || '',
    dockerfile_name: pipeline.dockerfile_name || 'Dockerfile',
    // 如果 pipeline 有 template，说明使用的是模板，否则使用项目 Dockerfile
    use_project_dockerfile: !pipeline.template,  // 有模板则 false，无模板则 true
    source_id: pipeline.source_id || '',
    push_mode: pipeline.push_mode || 'multi',
    selected_service: pipeline.selected_services && pipeline.selected_services.length === 1 ? pipeline.selected_services[0] : '',
    selected_services: pipeline.selected_services || [],
    service_push_config: pipeline.service_push_config || {},
    service_template_params: pipeline.service_template_params || {},
    resource_package_configs: pipeline.resource_package_configs || []
  }
  // 加载服务列表
  if (pipeline.template || pipeline.use_project_dockerfile) {
    loadServices()
  }
  showModal.value = true
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
      source_id: selectedSourceId.value || formData.value.source_id || null,
      // 多服务配置：根据推送模式处理
      selected_services: formData.value.push_mode === 'single' && formData.value.selected_service 
        ? [formData.value.selected_service] 
        : formData.value.selected_services && formData.value.selected_services.length > 0
        ? formData.value.selected_services
        : null,
      service_push_config: formData.value.service_push_config && Object.keys(formData.value.service_push_config).length > 0
        ? formData.value.service_push_config
        : null,
      service_template_params: formData.value.service_template_params && Object.keys(formData.value.service_template_params).length > 0
        ? formData.value.service_template_params
        : null,
      resource_package_configs: formData.value.resource_package_configs && formData.value.resource_package_configs.length > 0
        ? formData.value.resource_package_configs
        : null
    }
    // 移除webhook_branch_strategy，因为后端不需要这个字段
    delete payload.webhook_branch_strategy
    delete payload.selected_service  // 移除单服务字段，后端不需要
    delete payload.trigger_schedule  // 移除前端字段
    
    // 验证：如果启用定时触发，必须填写cron表达式
    if (payload.trigger_schedule && !payload.cron_expression) {
      alert('请填写 Cron 表达式')
      return
    }
    
    // 验证：如果使用模板，必须选择了模板
    if (!payload.use_project_dockerfile && !payload.template) {
      alert('使用模板时必须选择 Dockerfile 模板')
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
  }
}

function closeModal() {
  showModal.value = false
  editingPipeline.value = null
  services.value = []
  loadingServices.value = false
  servicesError.value = ''
}

// 加载服务列表
async function loadServices() {
  if (!formData.value.git_url) {
    services.value = []
    return
  }

  loadingServices.value = true
  servicesError.value = ''

  try {
    if (formData.value.use_project_dockerfile) {
      // 使用项目 Dockerfile
      const payload = {
        git_url: formData.value.git_url,
        branch: formData.value.branch || null,
        dockerfile_name: formData.value.dockerfile_name || 'Dockerfile',
        source_id: selectedSourceId.value || formData.value.source_id || null
      }
      const res = await axios.post('/api/parse-dockerfile-services', payload)
      if (res.data.services && res.data.services.length > 0) {
        services.value = res.data.services
        // 如果之前没有选择服务，默认全选
        if (!formData.value.selected_services || formData.value.selected_services.length === 0) {
          formData.value.selected_services = services.value.map(s => s.name)
          initializeServiceConfigs()
        }
      } else {
        services.value = []
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
        // 如果之前没有选择服务，根据推送模式初始化
        if (!formData.value.selected_services || formData.value.selected_services.length === 0) {
          if (formData.value.push_mode === 'single') {
            formData.value.selected_services = []
          } else {
            formData.value.selected_services = services.value.map(s => s.name)
            initializeServiceConfigs()
          }
        }
      } else {
        services.value = []
      }
    } else {
      services.value = []
    }
  } catch (error) {
    console.error('加载服务列表失败:', error)
    servicesError.value = error.response?.data?.detail || '加载服务列表失败'
    services.value = []
  } finally {
    loadingServices.value = false
  }
}

// 初始化服务配置
function initializeServiceConfigs() {
  if (!formData.value.service_push_config) {
    formData.value.service_push_config = {}
  }
  formData.value.selected_services.forEach(serviceName => {
    if (formData.value.service_push_config[serviceName] === undefined) {
      formData.value.service_push_config[serviceName] = false
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
    if (formData.value.service_push_config[serviceName] === undefined) {
      formData.value.service_push_config[serviceName] = false
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
    if (formData.value.service_push_config[serviceName] === undefined) {
      formData.value.service_push_config[serviceName] = false
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


// 加载资源包列表
async function loadResourcePackages() {
  try {
    const res = await axios.get('/api/resource-packages')
    resourcePackages.value = res.data.packages || []
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
    formData.value.resource_package_configs.splice(index, 1)
  } else {
    formData.value.resource_package_configs.push({
      package_id: pkg.package_id,
      target_path: 'resources'
    })
  }
}

// 获取资源包配置
function getResourcePackageConfig(packageId) {
  let config = formData.value.resource_package_configs.find(p => p.package_id === packageId)
  if (!config) {
    config = {
      package_id: packageId,
      target_path: 'resources'
    }
    formData.value.resource_package_configs.push(config)
  }
  return config
}

// 模板变化处理
function onTemplateChange() {
  // 选择模板时，确保 use_project_dockerfile 为 false
  if (formData.value.template) {
    formData.value.use_project_dockerfile = false
  }
}

// 监听 use_project_dockerfile 变化
watch(() => formData.value.use_project_dockerfile, (newVal) => {
  if (newVal) {
    // 使用项目 Dockerfile 时，清空模板
    formData.value.template = ''
  }
})

// 监听模板和 use_project_dockerfile 变化，自动加载服务
watch(() => [formData.value.template, formData.value.use_project_dockerfile, formData.value.git_url, formData.value.branch], () => {
  if (formData.value.git_url && (formData.value.template || formData.value.use_project_dockerfile)) {
    loadServices()
  }
}, { deep: true })

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

// 手动运行流水线
async function runPipeline(pipeline) {
  if (running.value) return
  
  if (!confirm(`确定要运行流水线 "${pipeline.name}" 吗？`)) {
    return
  }
  
  running.value = pipeline.pipeline_id
  try {
    const res = await axios.post(`/api/pipelines/${pipeline.pipeline_id}/run`)
    
    if (res.data.task_id) {
      alert(`流水线已启动！\n任务 ID: ${res.data.task_id}\n分支: ${res.data.branch || '默认'}`)
      // 刷新流水线列表（更新触发次数和时间）
      loadPipelines()
    }
  } catch (error) {
    console.error('运行流水线失败:', error)
    alert(error.response?.data?.detail || '运行流水线失败')
  } finally {
    running.value = null
  }
}

function showWebhookUrl(pipeline) {
  const baseUrl = window.location.origin
  webhookUrl.value = `${baseUrl}/api/webhook/${pipeline.webhook_token}`
  showWebhookModal.value = true
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
  const icons = {
    'jar': 'fab fa-java',
    'nodejs': 'fab fa-node-js',
    'python': 'fab fa-python',
    'go': 'fab fa-golang',
    'rust': 'fas fa-cog',
    'static': 'fas fa-globe'
  }
  return icons[type] || 'fas fa-file-code'
}

function getProjectTypeLabel(type) {
  const labels = {
    'jar': 'Java 应用',
    'nodejs': 'Node.js 应用',
    'python': 'Python 应用',
    'go': 'Go 应用',
    'rust': 'Rust 应用',
    'static': '静态网站'
  }
  return labels[type] || type
}

function getProjectTypeBadgeClass(type) {
  const classes = {
    'jar': 'bg-danger',
    'nodejs': 'bg-success',
    'python': 'bg-info',
    'go': 'bg-primary',
    'rust': 'bg-dark',
    'static': 'bg-secondary'
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

// 任务状态更新处理
function onTaskStatusUpdated(newStatus) {
  if (selectedTask.value) {
    selectedTask.value.status = newStatus
    // 如果任务状态改变，刷新流水线列表
    if (newStatus === 'completed' || newStatus === 'failed') {
      loadPipelines()
    }
  }
}

function viewTaskLogs(taskId, task) {
  if (!taskId) {
    console.error('viewTaskLogs: taskId 为空', { taskId, task })
    alert('任务ID不存在，无法查看日志')
    return
  }
  
  if (viewingLogs.value === taskId) {
    // 如果正在查看同一个任务的日志，直接返回
    return
  }
  
  viewingLogs.value = taskId
  
  // 确保 task 对象有 task_id 属性
  if (task) {
    if (!task.task_id) {
      task = { ...task, task_id: taskId }
    }
  } else {
    // 如果 task 为空，创建一个基本的 task 对象
    task = { 
      task_id: taskId, 
      status: 'unknown',
      image: '未知',
      tag: 'latest'
    }
  }
  
  selectedTask.value = task
  showLogModal.value = true
  
  // 延迟清除 viewingLogs，避免重复点击
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

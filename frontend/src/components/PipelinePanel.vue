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
              <div class="d-flex align-items-center justify-content-between mb-1">
                <h5 class="card-title mb-0">
                  <strong>{{ pipeline.name }}</strong>
                  <span v-if="pipeline.enabled" class="badge bg-success ms-2">
                    <i class="fas fa-check-circle"></i> 已启用
                  </span>
                  <span v-else class="badge bg-secondary ms-2">
                    <i class="fas fa-times-circle"></i> 已禁用
                  </span>
                </h5>
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
            <div class="mb-3">
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
              <div class="d-flex align-items-center flex-wrap gap-2 ms-4">
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
            <div class="mb-3">
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
            </div>
            
            <!-- 当前任务状态 -->
            <div class="mb-3" v-if="pipeline.current_task_info">
              <div class="d-flex align-items-center justify-content-between">
                <span class="text-muted" style="font-size: 0.9rem;">当前任务：</span>
                <span v-if="pipeline.current_task_status === 'running'" class="badge bg-primary">
                  <span class="spinner-border spinner-border-sm me-1" style="width: 0.7rem; height: 0.7rem;"></span> 运行中
                </span>
                <span v-else-if="pipeline.current_task_status === 'pending'" class="badge bg-warning">
                  <i class="fas fa-clock"></i> 等待中
                </span>
              </div>
            </div>
            
            <!-- 最后构建 -->
            <div class="mb-3" v-if="pipeline.last_build">
              <div class="d-flex align-items-center justify-content-between mb-1">
                <span class="text-muted" style="font-size: 0.9rem;">最后构建：</span>
                <div class="d-flex align-items-center gap-2">
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
                    v-if="pipeline.last_build.task_id && pipeline.last_build.status !== 'deleted'"
                    class="btn btn-sm btn-outline-info p-1" 
                    style="width: 24px; height: 24px; line-height: 1;"
                    @click="viewTaskLogs(pipeline.last_build.task_id, pipeline.last_build)"
                    title="查看日志"
                  >
                    <i class="fas fa-terminal" style="font-size: 0.75rem;"></i>
                  </button>
                </div>
              </div>
              <div class="d-flex justify-content-between align-items-center ms-4">
                <small class="text-muted" :title="formatDateTime(pipeline.last_build.completed_at || pipeline.last_build.created_at)" style="font-size: 0.85rem;">
                  {{ formatDateTime(pipeline.last_build.completed_at || pipeline.last_build.created_at) }}
                </small>
                <small class="text-muted">
                  <code style="font-size: 0.85rem;">{{ pipeline.last_build.task_id.substring(0, 8) }}</code>
                </small>
              </div>
            </div>
            <div v-else class="mb-3">
              <span class="text-muted" style="font-size: 0.9rem;">最后构建：暂无</span>
            </div>
            
            <!-- 统计信息 -->
            <div class="border-top pt-2 mt-2">
              <div class="row text-center">
                <div class="col-6">
                  <div class="text-muted mb-1" style="font-size: 0.85rem;">触发次数</div>
                  <div class="fw-bold" style="font-size: 1.1rem;">{{ pipeline.trigger_count || 0 }}</div>
                </div>
                <div class="col-6">
                  <div class="text-muted mb-1" style="font-size: 0.85rem;">最后触发</div>
                  <div class="small" v-if="pipeline.last_triggered_at" :title="formatDateTime(pipeline.last_triggered_at)" style="font-size: 0.85rem;">
                    {{ formatDateTime(pipeline.last_triggered_at) }}
                  </div>
                  <div class="small text-muted" v-else style="font-size: 0.85rem;">-</div>
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
                  <label class="form-label">Dockerfile 模板</label>
                  <select v-model="formData.template" class="form-select form-select-sm">
                    <option value="">使用项目中的 Dockerfile</option>
                    <option v-for="tpl in templates" :key="tpl.name" :value="tpl.name">
                      {{ tpl.name }} ({{ tpl.project_type }})
                    </option>
                  </select>
                </div>
                <div class="mb-3">
                  <label class="form-label">Dockerfile 文件名</label>
                  <input 
                    v-model="formData.dockerfile_name" 
                    type="text" 
                    class="form-control form-control-sm"
                    placeholder="Dockerfile"
                  >
                  <small class="text-muted">默认为 Dockerfile，可自定义文件名（当使用项目中的 Dockerfile 时）</small>
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
    <div v-if="showLogModal && selectedTask" class="modal fade show" style="display: block; z-index: 1070;" tabindex="-1" @click.self="closeLogModal">
      <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-terminal"></i> 任务日志 - {{ selectedTask.image || '未知' }}:{{ selectedTask.tag || 'latest' }}
            </h5>
            <button type="button" class="btn-close" @click="closeLogModal"></button>
          </div>
          <div class="modal-body">
            <pre class="bg-dark text-light p-3 rounded" style="max-height: 500px; overflow-y: auto; font-size: 0.85rem; white-space: pre-wrap; word-wrap: break-word;">{{ taskLogs }}</pre>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeLogModal">关闭</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showLogModal" class="modal-backdrop fade show" style="z-index: 1065;"></div>

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
                <select v-model="historyFilter.trigger_source" class="form-select form-select-sm" @change="loadHistory">
                  <option value="">全部</option>
                  <option value="webhook">Webhook</option>
                  <option value="manual">手动</option>
                  <option value="cron">定时</option>
                </select>
              </div>
              <div class="col-md-4">
                <label class="form-label small">任务状态</label>
                <select v-model="historyFilter.status" class="form-select form-select-sm" @change="loadHistory">
                  <option value="">全部</option>
                  <option value="pending">等待中</option>
                  <option value="running">进行中</option>
                  <option value="completed">已完成</option>
                  <option value="failed">失败</option>
                </select>
              </div>
              <div class="col-md-4 d-flex align-items-end">
                <button class="btn btn-sm btn-outline-primary" @click="loadHistory">
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
                        @click="viewTaskLogs(task.task_id, task)"
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
            <div class="text-muted small">
              共 {{ historyTasks.length }} 条记录
            </div>
            <button type="button" class="btn btn-secondary btn-sm" @click="closeHistoryModal">关闭</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showHistoryModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, ref, inject, watch } from 'vue'

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
const showLogModal = ref(false)
const selectedTask = ref(null)
const taskLogs = ref('')
const viewingLogs = ref(null)

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
})

onMounted(() => {
  loadPipelines()
  loadTemplates()
  loadRegistries()
  loadGitSources()
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
    source_id: ''
  }
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
    
    // 准备提交数据
    const payload = {
      ...formData.value,
      // 将分支策略转换为旧格式（向后兼容）
      webhook_branch_filter: webhook_branch_filter,
      webhook_use_push_branch: webhook_use_push_branch,
      // 将分支标签映射转换为对象格式
      branch_tag_mapping: Object.keys(branch_tag_mapping).length > 0 ? branch_tag_mapping : null,
      // 如果未启用定时触发，则cron_expression为null
      cron_expression: formData.value.trigger_schedule ? formData.value.cron_expression : null,
      // 传递数据源ID
      source_id: selectedSourceId.value || null
    }
    // 移除webhook_branch_strategy，因为后端不需要这个字段
    delete payload.webhook_branch_strategy
    
    // 验证：如果启用定时触发，必须填写cron表达式
    if (payload.trigger_schedule && !payload.cron_expression) {
      alert('请填写 Cron 表达式')
      return
    }
    
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
  showHistoryModal.value = true
  loadHistory()
}

function closeHistoryModal() {
  showHistoryModal.value = false
  currentPipeline.value = null
  historyTasks.value = []
}

async function loadHistory() {
  if (!currentPipeline.value) return
  
  historyLoading.value = true
  try {
    const params = new URLSearchParams()
    if (historyFilter.value.trigger_source) {
      params.append('trigger_source', historyFilter.value.trigger_source)
    }
    if (historyFilter.value.status) {
      params.append('status', historyFilter.value.status)
    }
    params.append('limit', '100')
    
    const url = `/api/pipelines/${currentPipeline.value.pipeline_id}/tasks?${params.toString()}`
    const res = await axios.get(url)
    historyTasks.value = res.data.tasks || []
  } catch (error) {
    console.error('加载历史构建失败:', error)
    alert('加载历史构建失败')
    historyTasks.value = []
  } finally {
    historyLoading.value = false
  }
}

async function viewTaskLogs(taskId, task) {
  if (viewingLogs.value) return
  
  viewingLogs.value = taskId
  selectedTask.value = task
  showLogModal.value = true
  taskLogs.value = '加载中...'
  
  try {
    const res = await axios.get(`/api/build-tasks/${taskId}/logs`)
    // 直接使用 res.data,不设置 responseType
    if (typeof res.data === 'string') {
      taskLogs.value = res.data || '暂无日志'
    } else {
      // 如果返回的不是字符串,尝试转换
      taskLogs.value = JSON.stringify(res.data, null, 2)
    }
  } catch (err) {
    console.error('获取日志失败:', err)
    const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || '未知错误'
    taskLogs.value = `加载日志失败: ${errorMsg}`
  } finally {
    viewingLogs.value = null
  }
}

function closeLogModal() {
  showLogModal.value = false
  selectedTask.value = null
  taskLogs.value = ''
  viewingLogs.value = null
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

<template>
  <div class="data-source-panel">
    <!-- Tab 导航 -->
    <ul class="nav nav-tabs mb-3">
      <li class="nav-item">
        <button 
          type="button" 
          class="nav-link" 
          :class="{ active: activeSubTab === 'git' }" 
          @click="activeSubTab = 'git'"
        >
          <i class="fas fa-code-branch"></i> Git 数据源
        </button>
      </li>
      <li class="nav-item">
        <button 
          type="button" 
          class="nav-link" 
          :class="{ active: activeSubTab === 'registry' }" 
          @click="activeSubTab = 'registry'"
        >
          <i class="fas fa-box"></i> 镜像仓库
        </button>
      </li>
    </ul>

    <!-- Git 数据源 Tab -->
    <div v-show="activeSubTab === 'git'">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0">
          <i class="fas fa-database"></i> Git 数据源管理
        </h5>
        <div class="d-flex gap-2">
          <button 
            class="btn btn-outline-secondary btn-sm" 
            @click="loadSources"
            :disabled="loading"
            title="刷新列表"
          >
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i> 刷新
          </button>
          <button class="btn btn-primary btn-sm" @click="showCreateModal">
            <i class="fas fa-plus"></i> 新建数据源
          </button>
        </div>
      </div>

      <!-- 数据源列表 -->
      <div v-if="loading" class="text-center py-5">
      <span class="spinner-border spinner-border-sm"></span> 加载中...
    </div>
      <div v-else-if="sources.length === 0" class="text-center py-5 text-muted">
        <i class="fas fa-inbox fa-3x mb-3"></i>
        <p class="mb-0">暂无数据源</p>
        <p class="text-muted small mt-2">在镜像构建或流水线中验证 Git 仓库时可保存为数据源</p>
      </div>
      <div v-else class="row g-4">
      <div v-for="source in sources" :key="source.source_id" class="col-12 col-md-6 col-xl-4">
        <div class="card h-100 shadow-sm">
          <div class="card-header bg-white">
            <div class="mb-2">
              <h5 class="card-title mb-0">
                <strong>{{ source.name }}</strong>
              </h5>
              <p class="text-muted mb-0 mt-1" v-if="source.description" style="font-size: 0.9rem;">
                {{ source.description }}
              </p>
            </div>
            <div class="btn-group btn-group-sm w-100">
              <button 
                class="btn btn-outline-info" 
                @click="refreshSource(source)"
                :disabled="refreshing === source.source_id"
                title="刷新分支和标签"
              >
                <i class="fas fa-sync-alt" :class="{ 'fa-spin': refreshing === source.source_id }"></i>
              </button>
              <button 
                class="btn btn-outline-primary" 
                @click="editSource(source)"
                title="编辑"
              >
                <i class="fas fa-edit"></i>
              </button>
              <button 
                class="btn btn-outline-danger" 
                @click="deleteSource(source)"
                title="删除"
              >
                <i class="fas fa-trash"></i>
              </button>
            </div>
          </div>
          
          <div class="card-body">
            <div class="mb-3">
              <div class="d-flex align-items-center mb-1">
                <i class="fas fa-code-branch text-muted me-2" style="width: 18px;"></i>
                <small class="font-monospace text-truncate" :title="source.git_url" style="font-size: 0.9rem;">
                  {{ formatGitUrl(source.git_url) }}
                </small>
              </div>
            </div>
            
            <div class="mb-3">
              <div class="d-flex align-items-center mb-1">
                <i class="fas fa-code-branch text-muted me-2" style="width: 18px;"></i>
                <small class="text-muted">分支：{{ source.branches?.length || 0 }} 个</small>
              </div>
              <div class="d-flex align-items-center mb-1">
                <i class="fas fa-tag text-muted me-2" style="width: 18px;"></i>
                <small class="text-muted">标签：{{ source.tags?.length || 0 }} 个</small>
              </div>
              <div v-if="source.default_branch" class="d-flex align-items-center mb-1">
                <i class="fas fa-check-circle text-success me-2" style="width: 18px;"></i>
                <small class="text-muted">默认分支：{{ source.default_branch }}</small>
              </div>
              <div class="d-flex align-items-center">
                <i class="fab fa-docker text-info me-2" style="width: 18px;"></i>
                <small class="text-muted">
                  Dockerfile：{{ (source.dockerfiles && Object.keys(source.dockerfiles).length) || 0 }} 个
                </small>
              </div>
            </div>
            
            <div class="border-top pt-2 mt-2">
              <button 
                class="btn btn-sm btn-outline-info w-100" 
                @click="manageDockerfiles(source)"
                title="管理 Dockerfile"
              >
                <i class="fab fa-docker"></i> 管理 Dockerfile
              </button>
            </div>
            
            <div class="border-top pt-2 mt-2">
              <div class="text-muted small">
                <div>创建时间：{{ formatDateTime(source.created_at) }}</div>
                <div v-if="source.updated_at !== source.created_at">
                  更新时间：{{ formatDateTime(source.updated_at) }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- 创建/编辑数据源模态框 -->
    <div v-if="showModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1" @click.self="closeModal">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ editingSource ? '编辑数据源' : '新建数据源' }}
            </h5>
            <button type="button" class="btn-close" @click="closeModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveSource">
              <div class="mb-3">
                <label class="form-label">数据源名称 <span class="text-danger">*</span></label>
                <input 
                  v-model="formData.name" 
                  type="text" 
                  class="form-control form-control-sm" 
                  required
                  placeholder="例如：主项目仓库"
                >
              </div>
              <div class="mb-3">
                <label class="form-label">描述</label>
                <input 
                  v-model="formData.description" 
                  type="text" 
                  class="form-control form-control-sm"
                  placeholder="数据源描述（可选）"
                >
              </div>
              <div class="mb-3">
                <label class="form-label">Git 仓库地址 <span class="text-danger">*</span></label>
                <div class="input-group input-group-sm">
                  <input 
                    v-model="formData.git_url" 
                    type="text" 
                    class="form-control" 
                    required
                    placeholder="https://github.com/user/repo.git"
                    :readonly="editingSource"
                  >
                  <button 
                    type="button" 
                    class="btn btn-outline-primary" 
                    @click="verifyAndSave"
                    :disabled="!formData.git_url || verifying"
                  >
                    <span v-if="verifying" class="spinner-border spinner-border-sm me-1"></span>
                    <i v-else class="fas fa-search me-1"></i>
                    {{ verifying ? '验证中...' : (editingSource && !isVerified ? '重新验证' : '验证仓库') }}
                  </button>
                </div>
                <small class="text-muted">
                  <span v-if="editingSource">编辑模式下修改 Git 地址或认证信息需要重新验证</span>
                  <span v-else>新建数据源必须先验证 Git 仓库才能保存</span>
                </small>
                <div v-if="isVerified" class="alert alert-success alert-sm mt-2 mb-0">
                  <i class="fas fa-check-circle"></i> 仓库已验证，可以保存
                </div>
              </div>
              <div class="mb-3">
                <div class="card border-info">
                  <div class="card-header bg-info bg-opacity-10 py-2">
                    <small class="text-muted">
                      <i class="fas fa-lock"></i> 认证信息（可选）
                    </small>
                  </div>
                  <div class="card-body p-3">
                    <div class="row g-2">
                      <div class="col-md-6">
                        <label class="form-label small">Git 用户名</label>
                        <input 
                          v-model="formData.username" 
                          type="text" 
                          class="form-control form-control-sm"
                          placeholder="username 或 token"
                        >
                      </div>
                      <div class="col-md-6">
                        <label class="form-label small">Git 密码/Token</label>
                        <input 
                          v-model="formData.password" 
                          type="password" 
                          class="form-control form-control-sm"
                          placeholder="password 或 access token"
                        >
                      </div>
                    </div>
                    <div class="form-text small mt-2">
                      <i class="fas fa-info-circle"></i> 
                      私有仓库需要认证信息。可以使用用户名密码或 Personal Access Token
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="formData.branches && formData.branches.length > 0" class="mb-3">
                <label class="form-label">分支列表</label>
                <div class="border rounded p-2 bg-light" style="max-height: 150px; overflow-y: auto;">
                  <span v-for="branch in formData.branches" :key="branch" class="badge bg-secondary me-1 mb-1">
                    {{ branch }}
                  </span>
                </div>
              </div>
              <div v-if="formData.tags && formData.tags.length > 0" class="mb-3">
                <label class="form-label">标签列表</label>
                <div class="border rounded p-2 bg-light" style="max-height: 150px; overflow-y: auto;">
                  <span v-for="tag in formData.tags.slice(0, 20)" :key="tag" class="badge bg-info me-1 mb-1">
                    {{ tag }}
                  </span>
                  <span v-if="formData.tags.length > 20" class="text-muted small">
                    ... 还有 {{ formData.tags.length - 20 }} 个标签
                  </span>
                </div>
              </div>
              <div v-if="formData.branches && formData.branches.length > 0" class="mb-3">
                <label class="form-label">默认分支</label>
                <select 
                  v-model="formData.default_branch" 
                  class="form-select form-select-sm"
                  :disabled="!isVerified && !editingSource"
                >
                  <option value="">请选择默认分支</option>
                  <option v-for="branch in formData.branches" :key="branch" :value="branch">
                    {{ branch }}
                  </option>
                </select>
                <small class="text-muted">选择该数据源的默认分支</small>
              </div>
              <div v-else-if="formData.default_branch" class="mb-3">
                <label class="form-label">默认分支</label>
                <input 
                  :value="formData.default_branch" 
                  type="text" 
                  class="form-control form-control-sm" 
                  readonly
                >
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeModal">取消</button>
            <button 
              type="button" 
              class="btn btn-primary btn-sm" 
              @click="saveSource"
              :disabled="!formData.git_url || verifying || (!editingSource && !isVerified)"
              :title="!editingSource && !isVerified ? '请先验证 Git 仓库' : ''"
            >
              <i class="fas fa-save"></i> 保存
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>

    <!-- Dockerfile 管理模态框 -->
    <div v-if="showDockerfileModal && currentSource" class="modal fade show" style="display: block; z-index: 1060;" tabindex="-1" @click.self="closeDockerfileModal">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fab fa-docker"></i> Dockerfile 管理 - {{ currentSource.name }}
            </h5>
            <button type="button" class="btn-close" @click="closeDockerfileModal"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <label class="form-label">分支</label>
                <select 
                  v-model="selectedBranch" 
                  class="form-select form-select-sm"
                  @change="onDockerfileBranchChanged"
                >
                  <option value="">默认分支 ({{ currentSource.default_branch || 'main' }})</option>
                  <option v-for="branch in currentSource.branches || []" :key="branch" :value="branch">
                    {{ branch }}
                  </option>
                </select>
                <small class="text-muted">选择分支以查看该分支的 Dockerfile</small>
              </div>
              <div class="col-md-6 d-flex align-items-end">
                <div class="text-muted small">共 {{ dockerfileList.length }} 个 Dockerfile</div>
              </div>
            </div>
            <div class="d-flex justify-content-between align-items-center mb-3">
              <span class="text-muted"></span>
              <div class="btn-group btn-group-sm">
                <button 
                  class="btn btn-outline-info" 
                  @click="scanDockerfiles"
                  :disabled="scanningDockerfiles"
                  title="扫描 Dockerfile"
                >
                  <i class="fas fa-search" :class="{ 'fa-spin': scanningDockerfiles }"></i> 扫描
                </button>
                <button class="btn btn-primary" @click="showCreateDockerfile">
                  <i class="fas fa-plus"></i> 新建
                </button>
              </div>
            </div>

            <!-- Dockerfile 列表 -->
            <div v-if="loadingDockerfiles" class="text-center py-3">
              <span class="spinner-border spinner-border-sm"></span> 加载中...
            </div>
            <div v-else-if="dockerfileList.length === 0" class="text-center py-4 text-muted">
              <i class="fab fa-docker fa-3x mb-3"></i>
              <p>暂无 Dockerfile</p>
              <p class="small">验证 Git 仓库时会自动扫描 Dockerfile，您也可以手动添加</p>
            </div>
            <div v-else class="list-group">
              <div v-for="item in dockerfileList" :key="item.path" class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                  <div class="flex-grow-1">
                    <h6 class="mb-1">
                      <i class="fab fa-docker text-info"></i> {{ item.path }}
                    </h6>
                    <small class="text-muted">共 {{ item.lineCount }} 行</small>
                  </div>
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" @click="editDockerfile(item.path, item.content)" title="编辑">
                      <i class="fas fa-edit"></i>
                    </button>
                    <button 
                      v-if="item.hasChanges || item.originalContent === ''"
                      class="btn btn-outline-success" 
                      @click="openCommitModal(item.path)"
                      title="提交到 Git 仓库"
                    >
                      <i class="fas fa-code-branch"></i>
                    </button>
                    <button class="btn btn-outline-danger" @click="deleteDockerfile(item.path)" title="删除">
                      <i class="fas fa-trash"></i>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showDockerfileModal" class="modal-backdrop fade show" style="z-index: 1055;"></div>

    <!-- Dockerfile 编辑器模态框 -->
    <div v-if="showDockerfileEditor && currentSource" class="modal fade show" style="display: block; z-index: 1070;" tabindex="-1" @click.self="closeDockerfileEditor">
      <div class="modal-dialog modal-xl">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fab fa-docker"></i> {{ editingDockerfilePath ? '编辑' : '新建' }} Dockerfile
            </h5>
            <button type="button" class="btn-close" @click="closeDockerfileEditor"></button>
          </div>
          <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
            <div class="mb-3">
              <label class="form-label">Dockerfile 路径 <span class="text-danger">*</span></label>
              <input 
                v-model="dockerfileForm.path" 
                type="text" 
                class="form-control form-control-sm"
                :readonly="!!editingDockerfilePath"
                placeholder="Dockerfile 或 Dockerfile.prod"
                required
              >
              <small class="text-muted">相对路径，如：Dockerfile、Dockerfile.prod、docker/Dockerfile</small>
            </div>
            <div class="mb-3">
              <label class="form-label">内容 <span class="text-danger">*</span></label>
              <codemirror
                v-model="dockerfileForm.content"
                :style="{ height: '400px', fontSize: '13px' }"
                :autofocus="true"
                :indent-with-tab="true"
                :tab-size="2"
                :extensions="dockerfileExtensions"
                placeholder="FROM ..."
              />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeDockerfileEditor">取消</button>
            <button type="button" class="btn btn-primary btn-sm" @click="saveDockerfile">
              <i class="fas fa-save"></i> 保存
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showDockerfileEditor" class="modal-backdrop fade show" style="z-index: 1065;"></div>

    <!-- 提交 Dockerfile 模态框 -->
    <div v-if="showCommitModal && currentSource" class="modal fade show" style="display: block; z-index: 1070;" tabindex="-1" @click.self="closeCommitModal">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-code-branch"></i> 提交 Dockerfile 到 Git 仓库
            </h5>
            <button type="button" class="btn-close" @click="closeCommitModal"></button>
          </div>
          <div class="modal-body">
            <div class="mb-3">
              <label class="form-label">Dockerfile 路径</label>
              <input 
                :value="committingDockerfilePath" 
                type="text" 
                class="form-control form-control-sm" 
                readonly
              >
            </div>
            <div class="mb-3">
              <label class="form-label">目标分支 <span class="text-danger">*</span></label>
              <select 
                v-model="commitForm.branch" 
                class="form-select form-select-sm"
                required
              >
                <option value="">请选择分支</option>
                <option v-for="branch in currentSource.branches || []" :key="branch" :value="branch">
                  {{ branch }}
                </option>
              </select>
              <small class="text-muted">选择要提交到的分支</small>
            </div>
            <div class="mb-3">
              <label class="form-label">提交信息</label>
              <input 
                v-model="commitForm.commitMessage" 
                type="text" 
                class="form-control form-control-sm"
                placeholder="例如：Update Dockerfile"
              >
              <small class="text-muted">如果不填写，将使用默认提交信息</small>
            </div>
            <div class="alert alert-info alert-sm mb-0">
              <i class="fas fa-info-circle"></i> 
              <strong>提示：</strong>提交前会自动同步远程仓库，确保与远程保持一致。如有冲突，将使用本地版本。
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeCommitModal">取消</button>
            <button 
              type="button" 
              class="btn btn-primary btn-sm" 
              @click="commitDockerfile"
              :disabled="!commitForm.branch || committing"
            >
              <span v-if="committing" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="fas fa-code-branch me-1"></i>
              {{ committing ? '提交中...' : '提交' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showCommitModal" class="modal-backdrop fade show" style="z-index: 1065;"></div>

    <!-- 镜像仓库 Tab -->
    <div v-show="activeSubTab === 'registry'">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h5 class="mb-0">
          <i class="fas fa-box"></i> 镜像仓库配置
        </h5>
        <div class="d-flex gap-2">
          <button 
            class="btn btn-outline-secondary btn-sm" 
            @click="loadRegistries"
            :disabled="loadingRegistries"
            title="刷新列表"
          >
            <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingRegistries }"></i> 刷新
          </button>
          <button type="button" class="btn btn-primary btn-sm" @click="showCreateRegistryModal">
            <i class="fas fa-plus"></i> 新建仓库
          </button>
        </div>
      </div>

      <!-- 仓库列表 -->
      <div v-if="loadingRegistries" class="text-center py-5">
        <span class="spinner-border spinner-border-sm"></span> 加载中...
      </div>
      <div v-else-if="registries && registries.length === 0" class="text-center py-5 text-muted">
        <i class="fas fa-box fa-3x mb-3"></i>
        <p class="mb-0">暂无镜像仓库</p>
        <p class="text-muted small mt-2">点击"新建仓库"按钮添加镜像仓库配置</p>
      </div>
      <div v-else class="row g-4">
        <div v-for="(registry, index) in registries" :key="index" class="col-12 col-md-6 col-xl-4">
          <div class="card h-100 shadow-sm" :class="{ 'border-primary': registry.active }">
            <div class="card-header bg-white">
              <div class="mb-2">
                <h5 class="card-title mb-0">
                  <strong>{{ registry.name }}</strong>
                  <span v-if="registry.active" class="badge bg-primary ms-2">激活</span>
                </h5>
              </div>
              <div class="btn-group btn-group-sm w-100">
                <button 
                  class="btn btn-outline-primary" 
                  @click="editRegistry(index)"
                  title="编辑"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button 
                  class="btn btn-outline-info" 
                  @click="testRegistryLogin(index)"
                  :disabled="testingRegistry === index"
                  title="测试登录"
                >
                  <i class="fas fa-vial" :class="{ 'fa-spin': testingRegistry === index }"></i>
                </button>
                <button 
                  class="btn btn-outline-danger" 
                  @click="removeRegistry(index)"
                  :disabled="registries.length === 1"
                  title="删除"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </div>
            
            <div class="card-body">
              <div class="mb-3">
                <div class="d-flex align-items-center mb-1">
                  <i class="fas fa-server text-muted me-2" style="width: 18px;"></i>
                  <small class="font-monospace text-truncate" :title="registry.registry" style="font-size: 0.9rem;">
                    {{ registry.registry }}
                  </small>
                </div>
              </div>
              
              <div class="mb-3">
                <div v-if="registry.registry_prefix" class="d-flex align-items-center mb-1">
                  <i class="fas fa-tag text-muted me-2" style="width: 18px;"></i>
                  <small class="text-muted">前缀：{{ registry.registry_prefix }}</small>
                </div>
                <div class="d-flex align-items-center mb-1">
                  <i class="fas fa-user text-muted me-2" style="width: 18px;"></i>
                  <small class="text-muted">账号：{{ registry.username || '未设置' }}</small>
                </div>
                <div class="d-flex align-items-center">
                  <i class="fas fa-key text-muted me-2" style="width: 18px;"></i>
                  <small class="text-muted">密码：{{ registry.password ? '已设置' : '未设置' }}</small>
                </div>
              </div>
              
              <div v-if="registryTestResult[index]" class="border-top pt-2 mt-2">
                <div 
                  v-if="registryTestResult[index].success" 
                  class="alert alert-success alert-sm mb-0 py-1"
                >
                  <i class="fas fa-check-circle"></i> {{ registryTestResult[index].message }}
                </div>
                <div 
                  v-else 
                  class="alert alert-danger alert-sm mb-0 py-1"
                >
                  <i class="fas fa-times-circle"></i> {{ registryTestResult[index].message }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑镜像仓库模态框 -->
    <div v-if="showRegistryModal" class="modal fade show" style="display: block; z-index: 1050;" tabindex="-1" @click.self="closeRegistryModal">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              {{ editingRegistryIndex !== null ? '编辑镜像仓库' : '新建镜像仓库' }}
            </h5>
            <button type="button" class="btn-close" @click="closeRegistryModal"></button>
          </div>
          <div class="modal-body">
            <form @submit.prevent="saveRegistry">
              <div class="mb-3">
                <label class="form-label">仓库名称 <span class="text-danger">*</span></label>
                <input 
                  v-model="registryForm.name" 
                  type="text" 
                  class="form-control" 
                  placeholder="如：Docker Hub"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label">Registry 地址 <span class="text-danger">*</span></label>
                <input 
                  v-model="registryForm.registry" 
                  type="text" 
                  class="form-control" 
                  placeholder="docker.io"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label">镜像前缀（可选）</label>
                <input 
                  v-model="registryForm.registry_prefix" 
                  type="text" 
                  class="form-control" 
                  placeholder="your-namespace"
                />
                <small class="text-muted">用于自动生成镜像名称的前缀</small>
              </div>
              <div class="mb-3">
                <label class="form-label">账号</label>
                <input 
                  v-model="registryForm.username" 
                  type="text" 
                  class="form-control" 
                  placeholder="用户名"
                />
              </div>
              <div class="mb-3">
                <label class="form-label">密码</label>
                <div class="input-group">
                  <input 
                    v-model="registryForm.password" 
                    type="password" 
                    class="form-control" 
                    placeholder="密码"
                  />
                  <button 
                    type="button" 
                    class="btn btn-outline-primary" 
                    @click="testCurrentRegistryLogin"
                    :disabled="testingRegistry === 'current'"
                    :title="testingRegistry === 'current' ? '测试中...' : '测试登录'"
                  >
                    <i 
                      :class="testingRegistry === 'current' ? 'fas fa-spinner fa-spin' : 'fas fa-vial'"
                    ></i>
                    {{ testingRegistry === 'current' ? '测试中...' : '测试' }}
                  </button>
                </div>
                <div v-if="registryTestResult['current']" class="mt-2">
                  <div 
                    v-if="registryTestResult['current'].success" 
                    class="alert alert-success alert-sm mb-0 py-1"
                  >
                    <i class="fas fa-check-circle"></i> {{ registryTestResult['current'].message }}
                  </div>
                  <div 
                    v-else 
                    class="alert alert-danger alert-sm mb-0 py-1"
                  >
                    <i class="fas fa-times-circle"></i> {{ registryTestResult['current'].message }}
                    <div v-if="registryTestResult['current'].suggestions" class="mt-1">
                      <small>
                        <ul class="mb-0 ps-3">
                          <li v-for="(suggestion, idx) in registryTestResult['current'].suggestions" :key="idx">
                            {{ suggestion }}
                          </li>
                        </ul>
                      </small>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mb-3">
                <div class="form-check">
                  <input 
                    v-model="registryForm.active"
                    type="checkbox" 
                    class="form-check-input" 
                    id="registryActive"
                  />
                  <label class="form-check-label" for="registryActive">
                    设为激活仓库
                  </label>
                </div>
                <small class="text-muted">激活的仓库将作为默认推送目标</small>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="closeRegistryModal">取消</button>
            <button 
              type="button" 
              class="btn btn-primary btn-sm" 
              @click="saveRegistry"
              :disabled="!registryForm.name || !registryForm.registry"
            >
              <i class="fas fa-save"></i> 保存
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showRegistryModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>
  </div>
</template>

<script setup>
import { StreamLanguage } from '@codemirror/language'
import { shell } from '@codemirror/legacy-modes/mode/shell'
import { oneDark } from '@codemirror/theme-one-dark'
import axios from 'axios'
import { onMounted, ref, watch } from 'vue'
import { Codemirror } from 'vue-codemirror'

const activeSubTab = ref('git')  // 'git' 或 'registry'

const sources = ref([])
const loading = ref(false)
const refreshing = ref(null)
const showModal = ref(false)
const editingSource = ref(null)
const verifying = ref(false)
const isVerified = ref(false)  // 验证状态标识

// 镜像仓库相关状态
const registries = ref([])
const loadingRegistries = ref(false)
const savingRegistries = ref(false)
const testingRegistry = ref(null)
const registryTestResult = ref({})
const showRegistryModal = ref(false)
const editingRegistryIndex = ref(null)
const registryForm = ref({
  name: '',
  registry: '',
  registry_prefix: '',
  username: '',
  password: '',
  active: false
})

// Dockerfile 管理相关状态
const showDockerfileModal = ref(false)
const showDockerfileEditor = ref(false)
const currentSource = ref(null)
const dockerfileList = ref([])
const loadingDockerfiles = ref(false)
const scanningDockerfiles = ref(false)
const editingDockerfilePath = ref(null)
const selectedBranch = ref('') // 当前选择的分支
const dockerfileForm = ref({
  path: '',
  content: ''
})

// 提交相关状态
const showCommitModal = ref(false)
const committingDockerfilePath = ref('')
const committing = ref(false)
const commitForm = ref({
  branch: '',
  commitMessage: ''
})

// CodeMirror 扩展配置（Dockerfile 使用 shell 模式近似）
const dockerfileExtensions = [
  StreamLanguage.define(shell),  // 使用 shell 模式近似 Dockerfile
  oneDark  // 使用暗色主题
]

const formData = ref({
  name: '',
  description: '',
  git_url: '',
  branches: [],
  tags: [],
  default_branch: '',
  username: '',
  password: ''
})

// 监听 Git URL 或认证信息变化，重置验证状态
watch(() => [formData.value.git_url, formData.value.username, formData.value.password], () => {
  // 如果 Git URL 或认证信息变化，重置验证状态（编辑模式下除外）
  if (!editingSource.value) {
    isVerified.value = false
  } else if (editingSource.value) {
    // 编辑模式下，如果 Git URL 或认证信息变化，需要重新验证
    const urlChanged = editingSource.value.git_url !== formData.value.git_url
    const usernameChanged = (editingSource.value.username || '') !== (formData.value.username || '')
    const passwordChanged = formData.value.password && formData.value.password !== '******'
    if (urlChanged || usernameChanged || passwordChanged) {
      isVerified.value = false
    }
  }
}, { deep: true })

// 监听 Git URL 变化，自动填充数据源名称
watch(() => formData.value.git_url, (newUrl) => {
  // 如果 Git URL 有值且名称为空，自动从 URL 提取仓库名
  if (newUrl && !formData.value.name && !editingSource.value) {
    const urlParts = newUrl.trim().replace('.git', '').split('/')
    const repoName = urlParts[urlParts.length - 1]
    if (repoName) {
      formData.value.name = repoName
    }
  }
})

// 监听 Tab 切换，加载对应数据
watch(activeSubTab, (newTab) => {
  if (newTab === 'registry') {
    loadRegistries()
  }
})

// 镜像仓库相关函数
async function loadRegistries() {
  loadingRegistries.value = true
  try {
    const res = await axios.get('/api/get-config')
    const docker = res.data.docker || {}
    let registriesList = docker.registries || []
    
    if (!registriesList || registriesList.length === 0) {
      registriesList = [{
        name: 'Docker Hub',
        registry: 'docker.io',
        registry_prefix: '',
        username: '',
        password: '',
        active: true
      }]
    }
    
    const hasActive = registriesList.some(r => r.active)
    if (!hasActive && registriesList.length > 0) {
      registriesList[0].active = true
    }
    
    registries.value = registriesList
  } catch (error) {
    console.error('加载镜像仓库配置失败:', error)
    alert('加载镜像仓库配置失败')
  } finally {
    loadingRegistries.value = false
  }
}

function showCreateRegistryModal() {
  editingRegistryIndex.value = null
  registryForm.value = {
    name: '',
    registry: 'docker.io',
    registry_prefix: '',
    username: '',
    password: '',
    active: false
  }
  registryTestResult.value = {}
  showRegistryModal.value = true
}

function editRegistry(index) {
  editingRegistryIndex.value = index
  const registry = registries.value[index]
  registryForm.value = {
    name: registry.name,
    registry: registry.registry,
    registry_prefix: registry.registry_prefix || '',
    username: registry.username || '',
    password: registry.password ? '******' : '',  // 不显示真实密码
    active: registry.active
  }
  registryTestResult.value = {}
  showRegistryModal.value = true
}

function closeRegistryModal() {
  showRegistryModal.value = false
  editingRegistryIndex.value = null
  registryForm.value = {
    name: '',
    registry: '',
    registry_prefix: '',
    username: '',
    password: '',
    active: false
  }
  registryTestResult.value = {}
}

async function saveRegistry() {
  if (!registryForm.value.name || !registryForm.value.registry) {
    alert('请填写仓库名称和 Registry 地址')
    return
  }
  
  savingRegistries.value = true
  try {
    if (editingRegistryIndex.value !== null) {
      // 更新现有仓库
      const index = editingRegistryIndex.value
      const password = (registryForm.value.password && registryForm.value.password !== '******') 
        ? registryForm.value.password 
        : (registries.value[index].password || '')
      
      registries.value[index] = {
        ...registryForm.value,
        password: password
      }
      
      // 如果设置为激活，取消其他仓库的激活状态
      if (registryForm.value.active) {
        registries.value.forEach((reg, i) => {
          if (i !== index) {
            reg.active = false
          }
        })
      }
    } else {
      // 添加新仓库
      const newRegistry = {
        ...registryForm.value
      }
      
      // 如果设置为激活，取消其他仓库的激活状态
      if (newRegistry.active) {
        registries.value.forEach(reg => {
          reg.active = false
        })
      }
      
      registries.value.push(newRegistry)
    }
    
    // 保存到服务器
    await saveRegistries()
    closeRegistryModal()
  } catch (error) {
    console.error('保存镜像仓库失败:', error)
    alert(error.response?.data?.detail || '保存镜像仓库失败')
  } finally {
    savingRegistries.value = false
  }
}

async function testCurrentRegistryLogin() {
  if (!registryForm.value.registry) {
    alert('请先填写Registry地址')
    return
  }
  
  if (!registryForm.value.username || !registryForm.value.password || registryForm.value.password === '******') {
    alert('请先填写用户名和密码')
    return
  }
  
  testingRegistry.value = 'current'
  registryTestResult.value['current'] = null
  
  try {
    const res = await axios.post('/api/registries/test', {
      name: registryForm.value.name,
      registry: registryForm.value.registry,
      username: registryForm.value.username,
      password: registryForm.value.password
    })
    
    registryTestResult.value['current'] = {
      success: res.data.success,
      message: res.data.message,
      details: res.data.details,
      suggestions: res.data.suggestions
    }
    
    if (res.data.success) {
      console.log('✅ Registry登录测试成功:', res.data)
    } else {
      console.warn('⚠️ Registry登录测试失败:', res.data)
    }
  } catch (error) {
    console.error('❌ Registry登录测试异常:', error)
    const errorData = error.response?.data || {}
    registryTestResult.value['current'] = {
      success: false,
      message: errorData.message || errorData.detail || '测试失败',
      details: errorData.details,
      suggestions: errorData.suggestions
    }
  } finally {
    testingRegistry.value = null
  }
}

function removeRegistry(index) {
  if (registries.value.length === 1) {
    alert('至少需要保留一个仓库')
    return
  }
  
  const wasActive = registries.value[index].active
  registries.value.splice(index, 1)
  
  if (wasActive && registries.value.length > 0) {
    registries.value[0].active = true
  }
}

function setActiveRegistry(index) {
  registries.value.forEach((reg, i) => {
    reg.active = (i === index)
  })
  // 自动保存
  saveRegistries()
}

async function testRegistryLogin(index) {
  const registry = registries.value[index]
  
  if (!registry.registry) {
    alert('请先填写Registry地址')
    return
  }
  
  if (!registry.username || !registry.password) {
    alert('请先填写用户名和密码')
    return
  }
  
  testingRegistry.value = index
  registryTestResult.value[index] = null
  
  try {
    const res = await axios.post('/api/registries/test', {
      name: registry.name,
      registry: registry.registry,
      username: registry.username,
      password: registry.password
    })
    
    registryTestResult.value[index] = {
      success: res.data.success,
      message: res.data.message,
      details: res.data.details,
      suggestions: res.data.suggestions
    }
    
    if (res.data.success) {
      console.log('✅ Registry登录测试成功:', res.data)
    } else {
      console.warn('⚠️ Registry登录测试失败:', res.data)
    }
  } catch (error) {
    console.error('❌ Registry登录测试异常:', error)
    const errorData = error.response?.data || {}
    registryTestResult.value[index] = {
      success: false,
      message: errorData.message || errorData.detail || '测试失败',
      details: errorData.details,
      suggestions: errorData.suggestions
    }
  } finally {
    testingRegistry.value = null
  }
}

async function saveRegistries() {
  savingRegistries.value = true
  try {
    const res = await axios.post('/api/registries', {
      registries: registries.value
    })
    console.log('✅ 仓库配置保存成功:', res.data)
    alert('镜像仓库配置保存成功')
  } catch (error) {
    console.error('❌ 保存镜像仓库配置失败:', error)
    const errorMsg = error.response?.data?.detail || error.response?.data?.error || '保存配置失败'
    alert(errorMsg)
  } finally {
    savingRegistries.value = false
  }
}

onMounted(() => {
  loadSources()
  loadRegistries()
})

async function loadSources() {
  loading.value = true
  try {
    const res = await axios.get('/api/git-sources')
    sources.value = res.data.sources || []
  } catch (error) {
    console.error('加载数据源列表失败:', error)
    alert('加载数据源列表失败')
  } finally {
    loading.value = false
  }
}

function showCreateModal() {
  editingSource.value = null
  isVerified.value = false
  formData.value = {
    name: '',
    description: '',
    git_url: '',
    branches: [],
    tags: [],
    default_branch: '',
    username: '',
    password: '',
    dockerfiles: {}
  }
  showModal.value = true
}

function editSource(source) {
  editingSource.value = source
  isVerified.value = true  // 编辑模式下，假设已存在的源是已验证的
  formData.value = {
    name: source.name,
    description: source.description || '',
    git_url: source.git_url,
    branches: source.branches || [],
    tags: source.tags || [],
    default_branch: source.default_branch || '',
    username: source.username || '',
    password: source.has_password ? '******' : '',  // 不显示真实密码，显示占位符
    dockerfiles: source.dockerfiles || {}
  }
  showModal.value = true
}

async function verifyAndSave() {
  if (!formData.value.git_url) {
    alert('请输入 Git 仓库地址')
    return
  }
  
  verifying.value = true
  isVerified.value = false
  try {
    const res = await axios.post('/api/verify-git-repo', {
      git_url: formData.value.git_url.trim(),
      save_as_source: false,  // 先不保存，验证后手动保存
      source_name: formData.value.name || undefined,
      source_description: formData.value.description || '',
      username: formData.value.username || undefined,
      password: formData.value.password || undefined
    })
    
    if (res.data.success) {
      formData.value.branches = res.data.branches || []
      formData.value.tags = res.data.tags || []
      formData.value.default_branch = res.data.default_branch || ''
      formData.value.dockerfiles = res.data.dockerfiles || {}  // 保存扫描到的 Dockerfile
      isVerified.value = true  // 标记为已验证
      
      // 如果有扫描到的 Dockerfile，提示用户
      if (res.data.dockerfiles && Object.keys(res.data.dockerfiles).length > 0) {
        const dockerfileCount = Object.keys(res.data.dockerfiles).length
        console.log(`✅ 扫描到 ${dockerfileCount} 个 Dockerfile:`, Object.keys(res.data.dockerfiles))
      }
      
      // 如果没有设置名称，使用仓库名作为默认名称
      if (!formData.value.name) {
        const urlParts = formData.value.git_url.replace('.git', '').split('/')
        formData.value.name = urlParts[urlParts.length - 1] || '未命名数据源'
      }
    } else {
      alert('验证失败：' + (res.data.detail || '未知错误'))
      isVerified.value = false
    }
  } catch (error) {
    console.error('验证仓库失败:', error)
    alert(error.response?.data?.detail || '验证仓库失败')
    isVerified.value = false
  } finally {
    verifying.value = false
  }
}

async function saveSource() {
  if (!formData.value.name || !formData.value.git_url) {
    alert('请填写必填字段')
    return
  }
  
  // 检查验证状态
  const isNewSource = !editingSource.value
  const gitUrlChanged = editingSource.value && editingSource.value.git_url !== formData.value.git_url
  const authChanged = editingSource.value && (
    editingSource.value.username !== formData.value.username || 
    (formData.value.password && formData.value.password !== '******')
  )
  const needsVerification = isNewSource || gitUrlChanged || authChanged || !isVerified.value
  
  if (needsVerification) {
    // 需要验证，检查是否已验证
    if (!isVerified.value || formData.value.branches.length === 0) {
      alert('请先验证 Git 仓库后再保存')
      return
    }
  }
  
  try {
    // 准备认证信息（如果密码是占位符，则不更新密码）
    const password = (formData.value.password && formData.value.password !== '******') 
      ? formData.value.password 
      : (editingSource.value ? undefined : formData.value.password)
    
    if (editingSource.value) {
      // 更新
      await axios.put(`/api/git-sources/${editingSource.value.source_id}`, {
        name: formData.value.name,
        description: formData.value.description,
        branches: formData.value.branches,
        tags: formData.value.tags,
        default_branch: formData.value.default_branch,
        username: formData.value.username || null,
        password: password
      })
      alert('数据源更新成功')
    } else {
      // 创建新数据源（包含验证时扫描到的 Dockerfile）
      await axios.post('/api/git-sources', {
        name: formData.value.name,
        description: formData.value.description,
        git_url: formData.value.git_url,
        branches: formData.value.branches,
        tags: formData.value.tags,
        default_branch: formData.value.default_branch,
        username: formData.value.username || null,
        password: password || null,
        dockerfiles: formData.value.dockerfiles || null
      })
      alert('数据源创建成功')
    }
    closeModal()
    loadSources()
  } catch (error) {
    console.error('保存数据源失败:', error)
    alert(error.response?.data?.detail || '保存数据源失败')
  }
}

function closeModal() {
  showModal.value = false
  editingSource.value = null
}

async function refreshSource(source) {
  if (!confirm(`确定要刷新数据源 "${source.name}" 的分支和标签吗？`)) {
    return
  }
  
  refreshing.value = source.source_id
  try {
    // 使用数据源的认证信息刷新
    const res = await axios.post('/api/verify-git-repo', {
      git_url: source.git_url,
      save_as_source: false,
      source_id: source.source_id  // 传递 source_id 以使用数据源的认证信息
    })
    
    if (res.data.success) {
      await axios.put(`/api/git-sources/${source.source_id}`, {
        branches: res.data.branches || [],
        tags: res.data.tags || [],
        default_branch: res.data.default_branch || source.default_branch
      })
      // 更新扫描到的 Dockerfile
      if (res.data.dockerfiles) {
        for (const [dockerfile_path, content] of Object.entries(res.data.dockerfiles)) {
          await axios.put(
            `/api/git-sources/${source.source_id}/dockerfiles/${encodeURIComponent(dockerfile_path)}`,
            { content: content }
          )
        }
      }
      alert('数据源刷新成功')
      loadSources()
    } else {
      alert('刷新失败：' + (res.data.detail || '未知错误'))
    }
  } catch (error) {
    console.error('刷新数据源失败:', error)
    alert(error.response?.data?.detail || '刷新数据源失败')
  } finally {
    refreshing.value = null
  }
}

async function deleteSource(source) {
  if (!confirm(`确定要删除数据源 "${source.name}" 吗？`)) {
    return
  }
  
  try {
    await axios.delete(`/api/git-sources/${source.source_id}`)
    alert('数据源已删除')
    loadSources()
  } catch (error) {
    console.error('删除数据源失败:', error)
    alert(error.response?.data?.detail || '删除数据源失败')
  }
}

function formatGitUrl(url) {
  if (!url) return ''
  return url.replace('https://', '').replace('http://', '').replace('.git', '')
}

function formatDateTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

// Dockerfile 管理函数
async function manageDockerfiles(source) {
  currentSource.value = source
  selectedBranch.value = '' // 重置分支选择
  showDockerfileModal.value = true
  await loadDockerfiles(source.source_id, true) // 保留更改状态
}

async function loadDockerfiles(sourceId, preserveChanges = false) {
  loadingDockerfiles.value = true
  try {
    const res = await axios.get(`/api/git-sources/${sourceId}/dockerfiles`)
    const dockerfiles = res.data.dockerfiles || {}
    
    // 保留现有的新创建项（originalContent === '' 的项）
    const existingNewItems = dockerfileList.value.filter(item => item.originalContent === '')
    const existingNewPaths = new Set(existingNewItems.map(item => item.path))
    
    // 如果 preserveChanges 为 true，保留现有的 hasChanges 状态
    if (preserveChanges) {
      const existingItems = dockerfileList.value.reduce((acc, item) => {
        acc[item.path] = item.hasChanges
        return acc
      }, {})
      
      dockerfileList.value = Object.keys(dockerfiles).map(path => {
        // 如果是新创建的项，保留其状态
        if (existingNewPaths.has(path)) {
          const existingItem = existingNewItems.find(item => item.path === path)
          return {
            path,
            content: dockerfiles[path],
            originalContent: '', // 保持为空，表示未提交
            lineCount: dockerfiles[path].split('\n').length,
            hasChanges: true // 新创建的应该显示提交按钮
          }
        }
        return {
          path,
          content: dockerfiles[path],
          originalContent: dockerfiles[path], // 保存原始内容用于比较
          lineCount: dockerfiles[path].split('\n').length,
          hasChanges: existingItems[path] || false // 保留原有的 hasChanges 状态
        }
      })
    } else {
      dockerfileList.value = Object.keys(dockerfiles).map(path => {
        // 如果是新创建的项，保留其状态
        if (existingNewPaths.has(path)) {
          const existingItem = existingNewItems.find(item => item.path === path)
          return {
            path,
            content: dockerfiles[path],
            originalContent: '', // 保持为空，表示未提交
            lineCount: dockerfiles[path].split('\n').length,
            hasChanges: true // 新创建的应该显示提交按钮
          }
        }
        return {
          path,
          content: dockerfiles[path],
          originalContent: dockerfiles[path], // 保存原始内容用于比较
          lineCount: dockerfiles[path].split('\n').length,
          hasChanges: false // 初始状态没有差异
        }
      })
    }
    
    // 添加新创建但不在服务器列表中的项（可能还未保存）
    existingNewItems.forEach(item => {
      if (!dockerfiles[item.path]) {
        dockerfileList.value.push(item)
      }
    })
  } catch (error) {
    console.error('加载 Dockerfile 列表失败:', error)
    alert('加载 Dockerfile 列表失败')
    dockerfileList.value = []
  } finally {
    loadingDockerfiles.value = false
  }
}

function closeDockerfileModal() {
  showDockerfileModal.value = false
  currentSource.value = null
  dockerfileList.value = []
  selectedBranch.value = ''
}

function showCreateDockerfile() {
  editingDockerfilePath.value = null
  dockerfileForm.value = {
    path: 'Dockerfile',
    content: 'FROM alpine:latest\n\n# TODO: 添加构建步骤\n'
  }
  showDockerfileEditor.value = true
}

function editDockerfile(path, content) {
  editingDockerfilePath.value = path
  dockerfileForm.value = {
    path: path,
    content: content
  }
  showDockerfileEditor.value = true
}

function closeDockerfileEditor() {
  showDockerfileEditor.value = false
  editingDockerfilePath.value = null
  dockerfileForm.value = {
    path: '',
    content: ''
  }
}

async function saveDockerfile() {
  if (!dockerfileForm.value.path || !dockerfileForm.value.content) {
    alert('请填写 Dockerfile 路径和内容')
    return
  }

  try {
    const isNew = !editingDockerfilePath.value // 判断是否是新建的
    
    await axios.put(
      `/api/git-sources/${currentSource.value.source_id}/dockerfiles/${encodeURIComponent(dockerfileForm.value.path)}`,
      { content: dockerfileForm.value.content }
    )
    
    // 更新本地列表中的内容，并检查是否有差异
    const dockerfileItem = dockerfileList.value.find(item => item.path === dockerfileForm.value.path)
    if (dockerfileItem) {
      // 已存在的 Dockerfile，更新内容并检查差异
      dockerfileItem.content = dockerfileForm.value.content
      dockerfileItem.lineCount = dockerfileForm.value.content.split('\n').length
      // 检查是否有差异（与原始内容比较）
      // 如果 originalContent 为空字符串，说明是新创建的，应该显示提交按钮
      dockerfileItem.hasChanges = dockerfileItem.originalContent === '' || dockerfileItem.content !== dockerfileItem.originalContent
    } else {
      // 如果是新创建的，添加到列表中并标记为有更改（需要提交）
      const newItem = {
        path: dockerfileForm.value.path,
        content: dockerfileForm.value.content,
        originalContent: '', // 新创建的没有原始内容（还未提交到 Git），设为空字符串表示未提交
        lineCount: dockerfileForm.value.content.split('\n').length,
        hasChanges: true // 新创建的应该显示提交按钮
      }
      dockerfileList.value.push(newItem)
    }
    
    alert('Dockerfile 保存成功')
    closeDockerfileEditor()
    // 刷新数据源列表以更新 Dockerfile 数量
    loadSources()
  } catch (error) {
    console.error('保存 Dockerfile 失败:', error)
    alert(error.response?.data?.detail || '保存 Dockerfile 失败')
  }
}

async function deleteDockerfile(path) {
  if (!confirm(`确定要删除 Dockerfile "${path}" 吗？`)) {
    return
  }

  try {
    await axios.delete(
      `/api/git-sources/${currentSource.value.source_id}/dockerfiles/${encodeURIComponent(path)}`
    )
    alert('Dockerfile 已删除')
    await loadDockerfiles(currentSource.value.source_id, true) // 保留更改状态
    // 刷新数据源列表以更新 Dockerfile 数量
    loadSources()
  } catch (error) {
    console.error('删除 Dockerfile 失败:', error)
    alert(error.response?.data?.detail || '删除 Dockerfile 失败')
  }
}

async function scanDockerfiles() {
  if (!currentSource.value) {
    return
  }
  
  const branch = selectedBranch.value || currentSource.value.default_branch || 'main'
  const branchText = branch ? `分支 "${branch}"` : '默认分支'
  
  if (!confirm(`确定要扫描数据源 "${currentSource.value.name}" 的 Dockerfile 吗？\n\n这将从 Git 仓库的 ${branchText} 扫描所有 Dockerfile。`)) {
    return
  }
  
  scanningDockerfiles.value = true
  try {
    // 调用验证接口，使用数据源的认证信息扫描 Dockerfile
    const res = await axios.post('/api/verify-git-repo', {
      git_url: currentSource.value.git_url,
      save_as_source: false,
      source_id: currentSource.value.source_id,  // 使用数据源的认证信息
      branch: branch || undefined  // 指定分支
    })
    
    if (res.data.success && res.data.dockerfiles) {
      // 更新扫描到的 Dockerfile
      const dockerfileCount = Object.keys(res.data.dockerfiles).length
      if (dockerfileCount > 0) {
        // 保留现有的 hasChanges 状态
        const existingChanges = dockerfileList.value.reduce((acc, item) => {
          acc[item.path] = item.hasChanges
          return acc
        }, {})
        const existingOriginalContent = dockerfileList.value.reduce((acc, item) => {
          acc[item.path] = item.originalContent
          return acc
        }, {})
        
        for (const [dockerfile_path, content] of Object.entries(res.data.dockerfiles)) {
          await axios.put(
            `/api/git-sources/${currentSource.value.source_id}/dockerfiles/${encodeURIComponent(dockerfile_path)}`,
            { content: content }
          )
        }
        
        // 刷新 Dockerfile 列表，保留更改状态
        await loadDockerfiles(currentSource.value.source_id, true)
        
        // 恢复 hasChanges 状态
        dockerfileList.value.forEach(item => {
          if (existingChanges[item.path] !== undefined) {
            item.hasChanges = existingChanges[item.path]
          }
          if (existingOriginalContent[item.path] !== undefined && existingOriginalContent[item.path] !== '') {
            item.originalContent = existingOriginalContent[item.path]
          }
        })
      }
      // 刷新数据源列表以更新 Dockerfile 数量
      loadSources()
    } else {
      alert('扫描失败：' + (res.data.detail || '未知错误'))
    }
  } catch (error) {
    console.error('扫描 Dockerfile 失败:', error)
    alert(error.response?.data?.detail || '扫描 Dockerfile 失败')
  } finally {
    scanningDockerfiles.value = false
  }
}

// 分支变化时的处理
async function onDockerfileBranchChanged() {
  if (!currentSource.value) {
    return
  }
  
  // 清空列表
  dockerfileList.value = []
  
  // 如果有选择分支，扫描该分支的 Dockerfile
  if (selectedBranch.value) {
    scanningDockerfiles.value = true
    try {
      const res = await axios.post('/api/verify-git-repo', {
        git_url: currentSource.value.git_url,
        save_as_source: false,
        source_id: currentSource.value.source_id,
        branch: selectedBranch.value
      })
      
      if (res.data.success && res.data.dockerfiles) {
        const dockerfiles = res.data.dockerfiles || {}
        dockerfileList.value = Object.keys(dockerfiles).map(path => ({
          path,
          content: dockerfiles[path],
          originalContent: dockerfiles[path], // 从分支扫描的，设为已提交状态
          lineCount: dockerfiles[path].split('\n').length,
          hasChanges: false
        }))
      }
    } catch (error) {
      console.error('加载分支 Dockerfile 失败:', error)
    } finally {
      scanningDockerfiles.value = false
    }
  } else {
    // 使用默认分支，从数据源加载
    await loadDockerfiles(currentSource.value.source_id, true)
  }
}

function openCommitModal(dockerfilePath) {
  if (!currentSource.value) {
    return
  }
  committingDockerfilePath.value = dockerfilePath
  commitForm.value = {
    branch: currentSource.value.default_branch || (currentSource.value.branches && currentSource.value.branches[0]) || '',
    commitMessage: `Update ${dockerfilePath} via jar2docker`
  }
  showCommitModal.value = true
}

function closeCommitModal() {
  showCommitModal.value = false
  committingDockerfilePath.value = ''
  commitForm.value = {
    branch: '',
    commitMessage: ''
  }
}

async function commitDockerfile() {
  if (!commitForm.value.branch) {
    alert('请选择目标分支')
    return
  }
  
  if (!currentSource.value || !committingDockerfilePath.value) {
    return
  }
  
  committing.value = true
  try {
    const res = await axios.post(
      `/api/git-sources/${currentSource.value.source_id}/dockerfiles/${encodeURIComponent(committingDockerfilePath.value)}/commit`,
      {
        branch: commitForm.value.branch,
        commit_message: commitForm.value.commitMessage || undefined
      }
    )
    
    if (res.data.success) {
      if (res.data.no_changes) {
        alert('没有更改需要提交')
        // 如果没有更改，重置差异状态
        const dockerfileItem = dockerfileList.value.find(item => item.path === committingDockerfilePath.value)
        if (dockerfileItem) {
          dockerfileItem.hasChanges = false
        }
      } else {
        alert(`✅ ${res.data.message}`)
        // 提交成功后，更新原始内容并重置差异状态
        const dockerfileItem = dockerfileList.value.find(item => item.path === committingDockerfilePath.value)
        if (dockerfileItem) {
          dockerfileItem.originalContent = dockerfileItem.content
          dockerfileItem.hasChanges = false
        }
      }
      closeCommitModal()
    } else {
      alert('提交失败：' + (res.data.detail || '未知错误'))
    }
  } catch (error) {
    console.error('提交 Dockerfile 失败:', error)
    alert(error.response?.data?.detail || '提交 Dockerfile 失败')
  } finally {
    committing.value = false
  }
}
</script>

<style scoped>
.data-source-panel {
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
</style>


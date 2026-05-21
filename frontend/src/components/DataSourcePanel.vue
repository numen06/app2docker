<template>
  <div class="data-source-panel">

    <PageToolbar title="Git 数据源管理" icon="fa-database">
      <template #actions>
        <Button
          variant="outline"
          size="sm"
          :disabled="loading"
          title="刷新列表"
          @click="loadSources"
        >
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
          刷新
        </Button>
        <Button size="sm" @click="showCreateModal">
          <i class="fas fa-plus"></i>
          新建数据源
        </Button>
      </template>
    </PageToolbar>
    <div v-if="loading" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <i class="fas fa-spinner fa-spin"></i>
      加载中…
    </div>

    <EmptyState
      v-else-if="sources.length === 0"
      message="暂无数据源"
      icon="fa-inbox"
    >
      <p class="mt-2 text-xs text-slate-400">在镜像构建或流水线中验证 Git 仓库时可保存为数据源</p>
    </EmptyState>
    <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div v-for="source in sources" :key="source.source_id">
        <div class="card h-full shadow-sm">
          <div class="card-header bg-white">
            <div class="mb-2">
              <h5 class="card-title mb-0">
                <strong>{{ source.name }}</strong>
              </h5>
              <p class="text-slate-500 mb-0 mt-1" v-if="source.description" style="font-size: 0.9rem;">
                {{ source.description }}
              </p>
            </div>
            <div class="flex w-full gap-1">
              <Button
                variant="outline"
                size="sm"
                class="flex-1"
                @click="refreshSource(source)"
                :disabled="refreshing === source.source_id"
                title="刷新分支和标签"
              >
                <i class="fas fa-sync-alt" :class="{ 'fa-spin': refreshing === source.source_id }"></i>
              </Button>
              <Button
                variant="outline"
                size="sm"
                class="flex-1"
                @click="editSource(source)"
                title="编辑"
              >
                <i class="fas fa-edit"></i>
              </Button>
              <Button
                variant="outline"
                size="sm"
                class="flex-1"
                title="成员授权"
                @click="openResourcePermission(source)"
              >
                <i class="fas fa-user-shield"></i>
              </Button>
              <Button
                variant="destructive"
                size="sm"
                class="flex-1"
                @click="deleteSource(source)"
                title="删除"
              >
                <i class="fas fa-trash"></i>
              </Button>
            </div>
          </div>
          
          <div class="card-body">
            <div class="mb-3">
              <div class="flex items-center mb-1">
                <i class="fas fa-code-branch text-slate-500 mr-2" style="width: 18px;"></i>
                <small class="font-mono truncate" :title="source.git_url" style="font-size: 0.9rem;">
                  {{ formatGitUrl(source.git_url) }}
                </small>
              </div>
            </div>
            
            <div class="mb-3">
              <div class="flex items-center mb-1">
                <i class="fas fa-code-branch text-slate-500 mr-2" style="width: 18px;"></i>
                <small class="text-slate-500">分支：{{ source.branches?.length || 0 }} 个</small>
              </div>
              <div class="flex items-center mb-1">
                <i class="fas fa-tag text-slate-500 mr-2" style="width: 18px;"></i>
                <small class="text-slate-500">标签：{{ source.tags?.length || 0 }} 个</small>
              </div>
              <div v-if="source.default_branch" class="flex items-center mb-1">
                <i class="fas fa-check-circle text-green-600 mr-2" style="width: 18px;"></i>
                <small class="text-slate-500">默认分支：{{ source.default_branch }}</small>
              </div>
              <div class="flex items-center">
                <i class="fab fa-docker text-sky-600 mr-2" style="width: 18px;"></i>
                <small class="text-slate-500">
                  Dockerfile：{{ (source.dockerfiles && Object.keys(source.dockerfiles).length) || 0 }} 个
                </small>
              </div>
            </div>
            
            <div class="border-t border-slate-200 pt-2 mt-2">
              <Button 
                variant="outline" size="sm" class="w-full" 
                @click="manageDockerfiles(source)"
                title="管理 Dockerfile"
              >
                <i class="fab fa-docker"></i> 管理 Dockerfile
              </Button>
            </div>
            
            <div class="border-t border-slate-200 pt-2 mt-2">
              <div class="text-slate-500 small">
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

    <!-- 创建/编辑数据源模态框 -->
    <div v-if="showModal" class="data-source-modal fixed inset-0 z-[2000] flex items-end justify-center overflow-y-auto bg-black/50 p-2 sm:items-center sm:p-4" @click.self="closeModal"
      >
      <div class="relative z-10 mx-auto w-full max-w-3xl">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="modal-title">
              {{ editingSource ? '编辑数据源' : '新建数据源' }}
            </h5>
            <button type="button" class="rounded-md p-2 text-slate-500 hover:bg-slate-100" @click="closeModal"><i class="fas fa-times"></i></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <form @submit.prevent="saveSource">
              <div class="mb-3">
                <label class="block text-sm font-medium text-slate-700">数据源名称 <span class="text-red-500">*</span></label>
                <input 
                  v-model="formData.name" 
                  type="text" 
                  class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400" 
                  required
                  placeholder="例如：主项目仓库"
                >
              </div>
              <div class="mb-3">
                <label class="block text-sm font-medium text-slate-700">描述</label>
                <input 
                  v-model="formData.description" 
                  type="text" 
                  class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                  placeholder="数据源描述（可选）"
                >
              </div>
              <div class="mb-3">
                <label class="block text-sm font-medium text-slate-700">Git 仓库地址 <span class="text-red-500">*</span></label>
                <div class="data-source-input-group input-group input-group-sm">
                  <input 
                    v-model="formData.git_url" 
                    type="text" 
                    class="flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400" 
                    required
                    placeholder="https://github.com/user/repo.git"
                    :readonly="editingSource"
                  >
                  <Button 
                    type="button" 
                    variant="outline" size="sm" 
                    @click="verifyAndSave"
                    :disabled="!formData.git_url || verifying"
                  >
                    <span v-if="verifying" class="fas fa-spinner fa-spin inline-block"></span>
                    <i v-else class="fas fa-search mr-1"></i>
                    {{ verifying ? '验证中...' : (editingSource && !isVerified ? '重新验证' : '验证仓库') }}
                  </Button>
                </div>
                <small class="text-slate-500">
                  <span v-if="editingSource">编辑模式下修改 Git 地址或认证信息需要重新验证</span>
                  <span v-else>新建数据源必须先验证 Git 仓库才能保存</span>
                </small>
                <div v-if="isVerified" class="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800 alert-sm mt-2 mb-0">
                  <i class="fas fa-check-circle"></i> 仓库已验证，可以保存
                </div>
              </div>
              <div class="mb-3">
                <div class="card border-info">
                  <div class="card-header bg-info bg-opacity-10 py-2">
                    <small class="text-slate-500">
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
                          class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                          placeholder="username 或 token"
                        >
                      </div>
                      <div class="col-md-6">
                        <label class="form-label small">Git 密码/Token</label>
                        <input 
                          v-model="formData.password" 
                          type="password" 
                          class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
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
                <label class="block text-sm font-medium text-slate-700">分支列表</label>
                <div class="border rounded p-2 bg-slate-50" style="max-height: 150px; overflow-y: auto;">
                  <Badge v-for="branch in formData.branches" :key="branch" variant="default" class="mr-1 mb-1">
                    {{ branch }}
                  </Badge>
                </div>
              </div>
              <div v-if="formData.tags && formData.tags.length > 0" class="mb-3">
                <label class="block text-sm font-medium text-slate-700">标签列表</label>
                <div class="border rounded p-2 bg-slate-50" style="max-height: 150px; overflow-y: auto;">
                  <Badge v-for="tag in formData.tags.slice(0, 20)" :key="tag" variant="info" class="mr-1 mb-1">
                    {{ tag }}
                  </Badge>
                  <span v-if="formData.tags.length > 20" class="text-slate-500 small">
                    ... 还有 {{ formData.tags.length - 20 }} 个标签
                  </span>
                </div>
              </div>
              <div v-if="formData.branches && formData.branches.length > 0" class="mb-3">
                <label class="block text-sm font-medium text-slate-700">默认分支</label>
                <select 
                  v-model="formData.default_branch" 
                  class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                  :disabled="!isVerified && !editingSource"
                >
                  <option value="">请选择默认分支</option>
                  <option v-for="branch in formData.branches" :key="branch" :value="branch">
                    {{ branch }}
                  </option>
                </select>
                <small class="text-slate-500">选择该数据源的默认分支</small>
              </div>
              <div v-else-if="formData.default_branch" class="mb-3">
                <label class="block text-sm font-medium text-slate-700">默认分支</label>
                <input 
                  :value="formData.default_branch" 
                  type="text" 
                  class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400" 
                  readonly
                >
              </div>
            </form>
          </div>
          <div class="data-source-modal-footer flex shrink-0 flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" size="sm" class="w-full sm:w-auto" @click="closeModal">取消</Button>
            <Button 
              type="button" 
              size="sm"
              class="w-full sm:w-auto"
              @click="saveSource"
              :disabled="!formData.git_url || verifying || (!editingSource && !isVerified)"
              :title="!editingSource && !isVerified ? '请先验证 Git 仓库' : ''"
            >
              <i class="fas fa-save"></i> 保存
            </Button>
          </div>
        </div>
      </div>
    </div>
<!-- Dockerfile 管理模态框 -->
    <div v-if="showDockerfileModal && currentSource" class="data-source-modal fixed inset-0 z-[2000] flex items-end justify-center overflow-y-auto bg-black/50 p-2 sm:items-center sm:p-4" @click.self="closeDockerfileModal"
      >
      <div class="relative z-10 mx-auto w-full max-w-5xl">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="modal-title">
              <i class="fab fa-docker"></i> Dockerfile 管理 - {{ currentSource.name }}
            </h5>
            <button type="button" class="rounded-md p-2 text-slate-500 hover:bg-slate-100" @click="closeDockerfileModal"><i class="fas fa-times"></i></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4" style="max-height: 70vh; overflow-y: auto;">
            <!-- 操作栏 -->
            <div class="data-source-dockerfile-toolbar row g-3 mb-4">
              <div class="col-md-5">
                <label class="form-label fw-semibold">
                  <i class="fas fa-code-branch text-slate-500 mr-1"></i> 分支选择
                </label>
                <select 
                  v-model="selectedBranch" 
                  class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                  @change="onDockerfileBranchChanged"
                >
                  <option value="">默认分支 ({{ currentSource.default_branch || 'main' }})</option>
                  <option v-for="branch in currentSource.branches || []" :key="branch" :value="branch">
                    {{ branch }}
                  </option>
                </select>
                <small class="text-slate-500 block mt-1">
                  <i class="fas fa-info-circle"></i> 选择分支以查看该分支的 Dockerfile
                </small>
              </div>
              <div class="col-md-4 flex items-end">
                <div class="text-slate-500 small">
                  <i class="fab fa-docker text-sky-600 mr-1"></i>
                  <strong>{{ dockerfileList.length }}</strong> 个 Dockerfile
                </div>
              </div>
              <div class="col-md-3 flex items-end gap-2">
                <Button 
                  variant="outline" size="sm" class="flex-1" 
                  @click="scanDockerfiles"
                  :disabled="scanningDockerfiles"
                  title="扫描 Dockerfile"
                >
                  <i class="fas fa-search" :class="{ 'fa-spin': scanningDockerfiles }"></i>
                  <span class="hidden sm:inline ml-1">扫描</span>
                </Button>
                <Button size="sm" class="flex-1" @click="showCreateDockerfile">
                  <i class="fas fa-plus"></i>
                  <span class="hidden sm:inline ml-1">新建</span>
                </Button>
              </div>
            </div>

            <!-- Dockerfile 列表 -->
            <div v-if="loadingDockerfiles" class="text-center py-12">
              <i class="fas fa-spinner fa-spin"></i>
              <p class="text-slate-500 mt-2 mb-0">加载中...</p>
            </div>
            <div v-else-if="dockerfileList.length === 0" class="text-center py-12 text-slate-500">
              <i class="fab fa-docker fa-4x mb-3 opacity-50"></i>
              <p class="mb-2 fw-semibold">暂无 Dockerfile</p>
              <p class="small mb-0">验证 Git 仓库时会自动扫描 Dockerfile，您也可以手动添加</p>
            </div>
            <div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              <div v-for="item in dockerfileList" :key="item.path" class="col-12">
                <div class="card border shadow-sm">
                  <div class="card-body p-3">
                    <div class="data-source-dockerfile-item flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-start">
                      <div class="min-w-0 flex-1">
                        <div class="flex flex-wrap items-center gap-2 mb-2">
                          <i class="fab fa-docker text-sky-600 mr-2 fs-5"></i>
                          <h6 class="mb-0 fw-semibold font-mono break-all text-sm">{{ item.path }}</h6>
                          <Badge v-if="item.hasChanges || item.originalContent === ''" 
                                variant="warning" class="ml-2 text-slate-900" 
                                title="有未提交的更改">
                            <i class="fas fa-exclamation-circle"></i> 未提交
                          </Badge>
                        </div>
                        <div class="flex flex-wrap items-center gap-2 text-slate-500 small sm:gap-3">
                          <span>
                            <i class="fas fa-file-lines mr-1"></i>
                            {{ item.lineCount }} 行
                          </span>
                          <span v-if="item.originalContent === ''" class="text-green-600">
                            <i class="fas fa-plus-circle mr-1"></i>
                            新建文件
                          </span>
                          <span v-else-if="item.hasChanges" class="text-amber-600">
                            <i class="fas fa-edit mr-1"></i>
                            已修改
                          </span>
                          <span v-else class="text-green-600">
                            <i class="fas fa-check-circle mr-1"></i>
                            已同步
                          </span>
                        </div>
                      </div>
                      <div class="flex w-full shrink-0 gap-1 sm:ml-3 sm:w-auto">
                        <Button 
                          variant="outline" size="sm"
                          class="flex-1 sm:flex-none"
                          @click="editDockerfile(item.path, item.content)" 
                          title="编辑 Dockerfile"
                        >
                          <i class="fas fa-edit"></i>
                          <span class="hidden md:inline ml-1">编辑</span>
                        </Button>
                        <Button 
                          v-if="item.hasChanges || item.originalContent === ''"
                          variant="outline" size="sm"
                          class="flex-1 sm:flex-none"
                          @click="openCommitModal(item.path)"
                          title="提交到 Git 仓库"
                        >
                          <i class="fas fa-code-branch"></i>
                          <span class="hidden md:inline ml-1">提交</span>
                        </Button>
                        <Button 
                          variant="destructive" size="sm"
                          class="flex-1 sm:flex-none"
                          @click="deleteDockerfile(item.path)" 
                          title="删除 Dockerfile"
                        >
                          <i class="fas fa-trash"></i>
                          <span class="hidden md:inline ml-1">删除</span>
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
<!-- Dockerfile 编辑器模态框 -->
    <div v-if="showDockerfileEditor && currentSource" class="data-source-modal fixed inset-0 z-[2000] flex items-end justify-center overflow-y-auto bg-black/50 p-2 sm:items-center sm:p-4" @click.self="closeDockerfileEditor"
      >
      <div class="relative z-10 mx-auto w-full max-w-5xl">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="modal-title">
              <i class="fab fa-docker"></i> {{ editingDockerfilePath ? '编辑' : '新建' }} Dockerfile
            </h5>
            <button type="button" class="rounded-md p-2 text-slate-500 hover:bg-slate-100" @click="closeDockerfileEditor"><i class="fas fa-times"></i></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4" style="max-height: 70vh; overflow-y: auto;">
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700">Dockerfile 路径 <span class="text-red-500">*</span></label>
              <input 
                v-model="dockerfileForm.path" 
                type="text" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                :readonly="!!editingDockerfilePath"
                placeholder="Dockerfile 或 Dockerfile.prod"
                required
              >
              <small class="text-slate-500">相对路径，如：Dockerfile、Dockerfile.prod、docker/Dockerfile</small>
            </div>
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700">内容 <span class="text-red-500">*</span></label>
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
          <div class="data-source-modal-footer flex shrink-0 flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" size="sm" class="w-full sm:w-auto" @click="closeDockerfileEditor">取消</Button>
            <Button type="button" size="sm" class="w-full sm:w-auto" @click="saveDockerfile">
              <i class="fas fa-save"></i> 保存
            </Button>
          </div>
        </div>
      </div>
    </div>
<!-- 提交 Dockerfile 模态框 -->
    <div v-if="showCommitModal && currentSource" class="data-source-modal fixed inset-0 z-[2000] flex items-end justify-center overflow-y-auto bg-black/50 p-2 sm:items-center sm:p-4" @click.self="closeCommitModal"
      >
      <div class="relative z-10 mx-auto w-full max-w-lg">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="modal-title">
              <i class="fas fa-code-branch"></i> 提交 Dockerfile 到 Git 仓库
            </h5>
            <button type="button" class="rounded-md p-2 text-slate-500 hover:bg-slate-100" @click="closeCommitModal"><i class="fas fa-times"></i></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700">Dockerfile 路径</label>
              <input 
                :value="committingDockerfilePath" 
                type="text" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400" 
                readonly
              >
            </div>
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700">目标分支 <span class="text-red-500">*</span></label>
              <select 
                v-model="commitForm.branch" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                required
              >
                <option value="">请选择分支</option>
                <option v-for="branch in currentSource.branches || []" :key="branch" :value="branch">
                  {{ branch }}
                </option>
              </select>
              <small class="text-slate-500">选择要提交到的分支</small>
            </div>
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700">提交信息</label>
              <input 
                v-model="commitForm.commitMessage" 
                type="text" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                placeholder="例如：Update Dockerfile"
              >
              <small class="text-slate-500">如果不填写，将使用默认提交信息</small>
            </div>
            <div class="rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900 alert-sm mb-0">
              <i class="fas fa-info-circle"></i> 
              <strong>提示：</strong>提交前会自动同步远程仓库，确保与远程保持一致。如有冲突，将使用本地版本。
            </div>
          </div>
          <div class="data-source-modal-footer flex shrink-0 flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" size="sm" class="w-full sm:w-auto" @click="closeCommitModal">取消</Button>
            <Button 
              type="button" 
              size="sm"
              class="w-full sm:w-auto"
              @click="commitDockerfile"
              :disabled="!commitForm.branch || committing"
            >
              <span v-if="committing" class="fas fa-spinner fa-spin inline-block"></span>
              <i v-else class="fas fa-code-branch mr-1"></i>
              {{ committing ? '提交中...' : '提交' }}
            </Button>
          </div>
        </div>
      </div>
    </div>

  <ResourceMemberPermissionDialog
    v-model="permissionDialogOpen"
    resource-type="git_source"
    :resource-id="permissionTarget?.source_id || ''"
    :team-id="teamStore.activeTeamId"
    :resource-name="permissionTarget?.name || ''"
  />
</div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import { StreamLanguage } from '@codemirror/language'
import { shell } from '@codemirror/legacy-modes/mode/shell'
import { oneDark } from '@codemirror/theme-one-dark'
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import { Badge } from "@/components/ui/badge";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import axios from 'axios'
import { onMounted, ref, watch } from 'vue'
import ResourceMemberPermissionDialog from '@/components/team/ResourceMemberPermissionDialog.vue'
import { useTeamStore } from '@/stores/team'
import { Codemirror } from 'vue-codemirror'


const teamStore = useTeamStore()

const permissionDialogOpen = ref(false)
const permissionTarget = ref(null)

function openResourcePermission(source) {
  permissionTarget.value = source
  permissionDialogOpen.value = true
}

const sources = ref([])
const loading = ref(false)
const refreshing = ref(null)
const showModal = ref(false)
const editingSource = ref(null)
const verifying = ref(false)
const isVerified = ref(false)  // 验证状态标识


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


onMounted(() => {
  loadSources()
})

async function loadSources() {
  loading.value = true
  try {
    const res = await axios.get('/api/git-sources')
    sources.value = res.data.sources || []
  } catch (error) {
    console.error('加载数据源列表失败:', error)
    toastError('加载数据源列表失败')
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
    toastError('请输入 Git 仓库地址')
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
      toastError('验证失败：' + (res.data.detail || '未知错误'))
      isVerified.value = false
    }
  } catch (error) {
    console.error('验证仓库失败:', error)
    toastApiError(error, '验证仓库失败')
    isVerified.value = false
  } finally {
    verifying.value = false
  }
}

async function saveSource() {
  if (!formData.value.name || !formData.value.git_url) {
    toastError('请填写必填字段')
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
      toastError('请先验证 Git 仓库后再保存')
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
      toastSuccess('数据源更新成功')
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
      toastSuccess('数据源创建成功')
    }
    closeModal()
    loadSources()
  } catch (error) {
    console.error('保存数据源失败:', error)
    toastApiError(error, '保存数据源失败')
  }
}

function closeModal() {
  showModal.value = false
  editingSource.value = null
}

async function refreshSource(source) {
  if (!(await showConfirm({ message: `确定要刷新数据源 "${source.name}" 的分支和标签吗？` }))) {
    return
  }
  
  refreshing.value = source.source_id
  try {
    // 调用 verify-git-repo API，传递 source_id 会自动更新数据源的缓存
    // 这与手动触发流水线中的刷新分支功能使用相同的逻辑
    const res = await axios.post('/api/verify-git-repo', {
      git_url: source.git_url,
      save_as_source: false,
      source_id: source.source_id  // 传递 source_id 会自动更新数据源的缓存（分支、标签、Dockerfile）
    })
    
    if (res.data.success) {
      // 后端已经自动更新了数据源的缓存，这里只需要刷新列表即可
      toastSuccess('数据源刷新成功')
      loadSources()
    } else {
      toastError('刷新失败：' + (res.data.detail || '未知错误'))
    }
  } catch (error) {
    console.error('刷新数据源失败:', error)
    toastApiError(error, '刷新数据源失败')
  } finally {
    refreshing.value = null
  }
}

async function deleteSource(source) {
  if (!(await showConfirm({ message: `确定要删除数据源 "${source.name}" 吗？`, danger: true }))) {
    return
  }
  
  try {
    await axios.delete(`/api/git-sources/${source.source_id}`)
    toastSuccess('数据源已删除')
    loadSources()
  } catch (error) {
    console.error('删除数据源失败:', error)
    toastApiError(error, '删除数据源失败')
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
    toastError('加载 Dockerfile 列表失败')
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
    toastError('请填写 Dockerfile 路径和内容')
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
    
    toastSuccess('Dockerfile 保存成功')
    closeDockerfileEditor()
    // 刷新数据源列表以更新 Dockerfile 数量
    loadSources()
  } catch (error) {
    console.error('保存 Dockerfile 失败:', error)
    toastApiError(error, '保存 Dockerfile 失败')
  }
}

async function deleteDockerfile(path) {
  if (!(await showConfirm({ message: `确定要删除 Dockerfile "${path}" 吗？`, danger: true }))) {
    return
  }

  try {
    await axios.delete(
      `/api/git-sources/${currentSource.value.source_id}/dockerfiles/${encodeURIComponent(path)}`
    )
    toastSuccess('Dockerfile 已删除')
    await loadDockerfiles(currentSource.value.source_id, true) // 保留更改状态
    // 刷新数据源列表以更新 Dockerfile 数量
    loadSources()
  } catch (error) {
    console.error('删除 Dockerfile 失败:', error)
    toastApiError(error, '删除 Dockerfile 失败')
  }
}

async function scanDockerfiles() {
  if (!currentSource.value) {
    return
  }
  
  const branch = selectedBranch.value || currentSource.value.default_branch || 'main'
  const branchText = branch ? `分支 "${branch}"` : '默认分支'
  
  if (!(await showConfirm({ message: `确定要扫描数据源 "${currentSource.value.name}" 的 Dockerfile 吗？\n\n这将从 Git 仓库的 ${branchText} 扫描所有 Dockerfile。` }))) {
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
      toastError('扫描失败：' + (res.data.detail || '未知错误'))
    }
  } catch (error) {
    console.error('扫描 Dockerfile 失败:', error)
    toastApiError(error, '扫描 Dockerfile 失败')
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
    commitMessage: `Update ${dockerfilePath} via app2docker`
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
    toastError('请选择目标分支')
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
        toastInfo('没有更改需要提交')
        // 如果没有更改，重置差异状态
        const dockerfileItem = dockerfileList.value.find(item => item.path === committingDockerfilePath.value)
        if (dockerfileItem) {
          dockerfileItem.hasChanges = false
        }
      } else {
        toastInfo(`✅ ${res.data.message}`)
        // 提交成功后，更新原始内容并重置差异状态
        const dockerfileItem = dockerfileList.value.find(item => item.path === committingDockerfilePath.value)
        if (dockerfileItem) {
          dockerfileItem.originalContent = dockerfileItem.content
          dockerfileItem.hasChanges = false
        }
      }
      closeCommitModal()
    } else {
      toastError('提交失败：' + (res.data.detail || '未知错误'))
    }
  } catch (error) {
    console.error('提交 Dockerfile 失败:', error)
    toastApiError(error, '提交 Dockerfile 失败')
  } finally {
    committing.value = false
  }
}
</script>

<style scoped>
.data-source-panel :deep(.card) {
  transition: transform 0.2s, box-shadow 0.2s;
}

.data-source-panel :deep(.card:hover) {
  transform: translateY(-2px);
  box-shadow: 0 0.5rem 1rem rgb(15 23 42 / 0.08);
}

@media (max-width: 767px) {
  .data-source-panel :deep(.card:hover) {
    transform: none;
    box-shadow: 0 1px 2px rgb(15 23 42 / 0.05);
  }

  .data-source-panel :deep(.card-header),
  .data-source-panel :deep(.card-body) {
    padding: 0.75rem;
  }

  .data-source-panel .row > [class*="col-md-"] {
    flex: 0 0 100%;
    width: 100%;
    max-width: 100%;
  }

  .data-source-dockerfile-toolbar > [class*="col-md-"] {
    margin-bottom: 0;
  }

  .data-source-dockerfile-toolbar .flex.items-end {
    width: 100%;
  }

  .data-source-input-group {
    flex-direction: column;
    align-items: stretch;
  }

  .data-source-input-group > input {
    width: 100%;
    border-radius: 0.375rem !important;
  }

  .data-source-input-group > .btn,
  .data-source-input-group > button {
    width: 100%;
    margin-top: 0.375rem;
    border-radius: 0.375rem !important;
  }

  .data-source-modal .modal-title {
    font-size: 0.9375rem;
    line-height: 1.35;
    word-break: break-word;
    padding-right: 0.5rem;
  }

  .data-source-modal > .relative {
    max-width: 100%;
  }

  .data-source-modal-footer > * {
    justify-content: center;
  }
}
</style>


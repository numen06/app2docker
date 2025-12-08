<template>
  <div class="data-source-panel">
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
      <p class="text-muted small mt-2">在源码构建或流水线中验证 Git 仓库时可保存为数据源</p>
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
              <div v-if="source.default_branch" class="d-flex align-items-center">
                <i class="fas fa-check-circle text-success me-2" style="width: 18px;"></i>
                <small class="text-muted">默认分支：{{ source.default_branch }}</small>
              </div>
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
                    v-if="!editingSource"
                    type="button" 
                    class="btn btn-outline-primary" 
                    @click="verifyAndSave"
                    :disabled="!formData.git_url || verifying"
                  >
                    <span v-if="verifying" class="spinner-border spinner-border-sm me-1"></span>
                    <i v-else class="fas fa-search me-1"></i>
                    {{ verifying ? '验证中...' : '验证并保存' }}
                  </button>
                </div>
                <small class="text-muted">编辑模式下无法修改 Git 地址，请先验证后保存</small>
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
              <div v-if="formData.default_branch" class="mb-3">
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
              :disabled="!formData.git_url || verifying"
            >
              <i class="fas fa-save"></i> 保存
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showModal" class="modal-backdrop fade show" style="z-index: 1045;"></div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { onMounted, ref, watch } from 'vue'

const sources = ref([])
const loading = ref(false)
const refreshing = ref(null)
const showModal = ref(false)
const editingSource = ref(null)
const verifying = ref(false)

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
    alert('加载数据源列表失败')
  } finally {
    loading.value = false
  }
}

function showCreateModal() {
  editingSource.value = null
  formData.value = {
    name: '',
    description: '',
    git_url: '',
    branches: [],
    tags: [],
    default_branch: '',
    username: '',
    password: ''
  }
  showModal.value = true
}

function editSource(source) {
  editingSource.value = source
  formData.value = {
    name: source.name,
    description: source.description || '',
    git_url: source.git_url,
    branches: source.branches || [],
    tags: source.tags || [],
    default_branch: source.default_branch || '',
    username: source.username || '',
    password: source.has_password ? '******' : ''  // 不显示真实密码，显示占位符
  }
  showModal.value = true
}

async function verifyAndSave() {
  if (!formData.value.git_url) {
    alert('请输入 Git 仓库地址')
    return
  }
  
  verifying.value = true
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
      
      // 如果没有设置名称，使用仓库名作为默认名称
      if (!formData.value.name) {
        const urlParts = formData.value.git_url.replace('.git', '').split('/')
        formData.value.name = urlParts[urlParts.length - 1] || '未命名数据源'
      }
    } else {
      alert('验证失败：' + (res.data.detail || '未知错误'))
    }
  } catch (error) {
    console.error('验证仓库失败:', error)
    alert(error.response?.data?.detail || '验证仓库失败')
  } finally {
    verifying.value = false
  }
}

async function saveSource() {
  if (!formData.value.name || !formData.value.git_url) {
    alert('请填写必填字段')
    return
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
      // 创建 - 如果还没有验证，先验证
      if (formData.value.branches.length === 0) {
        await verifyAndSave()
      }
      
      await axios.post('/api/git-sources', {
        name: formData.value.name,
        description: formData.value.description,
        git_url: formData.value.git_url,
        branches: formData.value.branches,
        tags: formData.value.tags,
        default_branch: formData.value.default_branch,
        username: formData.value.username || null,
        password: password || null
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


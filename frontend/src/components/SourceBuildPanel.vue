<template>
  <div class="source-build-panel">
    <form @submit.prevent="handleBuild">
      <div class="mb-3">
        <label class="form-label">
          项目类型 <span class="text-danger">*</span>
        </label>
        <div class="btn-group w-100" role="group">
          <button
            v-for="type in projectTypes"
            :key="type.value"
            type="button"
            class="btn"
            :class="form.projectType === type.value ? 'btn-primary' : 'btn-outline-primary'"
            @click="changeProjectType(type.value)"
          >
            <i :class="getProjectTypeIcon(type.value)"></i>
            {{ type.label }}
          </button>
        </div>
        <div class="form-text small text-muted">
          <i class="fas fa-info-circle"></i> 选择后自动过滤对应类型的模板
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label">模板</label>
        <div class="input-group input-group-sm mb-1">
          <span class="input-group-text"><i class="fas fa-search"></i></span>
          <input
            v-model="templateSearch"
            type="text"
            class="form-control"
            placeholder="搜索模板..."
            :disabled="form.useProjectDockerfile"
          />
        </div>
        <select 
          v-model="form.template" 
          class="form-select" 
          @change="loadTemplateParams"
          :disabled="form.useProjectDockerfile"
        >
          <option v-for="tpl in filteredTemplates" :key="tpl.name" :value="tpl.name">
            {{ tpl.name }} ({{ getProjectTypeLabel(tpl.project_type) }}{{ tpl.type === 'builtin' ? ' · 内置' : '' }})
          </option>
        </select>
        <div class="form-text small text-muted">
          <i class="fas fa-info-circle"></i> 
          <span v-if="form.useProjectDockerfile">
            将使用项目中的 Dockerfile，模板选项已禁用
          </span>
          <span v-else>
            已按项目类型过滤，可在模板管理中维护
          </span>
        </div>
      </div>

      <!-- Dockerfile 选择选项 -->
      <div class="row g-3 mb-3">
        <div class="col-md-12">
          <div class="form-check">
            <input 
              v-model="form.useProjectDockerfile" 
              type="checkbox" 
              class="form-check-input" 
              id="useProjectDockerfile"
            />
            <label class="form-check-label" for="useProjectDockerfile">
              <i class="fas fa-file-code"></i> 优先使用项目中的 Dockerfile
            </label>
          </div>
          <div class="form-text small text-muted">
            <i class="fas fa-info-circle"></i> 
            勾选后，如果项目中存在 Dockerfile，将优先使用项目中的 Dockerfile；否则使用选择的模板
          </div>
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label">
          Git 仓库地址 <span class="text-danger">*</span>
        </label>
        <div class="input-group">
          <input 
            v-model="form.gitUrl" 
            type="text" 
            class="form-control" 
            placeholder="https://github.com/user/repo.git 或 git@github.com:user/repo.git"
            :disabled="verifying"
            required
          />
          <button 
            type="button" 
            class="btn btn-outline-primary" 
            @click="verifyGitRepo"
            :disabled="!form.gitUrl || verifying || repoVerified"
          >
            <span v-if="verifying" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else-if="repoVerified" class="fas fa-check-circle me-1"></i>
            <i v-else class="fas fa-search me-1"></i>
            {{ verifying ? '验证中...' : (repoVerified ? '已验证' : '验证仓库') }}
          </button>
        </div>
        <div class="form-text small">
          <i class="fas fa-info-circle"></i> 
          支持 HTTPS 和 SSH 协议的 Git 仓库地址，请先验证仓库再选择分支
        </div>
        <div v-if="repoError" class="alert alert-danger alert-sm mt-2 mb-0">
          <i class="fas fa-exclamation-triangle"></i> {{ repoError }}
        </div>
        <div v-if="repoVerified" class="alert alert-success alert-sm mt-2 mb-0">
          <i class="fas fa-check-circle"></i> 仓库验证成功！找到 {{ branchesAndTags.branches.length }} 个分支、{{ branchesAndTags.tags.length }} 个标签
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label">分支/标签
            <span v-if="!repoVerified" class="text-muted small">(请先验证仓库)</span>
          </label>
          <select 
            v-if="repoVerified"
            v-model="form.branch" 
            class="form-select"
          >
            <option value="">使用默认分支 ({{ branchesAndTags.default_branch || 'main' }})</option>
            <optgroup v-if="branchesAndTags.branches.length > 0" label="分支">
              <option v-for="branch in branchesAndTags.branches" :key="branch" :value="branch">
                {{ branch }}
              </option>
            </optgroup>
            <optgroup v-if="branchesAndTags.tags.length > 0" label="标签">
              <option v-for="tag in branchesAndTags.tags" :key="tag" :value="tag">
                {{ tag }}
              </option>
            </optgroup>
          </select>
          <input 
            v-else
            type="text" 
            class="form-control" 
            placeholder="请先验证 Git 仓库"
            disabled
          />
          <div class="form-text small">
            <i class="fas fa-info-circle"></i> 
            验证仓库后可选择分支或标签，留空则使用默认分支
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">子目录（可选）</label>
          <input 
            v-model="form.subPath" 
            type="text" 
            class="form-control" 
            placeholder="留空则使用仓库根目录"
          />
          <div class="form-text small">
            <i class="fas fa-info-circle"></i> 
            如果项目在仓库的子目录中，指定相对路径
          </div>
        </div>
      </div>

      <!-- 推送选项（独立一栏） -->
      <div class="row g-3 mb-3">
        <div class="col-md-12">
          <div class="form-check">
            <input 
              v-model="form.push" 
              type="checkbox" 
              class="form-check-input" 
              id="pushImage"
            />
            <label class="form-check-label" for="pushImage">
              <i class="fas fa-cloud-upload-alt"></i> 构建后推送到仓库
            </label>
          </div>
          <div class="form-text small text-muted">
            <i class="fas fa-info-circle"></i> 
            勾选后将构建的镜像推送到激活的仓库
          </div>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label">
            镜像名称 <span class="text-danger">*</span>
          </label>
          <input 
            v-model="form.imageName" 
            type="text" 
            class="form-control" 
            :placeholder="imageNamePlaceholder" 
            required
          />
          <div class="form-text small">
            <i class="fas fa-info-circle"></i> 
            输入镜像名称（推送时会自动使用激活的仓库）
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">标签</label>
          <input v-model="form.tag" type="text" class="form-control" placeholder="latest" />
        </div>
      </div>

      <!-- 模板参数动态输入框 -->
      <div v-if="templateParams.length > 0" class="mb-3 p-3 bg-light rounded">
        <h6 class="mb-3">
          <i class="fas fa-sliders-h"></i> 模板参数
        </h6>
        <div class="row g-3">
          <div v-for="param in templateParams" :key="param.name" class="col-md-6">
            <label class="form-label">
              {{ param.description }}
              <span v-if="param.required" class="text-danger">*</span>
              <small v-if="param.default" class="text-muted">(默认: {{ param.default }})</small>
            </label>
            <input 
              v-model="form.templateParams[param.name]"
              type="text" 
              class="form-control form-control-sm"
              :placeholder="param.default || param.name"
              :required="param.required && !param.default"
            />
          </div>
        </div>
      </div>

      <button type="submit" class="btn btn-primary w-100" :disabled="building">
        <i class="fas fa-code-branch"></i> 
        {{ building ? '构建中...' : '开始构建' }}
        <span v-if="building" class="spinner-border spinner-border-sm ms-2"></span>
      </button>
    </form>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, ref, watch } from 'vue'

const form = ref({
  projectType: 'jar',
  template: '',
  gitUrl: '',
  branch: '',
  subPath: '',
  imageName: 'myapp/demo',
  tag: 'latest',
  push: false,
  templateParams: {},
  useProjectDockerfile: true  // 默认优先使用项目中的 Dockerfile
})

const templates = ref([])
const building = ref(false)
const templateParams = ref([])
const registries = ref([])
const templateSearch = ref('')  // 模板搜索关键字

// Git 仓库验证相关状态
const verifying = ref(false)
const repoVerified = ref(false)
const repoError = ref('')
const branchesAndTags = ref({
  branches: [],
  tags: [],
  default_branch: null
})

const projectTypes = computed(() => {
  const types = new Set()
  templates.value.forEach(t => types.add(t.project_type))
  
  const labelMap = {
    'jar': 'Java 应用（JAR）',
    'nodejs': 'Node.js 应用',
    'python': 'Python 应用',
    'go': 'Go 应用',
    'rust': 'Rust 应用'
  }
  
  // 定义排序顺序
  const orderMap = {
    'jar': 1,
    'nodejs': 2,
    'python': 3,
    'rust': 4,
    'go': 5  // Go 排在最后
  }
  
  const result = []
  types.forEach(type => {
    result.push({
      value: type,
      label: labelMap[type] || `${type.charAt(0).toUpperCase()}${type.slice(1)} 应用`,
      order: orderMap[type] || 999
    })
  })
  
  if (result.length === 0) {
    return [
      { value: 'jar', label: 'Java 应用（JAR）', order: 1 },
      { value: 'nodejs', label: 'Node.js 应用', order: 2 },
      { value: 'python', label: 'Python 应用', order: 3 },
      { value: 'rust', label: 'Rust 应用', order: 4 },
      { value: 'go', label: 'Go 应用', order: 5 }
    ]
  }
  
  // 按 order 排序
  return result.sort((a, b) => a.order - b.order)
})

const filteredTemplates = computed(() => {
  let list = templates.value.filter(t => t.project_type === form.value.projectType)
  if (templateSearch.value) {
    const kw = templateSearch.value.toLowerCase()
    list = list.filter(t => t.name.toLowerCase().includes(kw))
  }
  return list
})

const imageNamePlaceholder = computed(() => {
  return 'myapp/demo'
})

async function loadTemplates() {
  try {
    const res = await axios.get('/api/templates')
    templates.value = res.data.items || []
    if (filteredTemplates.value.length > 0) {
      form.value.template = filteredTemplates.value[0].name
      await loadTemplateParams()
    }
  } catch (error) {
    console.error('加载模板失败:', error)
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

function updateTemplates() {
  if (filteredTemplates.value.length > 0) {
    form.value.template = filteredTemplates.value[0].name
    loadTemplateParams()
  }
}

// 切换项目类型
function changeProjectType(type) {
  if (form.value.projectType === type) return
  form.value.projectType = type
  templateSearch.value = ''  // 清空搜索
  updateTemplates()
  // 如果当前模板不属于该类型，重置为第一个模板
  if (!filteredTemplates.value.some(t => t.name === form.value.template)) {
    form.value.template = filteredTemplates.value[0]?.name || ''
  }
}

// 获取项目类型图标
function getProjectTypeIcon(type) {
  const iconMap = {
    'jar': 'fab fa-java',
    'nodejs': 'fab fa-node-js',
    'python': 'fab fa-python',
    'go': 'fas fa-code',
    'rust': 'fas fa-cog'
  }
  return iconMap[type] || 'fas fa-cube'
}

// 获取项目类型标签
function getProjectTypeLabel(type) {
  const labelMap = {
    'jar': 'Java',
    'nodejs': 'Node.js',
    'python': 'Python',
    'go': 'Go',
    'rust': 'Rust'
  }
  return labelMap[type] || type
}

async function loadTemplateParams() {
  templateParams.value = []
  form.value.templateParams = {}
  
  if (!form.value.template || !form.value.projectType) {
    return
  }
  
  try {
    const res = await axios.get('/api/template-params', {
      params: {
        template: form.value.template,
        project_type: form.value.projectType
      }
    })
    
    templateParams.value = res.data.params || []
    
    templateParams.value.forEach(param => {
      if (param.default) {
        form.value.templateParams[param.name] = param.default
      }
    })
  } catch (error) {
    console.error('加载模板参数失败:', error)
  }
}


// 验证 Git 仓库
async function verifyGitRepo() {
  if (!form.value.gitUrl) {
    return
  }
  
  verifying.value = true
  repoError.value = ''
  repoVerified.value = false
  branchesAndTags.value = {
    branches: [],
    tags: [],
    default_branch: null
  }
  
  try {
    const res = await axios.post('/api/verify-git-repo', {
      git_url: form.value.gitUrl.trim()
    })
    
    if (res.data.success) {
      branchesAndTags.value = {
        branches: res.data.branches || [],
        tags: res.data.tags || [],
        default_branch: res.data.default_branch
      }
      repoVerified.value = true
      // 清空之前选择的分支
      form.value.branch = ''
    } else {
      repoError.value = '仓库验证失败'
    }
  } catch (error) {
    console.error('❗ 验证仓库失败:', error)
    repoError.value = error.response?.data?.detail || '无法访问仓库，请检查 URL 是否正确'
  } finally {
    verifying.value = false
  }
}

// 监听 Git URL 变化，重置验证状态
watch(() => form.value.gitUrl, () => {
  if (repoVerified.value) {
    repoVerified.value = false
    repoError.value = ''
    form.value.branch = ''
    branchesAndTags.value = {
      branches: [],
      tags: [],
      default_branch: null
    }
  }
})

async function handleBuild() {
  if (!form.value.gitUrl) {
    alert('请输入 Git 仓库地址')
    return
  }
  
  
  building.value = true
  
    const payload = {
      project_type: form.value.projectType,
      template: form.value.template,
      git_url: form.value.gitUrl.trim(),
      branch: form.value.branch.trim() || undefined,
      sub_path: form.value.subPath.trim() || undefined,
      imagename: form.value.imageName.trim(),
      tag: form.value.tag.trim() || 'latest',
      push: form.value.push ? 'on' : 'off',
      template_params: Object.keys(form.value.templateParams).length > 0 
        ? JSON.stringify(form.value.templateParams) 
        : undefined,
      use_project_dockerfile: form.value.useProjectDockerfile
    }
  
  try {
    const res = await axios.post('/api/build-from-source', payload)
    
    // 获取 build_id 或 task_id（兼容新旧版本）
    const buildId = res.data.build_id || res.data.task_id
    if (buildId) {
      console.log('✅ 构建任务已启动, task_id:', buildId)
      
      window.dispatchEvent(new CustomEvent('show-build-log'))
      
      setTimeout(() => {
        pollBuildLogs(buildId)
      }, 100)
    } else {
      console.warn('⚠️ 未返回 build_id')
      alert('构建启动失败：未返回 build_id')
      building.value = false
    }
  } catch (error) {
    console.error('❌ 构建请求失败:', error)
    alert(error.response?.data?.error || error.response?.data?.detail || '构建失败')
    building.value = false
  }
}

let pollInterval = null
async function pollBuildLogs(buildId) {
  console.log('🔄 开始轮询构建日志, task_id:', buildId)
  
  let lastLogLength = 0
  let taskCompleted = false
  
  const poll = async () => {
    try {
      // 先检查任务状态
      const taskRes = await axios.get(`/api/build-tasks/${buildId}`)
      const taskStatus = taskRes.data.status
      
      // 获取日志（兼容新旧API）
      let logs = ''
      try {
        // 优先尝试新API
        const res = await axios.get(`/api/build-tasks/${buildId}/logs`)
        logs = typeof res.data === 'string' ? res.data : String(res.data)
      } catch (e) {
        // 回退到旧API
        const res = await axios.get('/api/get-logs', {
          params: { build_id: buildId }
        })
        logs = typeof res.data === 'string' ? res.data : String(res.data)
      }
      
      const logLines = logs
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
      
      if (logLines.length > lastLogLength) {
        for (let i = lastLogLength; i < logLines.length; i++) {
          window.dispatchEvent(new CustomEvent('add-log', {
            detail: { text: logLines[i] }
          }))
        }
        lastLogLength = logLines.length
      }
      
      // 检查任务是否完成（优先检查任务状态）
      if (taskStatus === 'completed' || taskStatus === 'failed') {
        taskCompleted = true
        clearInterval(pollInterval)
        building.value = false
        console.log(`✅ 构建任务结束: ${taskStatus}`)
        window.dispatchEvent(new CustomEvent('add-log', {
          detail: { text: taskStatus === 'completed' ? '✅ 构建已完成' : '❌ 构建已失败' }
        }))
      }
    } catch (error) {
      console.error('❌ 获取日志失败:', error)
      if (error.response?.status === 404) {
        clearInterval(pollInterval)
        building.value = false
        window.dispatchEvent(new CustomEvent('add-log', {
          detail: { text: '❌ 任务不存在' }
        }))
      }
    }
  }
  
  window.dispatchEvent(new CustomEvent('add-log', {
    detail: { text: `🚀 开始构建，Task ID: ${buildId}` }
  }))
  
  await poll()
  
  let pollCount = 0
  pollInterval = setInterval(() => {
    if (taskCompleted) {
      clearInterval(pollInterval)
      return
    }
    
    pollCount++
    if (pollCount > 300) {  // 300 * 1000ms = 5分钟
      clearInterval(pollInterval)
      building.value = false
      console.log('⏰ 构建日志轮询超时')
      window.dispatchEvent(new CustomEvent('add-log', {
        detail: { text: '⏰ 构建日志轮询超时（5分钟）' }
      }))
    } else {
      poll()
    }
  }, 1000)  // 1秒 轮询一次
}

onMounted(() => {
  loadTemplates()
  loadRegistries()
})
</script>

<style scoped>
.source-build-panel {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 项目类型按钮组样式 */
.btn-group .btn {
  font-size: 0.9rem;
  padding: 0.5rem 0.75rem;
  transition: all 0.2s;
}

.btn-group .btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.btn-group .btn i {
  margin-right: 0.3rem;
}

/* 小型 Alert 样式 */
.alert-sm {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.alert-sm i {
  margin-right: 0.25rem;
}
</style>


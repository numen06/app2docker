<template>
  <div class="build-panel">
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
          />
        </div>
        <select v-model="form.template" class="form-select" @change="loadTemplateParams">
          <option v-for="tpl in filteredTemplates" :key="tpl.name" :value="tpl.name">
            {{ tpl.name }} ({{ getProjectTypeLabel(tpl.project_type) }}{{ tpl.type === 'builtin' ? ' · 内置' : '' }})
          </option>
        </select>
        <div class="form-text small text-muted">
          <i class="fas fa-info-circle"></i> 已按项目类型过滤，可在模板管理中维护
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label">
          选择文件 <span class="text-danger">*</span>
        </label>
        <input 
          type="file" 
          class="form-control" 
          :accept="fileAccept"
          @change="handleFileChange"
          @click="handleFileInputClick"
          required
        />
        <div v-if="form.file" class="alert alert-success mt-2 py-2 px-3 small">
          <i class="fas fa-check-circle"></i> 已选择: <strong>{{ form.file.name }}</strong> ({{ formatFileSize(form.file.size) }})
          <div class="mt-2 text-muted" style="font-size: 0.85em;">
            <i class="fas fa-info-circle"></i> 
            <strong>文件处理说明：</strong>
            <ul class="mb-0 mt-1" style="padding-left: 1.2em;">
              <li v-if="form.file.name.endsWith('.jar')">
                <strong>JAR 文件：</strong>将保存为固定名称 <code>app.jar</code>（原始文件名: <code>{{ form.file.name }}</code>）
              </li>
              <li v-else-if="isArchiveFile(form.file.name)">
                <strong>压缩包：</strong>
                <span v-if="form.extractArchive">
                  将自动解压到构建上下文根目录
                </span>
                <span v-else>
                  将保持压缩包原样（不解压）
                </span>
                （原始文件名: <code>{{ form.file.name }}</code>）
              </li>
              <li v-else>
                <strong>其他文件：</strong>将按原样保存到构建上下文（文件名: <code>{{ form.file.name }}</code>）
              </li>
            </ul>
            <div class="mt-2 p-2 bg-light rounded">
              <strong>💡 模板使用提示：</strong><br>
              在 Dockerfile 模板中可通过 <code>&#123;&#123;UPLOADED_FILENAME&#125;&#125;</code> 变量获取上传的原始文件名: <code>{{ form.file.name }}</code><br>
              <small class="text-muted">
                这样您可以在模板中根据文件名判断文件类型，决定是否需要特殊处理。
              </small>
            </div>
          </div>
        </div>
        <div v-else class="form-text small">
          <i class="fas fa-info-circle"></i> {{ fileHint }}
        </div>
        
        <!-- 压缩包解压选项 -->
        <div v-if="form.file && isArchiveFile(form.file.name)" class="mt-2">
          <div class="form-check">
            <input 
              v-model="form.extractArchive" 
              type="checkbox" 
              class="form-check-input" 
              id="extractArchive"
            />
            <label class="form-check-label" for="extractArchive">
              <i class="fas fa-file-archive"></i> 自动解压压缩包
            </label>
          </div>
          <div class="form-text small text-muted">
            <i class="fas fa-info-circle"></i> 
            勾选后将自动解压压缩包到构建上下文根目录；不勾选则保持压缩包原样，可在模板中手动处理
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
        <i class="fas fa-hammer"></i> 
        {{ building ? '构建中...' : '开始构建' }}
        <span v-if="building" class="spinner-border spinner-border-sm ms-2"></span>
      </button>
    </form>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'

const form = ref({
  projectType: 'jar',
  template: '',
  file: null,
  imageName: 'myapp/demo',
  tag: 'latest',
  push: false,
  extractArchive: true,  // 是否解压压缩包（默认解压）
  templateParams: {},  // 模板参数
})

const templates = ref([])
const building = ref(false)
const templateParams = ref([])  // 当前模板的参数列表
const registries = ref([])  // 仓库列表
const templateSearch = ref('')  // 模板搜索关键字

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
  
  // 如果没有模板，返回默认选项
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

const fileAccept = computed(() => {
  // Java 应用可以直接上传 .jar 文件
  if (form.value.projectType === 'jar') {
    return '.jar,.zip,.tar,.tar.gz,.tgz'
  }
  // 其他类型（Node.js/Python/Go 等）需要源码压缩包
  return '.zip,.tar,.tar.gz,.tgz'
})

const fileHint = computed(() => {
  if (form.value.projectType === 'jar') {
    return '支持 .jar 文件或 .zip、.tar、.tar.gz 压缩包'
  } else if (form.value.projectType === 'nodejs') {
    return '支持 .zip、.tar、.tar.gz 压缩包（包含 Node.js 项目源码）'
  } else if (form.value.projectType === 'python') {
    return '支持 .zip、.tar、.tar.gz 压缩包（包含 Python 源码和 requirements.txt）'
  } else if (form.value.projectType === 'go') {
    return '支持 .zip、.tar、.tar.gz 压缩包（包含 Go 源码和 go.mod）'
  }
  return '支持 .zip、.tar、.tar.gz 压缩包'
})

// 计算镜像名占位符
const imageNamePlaceholder = computed(() => {
  return 'myapp/demo'
})

async function loadTemplates() {
  try {
    const res = await axios.get('/api/templates')
    templates.value = res.data.items || []
    if (filteredTemplates.value.length > 0) {
      form.value.template = filteredTemplates.value[0].name
      await loadTemplateParams()  // 加载初始模板的参数
    }
  } catch (error) {
    console.error('加载模板失败:', error)
  }
}

// 加载仓库列表
async function loadRegistries() {
  try {
    const res = await axios.get('/api/registries')
    registries.value = res.data.registries || []
    console.log('📦 已加载仓库列表:', registries.value)
    
  } catch (error) {
    console.error('加载仓库列表失败:', error)
  }
}


function updateTemplates() {
  if (filteredTemplates.value.length > 0) {
    form.value.template = filteredTemplates.value[0].name
    loadTemplateParams()  // 加载新模板的参数
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

// 加载模板参数
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
    
    // 初始化默认值
    templateParams.value.forEach(param => {
      if (param.default) {
        form.value.templateParams[param.name] = param.default
      }
    })
    
    console.log('📋 模板参数:', templateParams.value)
  } catch (error) {
    console.error('加载模板参数失败:', error)
  }
}

function handleFileInputClick() {
  console.log('📂 文件选择对话框已打开，请在弹出的窗口中选择文件')
}

function handleFileChange(e) {
  form.value.file = e.target.files[0]
  if (form.value.file) {
    console.log('✅ 文件已选择:', form.value.file.name)
    // 如果是压缩包，默认勾选解压选项
    if (isArchiveFile(form.value.file.name)) {
      form.value.extractArchive = true
    }
    // 自动建议镜像名
    suggestImageName(form.value.file)
  } else {
    console.log('❌ 未选择文件')
  }
}

async function suggestImageName(file) {
  try {
    const formData = new FormData()
    formData.append('jar_file', file)
    const res = await axios.post('/api/suggest-image-name', formData)
    if (res.data.suggested_imagename) {
      form.value.imageName = res.data.suggested_imagename
    }
  } catch (error) {
    // 忽略错误
  }
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

function isArchiveFile(filename) {
  return filename.endsWith('.zip') || 
         filename.endsWith('.tar') || 
         filename.endsWith('.tar.gz') || 
         filename.endsWith('.tgz')
}

async function handleBuild() {
  if (!form.value.file) {
    alert('请选择文件')
    return
  }
  
  
  building.value = true
  const formData = new FormData()
  formData.append('app_file', form.value.file)
  formData.append('project_type', form.value.projectType)
  formData.append('template', form.value.template)
  formData.append('imagename', form.value.imageName)
  formData.append('tag', form.value.tag)
  if (form.value.push) {
    formData.append('push', 'on')
  }
  
  // 添加模板参数
  if (Object.keys(form.value.templateParams).length > 0) {
    formData.append('template_params', JSON.stringify(form.value.templateParams))
  }
  
  
  // 添加解压选项（仅压缩包时有效）
  if (form.value.file && isArchiveFile(form.value.file.name)) {
    formData.append('extract_archive', form.value.extractArchive ? 'on' : 'off')
  }
  
  try {
    const res = await axios.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    // 获取 build_id 或 task_id（兼容新旧版本）
    const buildId = res.data.build_id || res.data.task_id
    if (buildId) {
      console.log('✅ 构建任务已启动, task_id:', buildId)
      
      // 先打开日志窗口
      window.dispatchEvent(new CustomEvent('show-build-log'))
      
      // 等待一小段时间确保日志窗口已挂载，然后开始轮询
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
    alert(error.response?.data?.error || '构建失败')
    building.value = false
  }
}

// 轮询构建日志
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
      
      console.log('📥 收到日志响应 (前100字符):', logs.substring(0, 100))
      
      // 分割日志行，过滤空行
      const logLines = logs
        .split('\n')
        .map(line => line.trim())  // 去除两端空格
        .filter(line => line.length > 0)  // 过滤空行
      
      console.log(`📊 日志总行数: ${logLines.length}, 上次处理: ${lastLogLength}`)
      
      // 只添加新的日志行
      if (logLines.length > lastLogLength) {
        for (let i = lastLogLength; i < logLines.length; i++) {
          console.log(`➕ 添加日志 [${i}]:`, logLines[i])
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
      // 不要因为单次失败就停止轮询
      if (error.response?.status === 404) {
        clearInterval(pollInterval)
        building.value = false
        window.dispatchEvent(new CustomEvent('add-log', {
          detail: { text: '❌ 任务不存在' }
        }))
      }
    }
  }
  
  // 先发送一条初始日志
  window.dispatchEvent(new CustomEvent('add-log', {
    detail: { text: `🚀 开始构建，Task ID: ${buildId}` }
  }))
  
  // 立即执行一次
  await poll()
  
  // 每 1秒 轮询一次，最多300次（5分钟）
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
.build-panel {
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
</style>


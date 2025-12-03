<template>
  <div class="build-panel">
    <form @submit.prevent="handleBuild">
      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label">
            项目类型 <span class="text-danger">*</span>
          </label>
          <select 
            v-model="form.projectType" 
            class="form-select" 
            @change="updateTemplates"
            required
          >
            <option v-for="type in projectTypes" :key="type.value" :value="type.value">
              {{ type.label }}
            </option>
          </select>
          <div class="form-text small">
            <i class="fas fa-info-circle"></i> 选择项目类型（需要先在模板管理中添加对应类型的模板）
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">模板</label>
          <select v-model="form.template" class="form-select" @change="loadTemplateParams">
            <option v-for="tpl in filteredTemplates" :key="tpl.name" :value="tpl.name">
              {{ tpl.name }}
            </option>
          </select>
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
        </div>
        <div v-else class="form-text small">
          <i class="fas fa-info-circle"></i> {{ fileHint }}
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
            placeholder="myapp/demo" 
            required
          />
        </div>
        <div class="col-md-3">
          <label class="form-label">标签</label>
          <input v-model="form.tag" type="text" class="form-control" />
        </div>
        <div class="col-md-3 d-flex align-items-end">
          <div class="form-check">
            <input 
              v-model="form.push" 
              type="checkbox" 
              class="form-check-input" 
              id="pushImage"
            />
            <label class="form-check-label small" for="pushImage">推送</label>
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
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const form = ref({
  projectType: 'jar',
  template: '',
  file: null,
  imageName: 'myapp/demo',
  tag: 'latest',
  push: false,
  templateParams: {}  // 模板参数
})

const templates = ref([])
const building = ref(false)
const templateParams = ref([])  // 当前模板的参数列表

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
  
  const result = []
  types.forEach(type => {
    result.push({
      value: type,
      label: labelMap[type] || `${type.charAt(0).toUpperCase()}${type.slice(1)} 应用`
    })
  })
  
  // 如果没有模板，返回默认选项
  if (result.length === 0) {
    return [
      { value: 'jar', label: 'Java 应用（JAR）' },
      { value: 'nodejs', label: 'Node.js 应用' },
      { value: 'python', label: 'Python 应用' },
      { value: 'go', label: 'Go 应用' }
    ]
  }
  
  return result
})

const filteredTemplates = computed(() => {
  return templates.value.filter(t => t.project_type === form.value.projectType)
})

const fileAccept = computed(() => {
  return form.value.projectType === 'nodejs' 
    ? '.zip,.tar,.tar.gz,.tgz' 
    : '.jar,.zip,.tar,.tar.gz,.tgz'
})

const fileHint = computed(() => {
  return form.value.projectType === 'nodejs'
    ? '支持 .zip、.tar、.tar.gz 压缩包'
    : '支持 .jar 文件或 .zip、.tar、.tar.gz 压缩包'
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

function updateTemplates() {
  if (filteredTemplates.value.length > 0) {
    form.value.template = filteredTemplates.value[0].name
    loadTemplateParams()  // 加载新模板的参数
  }
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
  
  try {
    const res = await axios.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    // 获取 build_id
    const buildId = res.data.build_id
    if (buildId) {
      console.log('✅ 构建任务已启动, build_id:', buildId)
      
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
  console.log('🔄 开始轮询构建日志, build_id:', buildId)
  
  let lastLogLength = 0
  
  const poll = async () => {
    try {
      const res = await axios.get('/api/get-logs', {
        params: { build_id: buildId },
        responseType: 'text' // 确保以文本方式接收
      })
      
      console.log('📥 收到日志响应:', res.data.substring(0, 100) + '...')
      
      const logs = typeof res.data === 'string' ? res.data : String(res.data)
      const logLines = logs.split('\n').filter(line => line.trim())
      
      console.log(`📊 日志行数: ${logLines.length}, 上次: ${lastLogLength}`)
      
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
      
      // 检查是否构建完成
      const lastLine = logLines[logLines.length - 1] || ''
      const isDone = lastLine.includes('构建完成') || 
                     lastLine.includes('构建失败') || 
                     lastLine.includes('Successfully tagged') ||
                     lastLine.includes('Error') ||
                     lastLine.includes('推送完成')
      
      if (isDone) {
        clearInterval(pollInterval)
        building.value = false
        console.log('✅ 构建任务结束')
      }
    } catch (error) {
      console.error('❌ 获取日志失败:', error)
      // 不要因为单次失败就停止轮询
      if (error.response?.status === 404 || error.response?.status === 500) {
        clearInterval(pollInterval)
        building.value = false
        window.dispatchEvent(new CustomEvent('add-log', {
          detail: { text: '❌ 日志获取失败: ' + (error.response?.statusText || error.message) }
        }))
      }
    }
  }
  
  // 先发送一条初始日志
  window.dispatchEvent(new CustomEvent('add-log', {
    detail: { text: `🚀 开始构建，Build ID: ${buildId}` }
  }))
  
  // 立即执行一次
  await poll()
  
  // 每秒轮询一次，最多120秒
  let pollCount = 0
  pollInterval = setInterval(() => {
    pollCount++
    if (pollCount > 120) {
      clearInterval(pollInterval)
      building.value = false
      console.log('⏰ 构建日志轮询超时')
      window.dispatchEvent(new CustomEvent('add-log', {
        detail: { text: '⏰ 构建日志轮询超时（120秒）' }
      }))
    } else {
      poll()
    }
  }, 1000)
}

onMounted(() => {
  loadTemplates()
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
</style>


<template>
  <div class="export-panel">
    <!-- 子标签页 -->
    <ul class="nav nav-pills mb-3">
      <li class="nav-item">
        <button 
          class="nav-link" 
          :class="{ active: exportMode === 'single' }"
          @click="exportMode = 'single'"
          type="button"
        >
          <i class="fas fa-cube"></i> 单个镜像
        </button>
      </li>
      <li class="nav-item">
        <button 
          class="nav-link" 
          :class="{ active: exportMode === 'compose' }"
          @click="exportMode = 'compose'"
          type="button"
        >
          <i class="fas fa-diagram-project"></i> Compose 批量导出
        </button>
      </li>
    </ul>

    <!-- 单个镜像导出 -->
    <div v-if="exportMode === 'single'">
      <form @submit.prevent="handleExport">
        <!-- 仓库选择 -->
        <div class="row g-3 mb-3">
          <div class="col-md-12">
            <label class="form-label">
              <i class="fas fa-server"></i> 镜像仓库
            </label>
            <select v-model="form.registry" class="form-select" @change="updateImageName">
              <option v-for="reg in registries" :key="reg.name" :value="reg.name">
                {{ reg.name }} - {{ reg.registry }}
                <span v-if="reg.active"> (激活)</span>
              </option>
            </select>
            <div class="form-text small">
              <i class="fas fa-info-circle"></i> 
              选择仓库后会自动拼接镜像名，默认使用激活的仓库
            </div>
          </div>
        </div>

        <div class="row g-3 mb-3">
          <div class="col-md-6">
            <label class="form-label">
              镜像名称 <span class="text-danger">*</span>
            </label>
            <input 
              v-model="form.image" 
              type="text" 
              class="form-control" 
              :placeholder="imagePlaceholder" 
              required
              @input="handleImageNameInput"
              @paste="handleImageNamePaste"
            />
            <div class="form-text small">
              <i class="fas fa-info-circle"></i> 
              选择仓库后会自动拼接完整镜像名，您也可以手动修改
            </div>
          </div>
          <div class="col-md-3">
            <label class="form-label">标签</label>
            <input v-model="form.tag" type="text" class="form-control" />
          </div>
          <div class="col-md-3">
            <label class="form-label">压缩</label>
            <select v-model="form.compress" class="form-select">
              <option value="none">不压缩</option>
              <option value="gzip">GZIP</option>
            </select>
          </div>
        </div>

        <!-- 本地仓库选项 -->
        <div class="row g-3 mb-3">
          <div class="col-md-12">
            <div class="form-check">
              <input 
                v-model="form.useLocal" 
                class="form-check-input" 
                type="checkbox" 
                id="useLocal"
              />
              <label class="form-check-label" for="useLocal">
                <i class="fas fa-server"></i> 使用本地仓库（不执行 pull 操作）
              </label>
              <div class="form-text small">
                <i class="fas fa-info-circle"></i> 
                勾选后，将直接从本地 Docker 导出镜像，不会从远程仓库拉取
              </div>
            </div>
          </div>
        </div>

        <button type="submit" class="btn btn-warning w-100" :disabled="exporting">
          <i class="fas fa-download"></i> 
          {{ exporting ? '导出中...' : '导出镜像' }}
          <span v-if="exporting" class="spinner-border spinner-border-sm ms-2"></span>
        </button>
      </form>

      <!-- 导出状态提示 -->
      <div v-if="exporting && exportMode === 'single'" class="alert alert-info mt-3 mb-0">
        <div class="d-flex align-items-center">
          <div class="spinner-border spinner-border-sm me-2" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <div class="flex-grow-1">
            <strong>正在创建导出任务...</strong>
            <div class="small mt-1">
              镜像: <code>{{ form.image }}:{{ form.tag }}</code>
            </div>
            <div class="small text-muted mt-1">
              <i class="fas fa-info-circle"></i> 
              任务创建后，请到“任务管理”标签页查看进度和下载文件
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Compose 批量导出 -->
    <div v-if="exportMode === 'compose'">
      <ul class="nav nav-pills nav-fill mb-3">
        <li class="nav-item">
          <button 
            class="nav-link" 
            :class="{ active: inputMode === 'file' }"
            @click="inputMode = 'file'"
            type="button"
          >
            <i class="fas fa-file-upload"></i> 上传文件
          </button>
        </li>
        <li class="nav-item">
          <button 
            class="nav-link" 
            :class="{ active: inputMode === 'text' }"
            @click="inputMode = 'text'"
            type="button"
          >
            <i class="fas fa-edit"></i> 文本输入
          </button>
        </li>
      </ul>

      <div class="mb-3">
        <input 
          v-if="inputMode === 'file'"
          type="file" 
          class="form-control" 
          accept=".yml,.yaml,.YML,.YAML,.txt"
          @change="handleFileChange"
        />
        <codemirror
          v-else
          v-model="composeText" 
          :style="{ height: '400px', fontSize: '13px' }"
          :autofocus="true"
          :indent-with-tab="true"
          :tab-size="2"
          :extensions="extensions"
          placeholder="粘贴 docker-compose.yml 内容..."
        />
        <div class="form-text small">自动提取镜像列表</div>
      </div>

      <button 
        type="button" 
        class="btn btn-info w-100 mb-3" 
        @click="parseCompose"
        :disabled="parsing"
      >
        <i class="fas fa-search"></i> 
        {{ parsing ? '解析中...' : '解析镜像' }}
      </button>

      <!-- 镜像列表 -->
      <div v-if="images.length > 0" class="mt-3">
        <div class="d-flex justify-content-between align-items-center mb-2">
          <small class="text-muted">共 {{ images.length }} 个镜像</small>
          <div class="d-flex gap-2 align-items-center">
            <div class="form-check form-check-inline mb-0">
              <input 
                v-model="selectAll" 
                type="checkbox" 
                class="form-check-input" 
                id="selectAllImages"
                @change="toggleSelectAll"
              />
              <label class="form-check-label small" for="selectAllImages">全选</label>
            </div>
            <select v-model="composeCompress" class="form-select form-select-sm" style="width: auto;">
              <option value="none">tar</option>
              <option value="gzip">tar.gz</option>
            </select>
            <button 
              class="btn btn-sm btn-outline-secondary" 
              @click="downloadSelected"
              :disabled="selectedImages.length === 0 || exporting"
            >
              <i class="fas fa-download"></i> 
              {{ exporting ? '导出中...' : '下载' }}
              <span v-if="exporting" class="spinner-border spinner-border-sm ms-1"></span>
            </button>
          </div>
        </div>

        <div style="max-height: 300px; overflow-y: auto;">
          <table class="table table-sm table-striped align-middle mb-0">
            <thead class="table-light" style="position: sticky; top: 0;">
              <tr>
                <th style="width: 30px;"></th>
                <th>服务</th>
                <th>镜像:标签</th>
                <th class="text-end" style="width: 80px;">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(img, index) in images" :key="index">
                <td>
                  <input 
                    v-model="img.selected" 
                    type="checkbox" 
                    class="form-check-input"
                  />
                </td>
                <td>{{ img.service }}</td>
                <td>{{ img.image }}{{ img.tag && img.tag !== 'latest' ? ':' + img.tag : '' }}</td>
                <td class="text-end">
                  <button 
                    class="btn btn-sm btn-outline-primary py-0" 
                    style="font-size: 0.8rem;"
                    @click="downloadImage(img)"
                    :disabled="exporting"
                  >
                    <i class="fas fa-download"></i>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 导出状态提示 -->
      <div v-if="exporting && exportMode === 'compose'" class="alert alert-info mt-3 mb-0">
        <div class="d-flex align-items-center">
          <div class="spinner-border spinner-border-sm me-2" role="status">
            <span class="visually-hidden">加载中...</span>
          </div>
          <div class="flex-grow-1">
            <strong>正在创建导出任务...</strong>
            <div v-if="currentExporting" class="small mt-1">
              当前: <code>{{ currentExporting.image }}{{ currentExporting.tag && currentExporting.tag !== 'latest' ? ':' + currentExporting.tag : '' }}</code>
              <span v-if="exportProgress.total > 1">
                ({{ exportProgress.current }}/{{ exportProgress.total }})
              </span>
            </div>
            <div class="small text-muted mt-1">
              <i class="fas fa-info-circle"></i> 
              任务创建后，请到“任务管理”标签页查看进度和下载文件
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { yaml as yamlLang } from '@codemirror/lang-yaml'
import { oneDark } from '@codemirror/theme-one-dark'
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'
import { Codemirror } from 'vue-codemirror'

// 导出模式：single=单个镜像, compose=Compose批量导出
const exportMode = ref('single')

// 单个镜像导出
const form = ref({
  registry: '',  // 仓库名称
  image: '',  // 镜像名称（完整镜像名）
  tag: 'latest',
  compress: 'none',
  useLocal: false  // 是否使用本地仓库
})

const registries = ref([])
const exporting = ref(false)

// Compose 批量导出
const inputMode = ref('file')
const composeText = ref('')
const images = ref([])
const composeCompress = ref('none')
const selectAll = ref(false)
const parsing = ref(false)
const currentExporting = ref(null)  // 当前正在导出的镜像
const exportProgress = ref({ current: 0, total: 0 })  // 导出进度

// CodeMirror 扩展配置（YAML 模式）
const extensions = [
  oneDark,
  yamlLang()
]

const selectedImages = computed(() => {
  return images.value.filter(img => img.selected)
})

// 计算镜像名占位符
const imagePlaceholder = computed(() => {
  const selectedRegistry = registries.value.find(r => r.name === form.value.registry)
  if (selectedRegistry && selectedRegistry.registry_prefix) {
    const prefix = selectedRegistry.registry_prefix.trim()
    if (prefix) {
      return `${prefix}/myapp/demo`
    }
  }
  return 'myapp/demo'
})

// 加载仓库列表
async function loadRegistries() {
  try {
    const res = await axios.get('/api/registries')
    registries.value = res.data.registries || []
    
    // 设置默认仓库为激活的仓库
    const activeRegistry = registries.value.find(r => r.active)
    if (activeRegistry) {
      form.value.registry = activeRegistry.name
      updateImageName()
    } else if (registries.value.length > 0) {
      form.value.registry = registries.value[0].name
      updateImageName()
    }
  } catch (error) {
    console.error('加载仓库列表失败:', error)
  }
}

// 更新镜像名（根据仓库的 registry_prefix 自动拼接）
function updateImageName() {
  const selectedRegistry = registries.value.find(r => r.name === form.value.registry)
  if (selectedRegistry && selectedRegistry.registry_prefix) {
    const prefix = selectedRegistry.registry_prefix.trim()
    if (prefix) {
      // 如果当前镜像名为空或没有前缀，自动拼接
      if (!form.value.image || !form.value.image.startsWith(prefix)) {
        // 如果镜像名已经包含其他仓库的前缀，先移除
        let imageName = form.value.image
        registries.value.forEach(reg => {
          const regPrefix = reg.registry_prefix?.trim()
          if (regPrefix && imageName.startsWith(regPrefix + '/')) {
            imageName = imageName.substring(regPrefix.length + 1)
          }
        })
        
        // 拼接新仓库的前缀
        if (imageName) {
          form.value.image = `${prefix}/${imageName}`.replace(/\/+/g, '/')
        } else {
          form.value.image = `${prefix}/myapp/demo`
        }
      }
    } else {
      // 如果仓库没有前缀，移除当前镜像名的前缀
      if (form.value.image) {
        registries.value.forEach(reg => {
          const regPrefix = reg.registry_prefix?.trim()
          if (regPrefix && form.value.image.startsWith(regPrefix + '/')) {
            form.value.image = form.value.image.substring(regPrefix.length + 1)
          }
        })
      }
    }
  }
}

// 处理镜像名称输入，自动识别并分离标签
function handleImageNameInput(event) {
  const inputValue = event.target.value
  parseImageNameAndTag(inputValue)
}

// 处理镜像名称粘贴，自动识别并分离标签
function handleImageNamePaste(event) {
  // 等待粘贴内容写入输入框（v-model 会更新 form.value.image）
  setTimeout(() => {
    parseImageNameAndTag(form.value.image)
  }, 0)
}

// 解析镜像名称和标签
function parseImageNameAndTag(inputValue) {
  if (!inputValue || typeof inputValue !== 'string') {
    return
  }
  
  // 查找最后一个冒号（标签在最后一个冒号后面）
  // 注意：镜像名称可能包含端口号（如 registry:5000/image:tag），所以需要找到最后一个冒号
  const lastColonIndex = inputValue.lastIndexOf(':')
  
  if (lastColonIndex > 0 && lastColonIndex < inputValue.length - 1) {
    // 检查冒号后面是否有斜杠（如果有，可能是端口号，不是标签）
    const afterColon = inputValue.substring(lastColonIndex + 1)
    
    // 如果冒号后面没有斜杠，且不是纯数字（避免误判端口号），则认为是标签
    if (!afterColon.includes('/') && !/^\d+$/.test(afterColon)) {
      // 分离镜像名称和标签
      const imageName = inputValue.substring(0, lastColonIndex)
      const tag = afterColon.trim()
      
      // 更新表单
      form.value.image = imageName
      if (tag) {
        form.value.tag = tag
      }
    }
  }
}

// Compose 功能
function handleFileChange(e) {
  const file = e.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (ev) => {
      composeText.value = ev.target.result
    }
    reader.readAsText(file)
  }
}

function toggleSelectAll() {
  images.value.forEach(img => {
    img.selected = selectAll.value
  })
}

async function parseCompose() {
  if (!composeText.value.trim()) {
    alert('请上传文件或输入 docker-compose.yml 内容')
    return
  }
  
  parsing.value = true
  try {
    const res = await axios.post('/api/parse-compose', {
      content: composeText.value
    })
    
    images.value = (res.data.images || []).map(img => ({
      ...img,
      selected: false
    }))
    
    alert(`解析成功，共 ${images.value.length} 个镜像`)
  } catch (error) {
    alert(error.response?.data?.error || '解析失败')
  } finally {
    parsing.value = false
  }
}

async function downloadImage(img) {
  if (exporting.value) {
    alert('正在提交任务，请稍候...')
    return
  }
  
  exporting.value = true
  currentExporting.value = img
  
  try {
    const payload = {
      image: img.image,
      tag: img.tag || 'latest',
      compress: composeCompress.value
    }
    
    const res = await axios.post('/api/export-image', payload)
    
    alert(`导出任务已创建！
镜像: ${img.image}${img.tag && img.tag !== 'latest' ? ':' + img.tag : ''}
任务ID: ${res.data.task_id}

请到“任务管理”标签页查看进度和下载文件。`)
  } catch (error) {
    alert(error.response?.data?.error || error.message || '创建导出任务失败')
  } finally {
    exporting.value = false
    currentExporting.value = null
  }
}

async function downloadSelected() {
  if (exporting.value) {
    alert('正在提交任务，请稍候...')
    return
  }
  
  const selected = selectedImages.value
  if (selected.length === 0) {
    alert('请至少选择一个镜像')
    return
  }
  
  exporting.value = true
  exportProgress.value = { current: 0, total: selected.length }
  
  // 滚动到状态提示区域
  setTimeout(() => {
    const alertElement = document.querySelector('.export-panel .alert-info')
    if (alertElement) {
      alertElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, 100)
  
  try {
    const taskIds = []
    for (let i = 0; i < selected.length; i++) {
      const img = selected[i]
      currentExporting.value = img
      exportProgress.value.current = i + 1
      
      try {
        const payload = {
          image: img.image,
          tag: img.tag || 'latest',
          compress: composeCompress.value
        }
        
        const res = await axios.post('/api/export-image', payload)
        taskIds.push(res.data.task_id)
      } catch (error) {
        const errorMsg = error.response?.data?.error || error.message || '创建任务失败'
        console.error(`镜像 ${img.image} 创建任务失败:`, errorMsg)
        // 继续创建下一个任务
      }
    }
    
    if (taskIds.length > 0) {
      alert(`已创建 ${taskIds.length} 个导出任务！\n\n请到“任务管理”标签页查看进度和下载文件。`)
    } else {
      alert('所有任务创建失败，请检查网络连接')
    }
  } finally {
    exporting.value = false
    currentExporting.value = null
    exportProgress.value = { current: 0, total: 0 }
  }
}

onMounted(() => {
  loadRegistries()
})

async function handleExport() {
  if (!form.value.image) {
    alert('请输入镜像名称')
    return
  }
  
  if (exporting.value) {
    alert('正在提交任务，请稍候...')
    return
  }
  
  exporting.value = true
  
  // 滚动到状态提示区域
  setTimeout(() => {
    const alertElement = document.querySelector('.export-panel .alert-info')
    if (alertElement) {
      alertElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, 100)
  
  try {
    const payload = {
      image: form.value.image.trim(),
      tag: form.value.tag,
      compress: form.value.compress,
      use_local: form.value.useLocal
    }
    
    // 如果选择了仓库，传递仓库名称
    if (form.value.registry) {
      payload.registry = form.value.registry
    }
    
    const res = await axios.post('/api/export-image', payload)
    
    alert(`导出任务已创建！\n任务ID: ${res.data.task_id}\n\n请到“任务管理”标签页查看进度和下载文件。`)
    
    // 清空表单（可选）
    // form.value.image = ''
    // form.value.tag = 'latest'
  } catch (error) {
    alert(error.response?.data?.error || error.message || '创建导出任务失败')
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.export-panel {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>


<template>
  <div class="export-panel">
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

      <button type="submit" class="btn btn-warning w-100" :disabled="exporting">
        <i class="fas fa-download"></i> 
        {{ exporting ? '导出中...' : '导出镜像' }}
        <span v-if="exporting" class="spinner-border spinner-border-sm ms-2"></span>
      </button>
    </form>

    <!-- 导出状态提示 -->
    <div v-if="exporting" class="alert alert-info mt-3 mb-0">
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
            任务创建后，请到"导出任务"标签页查看进度和下载文件
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'

const form = ref({
  registry: '',  // 仓库名称
  image: '',  // 镜像名称（完整镜像名）
  tag: 'latest',
  compress: 'none'
})

const registries = ref([])
const exporting = ref(false)

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
      compress: form.value.compress
    }
    
    // 如果选择了仓库，传递仓库名称
    if (form.value.registry) {
      payload.registry = form.value.registry
    }
    
    const res = await axios.post('/api/export-image', payload)
    
    alert(`导出任务已创建！\n任务ID: ${res.data.task_id}\n\n请到"导出任务"标签页查看进度和下载文件。`)
    
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


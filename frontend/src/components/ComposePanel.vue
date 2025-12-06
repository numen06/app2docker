<template>
  <div class="compose-panel">
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
          <select v-model="compress" class="form-select form-select-sm" style="width: auto;">
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
    <div v-if="exporting" class="alert alert-info mt-3 mb-0">
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
            任务创建后，请到"导出任务"标签页查看进度和下载文件
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import axios from 'axios'
import yaml from 'js-yaml'
import { Codemirror } from 'vue-codemirror'
import { oneDark } from '@codemirror/theme-one-dark'
import { yaml as yamlLang } from '@codemirror/lang-yaml'

const inputMode = ref('file')
const composeText = ref('')
const composeFile = ref(null)
const images = ref([])
const compress = ref('none')
const selectAll = ref(false)
const parsing = ref(false)
const exporting = ref(false)
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
      compress: compress.value
    }
    
    const res = await axios.post('/api/export-image', payload)
    
    alert(`导出任务已创建！\n镜像: ${img.image}${img.tag && img.tag !== 'latest' ? ':' + img.tag : ''}\n任务ID: ${res.data.task_id}\n\n请到"导出任务"标签页查看进度和下载文件。`)
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
    const alertElement = document.querySelector('.compose-panel .alert-info')
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
          compress: compress.value
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
      alert(`已创建 ${taskIds.length} 个导出任务！\n\n请到"导出任务"标签页查看进度和下载文件。`)
    } else {
      alert('所有任务创建失败，请检查网络连接')
    }
  } finally {
    exporting.value = false
    currentExporting.value = null
    exportProgress.value = { current: 0, total: 0 }
  }
}
</script>

<style scoped>
.compose-panel {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.font-monospace {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
</style>


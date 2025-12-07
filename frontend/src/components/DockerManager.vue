<template>
  <div class="docker-manager">
    <!-- Docker 服务信息区域 -->
    <div class="card mb-3">
      <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center py-2">
        <div>
          <i class="fas fa-server"></i>
          <strong class="ms-1">Docker 服务信息</strong>
          <small v-if="infoLastSync" class="ms-3 opacity-75">
            <i class="fas fa-clock"></i> {{ formatTime(infoLastSync) }}
          </small>
        </div>
        <button class="btn btn-sm btn-light" @click="refreshDockerInfo(true)" :disabled="loadingInfo" title="刷新">
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingInfo }"></i>
        </button>
      </div>
      <div class="card-body py-2">
        <div v-if="loadingInfo" class="text-center py-3">
          <div class="spinner-border spinner-border-sm text-primary"></div>
          <span class="ms-2">正在获取 Docker 信息...</span>
        </div>
        
        <div v-else-if="dockerInfo" class="row g-2">
          <!-- 第一行：基本信息 -->
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">连接状态</div>
              <div class="info-value">
                <span class="badge" :class="dockerInfo.connected ? 'bg-success' : 'bg-danger'">
                  {{ dockerInfo.connected ? '已连接' : '未连接' }}
                </span>
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">Docker 版本</div>
              <div class="info-value">{{ dockerInfo.version || '-' }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">API 版本</div>
              <div class="info-value">{{ dockerInfo.api_version || '-' }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">构建器类型</div>
              <div class="info-value">
                <span class="badge" :class="getBuilderBadgeClass(dockerInfo.builder_type)">
                  {{ getBuilderLabel(dockerInfo.builder_type) }}
                </span>
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2" v-if="dockerInfo.remote_host">
            <div class="info-item">
              <div class="info-label">远程主机</div>
              <div class="info-value small">{{ dockerInfo.remote_host }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">操作系统</div>
              <div class="info-value">{{ dockerInfo.os_type || '-' }} {{ dockerInfo.arch || '' }}</div>
            </div>
          </div>
          
          <!-- 第二行：资源统计 -->
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">镜像数量</div>
              <div class="info-value">{{ dockerInfo.images_count || 0 }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">容器(运行/总)</div>
              <div class="info-value">
                <span class="text-success">{{ dockerInfo.containers_running || 0 }}</span> / {{ dockerInfo.containers_total || 0 }}
              </div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">存储驱动</div>
              <div class="info-value">{{ dockerInfo.storage_driver || '-' }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">数据根目录</div>
              <div class="info-value small text-truncate" :title="dockerInfo.docker_root">{{ dockerInfo.docker_root || '-' }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">镜像占用</div>
              <div class="info-value">{{ formatBytes(dockerInfo.images_size) }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">容器占用</div>
              <div class="info-value">{{ formatBytes(dockerInfo.containers_size) }}</div>
            </div>
          </div>
          
          <!-- 第三行：系统信息 -->
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">CPU 核心</div>
              <div class="info-value">{{ dockerInfo.ncpu || '-' }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">总内存</div>
              <div class="info-value">{{ formatBytes(dockerInfo.mem_total) }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">内核版本</div>
              <div class="info-value small">{{ dockerInfo.kernel_version || '-' }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">运行时</div>
              <div class="info-value">{{ dockerInfo.runtime || '-' }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">数据卷数量</div>
              <div class="info-value">{{ dockerInfo.volumes_count || 0 }}</div>
            </div>
          </div>
          <div class="col-6 col-md-2">
            <div class="info-item">
              <div class="info-label">网络数量</div>
              <div class="info-value">{{ dockerInfo.networks_count || 0 }}</div>
            </div>
          </div>
        </div>
        
        <div v-else class="alert alert-warning mb-0 py-2">
          <i class="fas fa-exclamation-triangle"></i>
          无法获取 Docker 信息，请检查服务状态
        </div>
      </div>
    </div>

    <!-- 容器和镜像 Tab 管理 -->
    <div class="card">
      <div class="card-header py-0 px-0">
        <ul class="nav nav-tabs" role="tablist">
          <li class="nav-item" role="presentation">
            <button 
              class="nav-link px-4 py-2" 
              :class="{ active: activeTab === 'containers' }" 
              @click="activeTab = 'containers'"
              type="button"
            >
              <i class="fas fa-cubes me-1"></i>容器管理
              <span v-if="containerTotal > 0" class="badge bg-info ms-1">{{ containerTotal }}</span>
            </button>
          </li>
          <li class="nav-item" role="presentation">
            <button 
              class="nav-link px-4 py-2" 
              :class="{ active: activeTab === 'images' }" 
              @click="activeTab = 'images'"
              type="button"
            >
              <i class="fas fa-images me-1"></i>镜像管理
              <span v-if="imageTotal > 0" class="badge bg-secondary ms-1">{{ imageTotal }}</span>
            </button>
          </li>
        </ul>
      </div>
      
      <!-- 容器 Tab -->
      <div v-show="activeTab === 'containers'" class="card-body p-0">
        <!-- 搜索和操作栏 -->
        <div class="d-flex justify-content-between align-items-center p-2 border-bottom bg-light">
          <div class="d-flex gap-2 align-items-center flex-grow-1">
            <div class="input-group input-group-sm" style="max-width: 300px;">
              <span class="input-group-text"><i class="fas fa-search"></i></span>
              <input type="text" class="form-control" v-model="containerSearch" placeholder="搜索容器名称/镜像..." @input="filterContainers">
            </div>
            <select class="form-select form-select-sm" style="width: auto;" v-model="containerStatusFilter" @change="filterContainers">
              <option value="">全部状态</option>
              <option value="running">运行中</option>
              <option value="exited">已停止</option>
              <option value="paused">已暂停</option>
            </select>
            <small v-if="containerLastSync" class="text-muted">
              <i class="fas fa-clock"></i> {{ formatTime(containerLastSync) }}
            </small>
          </div>
          <div class="d-flex gap-1">
            <button class="btn btn-sm btn-warning" @click="pruneContainers" :disabled="loadingContainers" title="清理已停止的容器">
              <i class="fas fa-broom"></i> 清理
            </button>
            <button class="btn btn-sm btn-primary" @click="loadContainers(true)" :disabled="loadingContainers">
              <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingContainers }"></i>
            </button>
          </div>
        </div>
        
        <div v-if="loadingContainers" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-info"></div>
          <span class="ms-2">加载容器列表...</span>
        </div>
        
        <div v-else-if="filteredContainers.length === 0" class="text-center text-muted py-4">
          <i class="fas fa-cube"></i> {{ containerSearch || containerStatusFilter ? '未找到匹配的容器' : '暂无容器' }}
        </div>
        
        <div v-else class="table-responsive">
          <table class="table table-hover table-sm mb-0">
            <thead class="table-light">
              <tr>
                <th>容器名称</th>
                <th>镜像</th>
                <th>状态</th>
                <th>端口</th>
                <th>创建时间</th>
                <th class="text-end">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in paginatedContainers" :key="c.id">
                <td><code class="small">{{ c.name }}</code></td>
                <td class="small text-muted text-truncate" style="max-width: 200px;" :title="c.image">{{ c.image }}</td>
                <td><span class="badge" :class="getStatusBadge(c.state)">{{ c.status }}</span></td>
                <td class="small">{{ c.ports || '-' }}</td>
                <td class="small">{{ formatTime(c.created) }}</td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button v-if="c.state !== 'running'" class="btn btn-outline-success" @click="startContainer(c)" title="启动"><i class="fas fa-play"></i></button>
                    <button v-if="c.state === 'running'" class="btn btn-outline-warning" @click="stopContainer(c, false)" title="停止"><i class="fas fa-stop"></i></button>
                    <button v-if="c.state === 'running'" class="btn btn-outline-danger" @click="stopContainer(c, true)" title="强制停止"><i class="fas fa-power-off"></i></button>
                    <button v-if="c.state === 'running'" class="btn btn-outline-info" @click="restartContainer(c)" title="重启"><i class="fas fa-redo"></i></button>
                    <button class="btn btn-outline-danger" @click="removeContainer(c)" title="删除"><i class="fas fa-trash"></i></button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <!-- 容器分页 -->
        <div v-if="filteredContainers.length > containerPageSize" class="d-flex justify-content-between align-items-center p-2 border-top">
          <small class="text-muted">显示 {{ (containerPage-1)*containerPageSize+1 }}-{{ Math.min(containerPage*containerPageSize, filteredContainers.length) }} / 共 {{ filteredContainers.length }} 个</small>
          <nav>
            <ul class="pagination pagination-sm mb-0">
              <li class="page-item" :class="{ disabled: containerPage <= 1 }">
                <button class="page-link" @click="containerPage--">上一页</button>
              </li>
              <li class="page-item disabled"><span class="page-link">{{ containerPage }}</span></li>
              <li class="page-item" :class="{ disabled: containerPage * containerPageSize >= filteredContainers.length }">
                <button class="page-link" @click="containerPage++">下一页</button>
              </li>
            </ul>
          </nav>
        </div>
      </div>
      
      <!-- 镜像 Tab -->
      <div v-show="activeTab === 'images'" class="card-body p-0">
        <!-- 搜索和操作栏 -->
        <div class="d-flex justify-content-between align-items-center p-2 border-bottom bg-light">
          <div class="d-flex gap-2 align-items-center flex-grow-1">
            <div class="input-group input-group-sm" style="max-width: 300px;">
              <span class="input-group-text"><i class="fas fa-search"></i></span>
              <input type="text" class="form-control" v-model="imageSearch" placeholder="搜索镜像名称/标签..." @input="filterImages">
            </div>
            <select class="form-select form-select-sm" style="width: auto;" v-model="imageTagFilter" @change="filterImages">
              <option value="">全部标签</option>
              <option value="latest">latest</option>
              <option value="none">&lt;none&gt;</option>
            </select>
            <small v-if="imageLastSync" class="text-muted">
              <i class="fas fa-clock"></i> {{ formatTime(imageLastSync) }}
            </small>
          </div>
          <div class="d-flex gap-1">
            <button class="btn btn-sm btn-warning" @click="pruneImages" :disabled="loadingImages" title="清理未使用镜像">
              <i class="fas fa-broom"></i> 清理
            </button>
            <button class="btn btn-sm btn-primary" @click="loadImages(true)" :disabled="loadingImages">
              <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingImages }"></i>
            </button>
          </div>
        </div>
        
        <div v-if="loadingImages" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-secondary"></div>
          <span class="ms-2">加载镜像列表...</span>
        </div>
        
        <div v-else-if="filteredImages.length === 0" class="text-center text-muted py-4">
          <i class="fas fa-box-open"></i> {{ imageSearch || imageTagFilter ? '未找到匹配的镜像' : '暂无镜像' }}
        </div>
        
        <div v-else class="table-responsive">
          <table class="table table-hover table-sm mb-0">
            <thead class="table-light">
              <tr>
                <th>镜像名称</th>
                <th>标签</th>
                <th>镜像ID</th>
                <th>大小</th>
                <th>创建时间</th>
                <th class="text-end">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="img in paginatedImages" :key="img.id + img.tag">
                <td><code class="small text-primary">{{ img.repository || '&lt;none&gt;' }}</code></td>
                <td><span class="badge bg-info">{{ img.tag || '&lt;none&gt;' }}</span></td>
                <td><small class="text-muted font-monospace">{{ img.id.substring(7, 19) }}</small></td>
                <td class="small">{{ formatBytes(img.size) }}</td>
                <td class="small">{{ formatTime(img.created) }}</td>
                <td class="text-end">
                  <button class="btn btn-sm btn-outline-danger" @click="deleteImage(img)" title="删除镜像"><i class="fas fa-trash"></i></button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <!-- 镜像分页 -->
        <div v-if="filteredImages.length > imagePageSize" class="d-flex justify-content-between align-items-center p-2 border-top">
          <small class="text-muted">显示 {{ (imagePage-1)*imagePageSize+1 }}-{{ Math.min(imagePage*imagePageSize, filteredImages.length) }} / 共 {{ filteredImages.length }} 个</small>
          <nav>
            <ul class="pagination pagination-sm mb-0">
              <li class="page-item" :class="{ disabled: imagePage <= 1 }">
                <button class="page-link" @click="imagePage--">上一页</button>
              </li>
              <li class="page-item disabled"><span class="page-link">{{ imagePage }}</span></li>
              <li class="page-item" :class="{ disabled: imagePage * imagePageSize >= filteredImages.length }">
                <button class="page-link" @click="imagePage++">下一页</button>
              </li>
            </ul>
          </nav>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'

// === Tab 控制 ===
const activeTab = ref('containers')

// === Docker 服务信息 ===
const dockerInfo = ref(null)
const loadingInfo = ref(false)
const infoLastSync = ref(null)
const infoCacheTimeout = 5 * 60 * 1000

async function refreshDockerInfo(force = false) {
  if (!force && infoLastSync.value && (Date.now() - new Date(infoLastSync.value).getTime() < infoCacheTimeout)) return
  loadingInfo.value = true
  try {
    const res = await axios.get('/api/docker/info')
    dockerInfo.value = res.data
    infoLastSync.value = new Date().toISOString()
  } catch (error) {
    console.error('获取 Docker 信息失败:', error)
    dockerInfo.value = null
  } finally {
    loadingInfo.value = false
  }
}

// === 容器管理 ===
const allContainers = ref([])
const containers = ref([])
const loadingContainers = ref(false)
const containerLastSync = ref(null)
const containerPage = ref(1)
const containerPageSize = 10
const containerTotal = ref(0)
const containerCacheTimeout = 5 * 60 * 1000
const containerSearch = ref('')
const containerStatusFilter = ref('')

const filteredContainers = computed(() => {
  let result = allContainers.value
  if (containerSearch.value) {
    const search = containerSearch.value.toLowerCase()
    result = result.filter(c => c.name.toLowerCase().includes(search) || c.image.toLowerCase().includes(search))
  }
  if (containerStatusFilter.value) {
    result = result.filter(c => c.state === containerStatusFilter.value)
  }
  return result
})

const paginatedContainers = computed(() => {
  const start = (containerPage.value - 1) * containerPageSize
  return filteredContainers.value.slice(start, start + containerPageSize)
})

function filterContainers() {
  containerPage.value = 1
}

async function loadContainers(force = false) {
  if (!force && containerLastSync.value && (Date.now() - new Date(containerLastSync.value).getTime() < containerCacheTimeout)) return
  loadingContainers.value = true
  try {
    const res = await axios.get('/api/docker/containers', { params: { page: 1, page_size: 1000 } })
    allContainers.value = res.data.containers || []
    containerTotal.value = res.data.total || allContainers.value.length
    containerLastSync.value = new Date().toISOString()
  } catch (error) {
    console.error('加载容器列表失败:', error)
    allContainers.value = []
  } finally {
    loadingContainers.value = false
  }
}

async function startContainer(c) {
  try { await axios.post(`/api/docker/containers/${c.id}/start`); loadContainers(true) } 
  catch (e) { alert(e.response?.data?.detail || '启动容器失败') }
}

async function stopContainer(c, force = false) {
  try { 
    await axios.post(`/api/docker/containers/${c.id}/stop`, null, { params: { force } })
    loadContainers(true) 
  } catch (e) { alert(e.response?.data?.detail || '停止容器失败') }
}

async function restartContainer(c) {
  try { await axios.post(`/api/docker/containers/${c.id}/restart`); loadContainers(true) } 
  catch (e) { alert(e.response?.data?.detail || '重启容器失败') }
}

async function removeContainer(c) {
  if (!confirm(`确定要删除容器 ${c.name} 吗？`)) return
  try { await axios.delete(`/api/docker/containers/${c.id}`); loadContainers(true) } 
  catch (e) { alert(e.response?.data?.detail || '删除容器失败') }
}

async function pruneContainers() {
  if (!confirm('确定要清理所有已停止的容器吗？')) return
  try {
    const res = await axios.post('/api/docker/containers/prune')
    alert(`已清理 ${res.data.deleted || 0} 个容器`)
    loadContainers(true)
    refreshDockerInfo(true)
  } catch (e) { alert(e.response?.data?.detail || '清理容器失败') }
}

// === 镜像管理 ===
const allImages = ref([])
const images = ref([])
const loadingImages = ref(false)
const imageLastSync = ref(null)
const imagePage = ref(1)
const imagePageSize = 10
const imageTotal = ref(0)
const imageCacheTimeout = 5 * 60 * 1000
const imageSearch = ref('')
const imageTagFilter = ref('')

const filteredImages = computed(() => {
  let result = allImages.value
  if (imageSearch.value) {
    const search = imageSearch.value.toLowerCase()
    result = result.filter(img => (img.repository || '').toLowerCase().includes(search) || (img.tag || '').toLowerCase().includes(search))
  }
  if (imageTagFilter.value === 'latest') {
    result = result.filter(img => img.tag === 'latest')
  } else if (imageTagFilter.value === 'none') {
    result = result.filter(img => img.tag === '<none>' || !img.tag)
  }
  return result
})

const paginatedImages = computed(() => {
  const start = (imagePage.value - 1) * imagePageSize
  return filteredImages.value.slice(start, start + imagePageSize)
})

function filterImages() {
  imagePage.value = 1
}

async function loadImages(force = false) {
  if (!force && imageLastSync.value && (Date.now() - new Date(imageLastSync.value).getTime() < imageCacheTimeout)) return
  loadingImages.value = true
  try {
    const res = await axios.get('/api/docker/images', { params: { page: 1, page_size: 1000 } })
    allImages.value = res.data.images || []
    imageTotal.value = res.data.total || allImages.value.length
    imageLastSync.value = new Date().toISOString()
  } catch (error) {
    console.error('加载镜像列表失败:', error)
    allImages.value = []
  } finally {
    loadingImages.value = false
  }
}

async function deleteImage(img) {
  const imgName = img.repository && img.tag ? `${img.repository}:${img.tag}` : img.id
  if (!confirm(`确定要删除镜像 ${imgName} 吗？`)) return
  try {
    await axios.delete('/api/docker/images', { data: { image_id: img.id } })
    loadImages(true)
    refreshDockerInfo(true)
  } catch (e) { alert(e.response?.data?.detail || '删除镜像失败') }
}

async function pruneImages() {
  if (!confirm('确定要清理所有未使用的镜像吗？这将释放磁盘空间。')) return
  try {
    const res = await axios.post('/api/docker/images/prune')
    alert(`已清理，释放空间: ${formatBytes(res.data.space_reclaimed || 0)}`)
    loadImages(true)
    refreshDockerInfo(true)
  } catch (e) { alert(e.response?.data?.detail || '清理镜像失败') }
}

// === 工具函数 ===
function formatBytes(bytes) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let idx = 0, value = bytes
  while (value >= 1024 && idx < units.length - 1) { value /= 1024; idx++ }
  return `${value.toFixed(1)} ${units[idx]}`
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  try {
    return new Date(timeStr).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return timeStr }
}

function getBuilderBadgeClass(type) {
  return { 'local': 'bg-success', 'remote': 'bg-primary', 'mock': 'bg-warning' }[type] || 'bg-secondary'
}

function getBuilderLabel(type) {
  return { 'local': '本地', 'remote': '远程', 'mock': '模拟' }[type] || '未知'
}

function getStatusBadge(state) {
  return { 'running': 'bg-success', 'exited': 'bg-secondary', 'paused': 'bg-warning', 'created': 'bg-info' }[state] || 'bg-secondary'
}

onMounted(() => {
  refreshDockerInfo()
  loadContainers()
  loadImages()
})
</script>

<style scoped>
.docker-manager { animation: fadeIn 0.3s; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.info-item { padding: 0.4rem 0.5rem; background: #f8f9fa; border-radius: 0.25rem; height: 100%; }
.info-label { font-size: 0.7rem; color: #6c757d; margin-bottom: 0.1rem; }
.info-value { font-size: 0.85rem; color: #212529; font-weight: 600; }

/* Tab 样式修复 */
.card-header.py-0 { background: #fff; border-bottom: 1px solid #dee2e6; }
.nav-tabs { border-bottom: none; margin-bottom: -1px; }
.nav-tabs .nav-link {
  color: #6c757d;
  border: 1px solid transparent;
  border-top-left-radius: 0.375rem;
  border-top-right-radius: 0.375rem;
  margin-bottom: 0;
  background: transparent;
  transition: color 0.15s, border-color 0.15s;
}
.nav-tabs .nav-link:hover {
  color: #0d6efd;
  border-color: #e9ecef #e9ecef #dee2e6;
}
.nav-tabs .nav-link.active {
  color: #0d6efd;
  background-color: #fff;
  border-color: #dee2e6 #dee2e6 #fff;
  font-weight: 600;
}

.table th { font-weight: 600; font-size: 0.8rem; white-space: nowrap; }
.table td { vertical-align: middle; font-size: 0.85rem; }
.table-sm td, .table-sm th { padding: 0.35rem 0.5rem; }
</style>

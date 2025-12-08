<template>
  <div class="template-panel">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h6 class="mb-0">
        <i class="fas fa-layer-group"></i> 模板列表
      </h6>
      <button class="btn btn-primary btn-sm" @click="openEditor(null, true)">
        <i class="fas fa-plus-circle"></i> 新增模板
      </button>
    </div>

    <!-- 模板列表表格 -->
    <div class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th>模板名称</th>
            <th>项目类型</th>
            <th>文件大小</th>
            <th>更新时间</th>
            <th class="text-end">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="text-center py-4">
              <div class="spinner-border spinner-border-sm me-2"></div>
              加载中...
            </td>
          </tr>
          <tr v-else-if="paginatedTemplates.length === 0">
            <td colspan="5" class="text-center text-muted py-4">
              <i class="fas fa-file-code fa-2x mb-2 d-block"></i>
              暂无模板，请点击"新增模板"创建
            </td>
          </tr>
          <tr v-for="tpl in paginatedTemplates" :key="tpl.name">
            <td>
              <strong>{{ tpl.name }}</strong>
              <i v-if="tpl.type === 'builtin'" class="fas fa-lock text-muted ms-1" title="内置模板"></i>
            </td>
            <td>
              <span 
                class="badge" 
                :class="getProjectTypeBadgeClass(tpl.project_type)"
              >
                {{ getProjectTypeLabel(tpl.project_type) }}
              </span>
            </td>
            <td>{{ formatBytes(tpl.size) }}</td>
            <td>{{ formatTime(tpl.updated_at) }}</td>
            <td class="text-end">
              <div class="btn-group btn-group-sm">
                <button 
                  class="btn btn-outline-info" 
                  @click="parseTemplate(tpl)"
                  title="解析"
                  :disabled="parsing === tpl.name"
                >
                  <i v-if="parsing === tpl.name" class="fas fa-spinner fa-spin"></i>
                  <i v-else class="fas fa-search"></i>
                </button>
                <button 
                  class="btn btn-outline-secondary" 
                  @click="previewTemplate(tpl)"
                  title="预览"
                >
                  <i class="fas fa-eye"></i>
                </button>
                <button 
                  class="btn btn-outline-primary" 
                  @click="openEditor(tpl, false)"
                  title="编辑"
                >
                  <i class="fas fa-pen"></i>
                </button>
                <button 
                  class="btn btn-outline-danger" 
                  @click="deleteTemplate(tpl)"
                  title="删除"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页控件 -->
    <div v-if="totalPages > 1" class="d-flex justify-content-between align-items-center mt-3">
      <div class="text-muted small">
        显示第 {{ (currentPage - 1) * pageSize + 1 }} - {{ Math.min(currentPage * pageSize, templates.length) }} 条，共 {{ templates.length }} 条
      </div>
      <nav>
        <ul class="pagination pagination-sm mb-0">
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <button class="page-link" @click="changePage(1)" :disabled="currentPage === 1">
              <i class="fas fa-angle-double-left"></i>
            </button>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <button class="page-link" @click="changePage(currentPage - 1)" :disabled="currentPage === 1">
              <i class="fas fa-angle-left"></i>
            </button>
          </li>
          <li 
            v-for="page in visiblePages" 
            :key="page" 
            class="page-item" 
            :class="{ active: currentPage === page }"
          >
            <button class="page-link" @click="changePage(page)">{{ page }}</button>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <button class="page-link" @click="changePage(currentPage + 1)" :disabled="currentPage === totalPages">
              <i class="fas fa-angle-right"></i>
            </button>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === totalPages }">
            <button class="page-link" @click="changePage(totalPages)" :disabled="currentPage === totalPages">
              <i class="fas fa-angle-double-right"></i>
            </button>
          </li>
        </ul>
      </nav>
    </div>

    <!-- 模板编辑器模态框 -->
    <TemplateEditorModal 
      v-model="showEditor"
      :template="currentTemplate"
      :is-new="isNew"
      @saved="handleSaved"
    />

    <!-- 模板预览模态框 -->
    <TemplatePreviewModal 
      v-model="showPreview"
      :template="currentTemplate"
    />

    <!-- 模板解析信息模态框 -->
    <div 
      v-if="showParseModal" 
      class="modal fade show d-block" 
      tabindex="-1"
      @click.self="closeParseModal"
      style="z-index: 1055;"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header bg-info text-white">
            <h5 class="modal-title">
              <i class="fas fa-search"></i> 模板解析信息
              <span v-if="parseTemplateData" class="ms-2">{{ parseTemplateData.name }}</span>
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="closeParseModal"></button>
          </div>
          <div class="modal-body">
            <div v-if="parsing" class="text-center py-4">
              <div class="spinner-border spinner-border-sm me-2"></div>
              正在解析模板...
            </div>
            <div v-else-if="parseError" class="alert alert-danger">
              <i class="fas fa-exclamation-triangle"></i> {{ parseError }}
            </div>
            <div v-else-if="parseInfo">
              <!-- 模板参数 -->
              <div class="mb-4">
                <h6 class="mb-3">
                  <i class="fas fa-sliders-h text-primary"></i> 模板参数
                  <span class="badge bg-primary ms-2">{{ parseInfo.params?.length || 0 }} 个</span>
                </h6>
                <div v-if="parseInfo.params && parseInfo.params.length > 0" class="table-responsive">
                  <table class="table table-sm table-bordered table-hover">
                    <thead class="table-light">
                      <tr>
                        <th style="width: 200px;">参数名称</th>
                        <th>描述</th>
                        <th style="width: 100px;">默认值</th>
                        <th style="width: 80px;">必填</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="param in parseInfo.params" :key="param.name">
                        <td><code>{{ param.name }}</code></td>
                        <td>{{ param.description || '-' }}</td>
                        <td>
                          <span v-if="param.default" class="badge bg-secondary">{{ param.default }}</span>
                          <span v-else class="text-muted">-</span>
                        </td>
                        <td>
                          <span v-if="param.required" class="badge bg-danger">是</span>
                          <span v-else class="badge bg-success">否</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="alert alert-info mb-0">
                  <i class="fas fa-info-circle"></i> 该模板没有可配置参数
                </div>
              </div>

              <!-- 服务阶段（多阶段构建） -->
              <div>
                <h6 class="mb-3">
                  <i class="fas fa-server text-info"></i> 服务阶段（多阶段构建）
                  <span class="badge bg-info ms-2">{{ parseInfo.services?.length || 0 }} 个</span>
                </h6>
                <div v-if="parseInfo.services && parseInfo.services.length > 0" class="table-responsive">
                  <table class="table table-sm table-bordered table-hover">
                    <thead class="table-light">
                      <tr>
                        <th style="width: 250px;">服务名称</th>
                        <th style="width: 100px;">端口</th>
                        <th style="width: 100px;">用户</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="service in parseInfo.services" :key="service.name">
                        <td><code>{{ service.name }}</code></td>
                        <td>
                          <span v-if="service.port" class="badge bg-secondary">{{ service.port }}</span>
                          <span v-else class="text-muted">-</span>
                        </td>
                        <td>
                          <span v-if="service.user" class="badge bg-secondary">{{ service.user }}</span>
                          <span v-else class="text-muted">-</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="alert alert-info mb-0">
                  <i class="fas fa-info-circle"></i> 该模板不是多阶段构建，或没有服务阶段
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="closeParseModal">
              <i class="fas fa-times"></i> 关闭
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showParseModal" class="modal-backdrop fade show"></div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'
import TemplateEditorModal from './TemplateEditorModal.vue'
import TemplatePreviewModal from './TemplatePreviewModal.vue'

const templates = ref([])
const loading = ref(false)
const showEditor = ref(false)
const showPreview = ref(false)
const currentTemplate = ref(null)
const isNew = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)

// 解析相关状态
const showParseModal = ref(false)
const parsing = ref(null)  // 正在解析的模板名称
const parseInfo = ref(null)  // 解析结果
const parseError = ref('')
const parseTemplateData = ref(null)  // 当前解析的模板数据

// 总页数
const totalPages = computed(() => Math.ceil(templates.value.length / pageSize.value))

// 当前页的模板列表
const paginatedTemplates = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return templates.value.slice(start, end)
})

// 可见的页码列表
const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  const pages = []
  
  if (total <= 7) {
    // 总页数小于7，显示所有页码
    for (let i = 1; i <= total; i++) {
      pages.push(i)
    }
  } else {
    // 总页数大于7，智能显示
    if (current <= 4) {
      // 前部：1 2 3 4 5 ... 最后页
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 3) {
      // 后部：1 ... 倍数第5页 倍数第4页 倍数第3页 倍数第2页 最后页
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      // 中间：1 ... current-1 current current+1 ... 最后页
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    }
  }
  
  return pages.filter(p => p !== '...' || pages.indexOf(p) === pages.lastIndexOf(p))
})

// 切换页码
function changePage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return
  currentPage.value = page
}

async function loadTemplates() {
  loading.value = true
  try {
    const res = await axios.get('/api/templates')
    templates.value = res.data.items || []
  } catch (error) {
    console.error('加载模板失败:', error)
    alert('加载模板列表失败')
  } finally {
    loading.value = false
  }
}

function openEditor(tpl, isNewTemplate) {
  currentTemplate.value = tpl
  isNew.value = isNewTemplate
  showEditor.value = true
}

function previewTemplate(tpl) {
  currentTemplate.value = tpl
  showPreview.value = true
}

async function parseTemplate(tpl) {
  parseTemplateData.value = tpl
  showParseModal.value = true
  parsing.value = tpl.name
  parseInfo.value = null
  parseError.value = ''
  
  try {
    const res = await axios.get('/api/template-params', {
      params: {
        template: tpl.name,
        project_type: tpl.project_type
      }
    })
    
    parseInfo.value = {
      params: res.data.params || [],
      services: res.data.services || []
    }
  } catch (error) {
    console.error('解析模板失败:', error)
    parseError.value = error.response?.data?.detail || '解析模板失败'
  } finally {
    parsing.value = null
  }
}

function closeParseModal() {
  showParseModal.value = false
  parseInfo.value = null
  parseError.value = ''
  parseTemplateData.value = null
}

async function deleteTemplate(tpl) {
  const msg = tpl.type === 'builtin'
    ? `此为内置模板，删除后仍可通过系统恢复。\n确认删除用户覆盖的 ${tpl.name} 吗？`
    : `确认删除模板 ${tpl.name} 吗？该操作不可恢复。`
  
  if (!confirm(msg)) return
  
  try {
    await axios.delete('/api/templates', {
      data: { name: tpl.name }
    })
    
    alert('模板已删除')
    await loadTemplates()
  } catch (error) {
    alert(error.response?.data?.error || '删除失败')
  }
}

function handleSaved() {
  loadTemplates()
}

function formatBytes(bytes) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let idx = 0
  let value = bytes
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024
    idx++
  }
  return `${value.toFixed(value < 10 && idx > 0 ? 1 : 0)} ${units[idx]}`
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  try {
    return new Date(timeStr).toLocaleString('zh-CN')
  } catch {
    return timeStr
  }
}

function getProjectTypeBadgeClass(type) {
  const colorMap = {
    'jar': 'bg-primary',
    'nodejs': 'bg-success',
    'python': 'bg-info',
    'go': 'bg-warning',
    'rust': 'bg-danger'
  }
  return colorMap[type] || 'bg-secondary'
}

function getProjectTypeLabel(type) {
  const labelMap = {
    'jar': 'JAR',
    'nodejs': 'Node.js',
    'python': 'Python',
    'go': 'Go',
    'rust': 'Rust'
  }
  return labelMap[type] || type.toUpperCase()
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.template-panel {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.table th {
  font-weight: 600;
  font-size: 0.9rem;
}

/* 分页样式优化 */
.pagination .page-link {
  min-width: 38px;
  text-align: center;
}

.pagination .page-item.disabled .page-link {
  cursor: not-allowed;
}

.pagination .page-item.active .page-link {
  font-weight: 600;
}
</style>

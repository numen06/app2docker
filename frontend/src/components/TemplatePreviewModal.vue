<template>
  <div 
    class="modal fade" 
    :class="{ show: modelValue, 'd-block': modelValue }"
    tabindex="-1"
    @click.self="close"
  >
    <div class="modal-dialog modal-xl">
      <div class="modal-content">
        <div class="modal-header bg-info text-white">
          <h5 class="modal-title">
            <i class="fas fa-eye"></i> 模板预览
            <span v-if="template?.name" class="ms-2">{{ template.name }}</span>
            <span v-if="template?.type === 'builtin'" class="badge bg-warning ms-2">
              <i class="fas fa-lock"></i> 内置
            </span>
          </h5>
          <button type="button" class="btn-close btn-close-white" @click="close"></button>
        </div>
        
        <div class="modal-body">
          <div v-if="loading" class="text-center py-4">
            <div class="spinner-border spinner-border-sm me-2"></div>
            加载中...
          </div>
          
          <div v-else>
            <!-- 元数据 -->
            <div class="row mb-3">
              <div class="col-md-3">
                <label class="form-label fw-bold">模板名称</label>
                <div class="form-control-plaintext">{{ templateData?.name || '-' }}</div>
              </div>
              <div class="col-md-3">
                <label class="form-label fw-bold">项目类型</label>
                <div class="form-control-plaintext">
                  <span 
                    class="badge" 
                    :class="template?.project_type === 'jar' ? 'bg-primary' : 'bg-success'"
                  >
                    {{ template?.project_type === 'nodejs' ? 'Node.js' : 'JAR' }}
                  </span>
                </div>
              </div>
              <div class="col-md-3">
                <label class="form-label fw-bold">文件大小</label>
                <div class="form-control-plaintext">{{ formatSize(template?.size) }}</div>
              </div>
              <div class="col-md-3">
                <label class="form-label fw-bold">更新时间</label>
                <div class="form-control-plaintext">{{ formatDate(template?.updated_at) }}</div>
              </div>
            </div>

            <!-- 模板信息：参数和服务阶段 -->
            <div class="row mb-3" v-if="templateInfo">
              <div class="col-md-6" v-if="templateInfo.params && templateInfo.params.length > 0">
                <div class="card border-primary">
                  <div class="card-header bg-primary bg-opacity-10 py-2">
                    <small class="fw-bold">
                      <i class="fas fa-sliders-h"></i> 模板参数 ({{ templateInfo.params.length }})
                    </small>
                  </div>
                  <div class="card-body p-2">
                    <div class="small">
                      <div v-for="param in templateInfo.params" :key="param.name" class="mb-1">
                        <code>{{ param.name }}</code>
                        <span v-if="param.default" class="text-muted"> (默认: {{ param.default }})</span>
                        <span v-if="param.required" class="badge bg-danger badge-sm ms-1">必填</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-md-6" v-if="templateInfo.services && templateInfo.services.length > 0">
                <div class="card border-info">
                  <div class="card-header bg-info bg-opacity-10 py-2">
                    <small class="fw-bold">
                      <i class="fas fa-server"></i> 服务阶段 ({{ templateInfo.services.length }})
                    </small>
                  </div>
                  <div class="card-body p-2">
                    <div class="table-responsive">
                      <table class="table table-sm table-bordered mb-0">
                        <thead>
                          <tr>
                            <th>服务名称</th>
                            <th>端口</th>
                            <th>用户</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="service in templateInfo.services" :key="service.name">
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
                  </div>
                </div>
              </div>
            </div>

            <!-- CodeMirror 只读预览 -->
            <div class="mb-2">
              <label class="form-label fw-bold">
                <i class="fas fa-file-code"></i> 模板内容
              </label>
            </div>
            <codemirror
              v-model="content"
              :style="{ height: '500px', fontSize: '13px' }"
              :disabled="true"
              :extensions="extensions"
            />
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="close">
            <i class="fas fa-times"></i> 关闭
          </button>
        </div>
      </div>
    </div>
  </div>
  
  <div v-if="modelValue" class="modal-backdrop fade show"></div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { Codemirror } from 'vue-codemirror'
import { oneDark } from '@codemirror/theme-one-dark'
import { StreamLanguage } from '@codemirror/language'
import { shell } from '@codemirror/legacy-modes/mode/shell'

const props = defineProps({
  modelValue: Boolean,
  template: Object
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)
const content = ref('')
const templateData = ref(null)
const templateInfo = ref(null)  // 模板信息（参数和服务阶段）

// CodeMirror 扩展配置（只读模式）
const extensions = [
  oneDark,
  StreamLanguage.define(shell)
]

watch(() => props.modelValue, async (show) => {
  if (show && props.template) {
    loading.value = true
    templateInfo.value = null
    
    try {
      // 加载模板内容
      const res = await axios.get(`/api/templates?name=${encodeURIComponent(props.template.name)}`)
      templateData.value = res.data
      content.value = res.data.content || ''
      
      // 加载模板参数和服务阶段信息
      try {
        const infoRes = await axios.get('/api/template-params', {
          params: {
            template: props.template.name,
            project_type: props.template.project_type
          }
        })
        templateInfo.value = {
          params: infoRes.data.params || [],
          services: infoRes.data.services || []
        }
      } catch (infoError) {
        console.error('加载模板信息失败:', infoError)
        // 不影响主流程，只记录错误
        templateInfo.value = {
          params: [],
          services: []
        }
      }
    } catch (error) {
      console.error('加载模板内容失败:', error)
      alert('加载模板内容失败')
      close()
    } finally {
      loading.value = false
    }
  }
})

function formatSize(bytes) {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

function close() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.modal.show {
  display: block !important;
}

.modal-backdrop.show {
  opacity: 0.5;
}
</style>

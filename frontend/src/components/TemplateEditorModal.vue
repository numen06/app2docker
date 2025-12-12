<template>
  <div 
    class="modal fade" 
    :class="{ show: modelValue, 'd-block': modelValue }"
    tabindex="-1"
  >
    <div class="modal-dialog modal-xl">
      <div class="modal-content">
        <div class="modal-header bg-primary text-white">
          <h5 class="modal-title">
            <i class="fas fa-code"></i>
            {{ isNew ? '新增模板' : '编辑模板' }}
            <span v-if="isBuiltin" class="badge bg-warning ms-2">
              <i class="fas fa-lock"></i> 内置
            </span>
          </h5>
          <button type="button" class="btn-close btn-close-white" @click="close"></button>
        </div>
        
        <div class="modal-body">
          <!-- 元数据 -->
          <div class="row mb-3">
            <div class="col-md-6">
              <label class="form-label">模板名称 <span class="text-danger">*</span></label>
              <input 
                v-model="form.name" 
                type="text" 
                class="form-control"
                :disabled="isBuiltin"
                placeholder="例如: my-custom-template"
              />
              <div v-if="isBuiltin" class="form-text text-warning">
                <i class="fas fa-info-circle"></i> 内置模板不可重命名，保存后将在用户目录创建覆盖
              </div>
            </div>
            <div class="col-md-6">
              <label class="form-label">项目类型 <span class="text-danger">*</span></label>
              <select 
                v-model="form.projectType" 
                class="form-select"
                :disabled="!canChangeProjectType"
                @change="validateProjectType"
              >
                <option value="jar">Java 应用（JAR）</option>
                <option value="nodejs">Node.js 应用</option>
                <option value="python">Python 应用</option>
                <option value="go">Go 应用</option>
                <option value="web">静态网站</option>
              </select>
              <div v-if="!canChangeProjectType" class="form-text text-warning">
                <i class="fas fa-lock"></i> 内置模板的项目类型不可修改
              </div>
              <div v-else-if="!isNew && projectTypeChanged" class="form-text text-info">
                <i class="fas fa-info-circle"></i> 修改项目类型后，模板将移动到新目录
              </div>
              <div v-else class="form-text">
                <i class="fas fa-lightbulb"></i> 请从下拉列表中选择项目类型
              </div>
            </div>
          </div>

          <!-- CodeMirror 编辑器 -->
          <div class="mb-3">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <label class="form-label mb-0">
                模板内容 <span class="text-danger">*</span>
              </label>
              <div class="btn-group btn-group-sm">
                <button 
                  type="button" 
                  class="btn btn-outline-secondary btn-sm"
                  @click="$refs.fileInput.click()"
                >
                  <i class="fas fa-upload"></i> 从文件加载
                </button>
              </div>
            </div>
            <input 
              ref="fileInput"
              type="file" 
              class="d-none"
              accept=".dockerfile,.Dockerfile,.txt"
              @change="handleFileUpload"
            />
            <codemirror
              v-model="form.content"
              :style="{ height: '500px', fontSize: '13px' }"
              :autofocus="true"
              :indent-with-tab="false"
              :tab-size="4"
              :extensions="extensions"
            />
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-outline-secondary" @click="close">
            <i class="fas fa-times"></i> 取消
          </button>
          <button type="button" class="btn btn-primary" @click="save" :disabled="saving">
            <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="fas fa-save"></i>
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
  
  <div v-if="modelValue" class="modal-backdrop fade show"></div>
</template>

<script setup>
import { StreamLanguage } from '@codemirror/language'
import { shell } from '@codemirror/legacy-modes/mode/shell'
import { oneDark } from '@codemirror/theme-one-dark'
import axios from 'axios'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Codemirror } from 'vue-codemirror'

const props = defineProps({
  modelValue: Boolean,
  template: Object,
  isNew: Boolean
})

const emit = defineEmits(['update:modelValue', 'saved'])

const form = ref({
  name: '',
  projectType: 'jar',
  content: ''
})

const saving = ref(false)
const originalName = ref('')
const fileInput = ref(null)

// CodeMirror 扩展配置
const extensions = [
  oneDark,
  StreamLanguage.define(shell)  // 使用 shell 模式近似 Dockerfile
]

const isBuiltin = computed(() => {
  return props.template?.type === 'builtin'
})

// 是否可以修改项目类型：新增模板或编辑用户自定义模板时可以
const canChangeProjectType = computed(() => {
  return props.isNew || !isBuiltin.value
})

// 项目类型是否已修改
const projectTypeChanged = computed(() => {
  if (props.isNew || !props.template) return false
  return form.value.projectType !== props.template.project_type
})

watch(() => props.modelValue, async (show) => {
  if (show) {
    if (props.isNew) {
      // 新建模板
      form.value = {
        name: '',
        projectType: 'jar',
        content: '# 新建 Dockerfile 模板\nFROM \n\nCOPY . /app\nWORKDIR /app\n\nEXPOSE 8080\n\nCMD []'
      }
      originalName.value = ''
    } else if (props.template) {
      // 编辑现有模板
      try {
        const res = await axios.get(`/api/templates?name=${encodeURIComponent(props.template.name)}`)
        form.value = {
          name: res.data.name,
          projectType: props.template.project_type || 'jar',
          content: res.data.content || ''
        }
        originalName.value = res.data.name
      } catch (error) {
        alert('加载模板内容失败')
        close()
      }
    }
  }
})


function validateProjectType() {
  // 清理项目类型输入：只保留字母、数字、下划线、连字符
  form.value.projectType = form.value.projectType
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '')
}

function handleFileUpload(e) {
  const file = e.target.files[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (ev) => {
      form.value.content = ev.target.result
      // 如果是新建且未填写名称，从文件名提取
      if (props.isNew && !form.value.name) {
        const baseName = file.name
          .replace(/\.Dockerfile$/i, '')
          .replace(/\.[^/.]+$/, '')
          .replace(/[^a-zA-Z0-9_-]/g, '-')
        form.value.name = baseName
      }
    }
    reader.readAsText(file)
  }
}

async function save() {
  if (!form.value.name.trim()) {
    alert('模板名称不能为空')
    return
  }
  if (!form.value.content.trim()) {
    alert('模板内容不能为空')
    return
  }
  if (!form.value.projectType.trim()) {
    alert('项目类型不能为空')
    return
  }
  
  // 验证项目类型格式
  const projectTypePattern = /^[a-z0-9_-]+$/
  if (!projectTypePattern.test(form.value.projectType)) {
    alert('项目类型只能包含小写字母、数字、下划线和连字符')
    return
  }
  
  // 如果修改了项目类型，需要确认
  if (projectTypeChanged.value) {
    const confirmMsg = `您正在将模板的项目类型从 "${props.template.project_type}" 修改为 "${form.value.projectType}"。\n\n` +
                       `模板将从 data/templates/${props.template.project_type}/ 移动到 data/templates/${form.value.projectType}/\n\n` +
                       `确认要继续吗？`
    if (!confirm(confirmMsg)) {
      return
    }
  }
  
  saving.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      content: form.value.content,
      project_type: form.value.projectType
    }
    
    if (!props.isNew) {
      payload.original_name = originalName.value
      // 始终传递旧的项目类型，以便后端能够准确找到模板
      payload.old_project_type = props.template.project_type || form.value.projectType
    }
    
    const method = props.isNew ? 'post' : 'put'
    const res = await axios[method]('/api/templates', payload)
    
    const successMsg = projectTypeChanged.value 
      ? `模板已保存并移动到新的项目类型目录`
      : res.data.message || '模板保存成功'
    alert(successMsg)
    emit('saved')
    close()
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.response?.data?.error || error.message || '保存失败'
    alert(`保存失败: ${errorMsg}`)
    console.error('保存模板失败:', error)
  } finally {
    saving.value = false
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

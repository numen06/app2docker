<template>
  <div class="build-config-editor">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h5 class="mb-0">
        <i class="fas fa-edit"></i> 编辑构建配置
      </h5>
      <div class="btn-group btn-group-sm">
        <button 
          type="button"
          class="btn btn-outline-info"
          @click="showJsonModal = true"
        >
          <i class="fas fa-code"></i> 查看JSON
        </button>
        <button 
          type="button"
          class="btn btn-primary"
          @click="saveConfig"
          :disabled="saving"
        >
          <i class="fas fa-save"></i> {{ saving ? '保存中...' : '保存配置' }}
        </button>
        <button 
          type="button"
          class="btn btn-secondary"
          @click="cancel"
        >
          <i class="fas fa-times"></i> 取消
        </button>
      </div>
    </div>

    <div class="card">
      <div class="card-body">
        <!-- Git配置 -->
        <div class="mb-4">
          <h6 class="border-bottom pb-2 mb-3">
            <i class="fas fa-code-branch text-primary"></i> Git 配置
          </h6>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">Git 仓库地址 <span class="text-danger">*</span></label>
              <input 
                v-model="formData.git_url" 
                type="text" 
                class="form-control form-control-sm" 
                required
                placeholder="https://github.com/user/repo.git"
              >
            </div>
            <div class="col-md-6">
              <label class="form-label">分支名称</label>
              <div class="input-group">
                <select 
                  v-model="formData.branch" 
                  class="form-select form-select-sm"
                  :disabled="loadingBranches"
                >
                  <option value="">-- 选择分支（留空使用默认分支） --</option>
                  <option v-for="branch in branches" :key="branch" :value="branch">
                    {{ branch }}
                  </option>
                </select>
                <button 
                  class="btn btn-outline-secondary btn-sm" 
                  type="button"
                  @click="loadBranches"
                  :disabled="loadingBranches || !formData.git_url"
                  title="自动加载分支列表"
                >
                  <i v-if="loadingBranches" class="fas fa-spinner fa-spin"></i>
                  <i v-else class="fas fa-sync-alt"></i>
                </button>
              </div>
              <small class="text-muted">
                <span v-if="loadingBranches">正在加载分支列表...</span>
                <span v-else-if="branches.length > 0">已加载 {{ branches.length }} 个分支</span>
                <span v-else>留空则使用默认分支，点击刷新按钮加载分支列表</span>
              </small>
            </div>
            <div class="col-md-6">
              <label class="form-label">Git 数据源</label>
              <select 
                v-model="formData.source_id" 
                class="form-select form-select-sm"
                @change="onSourceSelected"
              >
                <option value="">-- 选择数据源或手动输入 --</option>
                <option v-for="source in gitSources" :key="source.source_id" :value="source.source_id">
                  {{ source.name }} ({{ formatGitUrl(source.git_url) }})
                </option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label">项目类型 <span class="text-danger">*</span></label>
              <select v-model="formData.project_type" class="form-select form-select-sm">
                <option value="jar">Java 应用（JAR）</option>
                <option value="nodejs">Node.js 应用</option>
                <option value="python">Python 应用</option>
                <option value="go">Go 应用</option>
                <option value="web">静态网站</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Dockerfile配置 -->
        <div class="mb-4">
          <h6 class="border-bottom pb-2 mb-3">
            <i class="fas fa-file-code text-primary"></i> Dockerfile 配置
          </h6>
          <div class="row g-3">
            <div class="col-12">
              <label class="form-label">Dockerfile 来源</label>
              <div class="btn-group w-100 mb-2" role="group">
                <input 
                  type="radio" 
                  class="btn-check" 
                  id="use-project-dockerfile" 
                  :value="true"
                  v-model="formData.use_project_dockerfile"
                  @change="onDockerfileSourceChange"
                >
                <label class="btn btn-outline-primary" for="use-project-dockerfile">
                  <i class="fas fa-file-code"></i> 项目Dockerfile
                </label>
                
                <input 
                  type="radio" 
                  class="btn-check" 
                  id="use-template" 
                  :value="false"
                  v-model="formData.use_project_dockerfile"
                  @change="onDockerfileSourceChange"
                >
                <label class="btn btn-outline-primary" for="use-template">
                  <i class="fas fa-layer-group"></i> 使用模板
                </label>
              </div>
            </div>
            <div v-if="formData.use_project_dockerfile" class="col-md-6">
              <label class="form-label">Dockerfile 文件名</label>
              <input 
                v-model="formData.dockerfile_name" 
                type="text" 
                class="form-control form-control-sm"
                placeholder="Dockerfile"
              >
            </div>
            <div v-else class="col-md-6">
              <label class="form-label">模板名称</label>
              <select v-model="formData.template" class="form-select form-select-sm" @change="onTemplateChange">
                <option value="">-- 请选择模板 --</option>
                <option v-for="t in filteredTemplates" :key="t.name" :value="t.name">
                  {{ t.name }}
                </option>
              </select>
            </div>
            <div v-if="!formData.use_project_dockerfile && templateParams.length > 0" class="col-12">
              <label class="form-label">模板参数</label>
              <div class="table-responsive">
                <table class="table table-sm table-bordered">
                  <thead>
                    <tr>
                      <th>参数名</th>
                      <th>值</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="param in templateParams" :key="param.name">
                      <td>{{ param.name }} <span v-if="param.required" class="text-danger">*</span></td>
                      <td>
                        <input 
                          v-if="param.type === 'string'"
                          v-model="formData.template_params[param.name]"
                          type="text"
                          class="form-control form-control-sm"
                          :placeholder="param.default || ''"
                        >
                        <select 
                          v-else-if="param.type === 'select'"
                          v-model="formData.template_params[param.name]"
                          class="form-select form-select-sm"
                        >
                          <option value="">-- 请选择 --</option>
                          <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
                        </select>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- 镜像配置 -->
        <div class="mb-4">
          <h6 class="border-bottom pb-2 mb-3">
            <i class="fab fa-docker text-primary"></i> 镜像配置
          </h6>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">镜像名称 <span class="text-danger">*</span></label>
              <input 
                v-model="formData.image_name" 
                type="text" 
                class="form-control form-control-sm" 
                required
                placeholder="myapp/demo"
              >
            </div>
            <div class="col-md-6">
              <label class="form-label">镜像标签</label>
              <input 
                v-model="formData.tag" 
                type="text" 
                class="form-control form-control-sm"
                placeholder="latest"
              >
            </div>
            <div class="col-md-6">
              <label class="form-label">推送模式</label>
              <select v-model="formData.push_mode" class="form-select form-select-sm" @change="onPushModeChange">
                <option value="single">单服务推送</option>
                <option value="multi">多服务推送</option>
              </select>
            </div>
            <div class="col-md-6">
              <div class="form-check mt-4">
                <input 
                  class="form-check-input" 
                  type="checkbox" 
                  id="should_push"
                  v-model="formData.should_push"
                >
                <label class="form-check-label" for="should_push">
                  构建完成后推送到仓库
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 服务配置（多服务模式） -->
        <div v-if="formData.push_mode === 'multi' && services.length > 0" class="mb-4">
          <h6 class="border-bottom pb-2 mb-3">
            <i class="fas fa-layer-group text-primary"></i> 服务配置
          </h6>
          <div class="mb-3">
            <label class="form-label">选择服务</label>
            <div class="form-check" v-for="service in services" :key="service.name">
              <input 
                class="form-check-input" 
                type="checkbox" 
                :id="`service-${service.name}`"
                :value="service.name"
                v-model="formData.selected_services"
              >
              <label class="form-check-label" :for="`service-${service.name}`">
                {{ service.name }}
              </label>
            </div>
          </div>
          <div v-if="formData.selected_services.length > 0" class="table-responsive">
            <table class="table table-sm table-bordered">
              <thead>
                <tr>
                  <th>服务名</th>
                  <th>推送</th>
                  <th>镜像名</th>
                  <th>标签</th>
                  <th>仓库</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="serviceName in formData.selected_services" :key="serviceName">
                  <td>{{ serviceName }}</td>
                  <td>
                    <input 
                      type="checkbox" 
                      v-model="formData.service_push_config[serviceName].push"
                      class="form-check-input"
                    >
                  </td>
                  <td>
                    <input 
                      type="text" 
                      v-model="formData.service_push_config[serviceName].imageName"
                      class="form-control form-control-sm"
                      :placeholder="getServiceDefaultImageName(serviceName)"
                    >
                  </td>
                  <td>
                    <input 
                      type="text" 
                      v-model="formData.service_push_config[serviceName].tag"
                      class="form-control form-control-sm"
                      :placeholder="formData.tag || 'latest'"
                    >
                  </td>
                  <td>
                    <input 
                      type="text" 
                      v-model="formData.service_push_config[serviceName].registry"
                      class="form-control form-control-sm"
                      placeholder="可选"
                    >
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 单服务推送模式 -->
        <div v-if="formData.push_mode === 'single'" class="mb-4">
          <h6 class="border-bottom pb-2 mb-3">
            <i class="fas fa-cube text-primary"></i> 单服务配置
          </h6>
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label">选择服务</label>
              <select v-model="formData.selected_service" class="form-select form-select-sm">
                <option value="">-- 请选择服务 --</option>
                <option v-for="service in services" :key="service.name" :value="service.name">
                  {{ service.name }}
                </option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label">完整镜像名</label>
              <input 
                v-model="formData.custom_image_name" 
                type="text" 
                class="form-control form-control-sm"
                :placeholder="formData.selected_service ? `${formData.image_name}/${formData.selected_service}` : ''"
              >
            </div>
          </div>
        </div>

        <!-- 资源包配置 -->
        <div class="mb-4">
          <h6 class="border-bottom pb-2 mb-3">
            <i class="fas fa-archive text-primary"></i> 资源包配置
          </h6>
          <div v-if="packages.length === 0" class="text-muted">
            暂无资源包，请先创建资源包
          </div>
          <div v-else>
            <div class="form-check mb-2">
              <input 
                class="form-check-input" 
                type="checkbox" 
                id="select-all-packages"
                :checked="formData.resource_package_ids.length === packages.length"
                @change="toggleAllPackages"
              >
              <label class="form-check-label" for="select-all-packages">
                全选
              </label>
            </div>
            <div class="table-responsive">
              <table class="table table-sm table-bordered">
                <thead>
                  <tr>
                    <th width="50">选择</th>
                    <th>资源包名称</th>
                    <th>目标路径</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="pkg in packages" :key="pkg.package_id">
                    <td>
                      <input 
                        type="checkbox" 
                        :value="pkg.package_id"
                        v-model="formData.resource_package_ids"
                        class="form-check-input"
                      >
                    </td>
                    <td>{{ pkg.name }}</td>
                    <td>
                      <input 
                        type="text" 
                        v-model="formData.resource_package_paths[pkg.package_id]"
                        class="form-control form-control-sm"
                        :placeholder="pkg.name"
                      >
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- JSON模态框 -->
    <div v-if="showJsonModal" class="modal fade show" style="display: block; z-index: 1055;" tabindex="-1">
      <div class="modal-dialog modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">
              <i class="fas fa-code"></i> 构建配置JSON
            </h5>
            <button type="button" class="btn-close" @click="showJsonModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="d-flex justify-content-end mb-2">
              <button 
                type="button"
                class="btn btn-sm btn-outline-primary"
                @click="copyJson"
              >
                <i class="fas fa-copy"></i> 复制JSON
              </button>
            </div>
            <codemirror
              v-model="configJsonText"
              :style="{ height: '500px', fontSize: '13px' }"
              :disabled="true"
              :extensions="jsonEditorExtensions"
            />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary btn-sm" @click="showJsonModal = false">关闭</button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showJsonModal" class="modal-backdrop fade show" style="z-index: 1050;"></div>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { oneDark } from '@codemirror/theme-one-dark'
import { StreamLanguage } from '@codemirror/language'
import { javascript } from '@codemirror/legacy-modes/mode/javascript'

const props = defineProps({
  initialConfig: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['save', 'cancel'])

const saving = ref(false)
const showJsonModal = ref(false)
const configJsonText = ref('')  // JSON文本内容（用于CodeMirror）

// CodeMirror 扩展配置（JSON模式，使用JavaScript模式）
const jsonEditorExtensions = [
  StreamLanguage.define(javascript),
  oneDark
]
const gitSources = ref([])
const templates = ref([])
const templateParams = ref([])
const services = ref([])
const packages = ref([])
const loadingServices = ref(false)

const formData = ref({
  git_url: '',
  branch: '',
  source_id: '',
  project_type: 'jar',
  template: '',
  use_project_dockerfile: true,
  dockerfile_name: 'Dockerfile',
  template_params: {},
  image_name: '',
  tag: 'latest',
  push_mode: 'multi',
  should_push: false,
  selected_services: [],
  selected_service: '',
  custom_image_name: '',
  service_push_config: {},
  service_template_params: {},
  resource_package_ids: [],
  resource_package_paths: {}
})

// 初始化表单数据
function initFormData() {
  if (props.initialConfig && Object.keys(props.initialConfig).length > 0) {
    const config = props.initialConfig
    formData.value = {
      git_url: config.git_url || '',
      branch: config.branch || '',
      source_id: config.source_id || '',
      project_type: config.project_type || 'jar',
      template: config.template || '',
      use_project_dockerfile: config.use_project_dockerfile !== false,
      dockerfile_name: config.dockerfile_name || 'Dockerfile',
      template_params: config.template_params || {},
      image_name: config.image_name || '',
      tag: config.tag || 'latest',
      push_mode: config.push_mode || 'multi',
      should_push: config.should_push || false,
      selected_services: config.selected_services || [],
      selected_service: config.selected_services && config.selected_services.length === 1 ? config.selected_services[0] : '',
      custom_image_name: config.image_name || '',
      service_push_config: config.service_push_config || {},
      service_template_params: config.service_template_params || {},
      resource_package_ids: config.resource_package_ids || [],
      resource_package_paths: {}
    }
    
    // 如果有资源包配置，填充路径
    if (config.resource_package_configs && Array.isArray(config.resource_package_configs)) {
      config.resource_package_configs.forEach(pkgConfig => {
        formData.value.resource_package_paths[pkgConfig.package_id] = pkgConfig.target_path || pkgConfig.target_dir || ''
      })
    }
  }
}

// 过滤模板
const filteredTemplates = computed(() => {
  return templates.value.filter(t => t.project_type === formData.value.project_type)
})

// 构建配置JSON
const configJson = computed(() => {
  const config = {
    git_url: formData.value.git_url || '',
    image_name: formData.value.push_mode === 'single' && formData.value.custom_image_name
      ? formData.value.custom_image_name
      : formData.value.image_name,
    tag: formData.value.tag || 'latest',
    branch: formData.value.branch || undefined,
    project_type: formData.value.project_type || 'jar',
    template: formData.value.use_project_dockerfile ? undefined : (formData.value.template || undefined),
    template_params: Object.keys(formData.value.template_params || {}).length > 0 
      ? formData.value.template_params 
      : undefined,
    should_push: formData.value.should_push || false,
    use_project_dockerfile: formData.value.use_project_dockerfile !== false,
    dockerfile_name: formData.value.dockerfile_name || 'Dockerfile',
    source_id: formData.value.source_id || undefined,
    selected_services: formData.value.push_mode === 'single' 
      ? (formData.value.selected_service ? [formData.value.selected_service] : undefined)
      : (formData.value.selected_services.length > 0 ? formData.value.selected_services : undefined),
    service_push_config: Object.keys(formData.value.service_push_config || {}).length > 0 
      ? formData.value.service_push_config 
      : undefined,
    service_template_params: Object.keys(formData.value.service_template_params || {}).length > 0
      ? formData.value.service_template_params
      : undefined,
    push_mode: formData.value.push_mode || 'multi',
    resource_package_ids: formData.value.resource_package_ids.length > 0
      ? formData.value.resource_package_ids
      : undefined,
    trigger_source: 'manual'
  }
  
  // 移除undefined值
  Object.keys(config).forEach(key => {
    if (config[key] === undefined) {
      delete config[key]
    }
  })
  
  return JSON.stringify(config, null, 2)
})

// 加载数据
async function loadGitSources() {
  try {
    const res = await axios.get('/api/git-sources')
    gitSources.value = res.data.sources || []
  } catch (error) {
    console.error('加载Git数据源失败:', error)
  }
}

async function loadTemplates() {
  try {
    const res = await axios.get('/api/templates')
    templates.value = res.data.templates || []
  } catch (error) {
    console.error('加载模板失败:', error)
  }
}

async function loadResourcePackages() {
  try {
    const res = await axios.get('/api/resource-packages')
    packages.value = res.data.packages || []
  } catch (error) {
    console.error('加载资源包失败:', error)
  }
}

async function loadTemplateParams() {
  if (formData.value.use_project_dockerfile || !formData.value.template) {
    templateParams.value = []
    return
  }
  
  try {
    const res = await axios.get('/api/template-params', {
      params: {
        template: formData.value.template,
        project_type: formData.value.project_type
      }
    })
    templateParams.value = res.data.params || []
    
    // 初始化模板参数默认值
    templateParams.value.forEach(param => {
      if (param.default && !formData.value.template_params[param.name]) {
        formData.value.template_params[param.name] = param.default
      }
    })
  } catch (error) {
    console.error('加载模板参数失败:', error)
  }
}

async function analyzeServices() {
  if (!formData.value.git_url && !formData.value.source_id) {
    services.value = []
    return
  }
  
  loadingServices.value = true
  try {
    if (formData.value.use_project_dockerfile) {
      // 解析项目Dockerfile服务
      const source = gitSources.value.find(s => s.source_id === formData.value.source_id)
      if (source) {
        const res = await axios.post('/api/parse-dockerfile-services', {
          git_url: source.git_url,
          branch: formData.value.branch || undefined,
          dockerfile_name: formData.value.dockerfile_name || 'Dockerfile',
          source_id: formData.value.source_id
        })
        services.value = res.data.services || []
      }
    } else {
      // 解析模板服务
      if (formData.value.template) {
        const res = await axios.get('/api/template-params', {
          params: {
            template: formData.value.template,
            project_type: formData.value.project_type
          }
        })
        services.value = res.data.services || []
      }
    }
    
    // 初始化服务推送配置
    if (services.value.length > 0) {
      services.value.forEach(service => {
        if (!formData.value.service_push_config[service.name]) {
          formData.value.service_push_config[service.name] = {
            push: false,
            imageName: getServiceDefaultImageName(service.name),
            tag: formData.value.tag || 'latest',
            registry: ''
          }
        }
      })
    }
  } catch (error) {
    console.error('分析服务失败:', error)
    services.value = []
  } finally {
    loadingServices.value = false
  }
}

function getServiceDefaultImageName(serviceName) {
  const prefix = formData.value.image_name || 'myapp/demo'
  return `${prefix}/${serviceName}`
}

function formatGitUrl(url) {
  if (!url) return ''
  return url.replace('https://', '').replace('http://', '').replace('.git', '')
}

function onSourceSelected() {
  const source = gitSources.value.find(s => s.source_id === formData.value.source_id)
  if (source) {
    formData.value.git_url = source.git_url
    if (!formData.value.branch && source.default_branch) {
      formData.value.branch = source.default_branch
    }
  }
}

function onDockerfileSourceChange() {
  if (formData.value.use_project_dockerfile) {
    formData.value.template = ''
    templateParams.value = []
    formData.value.template_params = {}
  } else {
    formData.value.dockerfile_name = 'Dockerfile'
    loadTemplateParams()
  }
  analyzeServices()
}

function onTemplateChange() {
  loadTemplateParams()
  analyzeServices()
}

function onPushModeChange() {
  if (formData.value.push_mode === 'single') {
    formData.value.selected_services = []
    formData.value.selected_service = ''
  } else {
    formData.value.selected_service = ''
    formData.value.selected_services = services.value.map(s => s.name)
  }
}

function toggleAllPackages(event) {
  if (event.target.checked) {
    formData.value.resource_package_ids = packages.value.map(p => p.package_id)
  } else {
    formData.value.resource_package_ids = []
  }
}

// 复制配置JSON（带降级方案）
async function copyJson() {
  const text = configJson.value
  
  // 优先使用 Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      alert('JSON已复制到剪贴板')
      return
    } catch (err) {
      console.warn('Clipboard API 失败，尝试降级方案:', err)
    }
  }
  
  // 降级方案：使用传统的选择文本方式
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '-9999px'
    document.body.appendChild(textarea)
    textarea.select()
    textarea.setSelectionRange(0, text.length)
    
    const successful = document.execCommand('copy')
    document.body.removeChild(textarea)
    
    if (successful) {
      alert('JSON已复制到剪贴板')
    } else {
      throw new Error('execCommand 复制失败')
    }
  } catch (err) {
    console.error('复制失败:', err)
    alert('自动复制失败，请手动选择并复制文本（已自动选中）')
    nextTick(() => {
      const editor = document.querySelector('.cm-editor')
      if (editor) {
        const range = document.createRange()
        range.selectNodeContents(editor)
        const selection = window.getSelection()
        selection.removeAllRanges()
        selection.addRange(range)
      }
    })
  }
}

function saveConfig() {
  saving.value = true
  try {
    const config = JSON.parse(configJson.value)
    emit('save', config)
  } catch (error) {
    console.error('保存配置失败:', error)
    alert('保存失败：配置格式错误')
  } finally {
    saving.value = false
  }
}

function cancel() {
  emit('cancel')
}

// 监听模态框显示，确保内容同步（只在显示时更新，避免递归）
watch(showJsonModal, (isVisible) => {
  if (isVisible) {
    nextTick(() => {
      configJsonText.value = configJson.value
    })
  }
})

// 监听变化
watch(() => formData.value.git_url, () => {
  analyzeServices()
})

watch(() => formData.value.branch, () => {
  if (formData.value.use_project_dockerfile) {
    analyzeServices()
  }
})

watch(() => formData.value.project_type, () => {
  formData.value.template = ''
  loadTemplateParams()
  analyzeServices()
})

onMounted(() => {
  initFormData()
  loadGitSources()
  loadTemplates()
  loadResourcePackages()
  
  // 如果有初始配置，加载相关数据
  if (props.initialConfig && Object.keys(props.initialConfig).length > 0) {
    if (formData.value.source_id) {
      onSourceSelected()
    }
    if (!formData.value.use_project_dockerfile && formData.value.template) {
      loadTemplateParams()
    }
    analyzeServices()
  }
})
</script>

<style scoped>
.build-config-editor {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>


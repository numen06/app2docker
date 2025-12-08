<template>
  <div class="source-build-panel">
    <form @submit.prevent="handleBuild">
      <div class="mb-3">
        <label class="form-label">
          Git 数据源 <span class="text-danger">*</span>
        </label>
        <select 
          v-model="selectedSourceId" 
          class="form-select mb-2"
          @change="onSourceSelected"
          required
        >
          <option value="">-- 请选择数据源 --</option>
          <option v-for="source in gitSources" :key="source.source_id" :value="source.source_id">
            {{ source.name }} ({{ formatGitUrl(source.git_url) }})
          </option>
        </select>
        <div class="form-text small text-muted mb-2">
          <i class="fas fa-info-circle"></i> 
          请从已保存的数据源中选择，如需添加新数据源，请前往"数据源管理"
        </div>
        <div v-if="selectedSourceId && repoVerified" class="alert alert-success alert-sm mt-2 mb-0">
          <i class="fas fa-check-circle"></i> 
          数据源已选择：{{ branchesAndTags.branches.length }} 个分支、{{ branchesAndTags.tags.length }} 个标签
        </div>
        <div v-if="selectedSourceId && !repoVerified" class="alert alert-warning alert-sm mt-2 mb-0">
          <i class="fas fa-exclamation-triangle"></i> 
          数据源信息加载中...
        </div>
      </div>

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
            :disabled="form.useProjectDockerfile"
          />
        </div>
        <select 
          v-model="form.template" 
          class="form-select" 
          @change="loadTemplateParams"
          :disabled="form.useProjectDockerfile"
        >
          <option v-for="tpl in filteredTemplates" :key="tpl.name" :value="tpl.name">
            {{ tpl.name }} ({{ getProjectTypeLabel(tpl.project_type) }}{{ tpl.type === 'builtin' ? ' · 内置' : '' }})
          </option>
        </select>
        <div class="form-text small text-muted">
          <i class="fas fa-info-circle"></i> 
          <span v-if="form.useProjectDockerfile">
            将使用项目中的 Dockerfile，模板选项已禁用
          </span>
          <span v-else>
            已按项目类型过滤，可在模板管理中维护
          </span>
        </div>
      </div>

      <!-- Dockerfile 选择选项 -->
      <div class="row g-3 mb-3">
        <div class="col-md-12">
          <div class="form-check">
            <input 
              v-model="form.useProjectDockerfile" 
              type="checkbox" 
              class="form-check-input" 
              id="useProjectDockerfile"
              @change="onUseProjectDockerfileChange"
            />
            <label class="form-check-label" for="useProjectDockerfile">
              <i class="fas fa-file-code"></i> 优先使用项目中的 Dockerfile
            </label>
          </div>
          <div class="form-text small text-muted">
            <i class="fas fa-info-circle"></i> 
            勾选后，如果项目中存在 Dockerfile，将优先使用项目中的 Dockerfile；否则使用选择的模板
          </div>
        </div>
        <div class="col-md-12" v-if="form.useProjectDockerfile">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="form-label mb-0">Dockerfile 文件名</label>
            <button 
              type="button"
              class="btn btn-sm btn-outline-info"
              @click="scanDockerfiles"
              :disabled="!repoVerified || scanningDockerfiles"
              title="扫描当前分支的 Dockerfile"
            >
              <i class="fas fa-search" :class="{ 'fa-spin': scanningDockerfiles }"></i> 
              {{ scanningDockerfiles ? '扫描中...' : '扫描' }}
            </button>
          </div>
          <select 
            v-model="form.dockerfileName" 
            class="form-select form-select-sm"
          >
            <option value="Dockerfile">Dockerfile（默认）</option>
            <option v-for="dockerfile in availableDockerfiles" :key="dockerfile" :value="dockerfile">
              {{ dockerfile }}
            </option>
          </select>
          <div class="form-text small text-muted">
            <i class="fas fa-info-circle"></i> 
            <span v-if="form.branch && availableDockerfiles.length > 0">
              当前分支 "{{ form.branch }}" 的 Dockerfile 列表，或使用默认的 Dockerfile
            </span>
            <span v-else-if="form.branch">
              请先扫描分支 "{{ form.branch }}" 的 Dockerfile，或使用默认的 Dockerfile
            </span>
            <span v-else>
              请先选择分支并扫描，或使用默认的 Dockerfile
            </span>
          </div>
        </div>
      </div>

      <!-- 多服务选择面板（项目 Dockerfile 或模板） -->
      <div v-if="services.length > 0" class="mb-3">
        <div class="card border-info">
          <div class="card-header bg-info bg-opacity-10 d-flex justify-content-between align-items-center">
            <div>
              <i class="fas fa-server"></i> 服务选择
              <span class="badge bg-info ms-2">{{ services.length }} 个服务</span>
              <small class="text-muted ms-2">
                <i v-if="form.useProjectDockerfile" class="fas fa-file-code"></i>
                <i v-else class="fas fa-layer-group"></i>
                {{ form.useProjectDockerfile ? '来自项目 Dockerfile' : '来自模板' }}
              </small>
            </div>
            <div>
              <button 
                type="button"
                class="btn btn-sm btn-outline-info me-2"
                @click="selectAllServices"
                title="全选"
              >
                <i class="fas fa-check-square"></i> 全选
              </button>
              <button 
                type="button"
                class="btn btn-sm btn-outline-info"
                @click="deselectAllServices"
                title="全不选"
              >
                <i class="fas fa-square"></i> 全不选
              </button>
            </div>
          </div>
          <div class="card-body">
            <div v-if="parsingServices" class="text-center py-3">
              <span class="spinner-border spinner-border-sm me-2"></span>
              正在解析服务...
            </div>
            <div v-else-if="servicesError" class="alert alert-warning mb-0">
              <i class="fas fa-exclamation-triangle"></i> {{ servicesError }}
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-hover mb-0">
                <thead>
                  <tr>
                    <th style="width: 40px;">
                      <input 
                        type="checkbox" 
                        :checked="selectedServices.length === services.length && services.length > 0"
                        @change="toggleAllServices"
                        class="form-check-input"
                      />
                    </th>
                    <th>服务名称</th>
                    <th v-if="form.pushMode === 'multi' || form.useProjectDockerfile">镜像名</th>
                    <th v-if="form.pushMode === 'multi' || form.useProjectDockerfile">标签</th>
                    <th v-if="form.pushMode === 'multi' || form.useProjectDockerfile">推送仓库</th>
                    <th>端口</th>
                    <th>用户</th>
                    <th>构建</th>
                    <th v-if="form.pushMode === 'multi' || form.useProjectDockerfile">推送</th>
                    <th v-if="form.pushMode === 'single' && !form.useProjectDockerfile">包含</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="service in services" :key="service.name">
                    <td>
                      <input 
                        type="checkbox" 
                        :value="service.name"
                        v-model="selectedServices"
                        class="form-check-input"
                        @change="onServiceSelectionChange(service.name)"
                      />
                    </td>
                    <td>
                      <code>{{ service.name }}</code>
                    </td>
                    <!-- 多阶段推送模式或项目 Dockerfile：显示独立配置 -->
                    <template v-if="form.pushMode === 'multi' || form.useProjectDockerfile">
                      <td>
                        <input 
                          type="text" 
                          v-model="getServiceConfig(service.name).imageName"
                          :disabled="!selectedServices.includes(service.name)"
                          class="form-control form-control-sm"
                          :placeholder="getDefaultImageName(service.name)"
                          @blur="normalizeServiceConfig(service.name)"
                        />
                      </td>
                      <td>
                        <input 
                          type="text" 
                          v-model="getServiceConfig(service.name).tag"
                          :disabled="!selectedServices.includes(service.name)"
                          class="form-control form-control-sm"
                          :placeholder="form.tag || 'latest'"
                          @blur="normalizeServiceConfig(service.name)"
                        />
                      </td>
                      <td>
                        <select 
                          v-model="getServiceConfig(service.name).registry"
                          :disabled="!selectedServices.includes(service.name) || !getServiceConfig(service.name).push"
                          class="form-select form-select-sm"
                        >
                          <option value="">使用默认仓库</option>
                          <option v-for="reg in registries" :key="reg.name" :value="reg.name">
                            {{ reg.name }}
                          </option>
                        </select>
                      </td>
                      <td>
                        <span v-if="service.port" class="badge bg-secondary">{{ service.port }}</span>
                        <span v-else class="text-muted">-</span>
                      </td>
                      <td>
                        <span v-if="service.user" class="badge bg-secondary">{{ service.user }}</span>
                        <span v-else class="text-muted">-</span>
                      </td>
                      <td>
                        <span v-if="selectedServices.includes(service.name)" class="badge bg-success">
                          <i class="fas fa-check"></i> 是
                        </span>
                        <span v-else class="badge bg-secondary">
                          <i class="fas fa-times"></i> 否
                        </span>
                      </td>
                      <td>
                        <input 
                          type="checkbox" 
                          v-model="getServiceConfig(service.name).push"
                          :disabled="!selectedServices.includes(service.name)"
                          class="form-check-input"
                          :title="selectedServices.includes(service.name) ? '选择是否推送此服务镜像' : '请先选择构建此服务'"
                        />
                      </td>
                    </template>
                    <!-- 单一推送模式（仅模板）：简化显示 -->
                    <template v-else>
                      <td>
                        <span v-if="service.port" class="badge bg-secondary">{{ service.port }}</span>
                        <span v-else class="text-muted">-</span>
                      </td>
                      <td>
                        <span v-if="service.user" class="badge bg-secondary">{{ service.user }}</span>
                        <span v-else class="text-muted">-</span>
                      </td>
                      <td>
                        <span v-if="selectedServices.includes(service.name)" class="badge bg-success">
                          <i class="fas fa-check"></i> 是
                        </span>
                        <span v-else class="badge bg-secondary">
                          <i class="fas fa-times"></i> 否
                        </span>
                      </td>
                      <td>
                        <span v-if="selectedServices.includes(service.name)" class="badge bg-info">
                          <i class="fas fa-check"></i> 包含
                        </span>
                        <span v-else class="badge bg-secondary">
                          <i class="fas fa-times"></i> 不包含
                        </span>
                      </td>
                    </template>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="selectedServices.length > 0" class="mt-3 text-muted small">
              <i class="fas fa-info-circle"></i> 
              <span v-if="form.pushMode === 'single' && !form.useProjectDockerfile">
                单一推送模式：选中的 {{ selectedServices.length }} 个服务将构建到一个镜像中，使用统一的镜像名和标签。
              </span>
              <span v-else>
              已选择 {{ selectedServices.length }} 个服务进行构建
            </div>
          </div>
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-6">
          <label class="form-label">分支/标签
            <span v-if="!repoVerified" class="text-muted small">(请先验证仓库)</span>
          </label>
          <select 
            v-if="repoVerified"
            v-model="form.branch" 
            class="form-select"
            @change="onBranchChanged"
          >
            <option value="">使用默认分支 ({{ branchesAndTags.default_branch || 'main' }})</option>
            <optgroup v-if="branchesAndTags.branches.length > 0" label="分支">
              <option v-for="branch in branchesAndTags.branches" :key="branch" :value="branch">
                {{ branch }}
              </option>
            </optgroup>
            <optgroup v-if="branchesAndTags.tags.length > 0" label="标签">
              <option v-for="tag in branchesAndTags.tags" :key="tag" :value="tag">
                {{ tag }}
              </option>
            </optgroup>
          </select>
          <input 
            v-else
            type="text" 
            class="form-control" 
            placeholder="请先验证 Git 仓库"
            disabled
          />
          <div class="form-text small">
            <i class="fas fa-info-circle"></i> 
            验证仓库后可选择分支或标签，留空则使用默认分支
          </div>
        </div>
        <div class="col-md-6">
          <label class="form-label">子目录（可选）</label>
          <input 
            v-model="form.subPath" 
            type="text" 
            class="form-control" 
            placeholder="留空则使用仓库根目录"
          />
          <div class="form-text small">
            <i class="fas fa-info-circle"></i> 
            如果项目在仓库的子目录中，指定相对路径
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
      <div v-if="!form.useProjectDockerfile && templateParams.length > 0" class="mb-3">
        <div class="card border-primary">
          <div class="card-header bg-primary bg-opacity-10">
            <h6 class="mb-0">
              <i class="fas fa-sliders-h"></i> 模板参数配置
            </h6>
          </div>
          <div class="card-body">
            <div class="row g-3">
              <div v-for="param in templateParams" :key="param.name" class="col-md-6">
                <label class="form-label">
                  {{ param.description || param.name }}
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
                <small v-if="param.description && param.description !== param.name" class="form-text text-muted">
                  {{ param.description }}
                </small>
              </div>
            </div>
            <div v-if="templateParams.length === 0" class="text-muted small">
              <i class="fas fa-info-circle"></i> 当前模板无需配置参数
            </div>
          </div>
        </div>
      </div>

      <button type="submit" class="btn btn-primary w-100" :disabled="building">
        <i class="fas fa-code-branch"></i> 
        {{ building ? '构建中...' : '开始构建' }}
        <span v-if="building" class="spinner-border spinner-border-sm ms-2"></span>
      </button>
    </form>
  </div>
</template>

<script setup>
import axios from 'axios'
import { computed, onMounted, ref, watch } from 'vue'

const form = ref({
  projectType: 'jar',
  template: '',
  gitUrl: '',
  branch: '',
  subPath: '',
  imageName: 'myapp/demo',
  tag: 'latest',
  push: false,
  templateParams: {},
  useProjectDockerfile: true,  // 默认优先使用项目中的 Dockerfile
  dockerfileName: 'Dockerfile',  // Dockerfile文件名，默认Dockerfile
  pushMode: 'multi'  // 推送模式：'single' 单一推送，'multi' 多阶段推送
})

const templates = ref([])
const building = ref(false)
const templateParams = ref([])
const registries = ref([])
const templateSearch = ref('')  // 模板搜索关键字

// Git 数据源相关状态
const gitSources = ref([])
const selectedSourceId = ref('')
const availableDockerfiles = ref([]) // 当前数据源可用的 Dockerfile 列表
const scanningDockerfiles = ref(false) // 扫描 Dockerfile 状态

// Git 仓库验证相关状态
const repoVerified = ref(false)
const branchesAndTags = ref({
  branches: [],
  tags: [],
  default_branch: null
})

// 多服务构建相关状态
const services = ref([])  // 从 Dockerfile 或模板解析出的服务列表
const selectedServices = ref([])  // 选中的服务列表
const servicePushConfig = ref({})  // 每个服务的推送配置
const parsingServices = ref(false)  // 解析服务状态
const servicesError = ref('')  // 解析服务错误信息
const templateServices = ref([])  // 从模板解析出的服务列表

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

const imageNamePlaceholder = computed(() => {
  return 'myapp/demo'
})

async function loadTemplates() {
  try {
    const res = await axios.get('/api/templates')
    templates.value = res.data.items || []
    if (filteredTemplates.value.length > 0) {
      form.value.template = filteredTemplates.value[0].name
      await loadTemplateParams()
    }
  } catch (error) {
    console.error('加载模板失败:', error)
  }
}

async function loadRegistries() {
  try {
    const res = await axios.get('/api/registries')
    registries.value = res.data.registries || []
    
  } catch (error) {
    console.error('加载仓库列表失败:', error)
  }
}

function updateTemplates() {
  if (filteredTemplates.value.length > 0) {
    form.value.template = filteredTemplates.value[0].name
    loadTemplateParams()
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

async function loadTemplateParams() {
  templateParams.value = []
  form.value.templateParams = {}
  
  // 如果使用项目 Dockerfile，不需要加载模板参数
  if (form.value.useProjectDockerfile) {
    return
  }
  
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
    
    // 初始化参数值
    templateParams.value.forEach(param => {
      if (param.default) {
        form.value.templateParams[param.name] = param.default
      } else if (param.required) {
        // 必填参数但没有默认值，初始化为空字符串
        form.value.templateParams[param.name] = ''
      }
    })
    
    // 解析模板服务阶段（多阶段构建）
    templateServices.value = res.data.services || []
    if (templateServices.value.length > 0) {
      // 如果模板有服务阶段，合并到 services 中
      services.value = templateServices.value
      // 默认全选所有服务
      selectedServices.value = services.value.map(s => s.name)
      // 初始化推送配置（默认都不推送）
      servicePushConfig.value = {}
      services.value.forEach(s => {
        const config = getServiceConfig(s.name)
        config.push = false
        config.imageName = getDefaultImageName(s.name)
        config.tag = form.value.tag.trim() || 'latest'
        config.registry = ''
      })
    } else {
      // 如果模板没有服务阶段，清空服务列表
      services.value = []
      selectedServices.value = []
      servicePushConfig.value = {}
    }
  } catch (error) {
    console.error('加载模板参数失败:', error)
    templateParams.value = []
    templateServices.value = []
    services.value = []
    selectedServices.value = []
    servicePushConfig.value = {}
  }
}


// 解析 Dockerfile 服务列表（仅用于项目 Dockerfile）
async function parseDockerfileServices() {
  // 只有在使用项目 Dockerfile 时才解析
  if (!form.value.useProjectDockerfile) {
    // 如果使用模板，服务应该已经从模板中加载了，不需要从项目 Dockerfile 解析
    return
  }
  
  if (!repoVerified.value || !selectedSourceId.value || !form.value.gitUrl) {
    services.value = []
    selectedServices.value = []
    servicePushConfig.value = {}
    return
  }
  
  parsingServices.value = true
  servicesError.value = ''
  
  try {
    const payload = {
      git_url: form.value.gitUrl,
      branch: form.value.branch || undefined,
      dockerfile_name: form.value.dockerfileName || 'Dockerfile',
      source_id: selectedSourceId.value
    }
    
    const res = await axios.post('/api/parse-dockerfile-services', payload)
    
    if (res.data.services && res.data.services.length > 0) {
      services.value = res.data.services
      // 默认全选所有服务
      selectedServices.value = services.value.map(s => s.name)
      // 初始化推送配置（默认都不推送）
      servicePushConfig.value = {}
      services.value.forEach(s => {
        const config = getServiceConfig(s.name)
        config.push = false
        config.imageName = getDefaultImageName(s.name)
        config.tag = form.value.tag.trim() || 'latest'
        config.registry = ''
      })
    } else {
      services.value = []
      selectedServices.value = []
      servicePushConfig.value = {}
    }
  } catch (error) {
    console.error('解析 Dockerfile 服务失败:', error)
    servicesError.value = error.response?.data?.detail || '解析 Dockerfile 失败'
    services.value = []
    selectedServices.value = []
    servicePushConfig.value = {}
  } finally {
    parsingServices.value = false
  }
}

// 监听相关变化，自动解析服务（仅当使用项目 Dockerfile 时）
watch(() => [form.value.useProjectDockerfile, selectedSourceId.value, form.value.branch, form.value.dockerfileName, repoVerified.value], () => {
  // 如果使用模板，不从这里解析服务（服务应该从 loadTemplateParams 中获取）
  if (!form.value.useProjectDockerfile) {
    // 使用模板时，不清空服务列表，因为服务应该已经从模板中加载
    return
  }
  
  // 只有在使用项目 Dockerfile 时才解析服务
  if (repoVerified.value && selectedSourceId.value && form.value.gitUrl) {
    parseDockerfileServices()
  } else {
    // 数据源未验证或其他情况，清空服务列表
    services.value = []
    selectedServices.value = []
    servicePushConfig.value = {}
  }
}, { immediate: false })

// 获取服务的配置对象（如果不存在则创建默认配置）
function getServiceConfig(serviceName) {
  if (!servicePushConfig.value[serviceName]) {
    servicePushConfig.value[serviceName] = {
      push: false,
      imageName: '',
      tag: '',
      registry: ''
    }
  }
  return servicePushConfig.value[serviceName]
}

// 获取默认镜像名
function getDefaultImageName(serviceName) {
  const baseName = form.value.imageName.trim() || 'myapp/demo'
  return `${baseName}-${serviceName}`
}

// 规范化服务配置（填充默认值）
function normalizeServiceConfig(serviceName) {
  const config = getServiceConfig(serviceName)
  if (!config.imageName.trim()) {
    config.imageName = getDefaultImageName(serviceName)
  }
  if (!config.tag.trim()) {
    config.tag = form.value.tag.trim() || 'latest'
  }
}

// 服务选择变化时的处理
function onServiceSelectionChange(serviceName) {
  if (selectedServices.value.includes(serviceName)) {
    // 选中时，初始化配置
    normalizeServiceConfig(serviceName)
  } else {
    // 取消选中时，清空推送配置
    const config = getServiceConfig(serviceName)
    config.push = false
    config.registry = ''
  }
}

// 全选/全不选服务
function selectAllServices() {
  selectedServices.value = services.value.map(s => s.name)
  // 全选时，初始化所有服务的配置
  services.value.forEach(service => {
    normalizeServiceConfig(service.name)
  })
}

function deselectAllServices() {
  selectedServices.value = []
  // 全不选时，清空所有推送配置
  services.value.forEach(service => {
    const config = getServiceConfig(service.name)
    config.push = false
    config.registry = ''
  })
}

function toggleAllServices(event) {
  if (event.target.checked) {
    selectAllServices()
  } else {
    deselectAllServices()
  }
}

// 处理使用项目 Dockerfile 选项变化
function onUseProjectDockerfileChange() {
  if (!form.value.useProjectDockerfile) {
    // 切换到使用模板，重新加载模板参数和服务阶段
    loadTemplateParams()
    // 模板模式默认使用多阶段推送
    form.value.pushMode = 'multi'
  } else {
    // 切换到使用项目 Dockerfile，清空模板参数和服务
    templateParams.value = []
    form.value.templateParams = {}
    templateServices.value = []
    // 项目 Dockerfile 模式总是使用多阶段推送
    form.value.pushMode = 'multi'
    // 注意：services 会在 parseDockerfileServices 中重新填充
  }
}

async function handleBuild() {
  if (!selectedSourceId.value) {
    alert('请选择 Git 数据源')
    return
  }
  
  if (!repoVerified.value) {
    alert('数据源信息未加载完成，请稍候再试')
    return
  }
  
  // 如果有服务阶段（无论是模板还是项目 Dockerfile），验证至少选择一个服务
  if (services.value.length > 0 && selectedServices.value.length === 0) {
    alert('请至少选择一个服务进行构建')
    return
  }
  
  building.value = true
  
    const payload = {
      project_type: form.value.projectType,
      template: form.value.template,
      git_url: form.value.gitUrl.trim(),
      branch: form.value.branch.trim() || undefined,
      sub_path: form.value.subPath.trim() || undefined,
      imagename: form.value.imageName.trim(),
      tag: form.value.tag.trim() || 'latest',
      push: form.value.push ? 'on' : 'off',
      template_params: Object.keys(form.value.templateParams).length > 0 
        ? JSON.stringify(form.value.templateParams) 
        : undefined,
      use_project_dockerfile: form.value.useProjectDockerfile,
      dockerfile_name: form.value.dockerfileName || 'Dockerfile',
      source_id: selectedSourceId.value || undefined,
      push_mode: (!form.value.useProjectDockerfile) ? form.value.pushMode : undefined,  // 推送模式（仅模板模式）
      // 多服务构建参数（无论是模板还是项目 Dockerfile）
      selected_services: (selectedServices.value.length > 0) 
        ? selectedServices.value 
        : undefined,
      service_push_config: (selectedServices.value.length > 0) 
        ? Object.fromEntries(
            selectedServices.value.map(serviceName => {
              const config = getServiceConfig(serviceName)
              // 确保配置已规范化
              normalizeServiceConfig(serviceName)
              return [serviceName, {
                push: config.push || false,
                imageName: config.imageName || getDefaultImageName(serviceName),
                tag: config.tag || form.value.tag.trim() || 'latest',
                registry: config.registry || ''
              }]
            })
          )
        : undefined
    }
  
  try {
    const res = await axios.post('/api/build-from-source', payload)
    
    // 获取 build_id 或 task_id（兼容新旧版本）
    const buildId = res.data.build_id || res.data.task_id
    if (buildId) {
      console.log('✅ 构建任务已启动, task_id:', buildId)
      
      window.dispatchEvent(new CustomEvent('show-build-log'))
      
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
    alert(error.response?.data?.error || error.response?.data?.detail || '构建失败')
    building.value = false
  }
}

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
      
      const logLines = logs
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
      
      if (logLines.length > lastLogLength) {
        for (let i = lastLogLength; i < logLines.length; i++) {
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
      if (error.response?.status === 404) {
        clearInterval(pollInterval)
        building.value = false
        window.dispatchEvent(new CustomEvent('add-log', {
          detail: { text: '❌ 任务不存在' }
        }))
      }
    }
  }
  
  window.dispatchEvent(new CustomEvent('add-log', {
    detail: { text: `🚀 开始构建，Task ID: ${buildId}` }
  }))
  
  await poll()
  
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
  loadGitSources()
})

async function loadGitSources() {
  try {
    const res = await axios.get('/api/git-sources')
    gitSources.value = res.data.sources || []
  } catch (error) {
    console.error('加载数据源列表失败:', error)
  }
}

async function onSourceSelected() {
  if (!selectedSourceId.value) {
    availableDockerfiles.value = []
    form.value.gitUrl = ''
    repoVerified.value = false
    branchesAndTags.value = {
      branches: [],
      tags: [],
      default_branch: null
    }
    form.value.branch = ''
    return
  }
  
  const source = gitSources.value.find(s => s.source_id === selectedSourceId.value)
  if (source) {
    form.value.gitUrl = source.git_url
    branchesAndTags.value = {
      branches: source.branches || [],
      tags: source.tags || [],
      default_branch: source.default_branch || null
    }
    repoVerified.value = true
    form.value.branch = source.default_branch || ''
    
    // 清空 Dockerfile 列表，需要根据分支扫描
    availableDockerfiles.value = []
    form.value.dockerfileName = 'Dockerfile'
    
    // 如果选择了分支且使用项目 Dockerfile，自动扫描该分支的 Dockerfile
    if (form.value.branch && form.value.useProjectDockerfile) {
      setTimeout(() => {
        scanDockerfiles()
      }, 300)
    }
  }
}

// 加载数据源的 Dockerfile 列表（从数据源管理获取）
async function loadSourceDockerfiles(sourceId) {
  try {
    const res = await axios.get(`/api/git-sources/${sourceId}/dockerfiles`)
    const dockerfiles = res.data.dockerfiles || {}
    availableDockerfiles.value = Object.keys(dockerfiles).sort()
    
    // 如果当前选择的 Dockerfile 不在列表中，且列表不为空，则选择第一个
    if (availableDockerfiles.value.length > 0 && !availableDockerfiles.value.includes(form.value.dockerfileName)) {
      // 如果默认的 Dockerfile 不在列表中，选择列表中的第一个
      if (form.value.dockerfileName === 'Dockerfile' && !availableDockerfiles.value.includes('Dockerfile')) {
        form.value.dockerfileName = availableDockerfiles.value[0]
      }
    }
  } catch (error) {
    console.error('加载 Dockerfile 列表失败:', error)
    availableDockerfiles.value = []
  }
}

// 扫描指定分支的 Dockerfile（仅在使用项目 Dockerfile 时）
async function scanDockerfiles() {
  // 只有在使用项目 Dockerfile 时才扫描
  if (!form.value.useProjectDockerfile) {
    return
  }
  
  if (!selectedSourceId.value || !repoVerified.value) {
    alert('请先选择数据源')
    return
  }
  
  const branch = form.value.branch || branchesAndTags.value.default_branch || 'main'
  if (!branch) {
    alert('请先选择分支')
    return
  }
  
  scanningDockerfiles.value = true
  try {
    const payload = {
      git_url: form.value.gitUrl.trim(),
      save_as_source: false,
      branch: branch  // 指定要扫描的分支
    }
    
    // 如果选择了数据源，使用数据源的认证信息
    if (selectedSourceId.value) {
      payload.source_id = selectedSourceId.value
    }
    
    const res = await axios.post('/api/verify-git-repo', payload)
    
    if (res.data.success && res.data.dockerfiles) {
      const dockerfileCount = Object.keys(res.data.dockerfiles).length
      if (dockerfileCount > 0) {
        availableDockerfiles.value = Object.keys(res.data.dockerfiles).sort()
        // 如果当前选择的 Dockerfile 不在列表中，选择第一个
        if (!availableDockerfiles.value.includes(form.value.dockerfileName)) {
          form.value.dockerfileName = availableDockerfiles.value[0]
        }
        // 扫描完成，不显示提示，只更新选择框
      } else {
        availableDockerfiles.value = []
        // 如果列表为空，重置为默认值
        form.value.dockerfileName = 'Dockerfile'
      }
    } else {
      // 扫描失败时显示错误提示
      alert('扫描失败：' + (res.data.detail || '未知错误'))
    }
  } catch (error) {
    console.error('扫描 Dockerfile 失败:', error)
    alert(error.response?.data?.detail || '扫描 Dockerfile 失败')
  } finally {
    scanningDockerfiles.value = false
  }
}

// 分支变化时的处理
function onBranchChanged() {
  // 清空 Dockerfile 列表，需要重新扫描
  availableDockerfiles.value = []
  form.value.dockerfileName = 'Dockerfile'
  
  // 如果选择了分支且有数据源，且使用项目 Dockerfile，可以自动扫描
  if (form.value.branch && selectedSourceId.value && repoVerified.value && form.value.useProjectDockerfile) {
    // 延迟一下，让用户看到变化
    setTimeout(() => {
      scanDockerfiles()
    }, 300)
  }
}

function formatGitUrl(url) {
  if (!url) return ''
  return url.replace('https://', '').replace('http://', '').replace('.git', '')
}
</script>

<style scoped>
.source-build-panel {
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

/* 小型 Alert 样式 */
.alert-sm {
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.alert-sm i {
  margin-right: 0.25rem;
}
</style>


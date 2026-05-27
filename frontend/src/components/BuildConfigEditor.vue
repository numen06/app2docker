<template>
  <div class="build-config-editor">
    <div class="flex justify-between items-center mb-4">
      <h5 class="mb-0">
        <AppIcon  name="edit" /> 编辑构建配置
      </h5>
      <div class="inline-flex items-stretch text-sm">
        <Button 
          type="button"
          variant="outline" size="sm"
          @click="showJsonModal = true"
        >
          <AppIcon  name="code" /> 查看JSON
        </Button>
        <Button 
          type="button"
          
          @click="saveConfig"
          :disabled="saving"
        >
          <AppIcon  name="save" /> {{ saving ? '保存中...' : '保存配置' }}
        </Button>
        <Button 
          type="button"
          variant="outline"
          @click="cancel"
        >
          <AppIcon  name="times" /> 取消
        </Button>
      </div>
    </div>

    <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
      <div class="p-4">
        <!-- Git配置 -->
        <div class="mb-4">
          <h6 class="border-b border-slate-200 pb-2 mb-3">
            <AppIcon  name="code-branch" class="text-blue-600" /> Git 配置
          </h6>
          <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">Git 仓库地址 <span class="text-red-500">*</span></label>
              <input 
                v-model="formData.git_url" 
                type="text" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400" 
                required
                placeholder="https://github.com/user/repo.git"
              >
            </div>
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">分支名称</label>
              <div class="flex w-full">
                <select 
                  v-model="formData.branch" 
                  class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                  :disabled="loadingBranches"
                >
                  <option value="">-- 选择分支（留空使用默认分支） --</option>
                  <option v-for="branch in branches" :key="branch" :value="branch">
                    {{ branch }}
                  </option>
                </select>
                <Button 
                  variant="outline" size="sm" 
                  type="button"
                  @click="loadBranches"
                  :disabled="loadingBranches || !formData.git_url"
                  title="自动加载分支列表"
                >
                  <AppIcon v-if="loadingBranches"  name="spinner" spin />
                  <AppIcon v-else  name="sync-alt" />
                </Button>
              </div>
              <small class="text-slate-500">
                <span v-if="loadingBranches">正在加载分支列表...</span>
                <span v-else-if="branches.length > 0">已加载 {{ branches.length }} 个分支</span>
                <span v-else>留空则使用默认分支，点击刷新按钮加载分支列表</span>
              </small>
            </div>
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">Git 数据源</label>
              <select 
                v-model="formData.source_id" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                @change="onSourceSelected"
              >
                <option value="">-- 选择数据源或手动输入 --</option>
                <option v-for="source in gitSources" :key="source.source_id" :value="source.source_id">
                  {{ source.name }} ({{ formatGitUrl(source.git_url) }})
                </option>
              </select>
            </div>
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">项目类型 <span class="text-red-500">*</span></label>
              <select v-model="formData.project_type" class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400">
                <option value="">-- 请选择项目类型 --</option>
                <option v-for="pt in projectTypesList" :key="pt.value" :value="pt.value">
                  {{ pt.label }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <!-- Dockerfile配置 -->
        <div class="mb-4">
          <h6 class="border-b border-slate-200 pb-2 mb-3">
            <AppIcon  name="file-code" class="text-blue-600" /> Dockerfile 配置
          </h6>
          <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div class="col-span-full">
              <label class="block text-sm font-medium text-slate-700">Dockerfile 来源</label>
              <div class="inline-flex items-stretch w-full mb-2" role="group">
                <input 
                  type="radio" 
                  class="choice-input" 
                  id="use-project-dockerfile" 
                  :value="true"
                  v-model="formData.use_project_dockerfile"
                  @change="onDockerfileSourceChange"
                >
                <label class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700" for="use-project-dockerfile">
                  <AppIcon  name="file-code" /> 项目Dockerfile
                </label>
                
                <input 
                  type="radio" 
                  class="choice-input" 
                  id="use-template" 
                  :value="false"
                  v-model="formData.use_project_dockerfile"
                  @change="onDockerfileSourceChange"
                >
                <label class="inline-flex flex-1 cursor-pointer items-center justify-center rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 has-[:checked]:border-blue-600 has-[:checked]:bg-blue-50 has-[:checked]:text-blue-700" for="use-template">
                  <AppIcon  name="layer-group" /> 使用模板
                </label>
              </div>
            </div>
            <div v-if="formData.use_project_dockerfile" class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">Dockerfile 文件名</label>
              <input 
                v-model="formData.dockerfile_name" 
                type="text" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                placeholder="Dockerfile"
              >
            </div>
            <div v-else class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">模板名称</label>
              <select v-model="formData.template" class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400" @change="onTemplateChange">
                <option value="">-- 请选择模板 --</option>
                <option v-for="t in filteredTemplates" :key="t.name" :value="t.name">
                  {{ t.name }}
                </option>
              </select>
            </div>
            <div v-if="!formData.use_project_dockerfile && templateParams.length > 0" class="col-span-full">
              <label class="block text-sm font-medium text-slate-700">模板参数</label>
              <div class="table-scroll overflow-x-auto">
                <table class="w-full border-collapse text-sm border border-slate-200">
                  <thead>
                    <tr>
                      <th>参数名</th>
                      <th>值</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="param in templateParams" :key="param.name">
                      <td>{{ param.name }} <span v-if="param.required" class="text-red-500">*</span></td>
                      <td>
                        <input 
                          v-if="param.type === 'string'"
                          v-model="formData.template_params[param.name]"
                          type="text"
                          class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                          :placeholder="param.default || ''"
                        >
                        <select 
                          v-else-if="param.type === 'select'"
                          v-model="formData.template_params[param.name]"
                          class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
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
          <h6 class="border-b border-slate-200 pb-2 mb-3">
            <AppIcon  name="docker" class="text-blue-600" /> 镜像配置
          </h6>
          <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">镜像名称 <span class="text-red-500">*</span></label>
              <input 
                v-model="formData.image_name" 
                type="text" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400" 
                required
                placeholder="myapp/demo"
              >
            </div>
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">镜像标签</label>
              <input 
                v-model="formData.tag" 
                type="text" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                placeholder="latest"
              >
            </div>
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">推送模式</label>
              <select v-model="formData.push_mode" class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400" @change="onPushModeChange">
                <option value="single">单服务推送</option>
                <option value="multi">多服务推送</option>
              </select>
            </div>
            <div class="md:col-span-6">
              <div class="mt-4 flex items-center gap-2">
                <input 
                  class="h-4 w-4 rounded border-slate-300" 
                  type="checkbox" 
                  id="should_push"
                  v-model="formData.should_push"
                >
                <label class="text-sm text-slate-700" for="should_push">
                  构建完成后推送到仓库
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 服务配置（多服务模式） -->
        <div v-if="formData.push_mode === 'multi' && services.length > 0" class="mb-4">
          <h6 class="border-b border-slate-200 pb-2 mb-3">
            <AppIcon  name="layer-group" class="text-blue-600" /> 服务配置
          </h6>
          <div class="mb-3">
            <label class="block text-sm font-medium text-slate-700">选择服务</label>
            <div class="flex items-center gap-2" v-for="service in services" :key="service.name">
              <input 
                class="h-4 w-4 rounded border-slate-300" 
                type="checkbox" 
                :id="`service-${service.name}`"
                :value="service.name"
                v-model="formData.selected_services"
              >
              <label class="text-sm text-slate-700" :for="`service-${service.name}`">
                {{ service.name }}
              </label>
            </div>
          </div>
          <div v-if="formData.selected_services.length > 0" class="table-scroll overflow-x-auto">
            <table class="w-full border-collapse text-sm border border-slate-200">
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
                      class="h-4 w-4 rounded border-slate-300"
                    >
                  </td>
                  <td>
                    <input 
                      type="text" 
                      v-model="formData.service_push_config[serviceName].imageName"
                      class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                      :placeholder="getServiceDefaultImageName(serviceName)"
                    >
                  </td>
                  <td>
                    <input 
                      type="text" 
                      v-model="formData.service_push_config[serviceName].tag"
                      class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                      :placeholder="formData.tag || 'latest'"
                    >
                  </td>
                  <td>
                    <input 
                      type="text" 
                      v-model="formData.service_push_config[serviceName].registry"
                      class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
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
          <h6 class="border-b border-slate-200 pb-2 mb-3">
            <AppIcon  name="cube" class="text-blue-600" /> 单服务配置
          </h6>
          <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">选择服务</label>
              <select v-model="formData.selected_service" class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400">
                <option value="">-- 请选择服务 --</option>
                <option v-for="service in services" :key="service.name" :value="service.name">
                  {{ service.name }}
                </option>
              </select>
            </div>
            <div class="md:col-span-6">
              <label class="block text-sm font-medium text-slate-700">完整镜像名</label>
              <input 
                v-model="formData.custom_image_name" 
                type="text" 
                class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                :placeholder="formData.selected_service ? `${formData.image_name}/${formData.selected_service}` : ''"
              >
            </div>
          </div>
        </div>

        <!-- 资源包配置 -->
        <div class="mb-4">
          <h6 class="border-b border-slate-200 pb-2 mb-3">
            <AppIcon  name="archive" class="text-blue-600" /> 资源包配置
          </h6>
          <div v-if="packages.length === 0" class="text-slate-500">
            暂无资源包，请先创建资源包
          </div>
          <div v-else>
            <div class="mb-2 flex items-center gap-2">
              <input 
                class="h-4 w-4 rounded border-slate-300" 
                type="checkbox" 
                id="select-all-packages"
                :checked="formData.resource_package_ids.length === packages.length"
                @change="toggleAllPackages"
              >
              <label class="text-sm text-slate-700" for="select-all-packages">
                全选
              </label>
            </div>
            <div class="table-scroll overflow-x-auto">
              <table class="w-full border-collapse text-sm border border-slate-200">
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
                        class="h-4 w-4 rounded border-slate-300"
                      >
                    </td>
                    <td>{{ pkg.name }}</td>
                    <td>
                      <input 
                        type="text" 
                        v-model="formData.resource_package_paths[pkg.package_id]"
                        class="flex h-9 w-full rounded-md border border-slate-200 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
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
    <div v-if="showJsonModal" class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4" @click.self="showJsonModal = false">
      <div class="relative z-10 mx-auto w-full max-w-3xl">
        <div class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl" @click.stop>
          <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
            <h5 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
              <AppIcon  name="code" /> 构建配置JSON
            </h5>
            <button type="button" class="rounded-md p-2 text-slate-500 hover:bg-slate-100" @click="showJsonModal = false"><AppIcon  name="times" /></button>
          </div>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
            <div class="flex justify-end mb-2">
              <Button 
                type="button"
                variant="outline" size="sm"
                @click="copyJson"
              >
                <AppIcon  name="copy" /> 复制JSON
              </Button>
            </div>
            <codemirror
              v-model="configJsonText"
              :style="{ height: 'min(500px, 60vh)', fontSize: '13px' }"
              :disabled="true"
              :extensions="jsonEditorExtensions"
            />
          </div>
          <div class="flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3">
            <Button type="button" variant="outline" size="sm" @click="showJsonModal = false">关闭</Button>
          </div>
        </div>
      </div>
    </div>
</div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import { Badge } from "@/components/ui/badge";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import axios from 'axios'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { copyToClipboard } from '../utils/clipboard.js'
import { Codemirror } from 'vue-codemirror'
import { oneDark } from '@codemirror/theme-one-dark'
import { StreamLanguage } from '@codemirror/language'
import { javascript } from '@codemirror/legacy-modes/mode/javascript'
import { getServiceAnalysisWithCache } from '../utils/serviceAnalysisCache.js'
import { 
  getProjectTypes, 
  getProjectTypesSync 
} from '../utils/projectTypes.js'

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
// 项目类型相关
const projectTypesList = ref(getProjectTypesSync()) // 从缓存获取项目类型列表

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

// 项目类型处理（从缓存加载，如果没有则从API加载）
async function loadProjectTypes() {
  projectTypesList.value = await getProjectTypes()
}

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
        const gitUrl = source.git_url
        const branch = formData.value.branch || undefined
        const dockerfileName = formData.value.dockerfile_name || 'Dockerfile'
        const sourceId = formData.value.source_id
        
        // 使用缓存机制获取服务分析结果
        const servicesList = await getServiceAnalysisWithCache(
          async () => {
            return await axios.post('/api/parse-dockerfile-services', {
              git_url: gitUrl,
              branch: branch,
              dockerfile_name: dockerfileName,
              source_id: sourceId
            })
          },
          gitUrl,
          branch || 'main',
          dockerfileName,
          sourceId,
          false // 不强制刷新，使用缓存
        )
        services.value = servicesList || []
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
  const success = await copyToClipboard(text)
  if (success) {
    toastSuccess('JSON已复制到剪贴板')
  } else {
    toastError('自动复制失败，请手动选择并复制文本（已自动选中）')
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
    toastError('保存失败：配置格式错误')
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
  loadProjectTypes()
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


<template>
  <div class="pipeline-multi-service-tab space-y-4">
<div class="alert alert-info mb-3">
              <i class="fas fa-info-circle"></i>
              <strong>说明：</strong>此配置为独立的多服务配置，不需要读取
              Dockerfile。可以手动添加和配置服务。
            </div>

            <!-- 推送模式选择 -->
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700 mb-2"><strong>推送模式</strong></label>
              <div
                class="pipeline-webhook-strategy pipeline-push-mode-strategy"
                role="group"
                aria-label="推送模式"
              >
                <input
                  type="radio"
                  class="btn-check"
                  id="ms-mode-single"
                  value="single"
                  v-model="multiServiceFormData.push_mode"
                />
                <label class="pipeline-webhook-strategy__option" for="ms-mode-single">
                  <i class="fas fa-cube"></i>
                  单服务模式
                  <small>一个镜像对应整仓构建</small>
                </label>

                <input
                  type="radio"
                  class="btn-check"
                  id="ms-mode-multi"
                  value="multi"
                  v-model="multiServiceFormData.push_mode"
                />
                <label class="pipeline-webhook-strategy__option" for="ms-mode-multi">
                  <i class="fas fa-sitemap"></i>
                  多服务模式
                  <small>按阶段拆分镜像</small>
                </label>
              </div>
            </div>

            <!-- 全局镜像配置 / 服务配置 -->
            <div class="mb-3">
              <label class="block text-sm font-medium text-slate-700">
                <strong v-if="multiServiceFormData.push_mode === 'single'"
                  >服务配置</strong
                >
                <strong v-else>全局镜像配置（前缀）</strong>
              </label>
              <div class="row g-2">
                <div class="col-md-6">
                  <label class="form-label small">
                    <span v-if="multiServiceFormData.push_mode === 'single'"
                      >镜像名称</span
                    >
                    <span v-else>镜像名称前缀</span>
                  </label>
                  <input
                    v-model="multiServiceFormData.image_name"
                    type="text"
                    class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                    placeholder="myapp/demo"
                  />
                  <small class="text-slate-500 block mt-1">
                    <span v-if="multiServiceFormData.push_mode === 'single'">
                      <i class="fas fa-info-circle"></i>
                      单服务模式下，此配置将直接用于服务构建
                    </span>
                    <span v-else>
                      <i class="fas fa-info-circle"></i>
                      多服务模式下，每个启用的服务镜像名称将自动生成为:
                      <code
                        >{{
                          multiServiceFormData.image_name ||
                          "myapp/demo"
                        }}/服务名</code
                      >
                    </span>
                  </small>
                </div>
                <div class="col-md-6">
                  <label class="form-label small">
                    <span v-if="multiServiceFormData.push_mode === 'single'"
                      >标签</span
                    >
                    <span v-else>全局标签（快捷设置）</span>
                  </label>
                  <input
                    v-model="multiServiceFormData.tag"
                    type="text"
                    class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
                    placeholder="latest"
                  />
                  <small class="text-slate-500 block mt-1">
                    <span v-if="multiServiceFormData.push_mode === 'single'">
                      <i class="fas fa-info-circle"></i>
                      单服务模式下，此标签将直接用于服务构建
                    </span>
                    <span v-else>
                      <i class="fas fa-info-circle"></i>
                      多服务模式下，可快速为所有启用的服务设置标签（可在服务级别覆盖）
                    </span>
                  </small>
                </div>
              </div>
              <!-- 单服务模式下的推送开关 -->
              <div
                v-if="multiServiceFormData.push_mode === 'single'"
                class="mt-3"
              >
                <div class="form-check form-switch">
                  <input
                    :checked="getSingleServicePush()"
                    @change="updateSingleServicePush($event.target.checked)"
                    class="form-check-input"
                    type="checkbox"
                    id="singleServicePushCheck"
                    style="width: 3em; height: 1.5em"
                  />
                  <label
                    class="form-check-label fw-bold ml-2"
                    for="singleServicePushCheck"
                  >
                    <i class="fas fa-cloud-upload-alt text-green-600"></i>
                    构建完成后推送到仓库
                  </label>
                </div>
              </div>
            </div>

            <!-- 服务列表（仅多服务模式显示） -->
            <div v-if="multiServiceFormData.push_mode === 'multi'" class="mb-3">
              <div
                class="flex justify-between items-center mb-3"
              >
                <label class="form-label mb-0"><strong>服务列表</strong></label>
                <div class="pipeline-action-group" role="group">
                  <Button
                    type="button"
                    variant="outline" size="sm"
                    @click="enableAllServices"
                    title="全部启用"
                    :disabled="
                      multiServiceFormData.selected_services.length === 0
                    "
                  >
                    <i class="fas fa-check-circle"></i> 全部启用
                  </Button>
                  <Button
                    type="button"
                    variant="outline" size="sm"
                    @click="disableAllServices"
                    title="全部禁用"
                    :disabled="
                      multiServiceFormData.selected_services.length === 0
                    "
                  >
                    <i class="fas fa-times-circle"></i> 全部禁用
                  </Button>
                  <Button
                    type="button"
                    variant="outline" size="sm"
                    @click="addServiceToMultiConfig"
                    title="添加服务"
                  >
                    <i class="fas fa-plus"></i> 添加服务
                  </Button>
                  <Button
                    type="button"
                    variant="outline" size="sm"
                    @click="parseDockerfileForMultiService"
                    title="识别dockerfile"
                    :disabled="parsingDockerfileForMultiService"
                  >
                    <i class="fas fa-file-code"></i>
                    <span v-if="parsingDockerfileForMultiService"
                      >识别中...</span
                    >
                    <span v-else>识别dockerfile</span>
                  </Button>
                </div>
              </div>

              <div
                v-if="multiServiceFormData.selected_services.length === 0"
                class="text-slate-500 text-center py-12 border rounded bg-light"
              >
                <i class="fas fa-inbox text-4xl mb-3 text-slate-500"></i>
                <p class="mb-1">暂无服务</p>
                <small>点击"添加服务"按钮添加服务</small>
              </div>

              <div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                <div
                  v-for="(
                    serviceName, index
                  ) in multiServiceFormData.selected_services"
                  :key="`service-${index}-${serviceName}`"
                  class="col-12"
                >
                  <div
                    class="card shadow-sm border"
                    :class="{
                      'border-secondary opacity-75':
                        multiServiceFormData.push_mode === 'multi' &&
                        !(
                          multiServiceFormData.service_push_config[serviceName]
                            ?.enabled !== false
                        ),
                    }"
                  >
                    <div
                      class="card-header bg-light flex justify-between items-center py-2"
                    >
                      <div class="flex items-center">
                        <span class="badge bg-primary mr-2"
                          >#{{ index + 1 }}</span
                        >
                        <strong class="text-blue-600">{{
                          serviceName || "未命名服务"
                        }}</strong>
                        <!-- 多服务模式下的启用/禁用开关 -->
                        <div
                          v-if="multiServiceFormData.push_mode === 'multi'"
                          class="form-check form-switch ml-3"
                        >
                          <input
                            :checked="
                              multiServiceFormData.service_push_config[
                                serviceName
                              ]?.enabled !== false
                            "
                            @change="
                              updateServiceEnabled(
                                serviceName,
                                $event.target.checked
                              )
                            "
                            class="form-check-input"
                            type="checkbox"
                            :id="`enableCheck-${index}`"
                            style="width: 2.5em; height: 1.3em"
                          />
                          <label
                            class="form-check-label fw-bold ml-2"
                            :for="`enableCheck-${index}`"
                          >
                            <span
                              :class="
                                multiServiceFormData.service_push_config[
                                  serviceName
                                ]?.enabled !== false
                                  ? 'text-green-600'
                                  : 'text-slate-500'
                              "
                            >
                              <i
                                :class="
                                  multiServiceFormData.service_push_config[
                                    serviceName
                                  ]?.enabled !== false
                                    ? 'fas fa-check-circle'
                                    : 'fas fa-times-circle'
                                "
                              ></i>
                              {{
                                multiServiceFormData.service_push_config[
                                  serviceName
                                ]?.enabled !== false
                                  ? "启用"
                                  : "禁用"
                              }}
                            </span>
                          </label>
                        </div>
                      </div>
                      <Button
                        type="button"
                        variant="destructive" size="sm"
                        @click="removeServiceFromMultiConfig(index)"
                        :disabled="multiServiceFormData.push_mode === 'single'"
                        :title="
                          multiServiceFormData.push_mode === 'single'
                            ? '单服务模式下不能删除服务'
                            : '删除服务'
                        "
                      >
                        <i class="fas fa-trash"></i>
                      </Button>
                    </div>
                    <div
                      class="card-body"
                      :class="{
                        'opacity-50':
                          multiServiceFormData.push_mode === 'multi' &&
                          multiServiceFormData.service_push_config[serviceName]
                            ?.enabled === false,
                      }"
                    >
                      <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                        <div class="col-12">
                          <label class="form-label small fw-bold">
                            <i class="fas fa-tag text-blue-600"></i> 服务名称
                            <span class="text-red-500">*</span>
                          </label>
                          <input
                            :value="serviceName"
                            @input="
                              updateServiceName(index, $event.target.value)
                            "
                            type="text"
                            class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                            :disabled="
                              multiServiceFormData.push_mode === 'multi' &&
                              multiServiceFormData.service_push_config[
                                serviceName
                              ]?.enabled === false
                            "
                            placeholder="例如: api, web, worker"
                            required
                          />
                          <small class="text-slate-500 block mt-1">
                            <i class="fas fa-info-circle text-amber-600"></i>
                            <strong>注意：</strong>服务名称必须与 Dockerfile
                            中的阶段名（stage name）匹配才会生效。例如
                            Dockerfile 中有
                            <code>FROM node:18 AS api</code>，则服务名称应填写
                            <code>api</code>。
                          </small>
                        </div>
                        <div class="col-12">
                          <label class="form-label small fw-bold">
                            <i class="fas fa-image text-sky-600"></i> 镜像名称
                          </label>
                          <input
                            :value="
                              multiServiceFormData.service_push_config[
                                serviceName
                              ]?.imageName || ''
                            "
                            @input="
                              updateServiceImageName(
                                serviceName,
                                $event.target.value
                              )
                            "
                            type="text"
                            class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                            :disabled="
                              multiServiceFormData.push_mode === 'multi' &&
                              multiServiceFormData.service_push_config[
                                serviceName
                              ]?.enabled === false
                            "
                            :placeholder="
                              getMultiServiceDefaultImageName(serviceName)
                            "
                          />
                          <small class="text-slate-500 block mt-1">
                            <i class="fas fa-info-circle"></i>
                            <span
                              v-if="multiServiceFormData.push_mode === 'single'"
                              >留空使用全局配置</span
                            >
                            <span v-else
                              >留空使用前缀拼接:
                              {{
                                getMultiServiceDefaultImageName(serviceName)
                              }}</span
                            >
                          </small>
                        </div>
                        <div class="col-md-4">
                          <label class="form-label small fw-bold">
                            <i class="fas fa-tags text-amber-600"></i> 标签
                          </label>
                          <input
                            :value="
                              multiServiceFormData.service_push_config[
                                serviceName
                              ]?.tag || ''
                            "
                            @input="
                              updateServiceTag(serviceName, $event.target.value)
                            "
                            type="text"
                            class="flex h-10 w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
                            :disabled="
                              multiServiceFormData.push_mode === 'multi' &&
                              multiServiceFormData.service_push_config[
                                serviceName
                              ]?.enabled === false
                            "
                            :placeholder="
                              multiServiceFormData.tag || 'latest'
                            "
                          />
                        </div>
                        <div class="col-md-8 flex items-end">
                          <div class="form-check form-switch">
                            <input
                              :checked="
                                multiServiceFormData.service_push_config[
                                  serviceName
                                ]?.push || false
                              "
                              @change="
                                updateServicePush(
                                  serviceName,
                                  $event.target.checked
                                )
                              "
                              class="form-check-input"
                              type="checkbox"
                              :id="`pushCheck-${index}`"
                              :disabled="
                                multiServiceFormData.push_mode === 'multi' &&
                                multiServiceFormData.service_push_config[
                                  serviceName
                                ]?.enabled === false
                              "
                              style="width: 3em; height: 1.5em"
                            />
                            <label
                              class="form-check-label fw-bold ml-2"
                              :for="`pushCheck-${index}`"
                            >
                              <i
                                class="fas fa-cloud-upload-alt text-green-600"
                              ></i>
                              推送到仓库
                            </label>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
    <div v-if="!embedded" class="mt-4 flex justify-end gap-2 border-t border-slate-200 pt-4">
      <Button type="button" size="sm" :disabled="savingMultiServiceConfig" @click="saveMultiServiceConfig">
        <span v-if="savingMultiServiceConfig" class="fas fa-spinner fa-spin mr-1"></span>
        <i v-else class="fas fa-save mr-1"></i>
        {{ savingMultiServiceConfig ? '保存中...' : '保存' }}
      </Button>
    </div>
  </div>
</template>

<script setup>
import { inject, watch } from "vue";
import Button from "@/components/ui/button/Button.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { usePipelineMultiService } from "@/composables/usePipelineMultiService";

const props = defineProps({
  embedded: { type: Boolean, default: false },
});

const detail = inject(PIPELINE_DETAIL_KEY, null);
const editor = inject("pipelineEditor", null);

const {
  multiServiceFormData,
  savingMultiServiceConfig,
  parsingDockerfileForMultiService,
  loadFromPipeline,
  addServiceToMultiConfig,
  removeServiceFromMultiConfig,
  updateServiceName,
  updateServiceImageName,
  updateServiceTag,
  updateServicePush,
  getSingleServicePush,
  updateSingleServicePush,
  updateServiceEnabled,
  enableAllServices,
  disableAllServices,
  getMultiServiceDefaultImageName,
  parseDockerfileForMultiService,
  saveMultiServiceConfig,
} = usePipelineMultiService({
  formData: editor?.formData,
  getPipeline: () => editor?.editingPipeline?.value || detail?.pipeline?.value,
  embedded: props.embedded,
  onSaved: () => detail?.refresh?.(),
});

watch(
  () => editor?.editingPipeline?.value || detail?.pipeline?.value,
  (p) => {
    if (p) loadFromPipeline(p);
  },
  { immediate: true }
);
</script>


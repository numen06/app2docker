<template>
  <div class="pipeline-create-step-push-mode pipeline-config-pane">
    <div v-if="analyzing" class="py-6 text-center text-slate-500">
      <i class="fas fa-spinner fa-spin mr-1"></i>
      正在根据 Dockerfile 分析服务结构…
    </div>

    <template v-else>
      <div v-if="servicesError" class="alert alert-warning mb-3">
        <i class="fas fa-exclamation-triangle"></i> {{ servicesError }}
        <span class="block mt-1 text-sm">无法完成解析，请手动选择推送模式。</span>
      </div>
      <div v-else-if="services.length === 0" class="alert alert-info mb-3">
        <i class="fas fa-info-circle"></i>
        未从 <code class="text-xs">{{ dockerfileLabel }}</code> 识别到多阶段服务，建议选用<strong>单服务</strong>模式。
      </div>
      <div v-else class="alert alert-warning alert-sm mb-3">
        <i class="fas fa-info-circle"></i>
        已从 <code class="text-xs">{{ dockerfileLabel }}</code> 识别到
        {{ services.length }} 个服务（{{ serviceNamesPreview }}），建议选用<strong>多服务</strong>模式。
      </div>

      <div class="mb-3">
        <label class="block text-sm font-medium text-slate-700 mb-2">
          <strong>推送模式</strong>
          <span class="text-red-500">*</span>
          <span class="ml-1 font-normal text-slate-500">（可修改自动识别结果）</span>
        </label>
        <div
          class="pipeline-webhook-strategy pipeline-push-mode-strategy"
          role="group"
          aria-label="推送模式"
        >
          <input
            type="radio"
            class="btn-check"
            id="create-mode-single"
            value="single"
            v-model="formData.push_mode"
            @change="onPushModePick"
          />
          <label class="pipeline-webhook-strategy__option" for="create-mode-single">
            <i class="fas fa-cube"></i>
            单服务模式
            <small>一个镜像对应整仓构建</small>
          </label>

          <input
            type="radio"
            class="btn-check"
            id="create-mode-multi"
            value="multi"
            v-model="formData.push_mode"
            @change="onPushModePick"
          />
          <label class="pipeline-webhook-strategy__option" for="create-mode-multi">
            <i class="fas fa-sitemap"></i>
            多服务模式
            <small>按 Dockerfile 阶段拆分镜像</small>
          </label>
        </div>
      </div>

      <div
        v-if="formData.push_mode === 'multi' && services.length > 0"
        class="rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
      >
        <p class="mb-2 text-sm font-medium text-slate-700">将包含的服务（创建后可在配置页调整）</p>
        <ul class="mb-0 list-inside list-disc text-sm text-slate-600">
          <li v-for="svc in services" :key="svc.name">{{ svc.name }}</li>
        </ul>
      </div>
      <p
        v-else-if="formData.push_mode === 'multi' && services.length === 0"
        class="mb-0 text-sm text-slate-500"
      >
        多服务模式下未识别到具体服务，创建后可在配置页加载或手动添加。
      </p>
      <p v-else class="mb-0 text-sm text-slate-500">
        单服务模式下将忽略 Dockerfile 中的多阶段定义（若存在）。
      </p>
    </template>
  </div>
</template>

<script setup>
import { computed, inject } from "vue";

const editor = inject("pipelineEditor");

const {
  formData,
  services,
  servicesError,
  loadingServices,
  scanningDockerfiles,
  wizardServiceAnalysisDone,
  setWizardPushMode,
} = editor;

function onPushModePick() {
  setWizardPushMode(formData.value.push_mode);
}

const analyzing = computed(
  () =>
    loadingServices.value ||
    scanningDockerfiles.value ||
    !wizardServiceAnalysisDone.value
);

const dockerfileLabel = computed(
  () => formData.value.dockerfile_name || "Dockerfile"
);

const serviceNamesPreview = computed(() =>
  services.value
    .map((s) => s.name)
    .slice(0, 5)
    .join("、")
);
</script>

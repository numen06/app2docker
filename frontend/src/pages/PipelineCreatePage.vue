<template>
  <div class="pipeline-create-page">
    <div class="pipeline-create-toolbar mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex min-w-0 items-center gap-3">
        <Button type="button" variant="outline" size="sm" class="shrink-0" @click="goBack">
          <i class="fas fa-arrow-left mr-1"></i> 返回
        </Button>
        <div class="min-w-0">
          <h5 class="mb-0 text-lg font-semibold text-slate-800">新建流水线</h5>
          <p class="mb-0 text-sm text-slate-500">填写基础信息后进入配置页完善 Dockerfile、Webhook 等</p>
        </div>
      </div>
    </div>

    <StepsIndicator
      :steps="wizardSteps"
      :current-step="currentStep"
      :allow-jump-ahead="false"
      @step-click="goToStep"
    />

    <div class="step-content rounded-lg border border-slate-200 bg-white">
      <div v-if="currentStep === 1" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-info-circle text-blue-600"></i> 步骤 1：基本信息
        </h5>
        <PipelineFormEditor section="basic" />
      </div>

      <div v-else-if="currentStep === 2" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-code-branch text-blue-600"></i> 步骤 2：Git 仓库
        </h5>
        <PipelineCreateStepGit />
      </div>

      <div v-else-if="currentStep === 3" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-layer-group text-blue-600"></i> 步骤 3：服务模式
        </h5>
        <p class="mb-3 text-sm text-slate-500">
          系统将根据仓库中的 Dockerfile 自动判断单应用或多阶段（多服务）构建。
        </p>
        <PipelineCreateStepPushMode />
      </div>

      <div v-else-if="currentStep === 4" class="step-panel">
        <h5 class="mb-3">
          <i class="fas fa-check-circle text-green-600"></i> 步骤 4：确认创建
        </h5>
        <dl class="pipeline-create-summary grid gap-3 sm:grid-cols-2">
          <div>
            <dt class="text-xs font-medium text-slate-500">流水线名称</dt>
            <dd class="text-sm text-slate-900">{{ formData.name || "—" }}</dd>
          </div>
          <div>
            <dt class="text-xs font-medium text-slate-500">描述</dt>
            <dd class="text-sm text-slate-900">{{ formData.description || "（无）" }}</dd>
          </div>
          <div class="sm:col-span-2">
            <dt class="text-xs font-medium text-slate-500">Git 仓库</dt>
            <dd class="break-all text-sm text-slate-900">
              {{ summaryGitLabel }}
            </dd>
          </div>
          <div>
            <dt class="text-xs font-medium text-slate-500">分支</dt>
            <dd class="text-sm text-slate-900">
              {{ formData.branch || branchesAndTags.default_branch || "默认分支" }}
            </dd>
          </div>
          <div>
            <dt class="text-xs font-medium text-slate-500">Dockerfile</dt>
            <dd class="text-sm text-slate-900">
              {{ formData.dockerfile_name || "Dockerfile" }}
            </dd>
          </div>
          <div>
            <dt class="text-xs font-medium text-slate-500">推送模式</dt>
            <dd class="text-sm text-slate-900">{{ pushModeSummary }}</dd>
          </div>
          <div v-if="formData.push_mode === 'multi' && services.length" class="sm:col-span-2">
            <dt class="text-xs font-medium text-slate-500">识别到的服务</dt>
            <dd class="text-sm text-slate-900">
              {{ services.map((s) => s.name).join("、") }}
            </dd>
          </div>
        </dl>
        <p class="mt-4 text-sm text-slate-500">
          创建后将使用项目 Dockerfile 与默认标签 latest，可在配置页继续调整镜像、Webhook 等。
        </p>
      </div>
    </div>

    <div class="step-nav">
      <Button
        v-if="currentStep > 1"
        type="button"
        variant="outline"
        size="sm"
        :disabled="saving || stepTransitioning"
        @click="prevStep"
      >
        <i class="fas fa-arrow-left mr-1"></i> 上一步
      </Button>
      <span v-else></span>

      <Button
        v-if="currentStep < 4"
        type="button"
        size="sm"
        :disabled="!canProceed || stepTransitioning"
        @click="nextStep"
      >
        <span v-if="stepTransitioning" class="fas fa-spinner fa-spin mr-1"></span>
        下一步 <i v-if="!stepTransitioning" class="fas fa-arrow-right ml-1"></i>
      </Button>
      <Button
        v-else
        type="button"
        size="sm"
        :disabled="saving"
        @click="onCreate"
      >
        <span v-if="saving" class="fas fa-spinner fa-spin mr-1"></span>
        <i v-else class="fas fa-plus mr-1"></i>
        {{ saving ? "创建中…" : "创建流水线" }}
      </Button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, provide, ref } from "vue";
import { useRouter } from "vue-router";
import Button from "@/components/ui/button/Button.vue";
import StepsIndicator from "@/components/common/StepsIndicator.vue";
import PipelineFormEditor from "@/components/pipeline/PipelineFormEditor.vue";
import PipelineCreateStepGit from "@/components/pipeline/PipelineCreateStepGit.vue";
import PipelineCreateStepPushMode from "@/components/pipeline/PipelineCreateStepPushMode.vue";
import { usePipelineEditor } from "@/composables/usePipelineEditor";

const router = useRouter();
const currentStep = ref(1);
const stepTransitioning = ref(false);

const wizardSteps = [
  { num: 1, label: "基本信息" },
  { num: 2, label: "Git 仓库" },
  { num: 3, label: "服务模式" },
  { num: 4, label: "确认创建" },
];

const editor = usePipelineEditor({
  onSaved: (pipelineId) => {
    if (!pipelineId) return;
    router.push({
      name: "pipeline-detail",
      params: { pipelineId },
      query: { created: "1", tab: "basic" },
    });
  },
});

provide("pipelineEditor", editor);

const {
  formData,
  gitSources,
  branchesAndTags,
  services,
  saving,
  wizardServiceAnalysisDone,
  wizardForceSingleMode,
  initCreateForm,
  createPipelineMinimal,
  analyzeDockerfileForWizard,
} = editor;

const summaryGitLabel = computed(() => {
  if (formData.value.source_id) {
    const src = gitSources.value.find(
      (s) => s.source_id === formData.value.source_id
    );
    if (src) return `${src.name} (${src.git_url})`;
  }
  return formData.value.git_url?.trim() || "—";
});

const pushModeSummary = computed(() => {
  if (formData.value.push_mode === "single") {
    return services.value.length > 0 && wizardForceSingleMode.value
      ? "单服务（已忽略 Dockerfile 多阶段解析）"
      : "单服务 / 单应用";
  }
  return `多服务（${services.value.length} 个阶段）`;
});

const canProceedStep1 = computed(() => Boolean(formData.value.name?.trim()));

const canProceedStep2 = computed(
  () =>
    Boolean(formData.value.source_id) ||
    Boolean(formData.value.git_url?.trim())
);

const canProceedStep3 = computed(
  () =>
    wizardServiceAnalysisDone.value &&
    (formData.value.push_mode === "single" ||
      formData.value.push_mode === "multi")
);

const canProceed = computed(() => {
  if (currentStep.value === 1) return canProceedStep1.value;
  if (currentStep.value === 2) return canProceedStep2.value;
  if (currentStep.value === 3) return canProceedStep3.value;
  return true;
});

function goBack() {
  router.push("/app/pipeline");
}

function goToStep(num) {
  if (num > currentStep.value) return;
  currentStep.value = num;
}

async function nextStep() {
  if (!canProceed.value || currentStep.value >= 4 || stepTransitioning.value) {
    return;
  }

  if (currentStep.value === 2) {
    stepTransitioning.value = true;
    try {
      await analyzeDockerfileForWizard();
    } finally {
      stepTransitioning.value = false;
    }
  }

  currentStep.value += 1;
}

function prevStep() {
  if (currentStep.value === 3) {
    wizardServiceAnalysisDone.value = false;
  }
  if (currentStep.value > 1) currentStep.value -= 1;
}

async function onCreate() {
  await createPipelineMinimal();
}

onMounted(() => {
  initCreateForm();
});
</script>

<style scoped>
.pipeline-create-page {
  max-width: 56rem;
  margin-inline: auto;
}

.pipeline-create-summary dt {
  margin-bottom: 0.125rem;
}
</style>

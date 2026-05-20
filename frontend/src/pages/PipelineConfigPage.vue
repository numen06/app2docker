<template>
  <div class="pipeline-config-page">
    <div class="pipeline-config-toolbar">
      <div class="pipeline-config-toolbar__main">
        <Button type="button" variant="outline" size="sm" class="shrink-0" @click="goBack">
          <i class="fas fa-arrow-left mr-1"></i> 返回
        </Button>
        <div class="pipeline-config-toolbar__meta min-w-0">
          <p class="pipeline-config-toolbar__name">{{ pageTitle }}</p>
          <p v-if="isEdit" class="pipeline-config-toolbar__hint">编辑配置 · 修改后请点击保存</p>
          <p v-else class="pipeline-config-toolbar__hint">新建流水线 · 填写后保存</p>
        </div>
        <div v-if="isEdit && pipeline" class="flex shrink-0 flex-wrap gap-1">
          <span v-if="pipeline.enabled" class="badge bg-success">已启用</span>
          <span v-else class="badge bg-secondary">已禁用</span>
        </div>
      </div>
      <div v-if="pageState === 'ready'" class="pipeline-config-toolbar__actions">
        <Button type="button" variant="outline" size="sm" :disabled="saving" @click="goBack">
          取消
        </Button>
        <Button type="button" size="sm" :disabled="saving" @click="onSave">
          <span v-if="saving" class="fas fa-spinner fa-spin mr-1"></span>
          <i v-else class="fas fa-save mr-1"></i>
          {{ saving ? "保存中…" : "保存" }}
        </Button>
      </div>
    </div>

    <p v-if="pageState === 'error'" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>

    <div
      v-else-if="pageState === 'loading'"
      class="pipeline-config-body pipeline-config-body--loading"
    >
      <p class="text-slate-500">
        <i class="fas fa-spinner fa-spin mr-1"></i> 加载配置…
      </p>
    </div>

    <div v-else class="pipeline-config-body">
      <ul class="nav nav-tabs pipeline-config-tabs" role="tablist">
        <li
          v-for="t in PIPELINE_CONFIG_TABS"
          :key="t.key"
          class="nav-item"
          role="presentation"
        >
          <button
            type="button"
            class="nav-link"
            :class="{ active: activeSection === t.key }"
            @click="setSection(t.key)"
          >
            <i v-if="t.icon" :class="t.icon" class="mr-1"></i>{{ t.label }}
          </button>
        </li>
      </ul>

      <PipelineFormEditor :section="activeSection" />

      <div class="pipeline-config-footer">
        <Button type="button" variant="outline" size="sm" :disabled="saving" @click="goBack">
          取消
        </Button>
        <Button type="button" size="sm" :disabled="saving" @click="onSave">
          <span v-if="saving" class="fas fa-spinner fa-spin mr-1"></span>
          <i v-else class="fas fa-save mr-1"></i>
          {{ saving ? "保存中…" : "保存" }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import Button from "@/components/ui/button/Button.vue";
import PipelineFormEditor from "@/components/pipeline/PipelineFormEditor.vue";
import {
  PIPELINE_CONFIG_TABS,
  normalizePipelineConfigTab,
} from "@/constants/pipelineDetailTabs";
import { usePipelineEditor } from "@/composables/usePipelineEditor";

const props = defineProps({
  mode: {
    type: String,
    default: "edit",
    validator: (v) => v === "create" || v === "edit",
  },
});

const route = useRoute();
const router = useRouter();

const isEdit = computed(() => props.mode === "edit");
const pipelineId = computed(() => String(route.params.pipelineId || ""));

const pageState = ref("loading");
const errorMessage = ref("");

const activeSection = computed({
  get() {
    const q = route.query.tab;
    const raw = typeof q === "string" ? q : "basic";
    return normalizePipelineConfigTab(raw);
  },
  set(tab) {
    const name = isEdit.value ? "pipeline-detail" : "pipeline-create";
    const params = isEdit.value ? { pipelineId: pipelineId.value } : {};
    router.replace({
      name,
      params,
      query: { tab: normalizePipelineConfigTab(tab) },
    });
  },
});

function setSection(tab) {
  activeSection.value = tab;
}

const editor = usePipelineEditor({
  onSaved: () => {
    router.push("/app/pipeline");
  },
});

provide("pipelineEditor", editor);

const { saving, initCreateForm, loadPipelineForEdit, editingPipeline } = editor;

const pipeline = computed(() => editingPipeline.value);

const pageTitle = computed(() => {
  if (!isEdit.value) return "新建流水线";
  return pipeline.value?.name || "流水线配置";
});

function goBack() {
  router.push("/app/pipeline");
}

async function onSave() {
  await editor.savePipeline();
}

function syncLegacyTabQuery() {
  const raw = route.query.tab;
  if (typeof raw !== "string" || !raw) return;
  const normalized = normalizePipelineConfigTab(raw);
  if (normalized === raw) return;
  setSection(normalized);
}

async function bootstrap() {
  pageState.value = "loading";
  errorMessage.value = "";
  syncLegacyTabQuery();

  if (!isEdit.value) {
    initCreateForm();
    pageState.value = "ready";
    return;
  }

  if (!pipelineId.value) {
    errorMessage.value = "缺少流水线 ID";
    pageState.value = "error";
    return;
  }

  const ok = await loadPipelineForEdit(pipelineId.value);
  if (!ok) {
    errorMessage.value = "无法加载流水线配置";
    pageState.value = "error";
    return;
  }
  pageState.value = "ready";
}

onMounted(() => {
  bootstrap();
});

watch(pipelineId, () => {
  if (isEdit.value) bootstrap();
});

watch(
  () => route.query.tab,
  () => {
    syncLegacyTabQuery();
  }
);
</script>

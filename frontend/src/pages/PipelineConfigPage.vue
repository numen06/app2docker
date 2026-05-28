<template>
  <div class="pipeline-config-page">
    <div class="pipeline-config-toolbar">
      <div class="pipeline-config-toolbar__main">
        <Button type="button" variant="outline" size="sm" class="shrink-0" @click="goBack">
          <AppIcon  name="arrow-left" class="mr-1" /> 返回
        </Button>
        <div class="pipeline-config-toolbar__meta min-w-0">
          <p class="pipeline-config-toolbar__name">{{ pageTitle }}</p>
          <p class="pipeline-config-toolbar__hint">编辑配置 · 修改后请点击保存</p>
        </div>
        <div v-if="pipeline" class="flex shrink-0 flex-wrap gap-1">
          <span v-if="pipeline.enabled" class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-green-600 text-white">已启用</span>
          <span v-else class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-slate-500 text-white">已禁用</span>
        </div>
      </div>
      <div v-if="pageState === 'ready'" class="pipeline-config-toolbar__actions">
        <Button
          type="button"
          variant="outline"
          size="sm"
          @click="goToHistory"
        >
          <AppIcon  name="history" class="mr-1" /> 历史构建
        </Button>
        <Button type="button" variant="outline" size="sm" :disabled="saving" @click="goBack">
          取消
        </Button>
        <Button type="button" size="sm" :disabled="saving" @click="onSave">
          <AppIcon v-if="saving"  name="spinner" class="mr-1" spin />
          <AppIcon v-else  name="save" class="mr-1" />
          {{ saving ?"保存中…" :"保存" }}
        </Button>
      </div>
    </div>

    <div
      v-if="showCreatedBanner"
      class="mb-3 flex items-start justify-between gap-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800"
    >
      <span>
        <AppIcon  name="check-circle" class="mr-1" />
        流水线已创建，请继续完善 Dockerfile、多服务与 Webhook 等配置。
      </span>
      <button
        type="button"
        class="shrink-0 rounded p-1 text-green-700 hover:bg-green-100"
        aria-label="关闭提示"
        @click="dismissCreatedBanner"
      >
        <AppIcon  name="times" />
      </button>
    </div>

    <p v-if="pageState === 'error'" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>

    <div
      v-else-if="pageState === 'loading'"
      class="pipeline-config-body pipeline-config-body--loading"
    >
      <p class="text-slate-500">
        <AppIcon  name="spinner" class="mr-1" spin /> 加载配置…
      </p>
    </div>

    <div v-else class="pipeline-config-body">
      <ul class="pipeline-config-tabs" role="tablist">
        <li
          v-for="t in PIPELINE_CONFIG_TABS"
          :key="t.key"
          class="pipeline-config-tabs__item"
          role="presentation"
        >
          <button
            type="button"
            class="pipeline-config-tab"
            :class="{ 'is-active': activeSection === t.key }"
            @click="setSection(t.key)"
          >
            <AppIcon v-if="t.icon" :name="t.icon" class="mr-1" />{{ t.label }}
          </button>
        </li>
      </ul>

      <PipelineFormEditor :section="activeSection" />

      <div class="pipeline-config-footer">
        <Button type="button" variant="outline" size="sm" :disabled="saving" @click="goBack">
          取消
        </Button>
        <Button type="button" size="sm" :disabled="saving" @click="onSave">
          <AppIcon v-if="saving"  name="spinner" class="mr-1" spin />
          <AppIcon v-else  name="save" class="mr-1" />
          {{ saving ?"保存中…" :"保存" }}
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
import { goToPipelineList } from "@/utils/pipelineNavigation.js";

const route = useRoute();
const router = useRouter();

const pipelineId = computed(() => String(route.params.pipelineId ||""));

const pageState = ref("loading");
const errorMessage = ref("");
const createdBannerDismissed = ref(false);

const showCreatedBanner = computed(
  () => route.query.created ==="1" && !createdBannerDismissed.value
);

const activeSection = computed({
  get() {
    const q = route.query.tab;
    const raw = typeof q ==="string" ? q :"basic";
    return normalizePipelineConfigTab(raw);
  },
  set(tab) {
    const query = { tab: normalizePipelineConfigTab(tab) };
    if (route.query.created ==="1") {
      query.created ="1";
    }
    router.replace({
      name:"pipeline-detail",
      params: { pipelineId: pipelineId.value },
      query,
    });
  },
});

function setSection(tab) {
  activeSection.value = tab;
}

const editor = usePipelineEditor({
  onSaved: (id) => {
    if (id) {
      router.replace({
        name:"pipeline-detail",
        params: { pipelineId: id },
        query: { tab: activeSection.value },
      });
    }
  },
});

provide("pipelineEditor", editor);

const { saving, loadPipelineForEdit, editingPipeline } = editor;

const pipeline = computed(() => editingPipeline.value);

const pageTitle = computed(() => pipeline.value?.name ||"流水线配置");

function goBack() {
  goToPipelineList(router);
}

function goToHistory() {
  if (!pipelineId.value) return;
  router.push({
    name:"pipeline-history",
    params: { pipelineId: pipelineId.value },
  });
}

function dismissCreatedBanner() {
  createdBannerDismissed.value = true;
  const { created, ...rest } = { ...route.query };
  router.replace({
    name:"pipeline-detail",
    params: { pipelineId: pipelineId.value },
    query: rest,
  });
}

async function onSave() {
  await editor.savePipeline();
}

function syncLegacyTabQuery() {
  const raw = route.query.tab;
  if (typeof raw !=="string" || !raw) return;
  const normalized = normalizePipelineConfigTab(raw);
  if (normalized === raw) return;
  setSection(normalized);
}

async function loadPage() {
  pageState.value ="loading";
  errorMessage.value ="";
  syncLegacyTabQuery();

  if (!pipelineId.value) {
    errorMessage.value ="缺少流水线 ID";
    pageState.value ="error";
    return;
  }

  const ok = await loadPipelineForEdit(pipelineId.value);
  if (!ok) {
    errorMessage.value ="无法加载流水线配置";
    pageState.value ="error";
    return;
  }
  pageState.value ="ready";
}

onMounted(() => {
  loadPage();
});

watch(pipelineId, () => {
  loadPage();
});

watch(
  () => route.query.tab,
  () => {
    syncLegacyTabQuery();
  }
);
</script>

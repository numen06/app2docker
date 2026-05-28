<template>
  <div class="pipeline-history-page">
    <div class="pipeline-config-toolbar">
      <div class="pipeline-config-toolbar__main">
        <Button type="button" variant="outline" size="sm" class="shrink-0" @click="goBack">
          <AppIcon  name="arrow-left" class="mr-1" /> 返回
        </Button>
        <div class="pipeline-config-toolbar__meta min-w-0">
          <p class="pipeline-config-toolbar__name">{{ pageTitle }}</p>
          <p class="pipeline-config-toolbar__hint">构建任务记录与日志</p>
        </div>
        <div v-if="pipeline" class="flex shrink-0 flex-wrap gap-1">
          <span v-if="pipeline.enabled" class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-green-600 text-white">已启用</span>
          <span v-else class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-slate-500 text-white">已禁用</span>
        </div>
      </div>
      <div v-if="pageState === 'ready'" class="pipeline-config-toolbar__actions">
        <Button type="button" variant="outline" size="sm" @click="goToConfig">
          <AppIcon  name="cog" class="mr-1" /> 配置流水线
        </Button>
      </div>
    </div>

    <p
      v-if="pageState === 'error'"
      class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
    >
      {{ errorMessage }}
    </p>

    <div
      v-else-if="pageState === 'loading'"
      class="pipeline-config-body pipeline-config-body--loading"
    >
      <p class="text-slate-500">
        <AppIcon  name="spinner" class="mr-1" spin /> 加载中…
      </p>
    </div>

    <div v-else class="pipeline-config-body">
      <PipelineHistoryTab />
    </div>

    <BuildTaskLogModal :controller="buildTaskLogs" />
  </div>
</template>

<script setup>
import { computed, onMounted, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";
import Button from "@/components/ui/button/Button.vue";
import PipelineHistoryTab from "@/components/pipeline/detail/PipelineHistoryTab.vue";
import BuildTaskLogModal from "@/components/BuildTaskLogModal.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { useBuildTaskLogs } from "@/composables/useBuildTaskLogs";

const route = useRoute();
const router = useRouter();

const pipelineId = computed(() => String(route.params.pipelineId ||""));
const pipeline = ref(null);
const pageState = ref("loading");
const errorMessage = ref("");

const buildTaskLogs = useBuildTaskLogs();

const pageTitle = computed(() => {
  const name = pipeline.value?.name;
  return name ? `历史构建 · ${name}` :"历史构建";
});

provide(PIPELINE_DETAIL_KEY, {
  pipeline,
  loading: computed(() => pageState.value ==="loading"),
  error: errorMessage,
  refresh: loadPage,
  setTab: () => {},
  viewTaskLogs: buildTaskLogs.viewTaskLogs,
  viewingLogs: buildTaskLogs.viewingLogs,
});

function goBack() {
  router.push("/app/pipeline");
}

function goToConfig() {
  if (!pipelineId.value) return;
  router.push({
    name:"pipeline-detail",
    params: { pipelineId: pipelineId.value },
    query: { tab:"basic" },
  });
}

async function loadPage() {
  pageState.value ="loading";
  errorMessage.value ="";

  if (!pipelineId.value) {
    errorMessage.value ="缺少流水线 ID";
    pageState.value ="error";
    return;
  }

  try {
    const res = await axios.get(`/api/pipelines/${pipelineId.value}`);
    pipeline.value = res.data;
    pageState.value ="ready";
  } catch (e) {
    errorMessage.value =
      e.response?.data?.detail || e.response?.data?.message ||"无法加载流水线";
    pipeline.value = null;
    pageState.value ="error";
  }
}

onMounted(() => {
  loadPage();
});

watch(pipelineId, () => {
  loadPage();
});
</script>

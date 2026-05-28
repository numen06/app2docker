<template>
  <div v-if="pipeline" class="pipeline-overview-tab space-y-4">
    <div class="flex flex-wrap gap-2">
      <span v-if="pipeline.enabled" class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-green-600 text-white">已启用</span>
      <span v-else class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-slate-500 text-white">已禁用</span>
      <span class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium" :class="getProjectTypeBadgeClass(pipeline.project_type)">
        {{ getProjectTypeLabel(pipeline.project_type) }}
      </span>
      <span v-if="pipeline.webhook_token" class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-blue-600 text-white">Webhook</span>
      <span v-if="pipeline.tag_build_enabled" class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-amber-500 text-white">Tag 构建</span>
      <span v-if="pipeline.cron_expression" class="inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium bg-sky-500 text-white">定时</span>
    </div>

    <div v-if="pipeline.description" class="text-slate-600">
      {{ pipeline.description }}
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      <div class="rounded-lg border border-slate-200 p-3">
        <h6 class="mb-2 text-slate-700"><AppIcon  name="code-branch" class="mr-1" /> Git</h6>
        <p class="mb-0 font-mono text-sm break-all">{{ pipeline.git_url }}</p>
        <p class="mb-0 mt-1 text-sm text-slate-500">分支: {{ pipeline.branch ||"默认" }}</p>
      </div>
      <div class="rounded-lg border border-slate-200 p-3">
        <h6 class="mb-2 text-slate-700"><AppIcon  name="docker" class="mr-1" /> 镜像</h6>
        <p class="mb-0 font-mono text-sm">{{ pipeline.image_name }}:{{ pipeline.tag }}</p>
        <p
          v-if="pipeline.selected_services?.length"
          class="mb-0 mt-1 text-sm text-slate-500"
        >
          {{ pipeline.selected_services.length }} 个服务 ·
          {{ pipeline.push_mode ==="multi" ?"多阶段" :"单一" }}推送
        </p>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-3">
      <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 text-center">
        <div class="text-xs text-slate-500">触发次数</div>
        <div class="text-xl font-semibold text-blue-600">{{ pipeline.trigger_count || 0 }}</div>
      </div>
      <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 text-center">
        <div class="text-xs text-slate-500">成功</div>
        <div class="text-xl font-semibold text-green-600">{{ pipeline.success_count || 0 }}</div>
      </div>
      <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 text-center">
        <div class="text-xs text-slate-500">失败</div>
        <div class="text-xl font-semibold text-red-600">{{ pipeline.failed_count || 0 }}</div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, inject } from "vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import {
  getProjectTypeBadgeClass,
  getProjectTypeLabel,
} from "@/utils/projectTypes.js";

const detail = inject(PIPELINE_DETAIL_KEY);
const pipeline = computed(() => detail.pipeline.value);
</script>

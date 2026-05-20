<template>
  <div class="pipeline-settings-tab max-w-lg">
    <div class="rounded-lg border border-red-200 bg-red-50/50 p-4">
      <h6 class="mb-2 text-red-700">
        <i class="fas fa-exclamation-triangle mr-1"></i> 危险操作
      </h6>
      <p class="mb-3 text-sm text-slate-600">
        删除后将无法恢复，相关构建历史可能一并清理。
      </p>
      <Button variant="destructive" size="sm" @click="deletePipeline">
        <i class="fas fa-trash mr-1"></i> 删除流水线
      </Button>
    </div>
  </div>
</template>

<script setup>
import { inject } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import Button from "@/components/ui/button/Button.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { goToPipelineList } from "@/utils/pipelineNavigation.js";

const detail = inject(PIPELINE_DETAIL_KEY);
const router = useRouter();

async function deletePipeline() {
  const p = detail.pipeline.value;
  if (!p) return;
  if (!confirm(`确定要删除流水线「${p.name}」吗？`)) return;
  try {
    await axios.delete(`/api/pipelines/${p.pipeline_id}`);
    await goToPipelineList(router);
    alert("流水线已删除");
  } catch (error) {
    alert(error.response?.data?.detail || "删除失败");
  }
}
</script>

<template>
  <div class="pipeline-settings-tab max-w-lg">
    <div class="rounded-lg border border-red-200 bg-red-50/50 p-4">
      <h6 class="mb-2 text-red-700">
        <AppIcon  name="exclamation-triangle" class="mr-1" /> 危险操作
      </h6>
      <p class="mb-3 text-sm text-slate-600">
        删除后将无法恢复，相关构建历史可能一并清理。
      </p>
      <Button variant="destructive" size="sm" @click="deletePipeline">
        <AppIcon  name="trash" class="mr-1" /> 删除流水线
      </Button>
    </div>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

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
  if (!(await showConfirm({ message: `确定要删除流水线「${p.name}」吗？`, danger: true }))) return;
  try {
    await axios.delete(`/api/pipelines/${p.pipeline_id}`);
    await goToPipelineList(router);
    toastSuccess("流水线已删除");
  } catch (error) {
    toastApiError(error,"删除失败");
  }
}
</script>

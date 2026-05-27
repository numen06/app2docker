<template>
  <div class="pipeline-history-tab">
    <div class="mb-3 grid grid-cols-1 gap-3 md:grid-cols-3">
      <div>
        <label class="mb-1 block text-xs font-medium text-slate-600">触发来源</label>
        <select
          v-model="historyFilter.trigger_source"
          class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
          @change="resetAndLoad"
        >
          <option value="">全部</option>
          <option value="webhook">Webhook</option>
          <option value="manual">手动</option>
          <option value="cron">定时</option>
        </select>
      </div>
      <div>
        <label class="mb-1 block text-xs font-medium text-slate-600">任务状态</label>
        <select
          v-model="historyFilter.status"
          class="flex h-9 w-full rounded-md border border-slate-200 px-3 py-1 text-sm"
          @change="resetAndLoad"
        >
          <option value="">全部</option>
          <option value="pending">等待中</option>
          <option value="running">进行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
      </div>
      <div class="flex items-end">
        <Button variant="outline" size="sm" @click="loadHistory()">
          <AppIcon  name="sync-alt" /> 刷新
        </Button>
      </div>
    </div>

    <div v-if="historyLoading" class="py-8 text-center">
      <AppIcon  name="spinner" spin /> 加载中...
    </div>
    <div v-else-if="historyTasks.length === 0" class="py-8 text-center text-slate-500">
      <p class="mb-0">暂无历史构建记录</p>
    </div>
    <div v-else class="overflow-x-auto">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th>任务ID</th>
            <th>来源</th>
            <th>状态</th>
            <th>镜像</th>
            <th>触发时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in historyTasks" :key="task.task_id">
            <td><code>{{ task.task_id?.substring(0, 8) }}</code></td>
            <td>{{ task.trigger_source ||"-" }}</td>
            <td>{{ task.status }}</td>
            <td class="font-mono text-xs">{{ task.image }}:{{ task.tag }}</td>
            <td class="text-xs text-slate-500">{{ formatDateTime(task.triggered_at) }}</td>
            <td>
              <Button
                v-if="task.task_id && task.status !== 'deleted'"
                variant="outline"
                size="sm"
                @click="detail.viewTaskLogs(task.task_id, task)"
              >
                日志
              </Button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="historyPagination.total > 0"
      class="mt-3 flex items-center justify-between"
    >
      <small class="text-slate-500">
        共 {{ historyPagination.total }} 条 · 第 {{ historyPagination.currentPage }} /
        {{ totalPages }} 页
      </small>
      <div class="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          :disabled="historyPagination.currentPage <= 1"
          @click="changeHistoryPage(historyPagination.currentPage - 1)"
        >
          上一页
        </Button>
        <Button
          variant="outline"
          size="sm"
          :disabled="historyPagination.currentPage >= totalPages"
          @click="changeHistoryPage(historyPagination.currentPage + 1)"
        >
          下一页
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

import { computed, inject, onMounted, ref, watch } from "vue";
import axios from "axios";
import Button from "@/components/ui/button/Button.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { formatDateTime } from "@/utils/pipelineDisplay";

const detail = inject(PIPELINE_DETAIL_KEY);
const historyTasks = ref([]);
const historyLoading = ref(false);
const historyFilter = ref({ trigger_source:"", status:"" });
const historyPagination = ref({ currentPage: 1, pageSize: 10, total: 0 });

const totalPages = computed(() =>
  Math.max(
    1,
    Math.ceil(historyPagination.value.total / historyPagination.value.pageSize)
  )
);

function resetAndLoad() {
  historyPagination.value.currentPage = 1;
  loadHistory();
}

async function loadHistory(page = null) {
  const pipeline = detail.pipeline.value;
  if (!pipeline?.pipeline_id) return;
  if (page !== null) historyPagination.value.currentPage = page;
  historyLoading.value = true;
  try {
    const params = new URLSearchParams();
    if (historyFilter.value.trigger_source) {
      params.append("trigger_source", historyFilter.value.trigger_source);
    }
    if (historyFilter.value.status) {
      params.append("status", historyFilter.value.status);
    }
    params.append("page", String(historyPagination.value.currentPage));
    params.append("page_size", String(historyPagination.value.pageSize));
    const res = await axios.get(
      `/api/pipelines/${pipeline.pipeline_id}/tasks?${params}`
    );
    historyTasks.value = res.data?.tasks || (Array.isArray(res.data) ? res.data : []);
    historyPagination.value.total = res.data?.total ?? historyTasks.value.length;
  } catch (e) {
    toastApiError(e,"加载历史失败");
    historyTasks.value = [];
  } finally {
    historyLoading.value = false;
  }
}

function changeHistoryPage(page) {
  if (page < 1 || page > totalPages.value) return;
  loadHistory(page);
}

onMounted(() => loadHistory());
watch(
  () => detail.pipeline.value?.pipeline_id,
  () => {
    historyPagination.value.currentPage = 1;
    loadHistory();
  }
);
</script>

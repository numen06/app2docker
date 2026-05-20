<template>
  <FormDialog
    :model-value="modelValue"
    :title="`任务日志 - ${task?.image || '未知'}:${task?.tag || 'latest'}`"
    icon="fa-list-alt"
    size="2xl"
    @update:model-value="onClose"
  >
    <div
      v-if="task"
      class="-mt-2 mb-3 rounded-md border px-3 py-2 text-sm"
      :class="headerBannerClass(task.status)"
    >
      <i :class="getStatusIcon(task.status)" class="mr-1"></i>
      {{ getStatusText(task.status) }}
      <Badge v-if="isTaskRunning" class="ml-2">
        <i class="fas fa-spinner fa-spin mr-1"></i> 运行中
      </Badge>
    </div>

    <div class="mb-2 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
      <div class="flex flex-wrap items-center gap-2">
        <Button type="button" variant="outline" size="sm" :disabled="refreshingLogs" @click="refreshLogs">
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': refreshingLogs }"></i> 刷新
        </Button>
        <Button type="button" variant="outline" size="sm" @click="toggleAutoScroll">
          <i class="fas" :class="autoScroll ? 'fa-pause' : 'fa-play'"></i>
          {{ autoScroll ? "暂停滚动" : "自动滚动" }}
        </Button>
        <Button type="button" variant="outline" size="sm" @click="copyLogs">
          <i class="fas fa-copy"></i> 复制
        </Button>
        <Button type="button" variant="outline" size="sm" @click="scrollToTop">到顶</Button>
        <Button type="button" variant="outline" size="sm" @click="scrollToBottom">到底</Button>
        <span v-if="isTaskRunning" class="text-xs text-slate-500">
          <i class="fas fa-info-circle"></i> 正在自动刷新日志...
        </span>
      </div>
      <span class="text-xs text-slate-500">
        任务ID: <code>{{ task?.task_id?.substring(0, 8) || "未知" }}</code>
      </span>
    </div>

    <div
      v-if="task && ['failed', 'completed', 'stopped'].includes(task.status)"
      class="mb-3"
    >
      <Button
        type="button"
        variant="outline"
        size="sm"
        class="w-full justify-between"
        @click="showTaskSummary = !showTaskSummary"
      >
        <span><i :class="getStatusIcon(task.status)" class="mr-2"></i><strong>{{ getStatusText(task.status) }}</strong></span>
        <i class="fas" :class="showTaskSummary ? 'fa-chevron-up' : 'fa-chevron-down'"></i>
      </Button>
      <div v-if="showTaskSummary" class="mt-2 rounded-md border p-3 text-sm" :class="summaryBoxClass(task.status)">
        <div v-if="task.status === 'failed' && task.error" class="mb-3">
          <strong>错误信息：</strong>
          <pre class="mt-1 max-h-[150px] overflow-y-auto rounded bg-slate-900 p-2 text-xs text-slate-100">{{ task.error }}</pre>
        </div>
        <div v-if="task.status === 'completed'" class="space-y-1 text-slate-700">
          <div><strong>创建时间：</strong>{{ formatTime(task.created_at) }}</div>
          <div v-if="task.completed_at"><strong>完成时间：</strong>{{ formatTime(task.completed_at) }}</div>
          <div v-if="task.completed_at"><strong>耗时：</strong>{{ calculateDuration(task.created_at, task.completed_at) }}</div>
        </div>
        <div v-if="task.status === 'stopped'" class="space-y-1 text-slate-700">
          <div><strong>创建时间：</strong>{{ formatTime(task.created_at) }}</div>
          <div v-if="task.completed_at"><strong>停止时间：</strong>{{ formatTime(task.completed_at) }}</div>
        </div>
      </div>
    </div>

    <pre
      ref="logContainer"
      class="max-h-[60vh] min-h-[300px] overflow-auto rounded-md bg-slate-900 p-3 font-mono text-sm leading-relaxed text-slate-100"
      style="white-space: pre-wrap; word-wrap: break-word"
    >{{ logs || "暂无日志" }}</pre>

    <template #footer>
      <Button type="button" variant="secondary" size="sm" @click="close">关闭</Button>
    </template>
  </FormDialog>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from "vue";
import axios from "axios";
import { copyToClipboard } from "../utils/clipboard.js";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Badge from "@/components/ui/badge/Badge.vue";
import Button from "@/components/ui/button/Button.vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  task: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue", "task-status-updated"]);

const logs = ref("");
const logContainer = ref(null);
const logPollingInterval = ref(null);
const autoScroll = ref(true);
const refreshingLogs = ref(false);
const showTaskSummary = ref(false);

const isTaskRunning = computed(() => {
  if (!props.task) return false;
  return props.task.status === "running" || props.task.status === "pending";
});

function headerBannerClass(status) {
  if (status === "failed") return "border-red-200 bg-red-50 text-red-800";
  if (status === "completed") return "border-green-200 bg-green-50 text-green-800";
  if (status === "stopped") return "border-amber-200 bg-amber-50 text-amber-900";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function summaryBoxClass(status) {
  if (status === "failed") return "border-red-200 bg-red-50/50";
  if (status === "completed") return "border-green-200 bg-green-50/50";
  if (status === "stopped") return "border-amber-200 bg-amber-50/50";
  return "border-slate-200 bg-slate-50";
}

function scrollToTop() {
  if (logContainer.value) {
    autoScroll.value = false;
    nextTick(() => {
      if (logContainer.value) logContainer.value.scrollTop = 0;
    });
  }
}

function scrollToBottom() {
  if (logContainer.value) {
    nextTick(() => {
      if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight;
    });
  }
}

async function fetchTaskLogs(taskId, silent = false) {
  if (!silent) refreshingLogs.value = true;
  try {
    const res = await axios.get(`/api/build-tasks/${taskId}/logs`);
    const oldLength = logs.value.length;
    logs.value = typeof res.data === "string" ? res.data || "暂无日志" : JSON.stringify(res.data, null, 2);
    if (logs.value.length > oldLength && autoScroll.value) {
      setTimeout(() => scrollToBottom(), 50);
    }
  } catch (err) {
    const errorMsg = err.response?.data?.detail || err.response?.data?.error || err.message || "未知错误";
    logs.value = `加载日志失败: ${errorMsg}`;
  } finally {
    refreshingLogs.value = false;
  }
}

async function refreshLogs() {
  if (!props.task) return;
  await fetchTaskLogs(props.task.task_id, false);
}

function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value;
  if (autoScroll.value) scrollToBottom();
}

async function copyLogs() {
  const success = await copyToClipboard(logs.value);
  alert(success ? "日志已复制到剪贴板" : "复制失败，请手动选择文本复制");
}

function startLogPolling(taskId) {
  if (logPollingInterval.value) clearInterval(logPollingInterval.value);
  if (isTaskRunning.value) {
    logPollingInterval.value = setInterval(async () => {
      if (props.modelValue && props.task) {
        await fetchTaskLogs(taskId, true);
        try {
          const res = await axios.get(`/api/build-tasks/${taskId}`);
          if (res.data?.status) {
            emit("task-status-updated", res.data.status);
            if (res.data.status === "completed" || res.data.status === "failed") stopLogPolling();
          }
        } catch (err) {
          console.error("获取任务状态失败:", err);
        }
      } else {
        stopLogPolling();
      }
    }, 2000);
  }
}

function stopLogPolling() {
  if (logPollingInterval.value) {
    clearInterval(logPollingInterval.value);
    logPollingInterval.value = null;
  }
}

function lockBodyScroll() {
  document.body.style.overflow = "hidden";
}
function unlockBodyScroll() {
  document.body.style.overflow = "";
}

function onClose(v) {
  if (!v) close();
}

function close() {
  stopLogPolling();
  unlockBodyScroll();
  emit("update:modelValue", false);
}

function getStatusIcon(status) {
  if (status === "failed") return "fas fa-times-circle";
  if (status === "completed") return "fas fa-check-circle";
  if (status === "stopped") return "fas fa-stop-circle";
  if (status === "running") return "fas fa-spinner fa-spin";
  if (status === "pending") return "fas fa-clock";
  return "fas fa-info-circle";
}

function getStatusText(status) {
  const map = {
    failed: "任务失败",
    completed: "任务成功",
    stopped: "任务已停止",
    running: "任务进行中",
    pending: "任务等待中",
  };
  return map[status] || "未知状态";
}

function formatTime(timeStr) {
  if (!timeStr) return "-";
  return new Date(timeStr).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function calculateDuration(startTime, endTime) {
  if (!startTime || !endTime) return "-";
  const diff = Math.floor((new Date(endTime) - new Date(startTime)) / 1000);
  const hours = Math.floor(diff / 3600);
  const minutes = Math.floor((diff % 3600) / 60);
  const seconds = diff % 60;
  if (hours > 0) return `${hours}小时${minutes}分钟${seconds}秒`;
  if (minutes > 0) return `${minutes}分钟${seconds}秒`;
  return `${seconds}秒`;
}

function loadLogsIfNeeded() {
  if (props.modelValue && props.task?.task_id) {
    logs.value = "加载中...";
    fetchTaskLogs(props.task.task_id);
    startLogPolling(props.task.task_id);
  } else {
    stopLogPolling();
    if (!props.modelValue) logs.value = "";
    else if (!props.task) logs.value = "任务信息不存在";
    else logs.value = "任务ID不存在";
  }
}

watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      lockBodyScroll();
      loadLogsIfNeeded();
    } else {
      stopLogPolling();
      logs.value = "";
      unlockBodyScroll();
    }
  }
);

watch(
  () => props.task,
  () => {
    if (props.modelValue && props.task) setTimeout(() => loadLogsIfNeeded(), 0);
  },
  { deep: true }
);

watch(
  () => props.task?.status,
  (newStatus) => {
    if (newStatus === "completed" || newStatus === "failed") stopLogPolling();
    else if ((newStatus === "running" || newStatus === "pending") && props.task?.task_id) {
      startLogPolling(props.task.task_id);
    }
  }
);

onUnmounted(() => {
  stopLogPolling();
  unlockBodyScroll();
});
</script>

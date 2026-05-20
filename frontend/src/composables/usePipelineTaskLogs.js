import axios from "axios";
import { computed, nextTick, ref, watch } from "vue";
import { copyToClipboard } from "@/utils/clipboard.js";

export function usePipelineTaskLogs({ onTaskFinished } = {}) {
  const showLogModal = ref(false);
  const selectedTask = ref(null);
  const viewingLogs = ref(null);
  const taskLogs = ref("");
  const logContainer = ref(null);
  const logPollingInterval = ref(null);
  const autoScroll = ref(true);
  const refreshingLogs = ref(false);

  const isLogTaskRunning = computed(() => {
    if (!selectedTask.value) return false;
    const status = selectedTask.value.status;
    return status === "running" || status === "pending";
  });

  function getLogStatusHeaderClass(status) {
    if (status === "failed") return "bg-danger text-white";
    if (status === "completed") return "bg-success text-white";
    if (status === "stopped") return "bg-warning text-dark";
    return "bg-primary text-white";
  }

  function getLogStatusSummaryClass(status) {
    if (status === "failed") return "bg-danger-subtle";
    if (status === "completed") return "bg-success-subtle";
    if (status === "stopped") return "bg-warning-subtle";
    return "";
  }

  function getLogStatusIcon(status) {
    if (status === "failed") return "fas fa-times-circle";
    if (status === "completed") return "fas fa-check-circle";
    if (status === "stopped") return "fas fa-stop-circle";
    if (status === "running") return "fas fa-spinner fa-spin";
    if (status === "pending") return "fas fa-clock";
    return "fas fa-info-circle";
  }

  function getLogStatusText(status) {
    if (status === "failed") return "构建失败";
    if (status === "completed") return "构建成功";
    if (status === "stopped") return "构建已停止";
    if (status === "running") return "构建中";
    if (status === "pending") return "等待中";
    return "未知状态";
  }

  function formatLogTime(time) {
    if (!time) return "未知";
    return new Date(time).toLocaleString("zh-CN");
  }

  function calculateLogDuration(start, end) {
    if (!start || !end) return "未知";
    const duration = Math.floor(
      (new Date(end).getTime() - new Date(start).getTime()) / 1000
    );
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    return `${minutes}分${seconds}秒`;
  }

  async function fetchTaskLogs(taskId, silent = false) {
    if (!silent) refreshingLogs.value = true;
    try {
      const res = await axios.get(`/api/build-tasks/${taskId}/logs`);
      const oldLength = taskLogs.value.length;
      if (typeof res.data === "string") {
        taskLogs.value = res.data || "暂无日志";
      } else {
        taskLogs.value = JSON.stringify(res.data, null, 2);
      }
      if (taskLogs.value.length > oldLength && autoScroll.value) {
        setTimeout(() => scrollLogToBottom(), 50);
      }
    } catch (error) {
      console.error("获取任务日志失败:", error);
      taskLogs.value = `获取日志失败: ${error.message || "未知错误"}`;
    } finally {
      refreshingLogs.value = false;
    }
  }

  function scrollLogToTop() {
    if (logContainer.value) {
      autoScroll.value = false;
      nextTick(() => {
        if (logContainer.value) logContainer.value.scrollTop = 0;
      });
    }
  }

  function scrollLogToBottom() {
    if (logContainer.value) {
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight;
        }
      });
    }
  }

  function stopLogPolling() {
    if (logPollingInterval.value) {
      clearInterval(logPollingInterval.value);
      logPollingInterval.value = null;
    }
  }

  function startLogPolling(taskId) {
    stopLogPolling();
    if (
      selectedTask.value &&
      (selectedTask.value.status === "running" ||
        selectedTask.value.status === "pending")
    ) {
      logPollingInterval.value = setInterval(() => {
        fetchTaskLogs(taskId, true);
      }, 2000);
    }
  }

  function refreshLogs() {
    if (selectedTask.value?.task_id) {
      fetchTaskLogs(selectedTask.value.task_id);
    }
  }

  function toggleAutoScroll() {
    autoScroll.value = !autoScroll.value;
    if (autoScroll.value) scrollLogToBottom();
  }

  async function copyLogs() {
    if (!taskLogs.value) return;
    const success = await copyToClipboard(taskLogs.value);
    alert(success ? "日志已复制到剪贴板" : "复制失败");
  }

  function closeLogModal() {
    showLogModal.value = false;
    stopLogPolling();
    taskLogs.value = "";
    selectedTask.value = null;
    viewingLogs.value = null;
  }

  function viewTaskLogs(taskId, task) {
    if (!taskId) {
      alert("任务ID不存在，无法查看日志");
      return;
    }
    if (viewingLogs.value === taskId) return;

    viewingLogs.value = taskId;
    let normalized = task;
    if (normalized) {
      if (!normalized.task_id) normalized = { ...normalized, task_id: taskId };
      if (!normalized.image) normalized = { ...normalized, image: normalized.image_name || "未知" };
      if (!normalized.tag) normalized = { ...normalized, tag: "latest" };
    } else {
      normalized = {
        task_id: taskId,
        status: "unknown",
        image: "未知",
        tag: "latest",
      };
    }

    selectedTask.value = normalized;
    showLogModal.value = true;
    taskLogs.value = "加载中...";
    fetchTaskLogs(taskId);

    if (normalized.status === "running" || normalized.status === "pending") {
      startLogPolling(taskId);
    }

    const statusCheckInterval = setInterval(async () => {
      try {
        const res = await axios.get(`/api/build-tasks/${taskId}`);
        if (res.data?.status && selectedTask.value?.task_id === taskId) {
          selectedTask.value.status = res.data.status;
          if (
            ["completed", "failed", "stopped"].includes(res.data.status)
          ) {
            stopLogPolling();
            clearInterval(statusCheckInterval);
            fetchTaskLogs(taskId);
            onTaskFinished?.();
          } else if (
            res.data.status === "running" ||
            res.data.status === "pending"
          ) {
            startLogPolling(taskId);
          }
        }
      } catch (error) {
        console.error("检查任务状态失败:", error);
      }
    }, 3000);

    const unwatchStatus = watch(showLogModal, (open) => {
      if (!open) {
        clearInterval(statusCheckInterval);
        unwatchStatus();
      }
    });

    setTimeout(() => {
      if (viewingLogs.value === taskId) viewingLogs.value = null;
    }, 100);
  }

  return {
    showLogModal,
    selectedTask,
    viewingLogs,
    taskLogs,
    logContainer,
    autoScroll,
    refreshingLogs,
    isLogTaskRunning,
    getLogStatusHeaderClass,
    getLogStatusSummaryClass,
    getLogStatusIcon,
    getLogStatusText,
    formatLogTime,
    calculateLogDuration,
    viewTaskLogs,
    closeLogModal,
    refreshLogs,
    toggleAutoScroll,
    copyLogs,
    scrollLogToTop,
    scrollLogToBottom,
  };
}

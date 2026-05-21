import { ref } from "vue";
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

/**
 * 构建任务日志查看状态（UI 由 TaskLogModal / BuildTaskLogModal 承载）
 */
export function useBuildTaskLogs({ onTaskFinished } = {}) {
  const showLogModal = ref(false);
  const selectedTask = ref(null);
  const viewingLogs = ref(null);

  function closeLogModal() {
    showLogModal.value = false;
    selectedTask.value = null;
    viewingLogs.value = null;
  }

  function normalizeTask(taskId, task) {
    if (task) {
      const normalized = { ...task };
      if (!normalized.task_id) normalized.task_id = taskId;
      if (!normalized.image) {
        normalized.image = normalized.image_name || "未知";
      }
      if (!normalized.tag) normalized.tag = "latest";
      return normalized;
    }
    return {
      task_id: taskId,
      status: "unknown",
      image: "未知",
      tag: "latest",
    };
  }

  function viewTaskLogs(taskId, task) {
    if (!taskId) {
      toastError("任务ID不存在，无法查看日志");
      return;
    }
    if (viewingLogs.value === taskId) return;

    viewingLogs.value = taskId;
    selectedTask.value = normalizeTask(taskId, task);
    showLogModal.value = true;

    setTimeout(() => {
      if (viewingLogs.value === taskId) viewingLogs.value = null;
    }, 100);
  }

  /** 与任务管理页 viewLogs(task) 签名一致 */
  function viewLogs(task) {
    if (!task?.task_id) {
      toastError("任务ID不存在，无法查看日志");
      return;
    }
    viewTaskLogs(task.task_id, task);
  }

  function handleTaskStatusUpdated(newStatus) {
    if (selectedTask.value) {
      selectedTask.value = { ...selectedTask.value, status: newStatus };
    }
    if (["completed", "failed", "stopped"].includes(newStatus)) {
      onTaskFinished?.();
    }
  }

  function isViewingLog(taskId) {
    return viewingLogs.value === taskId;
  }

  return {
    showLogModal,
    selectedTask,
    viewingLogs,
    viewTaskLogs,
    viewLogs,
    closeLogModal,
    handleTaskStatusUpdated,
    isViewingLog,
  };
}

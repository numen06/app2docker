import axios from "axios";
import { showToast } from "@/composables/useToast";

const STORAGE_KEY = "app2docker-pending-tasks";
const MAX_STORED = 20;
const POLL_MS = 3000;
const GRACE_MS = 8000;
const STORAGE_TTL_MS = 24 * 60 * 60 * 1000;

/** @type {Map<string, { meta: object, seenRunning: boolean, registeredAt: number, notified: boolean }>} */
const tracked = new Map();
const notifiedIds = new Set();

let intervalId = null;
let onTaskCreatedHandler = null;

const TYPE_LABELS = {
  build: "构建",
  export: "导出",
  deploy: "部署",
  pipeline: "流水线",
};

function taskLabel(meta, task) {
  const type = meta?.task_type || task?.task_type || "build";
  const prefix = TYPE_LABELS[type] || "任务";
  const image = meta?.image || task?.image || task?.image_name;
  const tag = meta?.tag ?? task?.tag ?? "latest";
  const pipelineName = meta?.pipeline_name;
  let name = "";
  if (pipelineName) {
    name = pipelineName;
  } else if (image) {
    name = tag && tag !== "latest" ? `${image}:${tag}` : image;
  } else if (task?.task_id) {
    name = task.task_id.substring(0, 8);
  }
  return { prefix, name };
}

function persistTracked() {
  try {
    const arr = [...tracked.entries()].map(([task_id, entry]) => ({
      task_id,
      ...entry.meta,
      registeredAt: entry.registeredAt,
    }));
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(arr.slice(-MAX_STORED))
    );
  } catch {
    /* ignore quota */
  }
}

function loadPersisted() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return;
    const now = Date.now();
    for (const item of arr) {
      if (!item?.task_id) continue;
      if (item.registeredAt && now - item.registeredAt > STORAGE_TTL_MS) {
        continue;
      }
      registerTask(
        item.task_id,
        {
          task_type: item.task_type,
          image: item.image,
          tag: item.tag,
          pipeline_name: item.pipeline_name,
        },
        { persist: false }
      );
    }
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

/**
 * @param {string} taskId
 * @param {{ task_type?: string, image?: string, tag?: string, pipeline_name?: string }} [meta]
 * @param {{ persist?: boolean }} [options]
 */
export function registerTask(taskId, meta = {}, options = {}) {
  if (!taskId || notifiedIds.has(taskId)) return;
  tracked.set(taskId, {
    meta: { ...meta },
    seenRunning: false,
    registeredAt: Date.now(),
    notified: false,
  });
  if (options.persist !== false) {
    persistTracked();
  }
}

async function fetchTaskStatus(taskId) {
  try {
    const res = await axios.get(`/api/build-tasks/${taskId}`);
    return res.data;
  } catch (e) {
    if (e.response?.status === 404) {
      tracked.delete(taskId);
      persistTracked();
      return null;
    }
    throw e;
  }
}

function notifyTerminal(taskId, task, meta) {
  if (notifiedIds.has(taskId)) return;
  const status = task?.status;
  if (status !== "completed" && status !== "failed") return;

  notifiedIds.add(taskId);
  const { prefix, name } = taskLabel(meta, task);
  const suffix = name ? ` · ${name}` : "";

  if (status === "completed") {
    showToast({
      message: `${prefix}任务已完成${suffix}`,
      variant: "success",
    });
  } else {
    const err = (task?.error || "").slice(0, 80);
    showToast({
      message: `${prefix}任务失败${suffix}${err ? `\n${err}` : ""}`,
      variant: "error",
      duration: 8000,
    });
  }

  window.dispatchEvent(
    new CustomEvent("taskFinished", {
      detail: { task_id: taskId, status },
    })
  );
  tracked.delete(taskId);
  persistTracked();
}

async function pollOnce() {
  if (tracked.size === 0) return;

  let runningIds = new Set();
  try {
    const res = await axios.get("/api/tasks/running");
    const tasks = res.data?.tasks || [];
    runningIds = new Set(tasks.map((t) => t.task_id));
  } catch (e) {
    console.error("任务完成监听：获取运行中任务失败", e);
    return;
  }

  const now = Date.now();

  for (const [taskId, entry] of [...tracked.entries()]) {
    if (entry.notified) continue;

    if (runningIds.has(taskId)) {
      entry.seenRunning = true;
      continue;
    }

    if (!entry.seenRunning && now - entry.registeredAt < GRACE_MS) {
      continue;
    }

    try {
      const task = await fetchTaskStatus(taskId);
      if (!task) continue;

      if (["running", "pending"].includes(task.status)) {
        continue;
      }

      entry.notified = true;
      notifyTerminal(taskId, task, entry.meta);
    } catch (e) {
      console.error("任务完成监听：获取任务详情失败", taskId, e);
    }
  }
}

export function useTaskCompletionWatcher() {
  function handleTaskCreated(event) {
    const detail = event?.detail || {};
    const taskId = detail.task_id;
    if (!taskId) return;
    registerTask(taskId, {
      task_type: detail.task_type || "pipeline",
      image: detail.image,
      tag: detail.tag,
      pipeline_name: detail.pipeline_name,
    });
  }

  function start() {
    if (intervalId) return;
    loadPersisted();
    onTaskCreatedHandler = handleTaskCreated;
    window.addEventListener("taskCreated", onTaskCreatedHandler);
    intervalId = setInterval(pollOnce, POLL_MS);
    pollOnce();
  }

  function stop() {
    if (onTaskCreatedHandler) {
      window.removeEventListener("taskCreated", onTaskCreatedHandler);
      onTaskCreatedHandler = null;
    }
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }

  return { start, stop, registerTask };
}

<template>
  <div class="export-task-list">
    <PageToolbar title="导出任务清单" icon="fa-list-check">
      <template #actions>
        <NativeSelect v-model="statusFilter" class="h-9 w-auto">
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="running">进行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </NativeSelect>
        <Button variant="outline" size="sm" @click="loadTasks">
          <i class="fas fa-sync-alt"></i> 刷新
        </Button>
      </template>
    </PageToolbar>

    <div v-if="loading" class="py-8 text-center text-slate-500">
      <i class="fas fa-spinner fa-spin text-xl"></i>
    </div>

    <EmptyState v-else-if="filteredTasks.length === 0" message="暂无导出任务" icon="fa-inbox" />

    <div v-else class="overflow-x-auto rounded-lg border border-slate-200">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead class="w-[200px]">镜像</TableHead>
            <TableHead class="w-[100px]">标签</TableHead>
            <TableHead class="w-[100px]">压缩</TableHead>
            <TableHead class="w-[120px]">状态</TableHead>
            <TableHead class="w-[150px]">创建时间</TableHead>
            <TableHead class="w-[100px]">文件大小</TableHead>
            <TableHead class="w-[150px] text-end">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="task in filteredTasks" :key="task.task_id">
            <TableCell><code class="rounded bg-slate-100 px-1 text-xs">{{ task.image }}</code></TableCell>
            <TableCell>{{ task.tag }}</TableCell>
            <TableCell>
              <Badge v-if="task.compress === 'gzip'">GZIP</Badge>
              <Badge v-else variant="default">TAR</Badge>
            </TableCell>
            <TableCell>
              <Badge v-if="task.status === 'pending'"><i class="fas fa-clock mr-1"></i>等待中</Badge>
              <Badge v-else-if="task.status === 'running'" variant="info">
                <i class="fas fa-spinner fa-spin mr-1"></i>进行中
              </Badge>
              <Badge v-else-if="task.status === 'completed'" variant="success">
                <i class="fas fa-check-circle mr-1"></i>已完成
              </Badge>
              <Badge v-else-if="task.status === 'failed'" variant="danger">
                <i class="fas fa-times-circle mr-1"></i>失败
              </Badge>
            </TableCell>
            <TableCell class="text-sm text-slate-500">{{ formatTime(task.created_at) }}</TableCell>
            <TableCell class="text-sm">
              <span v-if="task.file_size">{{ formatFileSize(task.file_size) }}</span>
              <span v-else>-</span>
            </TableCell>
            <TableCell class="text-end">
              <div class="flex justify-end gap-1">
                <Button
                  v-if="task.status === 'completed'"
                  size="sm"
                  :disabled="downloading === task.task_id"
                  @click="downloadTask(task)"
                >
                  <i class="fas fa-download"></i>
                  <i v-if="downloading === task.task_id" class="fas fa-spinner fa-spin"></i>
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  :disabled="deleting === task.task_id"
                  @click="deleteTask(task)"
                >
                  <i class="fas fa-trash"></i>
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <AlertBanner v-if="error" variant="danger" :message="error" class="mt-3" />

    <div v-if="selectedFailedTask" class="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      <div class="flex items-start justify-between gap-2">
        <div>
          <strong>任务失败:</strong> {{ selectedFailedTask.image }}:{{ selectedFailedTask.tag }}
          <div class="mt-1"><code>{{ selectedFailedTask.error }}</code></div>
        </div>
        <Button variant="ghost" size="sm" @click="selectedFailedTask = null">
          <i class="fas fa-times"></i>
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import axios from "axios";
import { ref, computed, onMounted, onUnmounted } from "vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Badge from "@/components/ui/badge/Badge.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";

const tasks = ref([]);
const loading = ref(false);
const error = ref(null);
const statusFilter = ref("");
const downloading = ref(null);
const deleting = ref(null);
const selectedFailedTask = ref(null);
let refreshInterval = null;

const filteredTasks = computed(() => {
  if (!statusFilter.value) return tasks.value;
  return tasks.value.filter((t) => t.status === statusFilter.value);
});

function formatTime(isoString) {
  if (!isoString) return "-";
  return new Date(isoString).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function formatFileSize(bytes) {
  if (!bytes) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

async function loadTasks() {
  loading.value = true;
  error.value = null;
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {};
    const res = await axios.get("/api/export-tasks", { params });
    tasks.value = res.data.tasks || [];
  } catch (err) {
    error.value = err.response?.data?.error || err.message || "加载任务列表失败";
  } finally {
    loading.value = false;
  }
}

async function downloadTask(task) {
  if (downloading.value) return;
  downloading.value = task.task_id;
  try {
    const res = await axios.get(`/api/export-tasks/${task.task_id}/download`, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    const image = task.image.replace(/\//g, "_");
    const ext = task.compress === "gzip" ? ".tar.gz" : ".tar";
    a.download = `${image}-${task.tag}${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    toastApiError(err, "下载失败");
  } finally {
    downloading.value = null;
  }
}

async function deleteTask(task) {
  if (!(await showConfirm({ message: `确定要删除任务 "${task.image}:${task.tag}" 吗？`, danger: true }))) return;
  deleting.value = task.task_id;
  try {
    await axios.delete(`/api/export-tasks/${task.task_id}`);
    await loadTasks();
  } catch (err) {
    toastApiError(err, "删除失败");
  } finally {
    deleting.value = null;
  }
}

onMounted(() => {
  loadTasks();
  refreshInterval = setInterval(() => {
    const hasRunning = tasks.value.some((t) => t.status === "running" || t.status === "pending");
    if (hasRunning) loadTasks();
  }, 5000);
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
});
</script>

<style scoped>
.export-task-list {
  animation: fadeIn 0.3s;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

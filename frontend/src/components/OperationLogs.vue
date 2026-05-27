<template>
  <div class="min-w-0">
    <div
      class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
    >
      <p class="shrink-0 text-xs text-slate-500 sm:max-w-md">
        系统自动保留最近 90 天，过期日志每小时自动清理
      </p>
      <div class="flex w-full min-w-0 flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
        <Input
          v-model="filterUsername"
          type="text"
          class="w-full min-w-0 sm:w-36"
          placeholder="过滤用户名"
        />
        <NativeSelect v-model="filterOperation" class="w-full min-w-0 sm:w-40">
          <option value="">全部操作</option>
          <option
            v-for="opt in OPERATION_LOG_FILTER_OPTIONS"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </NativeSelect>
        <Button variant="outline" size="sm" :disabled="loading" @click="loadLogs">
          <AppIcon name="sync-alt" />
          刷新
        </Button>
        <DropdownMenu>
          <template #trigger>
            <Button variant="outline" size="sm" class="text-red-600 hover:text-red-700">
              <AppIcon  name="trash-alt" />
              清理日志
              <AppIcon  name="chevron-down" class="text-xs opacity-70" />
            </Button>
          </template>
          <DropdownMenuItem @select="clearLogs(7)">
            <AppIcon  name="calendar-week" class="mr-2 w-4" /> 保留最近 7 天
          </DropdownMenuItem>
          <DropdownMenuItem @select="clearLogs(30)">
            <AppIcon  name="calendar-alt" class="mr-2 w-4" /> 保留最近 30 天
          </DropdownMenuItem>
          <DropdownMenuItem @select="clearLogs(90)">
            <AppIcon  name="calendar" class="mr-2 w-4" /> 保留最近 90 天
          </DropdownMenuItem>
          <DropdownMenuItem class="text-red-600 focus:text-red-700" @select="clearLogs(null)">
            <AppIcon  name="exclamation-triangle" class="mr-2 w-4" /> 清空所有日志
          </DropdownMenuItem>
        </DropdownMenu>
      </div>
    </div>

    <div v-if="error" class="mb-4">
      <AlertBanner :message="error" />
    </div>

    <div
      v-if="loading"
      class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500"
    >
      <AppIcon  name="spinner" spin />
      加载中…
    </div>

    <EmptyState
      v-else-if="!error && logs.length === 0"
      :message="hasFilters ? '没有匹配的操作日志' : '暂无操作日志'"
    />

    <template v-else-if="!error && logs.length > 0">
      <div class="space-y-3 md:hidden">
        <div
          v-for="(log, index) in logs"
          :key="logKey(log, index)"
          class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
        >
          <div class="flex flex-wrap items-center gap-2">
            <Badge variant="info">{{ getOperationLogLabel(log.operation) }}</Badge>
            <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-800">{{
              log.username
            }}</code>
          </div>
          <p class="mt-1 text-xs text-slate-500">{{ formatTime(log.timestamp) }}</p>
          <pre
            v-if="log.details && Object.keys(log.details).length > 0"
            class="mt-2 max-h-32 overflow-auto break-all rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-600 whitespace-pre-wrap"
          >{{ formatDetails(log.details) }}</pre>
        </div>
      </div>

      <div class="hidden md:block min-w-0">
        <Table min-width-class="min-w-[44rem]">
          <TableHeader>
            <TableRow>
              <TableHead class="whitespace-nowrap">时间</TableHead>
              <TableHead class="whitespace-nowrap">用户名</TableHead>
              <TableHead class="whitespace-nowrap">操作</TableHead>
              <TableHead class="min-w-[12rem]">详情</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="(log, index) in logs" :key="logKey(log, index)">
              <TableCell class="whitespace-nowrap text-sm text-slate-600">{{
                formatTime(log.timestamp)
              }}</TableCell>
              <TableCell class="whitespace-nowrap">
                <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-800">{{
                  log.username
                }}</code>
              </TableCell>
              <TableCell class="whitespace-nowrap">
                <Badge variant="info">{{ getOperationLogLabel(log.operation) }}</Badge>
              </TableCell>
              <TableCell class="min-w-0 text-sm text-slate-500">
                <pre
                  v-if="log.details && Object.keys(log.details).length > 0"
                  class="max-h-24 overflow-auto break-words rounded bg-slate-50 px-1.5 py-0.5 font-mono text-xs whitespace-pre-wrap"
                  :title="formatDetails(log.details)"
                >{{ formatDetails(log.details) }}</pre>
                <span v-else>—</span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      <PaginationBar
        :page="currentPage"
        :page-size="pageSize"
        :total="totalLogs"
        :total-pages="totalPages"
        @update:page="onPageChange"
      />
    </template>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import axios from "axios";
import { computed, onMounted, ref, watch } from "vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import DropdownMenu from "@/components/ui/dropdown/DropdownMenu.vue";
import DropdownMenuItem from "@/components/ui/dropdown/DropdownMenuItem.vue";
import { Badge } from "@/components/ui/badge";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import {
  OPERATION_LOG_FILTER_OPTIONS,
  getOperationLogLabel,
} from "@/constants/operationLogActions.js";

const logs = ref([]);
const loading = ref(false);
const error = ref(null);
const filterUsername = ref("");
const filterOperation = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const totalLogs = ref(0);
const totalPages = ref(0);

const hasFilters = computed(
  () => Boolean(filterUsername.value?.trim() || filterOperation.value)
);

function logKey(log, index) {
  return `${log.timestamp ||""}-${log.username ||""}-${log.operation ||""}-${index}`;
}

function onPageChange(page) {
  if (page < 1 || (totalPages.value > 0 && page > totalPages.value)) return;
  if (page === currentPage.value) return;
  currentPage.value = page;
  loadLogs();
}

function formatTime(isoString) {
  if (!isoString) return"—";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return date.toLocaleString("zh-CN", {
    year:"numeric",
    month:"2-digit",
    day:"2-digit",
    hour:"2-digit",
    minute:"2-digit",
    second:"2-digit",
    hour12: false,
  });
}

function formatDetails(details) {
  try {
    return JSON.stringify(details, null, 2);
  } catch {
    return String(details);
  }
}

async function loadLogs() {
  loading.value = true;
  error.value = null;
  try {
    const params = { page: currentPage.value, page_size: pageSize.value };
    if (filterUsername.value?.trim()) params.username = filterUsername.value.trim();
    if (filterOperation.value) params.operation = filterOperation.value;

    const res = await axios.get("/api/operation-logs", { params });
    logs.value = res.data.logs || [];
    totalLogs.value = res.data.total || 0;
    totalPages.value = res.data.total_pages || 0;

    if (totalPages.value > 0 && currentPage.value > totalPages.value) {
      currentPage.value = totalPages.value;
      loading.value = false;
      return loadLogs();
    }
  } catch (err) {
    error.value =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||"加载操作日志失败";
    logs.value = [];
    totalLogs.value = 0;
    totalPages.value = 0;
  } finally {
    loading.value = false;
  }
}

async function clearLogs(days) {
  let confirmMessage ="";
  if (days === null) {
    confirmMessage ="确定要清空所有操作日志吗？此操作不可恢复！";
  } else {
    confirmMessage = `确定要清理操作日志吗？将保留最近 ${days} 天的日志，其他日志将被删除。`;
  }
  if (!(await showConfirm({ message: confirmMessage }))) return;

  try {
    const params = days ? { days } : {};
    const res = await axios.delete("/api/operation-logs", { params });
    toastSuccess(res.data.message ||"清理成功");
    currentPage.value = 1;
    await loadLogs();
  } catch (err) {
    toastApiError(err,"清理失败");
  }
}

watch([filterUsername, filterOperation], () => {
  currentPage.value = 1;
  loadLogs();
});

onMounted(() => {
  loadLogs();
});
</script>

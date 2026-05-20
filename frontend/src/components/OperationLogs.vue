<template>
  <div>
    <div
      class="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between"
    >
      <p class="text-xs text-slate-500 lg:max-w-md">
        系统自动保留最近 90 天，过期日志每小时自动清理
      </p>
      <div class="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
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
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
          刷新
        </Button>
        <DropdownMenu>
          <template #trigger>
            <Button variant="outline" size="sm" class="text-red-600 hover:text-red-700">
              <i class="fas fa-trash-alt"></i>
              清理日志
              <i class="fas fa-chevron-down text-xs opacity-70"></i>
            </Button>
          </template>
          <DropdownMenuItem @select="clearLogs(7)">
            <i class="fas fa-calendar-week mr-2 w-4"></i> 保留最近 7 天
          </DropdownMenuItem>
          <DropdownMenuItem @select="clearLogs(30)">
            <i class="fas fa-calendar-alt mr-2 w-4"></i> 保留最近 30 天
          </DropdownMenuItem>
          <DropdownMenuItem @select="clearLogs(90)">
            <i class="fas fa-calendar mr-2 w-4"></i> 保留最近 90 天
          </DropdownMenuItem>
          <DropdownMenuItem class="text-red-600 focus:text-red-700" @select="clearLogs(null)">
            <i class="fas fa-exclamation-triangle mr-2 w-4"></i> 清空所有日志
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
      <i class="fas fa-spinner fa-spin"></i>
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

      <div class="hidden md:block overflow-x-auto rounded-lg border border-slate-200">
        <Table min-width-class="min-w-[44rem]">
          <TableHeader>
            <TableRow>
              <TableHead class="w-[180px]">时间</TableHead>
              <TableHead class="w-[120px]">用户名</TableHead>
              <TableHead class="w-[160px]">操作</TableHead>
              <TableHead>详情</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="(log, index) in logs" :key="logKey(log, index)">
              <TableCell class="text-sm text-slate-600 whitespace-nowrap">{{
                formatTime(log.timestamp)
              }}</TableCell>
              <TableCell>
                <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-800">{{
                  log.username
                }}</code>
              </TableCell>
              <TableCell>
                <Badge variant="info">{{ getOperationLogLabel(log.operation) }}</Badge>
              </TableCell>
              <TableCell class="text-sm text-slate-500">
                <pre
                  v-if="log.details && Object.keys(log.details).length > 0"
                  class="max-h-24 max-w-xl overflow-auto rounded bg-slate-50 px-1.5 py-0.5 font-mono text-xs whitespace-pre-wrap"
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
import axios from "axios";
import { computed, onMounted, ref, watch } from "vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import DropdownMenu from "@/components/ui/dropdown-menu/DropdownMenu.vue";
import DropdownMenuItem from "@/components/ui/dropdown-menu/DropdownMenuItem.vue";
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
  return `${log.timestamp || ""}-${log.username || ""}-${log.operation || ""}-${index}`;
}

function onPageChange(page) {
  if (page < 1 || (totalPages.value > 0 && page > totalPages.value)) return;
  if (page === currentPage.value) return;
  currentPage.value = page;
  loadLogs();
}

function formatTime(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
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
      err.message ||
      "加载操作日志失败";
    logs.value = [];
    totalLogs.value = 0;
    totalPages.value = 0;
  } finally {
    loading.value = false;
  }
}

async function clearLogs(days) {
  let confirmMessage = "";
  if (days === null) {
    confirmMessage = "确定要清空所有操作日志吗？此操作不可恢复！";
  } else {
    confirmMessage = `确定要清理操作日志吗？将保留最近 ${days} 天的日志，其他日志将被删除。`;
  }
  if (!confirm(confirmMessage)) return;

  try {
    const params = days ? { days } : {};
    const res = await axios.delete("/api/operation-logs", { params });
    alert(res.data.message || "清理成功");
    currentPage.value = 1;
    await loadLogs();
  } catch (err) {
    alert(err.response?.data?.detail || err.message || "清理失败");
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

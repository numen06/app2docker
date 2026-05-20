<template>
  <div>
    <PageToolbar title="操作日志" icon="fa-history">
      <template #actions>
        <Input
          v-model="filterUsername"
          type="text"
          class="w-full min-w-0 sm:w-36"
          placeholder="过滤用户名"
        />
        <NativeSelect v-model="filterOperation" class="w-full min-w-0 sm:w-36">
          <option value="">全部操作</option>
          <option value="login">登录</option>
          <option value="logout">登出</option>
          <option value="change_password">修改密码</option>
          <option value="build">构建镜像</option>
          <option value="export">导出镜像</option>
          <option value="delete_export_task">删除导出任务</option>
          <option value="save_config">保存配置</option>
          <option value="save_registries">保存仓库配置</option>
          <option value="template_create">创建模板</option>
          <option value="template_update">更新模板</option>
          <option value="template_delete">删除模板</option>
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
      </template>
    </PageToolbar>

    <div v-if="loading" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <i class="fas fa-spinner fa-spin"></i>
      加载中…
    </div>

    <EmptyState v-else-if="logs.length === 0" message="暂无操作日志" />

    <template v-else>
    <div class="space-y-3 md:hidden">
      <div
        v-for="log in logs"
        :key="log.timestamp + log.username + log.operation"
        class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
      >
        <div class="flex flex-wrap items-center gap-2">
          <Badge variant="info">{{ getOperationName(log.operation) }}</Badge>
          <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-800">{{
            log.username
          }}</code>
        </div>
        <p class="mt-1 text-xs text-slate-500">{{ formatTime(log.timestamp) }}</p>
        <p
          v-if="log.details && Object.keys(log.details).length > 0"
          class="mt-2 break-all rounded bg-slate-100 px-2 py-1 font-mono text-xs text-slate-600"
        >
          {{ JSON.stringify(log.details) }}
        </p>
      </div>
    </div>

    <div class="hidden md:block">
    <Table min-width-class="min-w-[44rem]">
        <TableHeader>
          <TableRow>
            <TableHead class="w-[180px]">时间</TableHead>
            <TableHead class="w-[120px]">用户名</TableHead>
            <TableHead class="w-[150px]">操作</TableHead>
            <TableHead>详情</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow
            v-for="log in logs"
            :key="log.timestamp + log.username + log.operation"
          >
            <TableCell class="text-sm text-slate-600">{{ formatTime(log.timestamp) }}</TableCell>
            <TableCell>
              <code class="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-800">{{
                log.username
              }}</code>
            </TableCell>
            <TableCell>
              <Badge variant="info">{{ getOperationName(log.operation) }}</Badge>
            </TableCell>
            <TableCell class="text-sm text-slate-500">
              <code
                v-if="log.details && Object.keys(log.details).length > 0"
                class="block max-w-xl truncate rounded bg-slate-50 px-1.5 py-0.5 text-xs"
              >
                {{ JSON.stringify(log.details) }}
              </code>
              <span v-else>—</span>
            </TableCell>
          </TableRow>
        </TableBody>
    </Table>
    </div>
    </template>

    <PaginationBar
      :page="currentPage"
      :page-size="pageSize"
      :total="totalLogs"
      :total-pages="totalPages"
      @update:page="onPageChange"
    />

    <AlertBanner :message="error || ''" />
  </div>
</template>

<script setup>
import axios from "axios";
import { onMounted, ref, watch } from "vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
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

const logs = ref([]);
const loading = ref(false);
const error = ref(null);
const filterUsername = ref("");
const filterOperation = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const totalLogs = ref(0);
const totalPages = ref(0);

function onPageChange(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  currentPage.value = page;
  loadLogs();
}

function formatTime(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString);
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

function getOperationName(operation) {
  const names = {
    login: "登录",
    logout: "登出",
    change_password: "修改密码",
    build: "构建镜像",
    export: "导出镜像",
    delete_export_task: "删除导出任务",
    save_config: "保存配置",
    save_registries: "保存仓库配置",
    template_create: "创建模板",
    template_update: "更新模板",
    template_delete: "删除模板",
  };
  return names[operation] || operation;
}

async function loadLogs() {
  loading.value = true;
  error.value = null;
  try {
    const params = { page: currentPage.value, page_size: pageSize.value };
    if (filterUsername.value) params.username = filterUsername.value;
    if (filterOperation.value) params.operation = filterOperation.value;

    const res = await axios.get("/api/operation-logs", { params });
    logs.value = res.data.logs || [];
    totalLogs.value = res.data.total || 0;
    totalPages.value = res.data.total_pages || 0;
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

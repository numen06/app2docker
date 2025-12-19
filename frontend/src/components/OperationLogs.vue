<template>
  <div class="operation-logs">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0"><i class="fas fa-history"></i> 操作日志</h5>
      <div class="d-flex gap-2 align-items-center">
        <input
          v-model="filterUsername"
          type="text"
          class="form-control form-control-sm"
          placeholder="过滤用户名"
          style="width: 150px"
        />
        <select
          v-model="filterOperation"
          class="form-select form-select-sm"
          style="width: 150px"
        >
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
        </select>
        <button class="btn btn-sm btn-outline-primary" @click="loadLogs">
          <i class="fas fa-sync-alt"></i> 刷新
        </button>
        <div class="btn-group">
          <button
            type="button"
            class="btn btn-sm btn-outline-danger dropdown-toggle"
            data-bs-toggle="dropdown"
            aria-expanded="false"
          >
            <i class="fas fa-trash-alt"></i> 清理日志
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
            <li>
              <a class="dropdown-item" href="#" @click.prevent="clearLogs(7)">
                <i class="fas fa-calendar-week"></i> 保留最近 7 天
              </a>
            </li>
            <li>
              <a class="dropdown-item" href="#" @click.prevent="clearLogs(30)">
                <i class="fas fa-calendar-alt"></i> 保留最近 30 天
              </a>
            </li>
            <li>
              <a class="dropdown-item" href="#" @click.prevent="clearLogs(90)">
                <i class="fas fa-calendar"></i> 保留最近 90 天
              </a>
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <a
                class="dropdown-item text-danger"
                href="#"
                @click.prevent="clearLogs(null)"
              >
                <i class="fas fa-exclamation-triangle"></i> 清空所有日志
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 日志列表 -->
    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">加载中...</span>
      </div>
    </div>

    <div v-else-if="logs.length === 0" class="text-center py-4 text-muted">
      <i class="fas fa-inbox fa-2x mb-2"></i>
      <p class="mb-0">暂无操作日志</p>
    </div>

    <div v-else class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th style="width: 180px">时间</th>
            <th style="width: 120px">用户名</th>
            <th style="width: 150px">操作</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="log in logs"
            :key="log.timestamp + log.username + log.operation"
          >
            <td class="small">
              {{ formatTime(log.timestamp) }}
            </td>
            <td>
              <code class="small">{{ log.username }}</code>
            </td>
            <td>
              <span class="badge bg-primary">{{
                getOperationName(log.operation)
              }}</span>
            </td>
            <td class="small text-muted">
              <code v-if="log.details && Object.keys(log.details).length > 0">
                {{ JSON.stringify(log.details) }}
              </code>
              <span v-else>-</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页控件 -->
    <div
      v-if="totalPages > 1"
      class="d-flex justify-content-between align-items-center mt-3"
    >
      <div class="text-muted small">
        显示第 {{ totalLogs > 0 ? (currentPage - 1) * pageSize + 1 : 0 }} -
        {{ Math.min(currentPage * pageSize, totalLogs) }} 条，共
        {{ totalLogs }} 条
      </div>
      <nav>
        <ul class="pagination pagination-sm mb-0">
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <button
              class="page-link"
              @click="changePage(1)"
              :disabled="currentPage === 1"
            >
              <i class="fas fa-angle-double-left"></i>
            </button>
          </li>
          <li class="page-item" :class="{ disabled: currentPage === 1 }">
            <button
              class="page-link"
              @click="changePage(currentPage - 1)"
              :disabled="currentPage === 1"
            >
              <i class="fas fa-angle-left"></i>
            </button>
          </li>
          <li
            v-for="page in visiblePages"
            :key="page"
            class="page-item"
            :class="{ active: currentPage === page }"
          >
            <button class="page-link" @click="changePage(page)">
              {{ page }}
            </button>
          </li>
          <li
            class="page-item"
            :class="{ disabled: currentPage === totalPages }"
          >
            <button
              class="page-link"
              @click="changePage(currentPage + 1)"
              :disabled="currentPage === totalPages"
            >
              <i class="fas fa-angle-right"></i>
            </button>
          </li>
          <li
            class="page-item"
            :class="{ disabled: currentPage === totalPages }"
          >
            <button
              class="page-link"
              @click="changePage(totalPages)"
              :disabled="currentPage === totalPages"
            >
              <i class="fas fa-angle-double-right"></i>
            </button>
          </li>
        </ul>
      </nav>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="alert alert-danger mt-3 mb-0">
      <i class="fas fa-exclamation-circle"></i> {{ error }}
    </div>
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, onMounted, ref, watch } from "vue";

const logs = ref([]);
const loading = ref(false);
const error = ref(null);
const filterUsername = ref("");
const filterOperation = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const totalLogs = ref(0);
const totalPages = ref(0);

// 可见的页码列表
const visiblePages = computed(() => {
  const total = totalPages.value;
  const current = currentPage.value;
  const pages = [];

  if (total <= 7) {
    // 总页数小于7，显示所有页码
    for (let i = 1; i <= total; i++) {
      pages.push(i);
    }
  } else {
    // 总页数大于7，智能显示
    if (current <= 4) {
      // 前部：1 2 3 4 5 ... 最后页
      for (let i = 1; i <= 5; i++) pages.push(i);
      pages.push("...");
      pages.push(total);
    } else if (current >= total - 3) {
      // 后部：1 ... 倍数第5页 倍数第4页 倍数第3页 倍数第2页 最后页
      pages.push(1);
      pages.push("...");
      for (let i = total - 4; i <= total; i++) pages.push(i);
    } else {
      // 中间：1 ... current-1 current current+1 ... 最后页
      pages.push(1);
      pages.push("...");
      for (let i = current - 1; i <= current + 1; i++) pages.push(i);
      pages.push("...");
      pages.push(total);
    }
  }

  return pages.filter(
    (p) => p !== "..." || pages.indexOf(p) === pages.lastIndexOf(p)
  );
});

// 切换页码
function changePage(page) {
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
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    };

    // 将过滤条件传递到后端
    if (filterUsername.value) {
      params.username = filterUsername.value;
    }
    if (filterOperation.value) {
      params.operation = filterOperation.value;
    }

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
    console.error("加载操作日志失败:", err);
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

  if (!confirm(confirmMessage)) {
    return;
  }

  try {
    const params = days ? { days } : {};
    const res = await axios.delete("/api/operation-logs", { params });

    alert(res.data.message || "清理成功");
    // 重新加载日志
    await loadLogs();
  } catch (err) {
    alert(err.response?.data?.detail || err.message || "清理失败");
    console.error("清理操作日志失败:", err);
  }
}

// 监听过滤条件变化，重置到第一页并重新加载
watch([filterUsername, filterOperation], () => {
  currentPage.value = 1;
  loadLogs();
});

onMounted(() => {
  loadLogs();
});
</script>

<style scoped>
.operation-logs {
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

.table {
  font-size: 0.9rem;
}

code {
  font-size: 0.85rem;
  background-color: #f8f9fa;
  padding: 2px 6px;
  border-radius: 3px;
}

/* 分页样式优化 */
.pagination .page-link {
  min-width: 38px;
  text-align: center;
}

.pagination .page-item.disabled .page-link {
  cursor: not-allowed;
}

.pagination .page-item.active .page-link {
  font-weight: 600;
}
</style>

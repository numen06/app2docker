<template>
  <div class="task-manager">
    <!-- 基本信息块：下载目录和编译目录大小 -->
    <div class="info-cards mb-3">
      <div class="card info-card">
        <div class="card-body">
          <div class="d-flex align-items-center">
            <div class="info-icon me-3">
              <i class="fas fa-download"></i>
            </div>
            <div class="flex-grow-1">
              <div class="info-label">下载目录大小</div>
              <div class="info-value">{{ exportDirSize }}</div>
              <div v-if="exportDirCount > 0" class="info-sub">
                {{ exportDirCount }} 个文件
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="card info-card">
        <div class="card-body">
          <div class="d-flex align-items-center">
            <div class="info-icon me-3">
              <i class="fas fa-folder-open"></i>
            </div>
            <div class="flex-grow-1">
              <div class="info-label">编译目录大小</div>
              <div class="info-value">{{ buildDirSize }}</div>
              <div v-if="buildDirCount > 0" class="info-sub">
                {{ buildDirCount }} 个目录
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="d-flex justify-content-between align-items-center mb-3">
      <h5 class="mb-0"><i class="fas fa-tasks"></i> 任务管理</h5>
      <div class="d-flex gap-2 align-items-center">
        <select
          v-model="statusFilter"
          class="form-select form-select-sm"
          style="width: auto"
          @change="resetPage"
        >
          <option value="">全部状态</option>
          <option value="pending">等待中</option>
          <option value="running">进行中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
        <select
          v-model="categoryFilter"
          class="form-select form-select-sm"
          style="width: auto"
          @change="resetPage"
        >
          <option value="">全部类型</option>
          <option value="build">构建任务</option>
          <option value="export">导出任务</option>
        </select>
        <button class="btn btn-sm btn-outline-primary" @click="loadTasks">
          <i class="fas fa-sync-alt"></i> 刷新
        </button>
        <div class="btn-group">
          <button
            class="btn btn-sm btn-outline-danger dropdown-toggle"
            type="button"
            data-bs-toggle="dropdown"
            :disabled="cleaning"
          >
            <i class="fas fa-broom"></i> 清理任务
            <span
              v-if="cleaning"
              class="spinner-border spinner-border-sm ms-1"
            ></span>
          </button>
          <ul class="dropdown-menu dropdown-menu-end">
            <li>
              <a
                class="dropdown-item text-danger"
                href="#"
                @click.prevent="cleanupAll"
              >
                <i class="fas fa-trash-alt"></i> 清理全部（非运行中）
              </a>
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <a
                class="dropdown-item"
                href="#"
                @click.prevent="cleanupByStatus('completed')"
              >
                <i class="fas fa-check-circle"></i> 清理已完成的任务
              </a>
            </li>
            <li>
              <a
                class="dropdown-item"
                href="#"
                @click.prevent="cleanupByStatus('failed')"
              >
                <i class="fas fa-times-circle"></i> 清理失败的任务
              </a>
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <a
                class="dropdown-item"
                href="#"
                @click.prevent="cleanupByDaysPrompt"
              >
                <i class="fas fa-calendar-alt"></i> 清理N天前的任务
              </a>
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <a
                class="dropdown-item"
                href="#"
                @click.prevent="cleanupOrphanDirs"
              >
                <i class="fas fa-exclamation-triangle"></i> 清理异常目录
              </a>
            </li>
            <li>
              <a
                class="dropdown-item"
                href="#"
                @click.prevent="cleanupBuildDir"
                :class="{ 'text-muted': buildDirCount === 0 }"
              >
                <i class="fas fa-folder-open"></i> 清理编译目录（全部）
                <span v-if="buildDirCount > 0" class="text-muted small ms-2"
                  >({{ buildDirSize }})</span
                >
              </a>
            </li>
            <li><hr class="dropdown-divider" /></li>
            <li>
              <a
                class="dropdown-item"
                href="#"
                @click.prevent="cleanupExportDir"
                :class="{ 'text-muted': exportDirCount === 0 }"
              >
                <i class="fas fa-download"></i> 清理下载目录（全部）
                <span v-if="exportDirCount > 0" class="text-muted small ms-2"
                  >({{ exportDirSize }})</span
                >
              </a>
            </li>
            <li>
              <a
                class="dropdown-item"
                href="#"
                @click.prevent="cleanupExportDirDays"
                :class="{ 'text-muted': exportDirCount === 0 }"
              >
                <i class="fas fa-calendar-times"></i> 清理N天前的下载文件
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 任务列表 -->
    <div v-if="loading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">加载中...</span>
      </div>
    </div>

    <div
      v-else-if="paginatedTasks.length === 0"
      class="text-center py-4 text-muted"
    >
      <i class="fas fa-inbox fa-2x mb-2"></i>
      <p class="mb-0">暂无任务</p>
    </div>

    <div v-else class="table-responsive">
      <table class="table table-hover align-middle mb-0">
        <thead class="table-light">
          <tr>
            <th style="width: 100px">类型</th>
            <th style="width: 180px">镜像/任务</th>
            <th style="width: 120px">分支/Tag</th>
            <th style="width: 90px">来源</th>
            <th style="width: 100px">状态</th>
            <th style="width: 140px">创建时间</th>
            <th style="width: 90px">时长</th>
            <th style="width: 90px">文件大小</th>
            <th style="width: auto; min-width: 200px" class="text-end">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in paginatedTasks" :key="task.task_id">
            <td>
              <span v-if="task.task_category === 'build'" class="badge bg-info">
                <i class="fas fa-hammer"></i> 构建
              </span>
              <span v-else class="badge bg-secondary">
                <i class="fas fa-download"></i> 导出
              </span>
            </td>
            <td>
              <div>
                <code class="small">{{
                  task.image || (task.task_type ? task.task_type : "未知")
                }}</code>
                <div
                  v-if="
                    task.selected_services && task.selected_services.length > 0
                  "
                  class="mt-1"
                >
                  <span class="badge bg-info me-1" style="font-size: 0.7rem">
                    <i class="fas fa-layer-group"></i> 多服务 ({{
                      task.selected_services.length
                    }})
                  </span>
                  <div class="d-flex flex-wrap gap-1 mt-1">
                    <span
                      v-for="service in task.selected_services.slice(0, 5)"
                      :key="service"
                      class="badge bg-secondary"
                      style="font-size: 0.65rem"
                    >
                      {{ service }}
                    </span>
                    <span
                      v-if="task.selected_services.length > 5"
                      class="badge bg-secondary"
                      style="font-size: 0.65rem"
                    >
                      +{{ task.selected_services.length - 5 }}
                    </span>
                  </div>
                </div>
                <span
                  v-else-if="
                    task.push_mode === 'multi' && !task.selected_services
                  "
                  class="badge bg-secondary me-1"
                  style="font-size: 0.7rem"
                >
                  <i class="fas fa-cube"></i> 单应用
                </span>
              </div>
            </td>
            <td>
              <div>
                <!-- 分支显示 -->
                <div v-if="task.branch" class="mb-1">
                  <span class="badge bg-primary" style="font-size: 0.75rem">
                    <i class="fas fa-code-branch"></i> {{ task.branch }}
                  </span>
                </div>
                <!-- Tag显示 -->
                <div v-if="task.tag">
                  <span class="badge bg-info" style="font-size: 0.75rem">
                    <i class="fas fa-tag"></i> {{ task.tag }}
                  </span>
                </div>
                <!-- 如果都没有，显示占位符 -->
                <small v-if="!task.branch && !task.tag" class="text-muted"
                  >-</small
                >
              </div>
            </td>
            <td>
              <!-- 优先按 trigger_source 显示来源 -->
              <span
                v-if="task.trigger_source === 'webhook'"
                class="badge bg-info"
              >
                <i class="fas fa-link"></i> Webhook
              </span>
              <span
                v-else-if="task.source === '流水线'"
                class="badge bg-primary"
              >
                <i class="fas fa-project-diagram"></i> 流水线
              </span>
              <span v-else-if="task.source === 'Git源码'" class="badge bg-info">
                <i class="fas fa-code-branch"></i> Git源码
              </span>
              <span
                v-else-if="task.source === '文件上传'"
                class="badge bg-success"
              >
                <i class="fas fa-upload"></i> 文件上传
              </span>
              <span
                v-else-if="
                  task.source === '镜像构建' || task.source === '分步构建'
                "
                class="badge bg-warning"
              >
                <i class="fas fa-list-ol"></i> 镜像构建
              </span>
              <span v-else class="badge bg-secondary">
                <i class="fas fa-hammer"></i> {{ task.source || "手动构建" }}
              </span>
            </td>
            <td>
              <span v-if="task.status === 'pending'" class="badge bg-secondary">
                <i class="fas fa-clock"></i> 等待中
              </span>
              <span
                v-else-if="task.status === 'running'"
                class="badge bg-primary"
              >
                <span class="spinner-border spinner-border-sm me-1"></span>
                进行中
              </span>
              <span
                v-else-if="task.status === 'stopped'"
                class="badge bg-warning"
              >
                <i class="fas fa-stop-circle"></i> 已停止
              </span>
              <span
                v-else-if="task.status === 'completed'"
                class="badge bg-success"
              >
                <i class="fas fa-check-circle"></i> 已完成
              </span>
              <span
                v-else-if="task.status === 'failed'"
                class="badge bg-danger"
              >
                <i class="fas fa-times-circle"></i> 失败
              </span>
            </td>
            <td class="small text-muted">
              {{ formatTime(task.created_at) }}
            </td>
            <td class="small">
              <span v-if="task.status === 'running'" class="text-primary">
                <span
                  class="spinner-border spinner-border-sm me-1"
                  style="width: 0.7rem; height: 0.7rem"
                ></span>
                {{ calculateDuration(task.created_at, null) }}
              </span>
              <span
                v-else-if="task.completed_at"
                :class="{
                  'text-success': task.status === 'completed',
                  'text-danger': task.status === 'failed',
                }"
              >
                {{ calculateDuration(task.created_at, task.completed_at) }}
              </span>
              <span v-else class="text-muted">-</span>
            </td>
            <td class="small">
              <span v-if="task.file_size">{{
                formatFileSize(task.file_size)
              }}</span>
              <span v-else>-</span>
            </td>
            <td class="text-end">
              <div class="d-flex gap-1 justify-content-end flex-wrap">
                <!-- 构建任务操作 -->
                <template v-if="task.task_category === 'build'">
                  <button
                    class="btn btn-sm btn-outline-info"
                    @click="viewLogs(task)"
                    :disabled="viewingLogs === task.task_id"
                    :title="'查看构建日志'"
                  >
                    <i class="fas fa-terminal"></i>
                  </button>
                  <button
                    v-if="task.source !== '流水线' && !task.pipeline_id"
                    class="btn btn-sm btn-outline-primary"
                    @click="saveAsPipeline(task)"
                    :title="'另存为流水线'"
                  >
                    <i class="fas fa-save"></i>
                  </button>
                  <button
                    v-if="task.status === 'failed'"
                    class="btn btn-sm btn-outline-warning"
                    @click="rebuildTask(task)"
                    :disabled="rebuilding === task.task_id"
                    :title="'重新构建'"
                  >
                    <i class="fas fa-redo"></i>
                    <span
                      v-if="rebuilding === task.task_id"
                      class="spinner-border spinner-border-sm ms-1"
                    ></span>
                  </button>
                  <button
                    class="btn btn-sm btn-outline-secondary"
                    @click="viewTaskConfig(task)"
                    :title="'查看配置JSON'"
                  >
                    <i class="fas fa-code"></i>
                  </button>
                </template>

                <!-- 导出任务操作 -->
                <template v-if="task.task_category === 'export'">
                  <button
                    v-if="task.status === 'completed'"
                    class="btn btn-sm btn-success"
                    @click="downloadTask(task)"
                    :disabled="downloading === task.task_id"
                    :title="'下载导出文件'"
                  >
                    <i class="fas fa-download"></i>
                    <span
                      v-if="downloading === task.task_id"
                      class="spinner-border spinner-border-sm ms-1"
                    ></span>
                  </button>
                  <button
                    v-if="task.status === 'failed'"
                    class="btn btn-sm btn-outline-warning"
                    @click="retryExportTask(task)"
                    :disabled="retrying === task.task_id"
                    :title="'重试导出'"
                  >
                    <i class="fas fa-redo"></i>
                    <span
                      v-if="retrying === task.task_id"
                      class="spinner-border spinner-border-sm ms-1"
                    ></span>
                  </button>
                </template>

                <!-- 停止/删除按钮 -->
                <button
                  class="btn btn-sm"
                  :class="
                    task.status === 'running' || task.status === 'pending'
                      ? 'btn-outline-warning'
                      : 'btn-outline-danger'
                  "
                  @click="
                    task.status === 'running' || task.status === 'pending'
                      ? stopTask(task)
                      : deleteTask(task)
                  "
                  :disabled="
                    task.status === 'running' || task.status === 'pending'
                      ? stopping === task.task_id
                      : deleting === task.task_id
                  "
                  :title="
                    task.status === 'running' || task.status === 'pending'
                      ? '停止任务'
                      : '删除任务'
                  "
                >
                  <i
                    :class="
                      task.status === 'running' || task.status === 'pending'
                        ? 'fas fa-stop'
                        : 'fas fa-trash'
                    "
                  ></i>
                  <span
                    v-if="
                      (task.status === 'running' ||
                        task.status === 'pending') &&
                      stopping === task.task_id
                    "
                    class="spinner-border spinner-border-sm ms-1"
                  ></span>
                  <span
                    v-if="
                      task.status !== 'running' &&
                      task.status !== 'pending' &&
                      deleting === task.task_id
                    "
                    class="spinner-border spinner-border-sm ms-1"
                  ></span>
                </button>
              </div>
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
        显示第 {{ (currentPage - 1) * pageSize + 1 }} -
        {{ Math.min(currentPage * pageSize, totalTasks) }} 条，共
        {{ totalTasks }} 条
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

    <!-- 日志模态框 -->
    <TaskLogModal
      v-model="showLogModal"
      :task="selectedTask"
      @task-status-updated="onTaskStatusUpdated"
    />
  </div>

  <!-- 任务配置JSON模态框 -->
  <div
    v-if="showConfigModal"
    class="modal fade show"
    style="display: block"
    tabindex="-1"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title"><i class="fas fa-code"></i> 任务配置JSON</h5>
          <button
            type="button"
            class="btn-close"
            @click="showConfigModal = false"
          ></button>
        </div>
        <div class="modal-body">
          <div class="d-flex justify-content-end mb-2">
            <button
              class="btn btn-sm btn-outline-primary"
              @click="copyTaskConfigJson"
            >
              <i class="fas fa-copy"></i> 复制JSON
            </button>
          </div>
          <codemirror
            v-model="taskConfigJsonText"
            :style="{ height: '500px', fontSize: '13px' }"
            :disabled="true"
            :extensions="jsonEditorExtensions"
          />
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-secondary"
            @click="showConfigModal = false"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-if="showConfigModal" class="modal-backdrop fade show"></div>

  <!-- 另存为流水线模态框 -->
  <div
    v-if="showSaveAsPipelineModal"
    class="modal fade show"
    style="display: block"
    tabindex="-1"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title"><i class="fas fa-save"></i> 另存为流水线</h5>
          <button
            type="button"
            class="btn-close"
            @click="showSaveAsPipelineModal = false"
          ></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label"
              >流水线名称 <span class="text-danger">*</span></label
            >
            <input
              v-model="pipelineForm.name"
              type="text"
              class="form-control"
              placeholder="请输入流水线名称"
              required
            />
          </div>
          <div class="mb-3">
            <label class="form-label">描述</label>
            <textarea
              v-model="pipelineForm.description"
              class="form-control"
              rows="2"
              placeholder="请输入描述（可选）"
            ></textarea>
          </div>
          <div class="alert alert-info">
            <i class="fas fa-info-circle"></i>
            流水线将使用任务的完整配置，包括Git地址、分支、镜像名称、构建参数等。
          </div>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-secondary"
            @click="showSaveAsPipelineModal = false"
          >
            取消
          </button>
          <button
            type="button"
            class="btn btn-primary"
            @click="savePipelineFromTask"
            :disabled="saving"
          >
            <span
              v-if="saving"
              class="spinner-border spinner-border-sm me-1"
            ></span>
            {{ saving ? "保存中..." : "保存" }}
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-if="showSaveAsPipelineModal" class="modal-backdrop fade show"></div>
</template>

<script setup>
import { StreamLanguage } from "@codemirror/language";
import { javascript } from "@codemirror/legacy-modes/mode/javascript";
import { oneDark } from "@codemirror/theme-one-dark";
import axios from "axios";
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { Codemirror } from "vue-codemirror";
import TaskLogModal from "./TaskLogModal.vue";

const tasks = ref([]);
const loading = ref(false);
const error = ref(null);
const statusFilter = ref("");
const categoryFilter = ref("");
const downloading = ref(null);
const deleting = ref(null);
const rebuilding = ref(null); // 重建中的任务ID
const retrying = ref(null); // 重试中的任务ID
const stopping = ref(null); // 停止中的任务ID
const viewingLogs = ref(null);
const showLogModal = ref(false);
const selectedTask = ref(null);
// 错误弹窗已移除，错误信息现在显示在日志顶部
const currentPage = ref(1); // 当前页码
const pageSize = ref(10); // 每页显示数量
const cleaning = ref(false); // 清理中状态
const buildDirSize = ref("0 MB"); // 编译目录容量
const buildDirCount = ref(0); // 编译目录数量
const exportDirSize = ref("0 MB"); // 下载目录容量
const exportDirCount = ref(0); // 下载目录文件数量
const saving = ref(false); // 保存中状态
const showConfigModal = ref(false); // 任务配置JSON模态框
const taskConfigJson = ref(""); // 任务配置JSON
const taskConfigJsonText = ref(""); // JSON文本内容（用于CodeMirror）

// CodeMirror 扩展配置（JSON模式，使用JavaScript模式）
const jsonEditorExtensions = [StreamLanguage.define(javascript), oneDark];

const showSaveAsPipelineModal = ref(false); // 另存为流水线模态框
const pipelineForm = ref({
  name: "",
  description: "",
  git_url: "",
  branch: "",
  image_name: "",
  tag: "",
  project_type: "",
  template: "",
  template_params: {},
  sub_path: "",
  use_project_dockerfile: true,
  dockerfile_name: "Dockerfile",
  source_id: null,
  push: false,
  selected_services: null,
  service_push_config: null,
  service_template_params: null,
  push_mode: "multi",
  resource_package_configs: null,
  trigger_webhook: true,
  trigger_schedule: false,
  cron_expression: "",
  webhook_branch_filter: false,
  webhook_use_push_branch: true,
  branch_tag_mapping: null,
  enabled: true,
});
let refreshInterval = null;

const filteredTasks = computed(() => {
  let result = tasks.value;
  if (statusFilter.value) {
    result = result.filter((t) => t.status === statusFilter.value);
  }
  if (categoryFilter.value) {
    result = result.filter((t) => t.task_category === categoryFilter.value);
  }
  return result;
});

// 总任务数
const totalTasks = computed(() => filteredTasks.value.length);

// 总页数
const totalPages = computed(() => Math.ceil(totalTasks.value / pageSize.value));

// 当前页的任务列表
const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredTasks.value.slice(start, end);
});

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
}

// 重置到第1页（切换过滤条件时）
function resetPage() {
  currentPage.value = 1;
}

// handleLogsOrError 函数已移除，统一使用 viewLogs 函数
// 错误弹窗相关函数已移除，错误信息现在显示在日志顶部

function formatTime(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString);

  // 显示完整精确时间（包括年月日时分秒）
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

function calculateDuration(startTime, endTime) {
  if (!startTime) return "-";

  const start = new Date(startTime);
  const end = endTime ? new Date(endTime) : new Date();

  const diffMs = end - start;
  if (diffMs < 0) return "-";

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}小时${minutes % 60}分`;
  } else if (minutes > 0) {
    return `${minutes}分${seconds % 60}秒`;
  } else {
    return `${seconds}秒`;
  }
}

// 加载编译目录统计信息
async function loadBuildDirStats() {
  try {
    const res = await axios.get("/api/docker-build/stats");
    if (res.data.success) {
      buildDirSize.value =
        res.data.total_size_mb > 0 ? `${res.data.total_size_mb} MB` : "0 MB";
      buildDirCount.value = res.data.dir_count || 0;
    }
  } catch (err) {
    console.error("获取编译目录统计失败:", err);
    buildDirSize.value = "0 MB";
    buildDirCount.value = 0;
  }
}

// 加载下载目录统计信息
async function loadExportDirStats() {
  try {
    const res = await axios.get("/api/exports/stats");
    if (res.data.success) {
      exportDirSize.value =
        res.data.total_size_mb > 0 ? `${res.data.total_size_mb} MB` : "0 MB";
      exportDirCount.value = res.data.file_count || 0;
    }
  } catch (err) {
    console.error("获取下载目录统计失败:", err);
    exportDirSize.value = "0 MB";
    exportDirCount.value = 0;
  }
}

async function loadTasks() {
  loading.value = true;
  error.value = null;

  // 同时加载编译目录和下载目录统计
  await Promise.all([loadBuildDirStats(), loadExportDirStats()]);

  try {
    const params = {};
    if (statusFilter.value) params.status = statusFilter.value;
    const res = await axios.get("/api/tasks", { params });
    tasks.value = res.data.tasks || [];
  } catch (err) {
    error.value =
      err.response?.data?.error || err.message || "加载任务列表失败";
    console.error("加载任务列表失败:", err);
  } finally {
    loading.value = false;
  }
}

// 只刷新运行中任务的状态（不刷新整个页面）
async function refreshRunningTasks() {
  try {
    // 获取所有运行中的任务ID
    const runningTaskIds = tasks.value
      .filter((t) => t.status === "running" || t.status === "pending")
      .map((t) => ({ id: t.task_id, category: t.task_category }));

    if (runningTaskIds.length === 0) {
      return;
    }

    // 逐个更新运行中任务的状态
    for (const { id, category } of runningTaskIds) {
      try {
        let updatedTask = null;
        if (category === "build") {
          const res = await axios.get(`/api/build-tasks/${id}`);
          updatedTask = res.data;
        } else if (category === "export") {
          const res = await axios.get(`/api/export-tasks/${id}`);
          updatedTask = res.data.task;
        }

        if (updatedTask) {
          // 更新对应任务的状态
          const index = tasks.value.findIndex((t) => t.task_id === id);
          if (index !== -1) {
            const oldStatus = tasks.value[index].status;
            const newStatus = updatedTask.status;

            // 只更新状态相关字段，保留其他字段（不刷新整个列表）
            tasks.value[index].status = newStatus;
            tasks.value[index].completed_at = updatedTask.completed_at;
            tasks.value[index].error = updatedTask.error;
            tasks.value[index].file_size = updatedTask.file_size;

            // 如果任务完成，更新其他可能变化的字段
            if (
              newStatus === "completed" ||
              newStatus === "failed" ||
              newStatus === "stopped"
            ) {
              // 更新所有可能变化的字段，确保数据完整
              Object.assign(tasks.value[index], {
                status: newStatus,
                completed_at: updatedTask.completed_at,
                error: updatedTask.error,
                file_size: updatedTask.file_size,
              });
            }
          }
        }
      } catch (err) {
        // 单个任务更新失败不影响其他任务
        console.error(`更新任务 ${id} 状态失败:`, err);
      }
    }
    // 不再调用 loadTasks()，避免刷新整个页面
  } catch (err) {
    console.error("刷新运行中任务状态失败:", err);
  }
}

// 任务状态更新处理（不刷新整个页面，只更新当前任务状态）
function onTaskStatusUpdated(newStatus) {
  if (selectedTask.value) {
    selectedTask.value.status = newStatus;
    // 更新任务列表中的对应任务状态，不刷新整个列表
    const index = tasks.value.findIndex(
      (t) => t.task_id === selectedTask.value.task_id
    );
    if (index !== -1) {
      tasks.value[index].status = newStatus;
    }
  }
}

async function viewLogs(task) {
  if (viewingLogs.value) return;

  viewingLogs.value = task.task_id;
  selectedTask.value = task;
  showLogModal.value = true;

  viewingLogs.value = null;
}

// 查看任务配置JSON
async function viewTaskConfig(task) {
  try {
    const res = await axios.get(`/api/build-tasks/${task.task_id}/config`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    });

    taskConfigJson.value = JSON.stringify(res.data, null, 2);
    taskConfigJsonText.value = taskConfigJson.value;
    showConfigModal.value = true;
  } catch (err) {
    console.error("获取任务配置失败:", err);
    const errorMsg =
      err.response?.data?.detail || err.message || "获取任务配置失败";
    alert(`获取任务配置失败: ${errorMsg}`);
  }
}

// 复制JSON到剪贴板（带降级方案）
async function copyTaskConfigJson() {
  const text = taskConfigJson.value;

  // 优先使用 Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      alert("JSON配置已复制到剪贴板");
      return;
    } catch (err) {
      console.warn("Clipboard API 失败，尝试降级方案:", err);
    }
  }

  // 降级方案：使用传统的选择文本方式
  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, text.length);

    const successful = document.execCommand("copy");
    document.body.removeChild(textarea);

    if (successful) {
      alert("JSON配置已复制到剪贴板");
    } else {
      throw new Error("execCommand 复制失败");
    }
  } catch (err) {
    console.error("复制失败:", err);
    alert("自动复制失败，请手动选择并复制文本（已自动选中）");
    nextTick(() => {
      const editor = document.querySelector(".cm-editor");
      if (editor) {
        const range = document.createRange();
        range.selectNodeContents(editor);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
    });
  }
}

// 另存为流水线
async function saveAsPipeline(task) {
  try {
    // 获取任务配置
    const res = await axios.get(`/api/build-tasks/${task.task_id}/config`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    });

    const config = res.data;

    // 填充流水线表单
    pipelineForm.value = {
      name: `${task.image || "任务"}_${task.tag || "latest"}_${new Date()
        .toISOString()
        .slice(0, 10)}`,
      description: `从任务 ${task.task_id.slice(0, 8)} 创建${
        task.source === "流水线" ? "（流水线触发）" : ""
      }`,
      git_url: config.git_url || "",
      branch: config.branch || "",
      image_name: config.image_name || task.image || "",
      tag: config.tag || task.tag || "latest",
      project_type: config.project_type || "jar",
      template: config.template || "",
      template_params: config.template_params || {},
      sub_path: config.sub_path || "",
      use_project_dockerfile: config.use_project_dockerfile !== false,
      dockerfile_name: config.dockerfile_name || "Dockerfile",
      source_id: config.source_id || null,
      push: config.should_push || config.push || false,
      selected_services: config.selected_services || null,
      service_push_config: config.service_push_config || null,
      service_template_params: config.service_template_params || null,
      push_mode: config.push_mode || "multi",
      resource_package_configs:
        config.resource_package_configs || config.resource_package_ids || null,
      trigger_webhook: true,
      trigger_schedule: false,
      cron_expression: "",
      webhook_branch_filter: false,
      webhook_use_push_branch: true,
      branch_tag_mapping: null,
      enabled: true,
    };

    showSaveAsPipelineModal.value = true;
  } catch (err) {
    console.error("获取任务配置失败:", err);
    const errorMsg =
      err.response?.data?.detail || err.message || "获取任务配置失败";
    alert(`获取任务配置失败: ${errorMsg}`);
  }
}

async function downloadTask(task) {
  if (downloading.value) return;

  downloading.value = task.task_id;

  try {
    // 直接通过URL触发浏览器下载
    const downloadUrl = `/api/export-tasks/${task.task_id}/download`;

    // 生成文件名
    const image = task.image.replace(/\//g, "_");
    const tag = task.tag || "latest";
    const isCompressed =
      task.compress &&
      ["gzip", "gz", "tgz", "1", "true", "yes"].includes(
        task.compress.toLowerCase()
      );
    const ext = isCompressed ? ".tar.gz" : ".tar";
    const filename = `${image}-${tag}${ext}`;

    // 创建临时a标签，直接指向下载URL，让浏览器原生处理下载
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename; // 设置下载文件名
    a.style.display = "none";

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // 下载完成后清除loading状态（延迟一下确保下载已开始）
    setTimeout(() => {
      downloading.value = null;
    }, 500);
  } catch (err) {
    console.error("下载失败:", err);
    const errorMsg = err.message || "下载失败";
    error.value = `下载失败: ${errorMsg}`;
    // 3秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("下载失败")) {
        error.value = null;
      }
    }, 3000);
    downloading.value = null;
  }
}

async function stopTask(task) {
  if (stopping.value) return;

  // 确认对话框
  const taskName = task.image || task.task_type || "未知任务";
  const taskTag = task.tag || "latest";
  if (!confirm(`确定要停止任务 "${taskName}:${taskTag}" 吗？`)) {
    return;
  }

  stopping.value = task.task_id;
  error.value = null;

  try {
    if (task.task_category === "build") {
      await axios.post(`/api/build-tasks/${task.task_id}/stop`);
    } else {
      await axios.post(`/api/export-tasks/${task.task_id}/stop`);
    }

    // 刷新任务列表
    await loadTasks();
  } catch (err) {
    console.error("停止任务失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      "停止失败";
    error.value = `停止任务失败: ${errorMsg}`;
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("停止任务失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    stopping.value = null;
  }
}

async function deleteTask(task) {
  const taskName = task.image || task.task_type || "未知任务";
  const taskTag = task.tag || "-";
  const status = task.status;

  // 检查任务状态
  if (status === "running" || status === "pending") {
    alert(
      `无法删除任务：只有停止、完成或失败的任务才能删除（当前状态: ${
        status === "running" ? "进行中" : "等待中"
      }）\n\n请先停止任务。`
    );
    return;
  }

  if (!confirm(`确定要删除任务 "${taskName}:${taskTag}" 吗？`)) {
    return;
  }

  deleting.value = task.task_id;
  try {
    if (task.task_category === "build") {
      await axios.delete(`/api/build-tasks/${task.task_id}`);
    } else {
      await axios.delete(`/api/export-tasks/${task.task_id}`);
    }
    // 成功删除后刷新列表
    await loadTasks();
  } catch (err) {
    console.error("删除任务失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      "删除失败";
    error.value = `删除任务失败: ${errorMsg}`;
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("删除任务失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    deleting.value = null;
  }
}

async function cleanupAll() {
  if (cleaning.value) return;

  if (
    !confirm(
      `确定要清理所有非运行中的任务吗？\n\n这将清理所有已完成、失败、已停止的任务，清理后的任务无法恢复，请谨慎操作！`
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    const res = await axios.post("/api/tasks/cleanup", {});

    alert(`成功清理 ${res.data.removed_count} 个任务`);
    await loadTasks();
  } catch (err) {
    console.error("清理全部任务失败:", err);
    alert(err.response?.data?.detail || "清理失败");
  } finally {
    cleaning.value = false;
  }
}

async function cleanupByStatus(status) {
  if (cleaning.value) return;

  const statusText = status === "completed" ? "已完成" : "失败";
  if (
    !confirm(
      `确定要清理所有${statusText}的任务吗？\n\n清理后的任务无法恢复，请谨慎操作！`
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    const res = await axios.post("/api/tasks/cleanup", {
      status: status,
    });

    alert(`成功清理 ${res.data.removed_count} 个任务`);
    await loadTasks();
  } catch (err) {
    console.error("清理任务失败:", err);
    alert(err.response?.data?.detail || "清理失败");
  } finally {
    cleaning.value = false;
  }
}

async function cleanupByDaysPrompt() {
  if (cleaning.value) return;

  const daysInput = prompt(
    "请输入要清理的天数（例如：7 表示清理7天前的任务）：",
    "7"
  );
  if (!daysInput) {
    return;
  }

  const days = parseInt(daysInput);
  if (isNaN(days) || days < 1) {
    alert("请输入有效的天数（必须大于0）");
    return;
  }

  if (
    !confirm(
      `确定要清理 ${days} 天前的所有任务吗？\n\n清理后的任务无法恢复，请谨慎操作！`
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    const res = await axios.post("/api/tasks/cleanup", {
      days: days,
    });

    alert(`成功清理 ${res.data.removed_count} 个任务`);
    await loadTasks();
  } catch (err) {
    console.error("清理任务失败:", err);
    alert(err.response?.data?.detail || "清理失败");
  } finally {
    cleaning.value = false;
  }
}

async function cleanupOrphanDirs() {
  if (cleaning.value) return;

  if (
    !confirm(
      "确定要清理所有异常目录吗？\n\n此操作将删除所有没有对应任务的构建上下文目录，无法恢复，请谨慎操作！"
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    console.log("开始清理异常目录...");
    const res = await axios.post("/api/docker-build/cleanup", {
      cleanup_orphans_only: true,
    });

    console.log("清理异常目录响应:", res);
    console.log("响应数据:", res.data);

    // 检查响应数据
    if (res.data) {
      if (res.data.success === true) {
        const removedCount = res.data.removed_count || 0;
        const freedSpace = res.data.freed_space_mb || 0;
        let message =
          res.data.message ||
          `成功清理 ${removedCount} 个异常目录，释放空间 ${freedSpace} MB`;

        if (res.data.errors && res.data.errors.length > 0) {
          message += `\n\n部分目录清理失败: ${res.data.errors.length} 个`;
        }

        alert(message);

        // 刷新统计信息
        await Promise.all([loadBuildDirStats(), loadExportDirStats()]);
      } else {
        const errorMsg = res.data.message || res.data.detail || "清理失败";
        alert(typeof errorMsg === "string" ? errorMsg : String(errorMsg));
      }
    } else {
      console.warn("响应数据为空");
      alert("清理完成，但未收到响应数据");
      await Promise.all([loadBuildDirStats(), loadExportDirStats()]);
    }
  } catch (err) {
    console.error("清理异常目录失败:", err);
    let errorMsg = "清理失败";
    if (err.response) {
      if (err.response.data) {
        if (typeof err.response.data.detail === "string") {
          errorMsg = err.response.data.detail;
        } else if (typeof err.response.data.message === "string") {
          errorMsg = err.response.data.message;
        } else if (err.response.data.detail) {
          errorMsg = String(err.response.data.detail);
        } else {
          errorMsg = `清理失败: ${err.response.status} ${
            err.response.statusText || ""
          }`;
        }
      } else {
        errorMsg = `清理失败: ${err.response.status} ${
          err.response.statusText || ""
        }`;
      }
    } else if (err.message) {
      errorMsg = `清理失败: ${err.message}`;
    }

    alert(errorMsg);
  } finally {
    cleaning.value = false;
  }
}

async function cleanupBuildDir() {
  if (cleaning.value) return;

  if (
    !confirm(
      "确定要清空所有编译目录吗？\n\n此操作将删除所有构建上下文目录，无法恢复，请谨慎操作！"
    )
  ) {
    return;
  }

  cleaning.value = true;
  error.value = null;

  try {
    console.log("开始清理编译目录...");
    const res = await axios.post("/api/docker-build/cleanup", {
      keep_days: 0,
    });

    console.log("清理目录响应:", res);
    console.log("响应数据:", res.data);

    // 检查响应数据
    if (res.data) {
      if (res.data.success === true) {
        // 成功情况
        const removedCount = res.data.removed_count || 0;
        const freedSpace = res.data.freed_space_mb || 0;
        let message =
          res.data.message ||
          `成功清空编译目录，删除了 ${removedCount} 个目录，释放空间 ${freedSpace} MB`;

        // 如果有错误信息，也显示出来
        if (res.data.errors && res.data.errors.length > 0) {
          message += `\n\n部分目录清理失败: ${res.data.errors.length} 个`;
        }

        alert(message);

        // 刷新统计信息
        await Promise.all([loadBuildDirStats(), loadExportDirStats()]);
      } else {
        // 失败情况
        const errorMsg = res.data.message || res.data.detail || "清理失败";
        alert(typeof errorMsg === "string" ? errorMsg : String(errorMsg));
      }
    } else {
      console.warn("响应数据为空");
      alert("清理完成，但未收到响应数据");
      // 仍然刷新统计信息
      await loadBuildDirStats();
    }
  } catch (err) {
    console.error("清理编译目录失败:", err);
    console.error("错误对象:", err);
    console.error("错误响应:", err.response);
    console.error("错误数据:", err.response?.data);

    let errorMsg = "清理失败";
    if (err.response) {
      if (err.response.data) {
        if (typeof err.response.data.detail === "string") {
          errorMsg = err.response.data.detail;
        } else if (typeof err.response.data.message === "string") {
          errorMsg = err.response.data.message;
        } else if (err.response.data.detail) {
          errorMsg = String(err.response.data.detail);
        } else {
          errorMsg = `清理失败: ${err.response.status} ${
            err.response.statusText || ""
          }`;
        }
      } else {
        errorMsg = `清理失败: ${err.response.status} ${
          err.response.statusText || ""
        }`;
      }
    } else if (err.message) {
      errorMsg = `清理失败: ${err.message}`;
    }

    alert(errorMsg);
  } finally {
    cleaning.value = false;
  }
}

// 清理下载目录
async function cleanupExportDir() {
  if (cleaning.value) return;

  if (
    !confirm(
      "确定要清空所有下载文件吗？\n\n此操作将删除所有导出文件，无法恢复，请谨慎操作！"
    )
  ) {
    return;
  }

  cleaning.value = true;

  try {
    const res = await axios.post("/api/exports/cleanup", {
      keep_tasks: true, // 保留任务元数据
    });

    if (res.data.success) {
      const removedCount = res.data.removed_count || 0;
      const freedSpace = res.data.freed_space_mb || 0;
      const message =
        res.data.message ||
        `成功清理了 ${removedCount} 个文件，释放空间 ${freedSpace} MB`;
      alert(message);
      await loadExportDirStats(); // 重新加载统计
    } else {
      alert(res.data.message || res.data.detail || "清理失败");
    }
  } catch (err) {
    console.error("清理下载目录失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      "清理失败";
    alert(errorMsg);
  } finally {
    cleaning.value = false;
  }
}

// 清理N天前的下载文件
async function cleanupExportDirDays() {
  if (cleaning.value) return;

  const days = prompt(
    "请输入要清理多少天前的文件（例如：7 表示清理7天前的文件）："
  );
  if (!days || isNaN(days) || parseInt(days) <= 0) {
    return;
  }

  if (
    !confirm(
      `确定要清理 ${days} 天前的下载文件吗？\n\n此操作不可恢复，请谨慎操作！`
    )
  ) {
    return;
  }

  cleaning.value = true;

  try {
    const res = await axios.post("/api/exports/cleanup", {
      days: parseInt(days),
      keep_tasks: true, // 保留任务元数据
    });

    if (res.data.success) {
      const removedCount = res.data.removed_count || 0;
      const freedSpace = res.data.freed_space_mb || 0;
      const message =
        res.data.message ||
        `成功清理了 ${removedCount} 个文件，释放空间 ${freedSpace} MB`;
      alert(message);
      await loadExportDirStats(); // 重新加载统计
    } else {
      alert(res.data.message || res.data.detail || "清理失败");
    }
  } catch (err) {
    console.error("清理下载目录失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      "清理失败";
    alert(errorMsg);
  } finally {
    cleaning.value = false;
  }
}

// 从任务保存为流水线
async function savePipelineFromTask() {
  if (saving.value) return;

  if (!pipelineForm.value.name) {
    alert("请输入流水线名称");
    return;
  }

  if (!pipelineForm.value.git_url) {
    alert("Git 仓库地址不能为空");
    return;
  }

  saving.value = true;
  error.value = null;

  try {
    const payload = {
      name: pipelineForm.value.name,
      description: pipelineForm.value.description,
      git_url: pipelineForm.value.git_url,
      branch: pipelineForm.value.branch,
      project_type: pipelineForm.value.project_type,
      template: pipelineForm.value.template,
      image_name: pipelineForm.value.image_name,
      tag: pipelineForm.value.tag,
      push: pipelineForm.value.push,
      template_params: pipelineForm.value.template_params,
      sub_path: pipelineForm.value.sub_path,
      use_project_dockerfile: pipelineForm.value.use_project_dockerfile,
      dockerfile_name: pipelineForm.value.dockerfile_name || "Dockerfile",
      source_id: pipelineForm.value.source_id || null,
      selected_services: pipelineForm.value.selected_services || null,
      service_push_config: pipelineForm.value.service_push_config || null,
      service_template_params:
        pipelineForm.value.service_template_params || null,
      push_mode: pipelineForm.value.push_mode || "multi",
      resource_package_configs:
        pipelineForm.value.resource_package_configs || null,
      enabled: pipelineForm.value.enabled,
      cron_expression: pipelineForm.value.trigger_schedule
        ? pipelineForm.value.cron_expression
        : null,
      webhook_branch_filter: pipelineForm.value.webhook_branch_filter || false,
      webhook_use_push_branch:
        pipelineForm.value.webhook_use_push_branch !== false,
      branch_tag_mapping: pipelineForm.value.branch_tag_mapping || null,
    };

    await axios.post("/api/pipelines", payload, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
    });

    alert("流水线创建成功！");
    showSaveAsPipelineModal.value = false;
    // 可以跳转到流水线页面或刷新
  } catch (err) {
    console.error("保存流水线失败:", err);
    const errorMsg =
      err.response?.data?.detail || err.message || "保存流水线失败";
    error.value = `保存流水线失败: ${errorMsg}`;
    alert(`保存流水线失败: ${errorMsg}`);
  } finally {
    saving.value = false;
  }
}

// 重新构建任务
async function rebuildTask(task) {
  if (rebuilding.value) return;

  // 确认对话框
  const taskName = task.image || task.task_type || "未知任务";
  const taskTag = task.tag || "latest";
  if (!confirm(`确定要重新构建任务 "${taskName}:${taskTag}" 吗？`)) {
    return;
  }

  rebuilding.value = task.task_id;
  error.value = null;

  try {
    // 优先使用后端重试API，它会使用任务保存的完整JSON配置
    const res = await axios.post(
      `/api/build-tasks/${task.task_id}/retry`,
      {},
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      }
    );

    if (res.data && res.data.new_task_id) {
      alert(`任务重试成功！\n新任务 ID: ${res.data.new_task_id}`);
      await loadTasks(); // 刷新任务列表
    } else {
      throw new Error("重试响应格式错误");
    }
  } catch (err) {
    console.error("重新构建失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      "重新构建失败";
    error.value = `重新构建失败: ${errorMsg}`;
    alert(`重新构建失败: ${errorMsg}`);
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("重新构建失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    rebuilding.value = null;
  }
}

// 重试导出任务
async function retryExportTask(task) {
  if (retrying.value) return;

  // 确认对话框
  const taskName = task.image || "未知任务";
  const taskTag = task.tag || "latest";
  if (!confirm(`确定要重试导出任务 "${taskName}:${taskTag}" 吗？`)) {
    return;
  }

  retrying.value = task.task_id;
  error.value = null;

  try {
    // 从任务信息中提取导出参数
    const config = {
      image: task.image,
      tag: task.tag || "latest",
      compress: task.compress || "none",
      registry: task.registry || null,
      use_local: task.use_local || false,
    };

    // 验证必要参数
    if (!config.image) {
      throw new Error("任务缺少镜像名称，无法重试导出");
    }

    console.log("🔄 重试导出任务:", config);

    // 调用导出 API
    const res = await axios.post("/api/export-tasks", config);

    if (res.data.task_id) {
      alert(`重试导出任务已创建！\n任务 ID: ${res.data.task_id}`);
      // 刷新任务列表
      await loadTasks();
    } else {
      throw new Error("创建任务失败，未返回任务 ID");
    }
  } catch (err) {
    console.error("重试导出失败:", err);
    const errorMsg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      "重试导出失败";
    error.value = `重试导出失败: ${errorMsg}`;
    // 5秒后自动清除错误提示
    setTimeout(() => {
      if (error.value && error.value.includes("重试导出失败")) {
        error.value = null;
      }
    }, 5000);
  } finally {
    retrying.value = null;
  }
}

// 监听任务创建事件
function handleTaskCreated(event) {
  console.log("收到任务创建事件，刷新任务列表:", event.detail);
  // 延迟一下再刷新，确保后端任务已创建完成
  setTimeout(() => {
    loadTasks();
  }, 500);
}

onMounted(() => {
  // 监听任务创建事件
  window.addEventListener("taskCreated", handleTaskCreated);
  // 检查是否有从仪表盘传递过来的筛选条件
  const statusFilterFromStorage = sessionStorage.getItem("taskStatusFilter");
  if (statusFilterFromStorage) {
    statusFilter.value = statusFilterFromStorage;
    sessionStorage.removeItem("taskStatusFilter"); // 使用后清除
  }
  loadTasks();
  // 每3秒自动刷新一次（只更新运行中任务的状态，不刷新整个页面）
  refreshInterval = setInterval(() => {
    refreshRunningTasks();
  }, 3000);
});

onUnmounted(() => {
  // 移除任务创建事件监听器
  window.removeEventListener("taskCreated", handleTaskCreated);

  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<style scoped>
.task-manager {
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

/* 基本信息块样式 */
.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.info-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
}

.info-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.info-card .card-body {
  padding: 1rem 1.25rem;
}

.info-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  flex-shrink: 0;
}

.info-card:first-child .info-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.info-card:last-child .info-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.info-label {
  font-size: 0.85rem;
  color: #6c757d;
  margin-bottom: 0.25rem;
  font-weight: 500;
}

.info-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #212529;
  line-height: 1.2;
  margin-bottom: 0.25rem;
}

.info-sub {
  font-size: 0.75rem;
  color: #adb5bd;
  margin-top: 0.25rem;
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

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
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

/* 操作按钮优化 */
.d-flex.gap-1 .btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
  min-width: 32px;
}

.d-flex.gap-1 .btn i {
  font-size: 0.85rem;
}

/* 表格响应式优化 */
@media (max-width: 1400px) {
  .table th:nth-child(5),
  .table td:nth-child(5) {
    display: none;
  }
}

@media (max-width: 1200px) {
  .table th:nth-child(7),
  .table td:nth-child(7) {
    display: none;
  }
}
</style>

<template>
  <div class="image-migration-panel">
    <PageToolbar title="镜像迁移" icon="fa-right-left">
      <template #actions>
        <Button variant="outline" size="sm" :disabled="loading" @click="loadTasks">
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
          刷新
        </Button>
        <Button size="sm" @click="openCreateDialog">
          <i class="fas fa-plus"></i>
          新建迁移
        </Button>
      </template>
    </PageToolbar>

    <p class="mb-4 text-sm text-slate-600">
      选择已在「镜像仓库」中配置的源/目标仓库；镜像前缀随仓库配置，只需填写路径与标签。支持常用定时或自定义 Cron。
    </p>

    <div v-if="loading && !tasks.length" class="flex justify-center py-12 text-slate-500">
      <i class="fas fa-spinner fa-spin mr-2"></i> 加载中…
    </div>

    <EmptyState
      v-else-if="!tasks.length"
      message='暂无迁移任务，点击「新建迁移」创建'
      icon="fa-right-left"
    />

    <div v-else class="overflow-x-auto rounded-lg border border-slate-200">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>任务名称</TableHead>
            <TableHead>源镜像</TableHead>
            <TableHead>目标镜像</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>定时</TableHead>
            <TableHead>执行次数</TableHead>
            <TableHead>上次执行</TableHead>
            <TableHead class="text-end">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="task in tasks" :key="task.task_id">
            <TableCell class="font-medium">{{ task.task_name || "-" }}</TableCell>
            <TableCell>
              <code class="text-xs">{{ task.source_image }}</code>
            </TableCell>
            <TableCell>
              <code class="text-xs">{{ task.target_image }}</code>
            </TableCell>
            <TableCell>
              <Badge v-if="task.status === 'idle'" variant="default">空闲</Badge>
              <Badge v-else-if="task.status === 'pending'">
                <i class="fas fa-clock mr-1"></i>排队中
              </Badge>
              <Badge v-else-if="task.status === 'running'" variant="info">
                <i class="fas fa-spinner fa-spin mr-1"></i>迁移中
              </Badge>
              <Badge v-else-if="task.status === 'completed'" variant="success">成功</Badge>
              <Badge v-else-if="task.status === 'failed'" variant="danger">失败</Badge>
              <Badge v-else-if="task.status === 'stopped'" variant="warning">已停止</Badge>
              <span v-else>{{ task.status }}</span>
            </TableCell>
            <TableCell class="text-sm">
              <span v-if="task.schedule_enabled && task.schedule_cron">
                <i class="fas fa-clock text-blue-500 mr-1"></i>
                <span>{{ cronPresetLabel(task.schedule_cron) }}</span>
                <code class="ml-1 text-xs text-slate-500">{{ task.schedule_cron }}</code>
              </span>
              <span v-else class="text-slate-400">仅手动</span>
            </TableCell>
            <TableCell>{{ task.run_count || 0 }}</TableCell>
            <TableCell class="text-sm text-slate-500">
              <div v-if="task.last_run_at">{{ formatTime(task.last_run_at) }}</div>
              <div v-if="task.last_run_status" class="text-xs">
                {{ task.last_run_status === "completed" ? "成功" : task.last_run_status === "failed" ? "失败" : "" }}
              </div>
              <span v-if="!task.last_run_at">-</span>
            </TableCell>
            <TableCell class="text-end">
              <div class="flex flex-wrap justify-end gap-1">
                <Button
                  size="sm"
                  variant="outline"
                  :disabled="task.status === 'running' || task.status === 'pending' || executingId === task.task_id"
                  title="立即执行"
                  @click="executeTask(task)"
                >
                  <i class="fas fa-play"></i>
                </Button>
                <Button
                  v-if="task.schedule_cron"
                  size="sm"
                  variant="outline"
                  :title="task.schedule_enabled ? '禁用定时' : '启用定时'"
                  @click="toggleSchedule(task)"
                >
                  <i :class="task.schedule_enabled ? 'fas fa-pause' : 'fas fa-clock'"></i>
                </Button>
                <Button
                  v-if="task.status === 'running' || task.status === 'pending'"
                  size="sm"
                  variant="outline"
                  @click="stopTask(task)"
                >
                  <i class="fas fa-stop"></i>
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  :disabled="task.status === 'running'"
                  @click="openEditDialog(task)"
                >
                  <i class="fas fa-edit"></i>
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  :disabled="task.status === 'running'"
                  @click="deleteTask(task)"
                >
                  <i class="fas fa-trash"></i>
                </Button>
              </div>
              <div
                v-if="task.error && task.status === 'failed'"
                class="mt-1 max-w-xs truncate text-left text-xs text-red-600"
                :title="task.error"
              >
                {{ task.error }}
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <FormDialog
      v-model="showDialog"
      :title="editingTaskId ? '编辑迁移任务' : '新建镜像迁移'"
      icon="fa-right-left"
      size="lg"
    >
      <form class="space-y-4" @submit.prevent="saveTask">
        <div
          v-if="!registries.length"
          class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
        >
          请先在「资源与模板 → 镜像仓库」中配置源/目标仓库及认证信息。
        </div>
        <div class="space-y-2">
          <Label>任务名称</Label>
          <Input v-model="form.task_name" type="text" placeholder="例如：nginx 同步到内网" />
        </div>

        <!-- 源仓库 -->
        <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-3">
          <h4 class="text-sm font-semibold text-slate-800">
            <i class="fas fa-download mr-1 text-blue-600"></i> 源仓库
          </h4>
          <div class="space-y-2">
            <Label>镜像仓库 <span class="text-red-600">*</span></Label>
            <NativeSelect v-model="form.source_registry_name" required @change="onSourceRegistryChange">
              <option value="" disabled>请选择源仓库</option>
              <option v-for="reg in registries" :key="reg.registry_id || reg.name" :value="reg.name">
                {{ reg.name }}{{ reg.active ? " (激活)" : "" }}
              </option>
            </NativeSelect>
          </div>
          <div v-if="sourceReg" class="grid gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm md:grid-cols-2">
            <div class="text-slate-600">
              <span class="text-xs text-slate-500">仓库地址</span>
              <div class="font-mono text-slate-800">{{ sourceReg.registry || "docker.io" }}</div>
            </div>
            <div class="text-slate-600">
              <span class="text-xs text-slate-500">镜像前缀（随仓库）</span>
              <div class="font-mono text-slate-800">
                {{ sourceReg.registry_prefix?.trim() || "（无，使用仓库地址拼接）" }}
              </div>
            </div>
          </div>
          <div class="grid gap-3 md:grid-cols-12">
            <div class="space-y-2 md:col-span-8">
              <Label>镜像路径 <span class="text-red-600">*</span></Label>
              <Input
                v-model="form.source_image_path"
                required
                :placeholder="sourcePathPlaceholder"
                @input="onSourceImagePathInput"
                @paste="onSourceImagePaste"
              />
              <p class="text-xs text-slate-500">仅填路径部分，不含前缀；粘贴完整镜像名会自动拆分</p>
            </div>
            <div class="space-y-2 md:col-span-4">
              <Label>标签</Label>
              <Input v-model="form.source_tag" type="text" @input="syncTargetFromSource" />
            </div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <p v-if="sourcePreview" class="flex-1 text-xs text-slate-600">
              完整源镜像：<code class="rounded bg-slate-100 px-1">{{ sourcePreview }}</code>
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              class="shrink-0"
              :disabled="!canTestSourceImage || testingSource"
              @click="testSourceImage"
            >
              <i class="fas fa-vial" :class="{ 'fa-spin': testingSource }"></i>
              {{ testingSource ? "检测中…" : "测试源镜像" }}
            </Button>
          </div>
          <AlertBanner
            v-if="sourceTestResult"
            class="mt-0!"
            :message="sourceTestResult.message"
            :variant="sourceTestResult.success ? 'success' : 'danger'"
          />
          <ul
            v-if="sourceTestResult?.suggestions?.length"
            class="list-inside list-disc text-xs text-slate-600"
          >
            <li v-for="(s, idx) in sourceTestResult.suggestions" :key="idx">{{ s }}</li>
          </ul>
        </div>

        <!-- 目标仓库 -->
        <div class="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-3">
          <h4 class="text-sm font-semibold text-slate-800">
            <i class="fas fa-upload mr-1 text-green-600"></i> 目标仓库
          </h4>
          <div class="space-y-2">
            <Label>镜像仓库 <span class="text-red-600">*</span></Label>
            <NativeSelect v-model="form.target_registry_name" required @change="onTargetRegistryChange">
              <option value="" disabled>请选择目标仓库</option>
              <option v-for="reg in registries" :key="'t-' + (reg.registry_id || reg.name)" :value="reg.name">
                {{ reg.name }}{{ reg.active ? " (激活)" : "" }}
              </option>
            </NativeSelect>
          </div>
          <div v-if="targetReg" class="grid gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm md:grid-cols-2">
            <div class="text-slate-600">
              <span class="text-xs text-slate-500">仓库地址</span>
              <div class="font-mono text-slate-800">{{ targetReg.registry || "docker.io" }}</div>
            </div>
            <div class="text-slate-600">
              <span class="text-xs text-slate-500">镜像前缀（随仓库）</span>
              <div class="font-mono text-slate-800">
                {{ targetReg.registry_prefix?.trim() || "（无，使用仓库地址拼接）" }}
              </div>
            </div>
          </div>
          <div class="grid gap-3 md:grid-cols-12">
            <div class="space-y-2 md:col-span-8">
              <Label>镜像路径 <span class="text-red-600">*</span></Label>
              <Input
                v-model="form.target_image_path"
                required
                :placeholder="targetPathPlaceholder"
              />
            </div>
            <div class="space-y-2 md:col-span-4">
              <Label>标签</Label>
              <Input v-model="form.target_tag" type="text" />
            </div>
          </div>
          <p v-if="targetPreview" class="text-xs text-slate-600">
            完整目标镜像：<code class="rounded bg-slate-100 px-1">{{ targetPreview }}</code>
          </p>
        </div>

        <!-- 定时 -->
        <div class="rounded-lg border border-slate-200 p-3 space-y-3">
          <div class="flex items-center justify-between">
            <Label class="mb-0!">定时执行</Label>
            <label class="flex items-center gap-2 text-sm">
              <input v-model="form.schedule_enabled" type="checkbox" class="h-4 w-4 rounded" />
              启用定时
            </label>
          </div>
          <template v-if="form.schedule_enabled">
            <div class="space-y-2">
              <Label>常用周期</Label>
              <NativeSelect v-model="cronPresetKey" @change="applyCronPreset">
                <option v-for="p in CRON_PRESETS" :key="p.key" :value="p.key">
                  {{ p.label }}
                </option>
              </NativeSelect>
            </div>
            <div class="space-y-2">
              <Label>Cron 表达式</Label>
              <Input
                v-model="form.schedule_cron"
                class="font-mono text-sm"
                placeholder="0 2 * * *"
                @input="onCronManualInput"
              />
              <p class="text-xs text-slate-500">
                分 时 日 月 周；也可从上方选择常用周期后微调。示例：
                <code>*/30 * * * *</code> 每30分钟，
                <code>0 2 * * *</code> 每天2点
              </p>
            </div>
          </template>
          <p v-else class="text-xs text-slate-500">未启用时仅支持手动「立即执行」。</p>
        </div>

        <label v-if="!editingTaskId" class="flex items-center gap-2 text-sm text-slate-700">
          <input v-model="form.execute_now" type="checkbox" class="h-4 w-4 rounded" />
          保存后立即执行一次
        </label>
      </form>
      <template #footer>
        <Button variant="outline" type="button" @click="showDialog = false">取消</Button>
        <Button type="button" :disabled="saving || !registries.length" @click="saveTask">
          <i class="fas fa-save"></i>
          {{ saving ? "保存中…" : "保存" }}
        </Button>
      </template>
    </FormDialog>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";
import axios from "axios";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useTeamStore } from "@/stores/team";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Badge from "@/components/ui/badge/Badge.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";

const CRON_PRESETS = [
  { key: "custom", label: "自定义（手动输入）", cron: "" },
  { key: "30m", label: "每 30 分钟", cron: "*/30 * * * *" },
  { key: "1h", label: "每小时", cron: "0 * * * *" },
  { key: "2h", label: "每 2 小时", cron: "0 */2 * * *" },
  { key: "6h", label: "每 6 小时", cron: "0 */6 * * *" },
  { key: "daily0", label: "每天 0:00", cron: "0 0 * * *" },
  { key: "daily2", label: "每天 2:00", cron: "0 2 * * *" },
  { key: "daily6", label: "每天 6:00", cron: "0 6 * * *" },
  { key: "weekly", label: "每周一 0:00", cron: "0 0 * * 1" },
  { key: "monthly", label: "每月 1 日 0:00", cron: "0 0 1 * *" },
];

const teamStore = useTeamStore();
const tasks = ref([]);
const registries = ref([]);
const loading = ref(false);
const saving = ref(false);
const showDialog = ref(false);
const editingTaskId = ref(null);
const executingId = ref(null);
const testingSource = ref(false);
const sourceTestResult = ref(null);
const cronPresetKey = ref("custom");
let refreshInterval = null;

const emptyForm = () => ({
  task_name: "",
  source_registry_name: "",
  source_image_path: "",
  source_tag: "latest",
  target_registry_name: "",
  target_image_path: "",
  target_tag: "latest",
  schedule_cron: "",
  schedule_enabled: false,
  execute_now: true,
});

const form = ref(emptyForm());

function findRegistry(name) {
  return registries.value.find((r) => r.name === name);
}

const sourceReg = computed(() => findRegistry(form.value.source_registry_name));
const targetReg = computed(() => findRegistry(form.value.target_registry_name));

const sourcePathPlaceholder = computed(() => "myapp/demo");
const targetPathPlaceholder = computed(() => "myapp/demo");

/** 去掉各仓库前缀，得到用户应填写的路径 */
function stripAllRegistryPrefixes(path) {
  let p = (path || "").trim();
  if (!p) return "";
  for (const reg of registries.value) {
    p = stripRegistryPrefix(p, reg);
  }
  return p;
}

function stripRegistryPrefix(path, reg) {
  if (!path || !reg) return path || "";
  let p = path.trim();
  const prefix = (reg.registry_prefix || "").trim();
  const host = (reg.registry || "").trim();
  if (prefix) {
    if (p === prefix) return "";
    if (p.startsWith(`${prefix}/`)) return p.slice(prefix.length + 1);
    if (p.startsWith(prefix)) return p.slice(prefix.length).replace(/^\//, "");
  }
  if (host && host !== "docker.io") {
    if (p === host) return "";
    if (p.startsWith(`${host}/`)) return p.slice(host.length + 1);
  }
  return p;
}

/** 拼接完整镜像引用：前缀随仓库，路径为用户输入 */
function buildFullImageRef(registryName, imagePath, tag) {
  const reg = findRegistry(registryName);
  const rawPath = stripAllRegistryPrefixes(imagePath);
  const t = (tag || "latest").trim() || "latest";
  if (!rawPath && !reg) return "";

  const prefix = (reg?.registry_prefix || "").trim();
  const host = (reg?.registry || "").trim();

  let repo = rawPath;
  if (prefix) {
    repo = rawPath ? `${prefix}/${rawPath}`.replace(/\/+/g, "/") : prefix;
  } else if (host && host !== "docker.io") {
    repo = rawPath ? `${host}/${rawPath}`.replace(/\/+/g, "/") : host;
  }

  if (!repo) return "";
  const lastColon = repo.lastIndexOf(":");
  if (lastColon > 0 && lastColon < repo.length - 1) {
    const after = repo.substring(lastColon + 1);
    if (!after.includes("/")) return repo;
  }
  return `${repo}:${t}`;
}

const sourcePreview = computed(() =>
  buildFullImageRef(
    form.value.source_registry_name,
    form.value.source_image_path,
    form.value.source_tag,
  ),
);

const targetPreview = computed(() =>
  buildFullImageRef(
    form.value.target_registry_name,
    form.value.target_image_path,
    form.value.target_tag,
  ),
);

const canTestSourceImage = computed(
  () =>
    !!form.value.source_registry_name &&
    !!form.value.source_image_path?.trim() &&
    !!sourcePreview.value,
);

function cronPresetLabel(cron) {
  const p = CRON_PRESETS.find((x) => x.cron === cron);
  return p && p.key !== "custom" ? p.label : cron || "-";
}

function matchCronPresetKey(cron) {
  const c = (cron || "").trim();
  const found = CRON_PRESETS.find((p) => p.cron === c);
  return found ? found.key : "custom";
}

function applyCronPreset() {
  const preset = CRON_PRESETS.find((p) => p.key === cronPresetKey.value);
  if (preset && preset.key !== "custom") {
    form.value.schedule_cron = preset.cron;
  }
}

function onCronManualInput() {
  cronPresetKey.value = matchCronPresetKey(form.value.schedule_cron);
}

watch(
  () => form.value.schedule_enabled,
  (enabled) => {
    if (enabled && !form.value.schedule_cron) {
      cronPresetKey.value = "daily2";
      applyCronPreset();
    }
  },
);

function formatTime(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("zh-CN", { hour12: false });
}

function splitImageRef(fullRef) {
  const v = (fullRef || "").trim();
  if (!v) return { path: "", tag: "latest" };
  const lastColon = v.lastIndexOf(":");
  let path = v;
  let tag = "latest";
  if (lastColon > 0 && lastColon < v.length - 1) {
    const after = v.substring(lastColon + 1);
    if (!after.includes("/")) {
      path = v.substring(0, lastColon);
      tag = after.trim() || "latest";
    }
  }
  return { path, tag };
}

function parseSourceImagePathAndTag(inputValue) {
  if (!inputValue || typeof inputValue !== "string") return;
  const { path, tag } = splitImageRef(inputValue);
  form.value.source_image_path = stripAllRegistryPrefixes(path);
  if (tag) form.value.source_tag = tag;
}

function onSourceRegistryChange() {
  sourceTestResult.value = null;
  const reg = findRegistry(form.value.source_registry_name);
  if (!reg) return;
  if (!form.value.source_image_path) {
    form.value.source_image_path = "myapp/demo";
  } else {
    form.value.source_image_path = stripRegistryPrefix(form.value.source_image_path, reg);
  }
  syncTargetFromSource();
}

function onTargetRegistryChange() {
  const reg = findRegistry(form.value.target_registry_name);
  if (!reg) return;
  if (form.value.target_image_path) {
    form.value.target_image_path = stripRegistryPrefix(form.value.target_image_path, reg);
    return;
  }
  if (form.value.source_image_path) {
    form.value.target_image_path = form.value.source_image_path;
    if (form.value.source_tag && !form.value.target_tag) {
      form.value.target_tag = form.value.source_tag;
    }
  } else {
    form.value.target_image_path = "myapp/demo";
  }
}

function onSourceImagePathInput(event) {
  parseSourceImagePathAndTag(event.target.value);
  syncTargetFromSource();
}

function onSourceImagePaste() {
  setTimeout(() => {
    parseSourceImagePathAndTag(form.value.source_image_path);
    syncTargetFromSource();
  }, 0);
}

function syncTargetFromSource() {
  if (!form.value.target_registry_name || form.value.target_image_path) return;
  form.value.target_image_path = form.value.source_image_path || "myapp/demo";
  if (!form.value.target_tag && form.value.source_tag) {
    form.value.target_tag = form.value.source_tag;
  }
}

function teamIdForApi() {
  return teamStore.activeTeamIdForApi || teamStore.ensureActiveTeam();
}

async function testSourceImage() {
  if (!form.value.source_registry_name) {
    toastError("请先选择源仓库");
    return;
  }
  const source_image = sourcePreview.value;
  if (!source_image) {
    toastError("请先填写源镜像路径与标签");
    return;
  }
  const teamId = teamIdForApi();
  if (!teamId) {
    toastError("请先在顶部选择当前团队");
    return;
  }

  testingSource.value = true;
  sourceTestResult.value = null;
  try {
    const res = await axios.post(
      "/api/migration-tasks/test-source-image",
      {
        source_registry_name: form.value.source_registry_name,
        source_image,
      },
      { params: { team_id: teamId } },
    );
    const data = res.data || {};
    sourceTestResult.value = {
      success: !!data.success,
      message: data.message || (data.success ? "源镜像可用" : "检测失败"),
      suggestions: data.suggestions,
    };
  } catch (error) {
    const errorData = error.response?.data || {};
    sourceTestResult.value = {
      success: false,
      message: errorData.message || errorData.detail || "检测失败",
      suggestions: errorData.suggestions,
    };
  } finally {
    testingSource.value = false;
  }
}

async function loadRegistries() {
  try {
    const res = await axios.get("/api/registries");
    registries.value = res.data.registries || [];
    if (!registries.value.length) return;
    if (!showDialog.value && !form.value.source_registry_name) {
      pickDefaultRegistries();
    }
  } catch (e) {
    console.error(e);
  }
}

async function loadTasks() {
  loading.value = true;
  try {
    const res = await axios.get("/api/migration-tasks");
    tasks.value = res.data.tasks || [];
  } catch (e) {
    toastApiError(e, "加载迁移任务失败");
  } finally {
    loading.value = false;
  }
}

function pickDefaultRegistries() {
  const active = registries.value.find((r) => r.active);
  const pick = active || registries.value[0];
  if (!pick) return;
  form.value.source_registry_name = pick.name;
  onSourceRegistryChange();
}

function openCreateDialog() {
  if (!registries.value.length) {
    toastError("请先在「镜像仓库」中配置至少一个仓库");
    return;
  }
  editingTaskId.value = null;
  form.value = emptyForm();
  cronPresetKey.value = "custom";
  sourceTestResult.value = null;
  pickDefaultRegistries();
  showDialog.value = true;
}

function openEditDialog(task) {
  editingTaskId.value = task.task_id;
  const srcRegObj = findRegistry(task.source_registry_name);
  const tgtRegObj = findRegistry(task.target_registry_name);
  const src = splitImageRef(task.source_image);
  const tgt = splitImageRef(task.target_image);
  form.value = {
    task_name: task.task_name || "",
    source_registry_name: task.source_registry_name || "",
    source_image_path: stripRegistryPrefix(src.path, srcRegObj),
    source_tag: src.tag,
    target_registry_name: task.target_registry_name || "",
    target_image_path: stripRegistryPrefix(tgt.path, tgtRegObj),
    target_tag: tgt.tag,
    schedule_cron: task.schedule_cron || "",
    schedule_enabled: !!task.schedule_enabled,
    execute_now: false,
  };
  cronPresetKey.value = matchCronPresetKey(form.value.schedule_cron);
  sourceTestResult.value = null;
  showDialog.value = true;
}

async function saveTask() {
  if (!form.value.source_registry_name) {
    toastError("请选择源镜像仓库");
    return;
  }
  if (!form.value.target_registry_name) {
    toastError("请选择目标镜像仓库");
    return;
  }
  const source_image = sourcePreview.value;
  const target_image = targetPreview.value;
  if (!source_image || !target_image) {
    toastError("请填写镜像路径");
    return;
  }
  if (form.value.schedule_enabled && !form.value.schedule_cron?.trim()) {
    toastError("启用定时时请填写或选择 Cron 表达式");
    return;
  }

  saving.value = true;
  try {
    const payload = {
      task_name: form.value.task_name,
      source_registry_name: form.value.source_registry_name,
      source_image,
      target_registry_name: form.value.target_registry_name,
      target_image,
      schedule_cron: form.value.schedule_enabled ? form.value.schedule_cron.trim() : "",
      schedule_enabled: form.value.schedule_enabled,
    };

    if (editingTaskId.value) {
      await axios.put(`/api/migration-tasks/${editingTaskId.value}`, payload);
      toastSuccess("迁移任务已更新");
    } else {
      payload.execute_now = form.value.execute_now;
      await axios.post("/api/migration-tasks", payload);
      toastSuccess(
        form.value.execute_now ? "迁移任务已创建并开始执行" : "迁移任务已创建",
      );
    }
    showDialog.value = false;
    await loadTasks();
  } catch (e) {
    toastApiError(e, "保存失败");
  } finally {
    saving.value = false;
  }
}

async function executeTask(task) {
  executingId.value = task.task_id;
  try {
    await axios.post(`/api/migration-tasks/${task.task_id}/execute`);
    toastSuccess("迁移任务已启动");
    await loadTasks();
    startPolling();
  } catch (e) {
    toastApiError(e, "启动失败");
  } finally {
    executingId.value = null;
  }
}

async function stopTask(task) {
  try {
    await axios.post(`/api/migration-tasks/${task.task_id}/stop`);
    toastSuccess("任务已停止");
    await loadTasks();
  } catch (e) {
    toastApiError(e, "停止失败");
  }
}

async function toggleSchedule(task) {
  try {
    await axios.post(`/api/migration-tasks/${task.task_id}/toggle-schedule`, {
      enabled: !task.schedule_enabled,
    });
    toastSuccess(task.schedule_enabled ? "定时已禁用" : "定时已启用");
    await loadTasks();
  } catch (e) {
    toastApiError(e, "操作失败");
  }
}

async function deleteTask(task) {
  const ok = await showConfirm({
    title: "删除迁移任务",
    message: `确定删除「${task.task_name || task.source_image}」？`,
    confirmText: "删除",
    variant: "danger",
  });
  if (!ok) return;
  try {
    await axios.delete(`/api/migration-tasks/${task.task_id}`);
    toastSuccess("已删除");
    await loadTasks();
  } catch (e) {
    toastApiError(e, "删除失败");
  }
}

function startPolling() {
  if (refreshInterval) return;
  refreshInterval = setInterval(async () => {
    const hasActive = tasks.value.some((t) =>
      ["running", "pending"].includes(t.status),
    );
    if (!hasActive) {
      clearInterval(refreshInterval);
      refreshInterval = null;
      return;
    }
    await loadTasks();
  }, 3000);
}

function onTeamChanged() {
  loadRegistries();
  loadTasks();
}

onMounted(() => {
  loadRegistries();
  loadTasks();
  window.addEventListener("team-context-changed", onTeamChanged);
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
  window.removeEventListener("team-context-changed", onTeamChanged);
});
</script>

<style scoped>
.image-migration-panel {
  animation: fadeIn 0.3s;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

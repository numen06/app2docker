<template>
  <div class="template-panel">
    <PageToolbar title="模板管理" icon="fa-layer-group">
      <template #actions>
        <Button size="sm" @click="openEditor(null, true)">
          <i class="fas fa-plus-circle"></i>
          新增模板
        </Button>
      </template>
    </PageToolbar>

    <div v-if="loading" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <i class="fas fa-spinner fa-spin"></i>
      加载中…
    </div>

    <EmptyState
      v-else-if="templates.length === 0"
      message='暂无模板，请点击「新增模板」创建'
      icon="fa-file-code"
    />

    <Table v-else min-width-class="min-w-[48rem]">
      <TableHeader>
        <TableRow>
          <TableHead>模板名称</TableHead>
          <TableHead>项目类型</TableHead>
          <TableHead>文件大小</TableHead>
          <TableHead>更新时间</TableHead>
          <TableHead class="text-end">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="tpl in templates" :key="tpl.name">
          <TableCell class="font-medium text-slate-900">
            {{ tpl.name }}
            <i
              v-if="tpl.type === 'builtin'"
              class="fas fa-lock ml-1 text-slate-400"
              title="内置模板"
            ></i>
          </TableCell>
          <TableCell>
            <Badge :variant="projectTypeBadgeVariant(tpl.project_type)">
              {{ getProjectTypeLabel(tpl.project_type) }}
            </Badge>
          </TableCell>
          <TableCell class="text-slate-600">{{ formatBytes(tpl.size) }}</TableCell>
          <TableCell class="whitespace-nowrap text-slate-600">{{ formatTime(tpl.updated_at) }}</TableCell>
          <TableCell class="text-end">
            <div class="flex justify-end gap-1">
              <Button
                variant="outline"
                size="sm"
                title="解析"
                :disabled="parsing === tpl.name"
                @click="parseTemplate(tpl)"
              >
                <i v-if="parsing === tpl.name" class="fas fa-spinner fa-spin"></i>
                <i v-else class="fas fa-search"></i>
              </Button>
              <Button variant="outline" size="sm" title="预览" @click="previewTemplate(tpl)">
                <i class="fas fa-eye"></i>
              </Button>
              <Button variant="outline" size="sm" title="克隆" @click="cloneTemplate(tpl)">
                <i class="fas fa-copy"></i>
              </Button>
              <Button variant="outline" size="sm" title="编辑" @click="openEditor(tpl, false)">
                <i class="fas fa-pen"></i>
              </Button>
              <Button variant="destructive" size="sm" title="删除" @click="deleteTemplate(tpl)">
                <i class="fas fa-trash"></i>
              </Button>
            </div>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>

    <PaginationBar
      v-if="totalPages > 1"
      :page="currentPage"
      :page-size="pageSize"
      :total="totalTemplates"
      :total-pages="totalPages"
      @update:page="changePage"
    />

    <TemplateEditorModal
      v-model="showEditor"
      :template="currentTemplate"
      :is-new="isNew"
      @saved="handleSaved"
    />

    <TemplatePreviewModal v-model="showPreview" :template="currentTemplate" />

    <BaseDialog v-model="showParseModal">
      <div class="flex max-h-[90vh] w-full max-w-3xl flex-col">
        <div class="flex shrink-0 items-center justify-between border-b border-sky-600 bg-sky-600 px-4 py-3 text-white">
          <h3 class="flex items-center gap-2 text-lg font-semibold">
            <i class="fas fa-search"></i>
            模板解析信息
            <span v-if="parseTemplateData" class="font-normal opacity-90">{{ parseTemplateData.name }}</span>
          </h3>
          <button
            type="button"
            class="rounded-md p-2 text-white hover:bg-white/20"
            @click="closeParseModal"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <div v-if="parsing" class="flex items-center justify-center gap-2 py-8 text-slate-500">
            <i class="fas fa-spinner fa-spin"></i>
            正在解析模板…
          </div>
          <AlertBanner v-else-if="parseError" :message="parseError" variant="danger" />
          <div v-else-if="parseInfo" class="space-y-6">
            <section>
              <h4 class="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
                <i class="fas fa-sliders-h text-blue-600"></i>
                模板参数
                <Badge variant="info">{{ parseInfo.params?.length || 0 }} 个</Badge>
              </h4>
              <Table v-if="parseInfo.params?.length" class="border border-slate-200">
                <TableHeader>
                  <TableRow>
                    <TableHead class="w-48">参数名称</TableHead>
                    <TableHead>描述</TableHead>
                    <TableHead class="w-28">默认值</TableHead>
                    <TableHead class="w-20">必填</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-for="param in parseInfo.params" :key="param.name">
                    <TableCell><code class="text-xs">{{ param.name }}</code></TableCell>
                    <TableCell class="text-slate-600">{{ param.description || "—" }}</TableCell>
                    <TableCell>
                      <Badge v-if="param.default" variant="default">{{ param.default }}</Badge>
                      <span v-else class="text-slate-400">—</span>
                    </TableCell>
                    <TableCell>
                      <Badge :variant="param.required ? 'danger' : 'success'">
                        {{ param.required ? "是" : "否" }}
                      </Badge>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <p v-else class="rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-sky-800">
                该模板没有可配置参数
              </p>
            </section>
            <section>
              <h4 class="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
                <i class="fas fa-server text-sky-600"></i>
                服务阶段（多阶段构建）
                <Badge variant="info">{{ parseInfo.services?.length || 0 }} 个</Badge>
              </h4>
              <Table v-if="parseInfo.services?.length" class="border border-slate-200">
                <TableHeader>
                  <TableRow>
                    <TableHead>服务名称</TableHead>
                    <TableHead class="w-28">端口</TableHead>
                    <TableHead class="w-28">用户</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-for="service in parseInfo.services" :key="service.name">
                    <TableCell><code class="text-xs">{{ service.name }}</code></TableCell>
                    <TableCell>
                      <Badge v-if="service.port" variant="default">{{ service.port }}</Badge>
                      <span v-else class="text-slate-400">—</span>
                    </TableCell>
                    <TableCell>
                      <Badge v-if="service.user" variant="default">{{ service.user }}</Badge>
                      <span v-else class="text-slate-400">—</span>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <p v-else class="rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-sky-800">
                该模板不是多阶段构建，或没有服务阶段
              </p>
            </section>
          </div>
        </div>
        <div class="flex shrink-0 justify-end border-t border-slate-200 bg-slate-50 px-4 py-3">
          <Button variant="outline" @click="closeParseModal">关闭</Button>
        </div>
      </div>
    </BaseDialog>
  </div>
</template>

<script setup>
import axios from "axios";
import { onMounted, ref } from "vue";
import TemplateEditorModal from "./TemplateEditorModal.vue";
import TemplatePreviewModal from "./TemplatePreviewModal.vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import { Badge } from "@/components/ui/badge";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import {
  getProjectTypes,
  getProjectTypesSync,
  getProjectTypeLabel,
} from "../utils/projectTypes.js";

const projectTypesList = ref(getProjectTypesSync());

const templates = ref([]);
const loading = ref(false);
const showEditor = ref(false);
const showPreview = ref(false);
const currentTemplate = ref(null);
const isNew = ref(false);
const currentPage = ref(1);
const pageSize = ref(10);
const totalTemplates = ref(0);
const totalPages = ref(0);

const showParseModal = ref(false);
const parsing = ref(null);
const parseInfo = ref(null);
const parseError = ref("");
const parseTemplateData = ref(null);

function projectTypeBadgeVariant(type) {
  const map = {
    jar: "default",
    war: "warning",
    node: "success",
    python: "info",
    go: "info",
    static: "default",
  };
  return map[type] || "default";
}

function changePage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  currentPage.value = page;
  loadTemplates();
}

async function loadTemplates() {
  loading.value = true;
  try {
    const res = await axios.get("/api/templates", {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
      },
    });
    templates.value = res.data.items || [];
    totalTemplates.value = res.data.total || 0;
    totalPages.value = res.data.total_pages || 0;
  } catch (error) {
    console.error("加载模板失败:", error);
    alert("加载模板列表失败");
    templates.value = [];
    totalTemplates.value = 0;
    totalPages.value = 0;
  } finally {
    loading.value = false;
  }
}

function openEditor(tpl, isNewTemplate) {
  currentTemplate.value = tpl;
  isNew.value = isNewTemplate;
  showEditor.value = true;
}

function previewTemplate(tpl) {
  currentTemplate.value = tpl;
  showPreview.value = true;
}

async function cloneTemplate(tpl) {
  try {
    const res = await axios.get("/api/templates", {
      params: { name: tpl.name },
    });

    const projectType = res.data.project_type || tpl.project_type;

    let newName = `${tpl.name}_copy`;
    let counter = 1;

    while (
      templates.value.some(
        (t) => t.name === newName && (t.project_type || "jar") === projectType
      )
    ) {
      newName = `${tpl.name}_copy_${counter}`;
      counter++;
    }

    currentTemplate.value = {
      name: newName,
      project_type: projectType,
      content: res.data.content,
      type: "user",
    };
    isNew.value = true;
    showEditor.value = true;
  } catch (error) {
    console.error("克隆模板失败:", error);
    alert(error.response?.data?.detail || "克隆模板失败");
  }
}

async function parseTemplate(tpl) {
  parseTemplateData.value = tpl;
  showParseModal.value = true;
  parsing.value = tpl.name;
  parseInfo.value = null;
  parseError.value = "";

  try {
    const res = await axios.get("/api/template-params", {
      params: {
        template: tpl.name,
        project_type: tpl.project_type,
      },
    });

    parseInfo.value = {
      params: res.data.params || [],
      services: res.data.services || [],
    };
  } catch (error) {
    console.error("解析模板失败:", error);
    parseError.value = error.response?.data?.detail || "解析模板失败";
  } finally {
    parsing.value = null;
  }
}

function closeParseModal() {
  showParseModal.value = false;
  parseInfo.value = null;
  parseError.value = "";
  parseTemplateData.value = null;
}

async function deleteTemplate(tpl) {
  const msg =
    tpl.type === "builtin"
      ? `此为内置模板，删除后仍可通过系统恢复。\n确认删除用户覆盖的 ${tpl.name} 吗？`
      : `确认删除模板 ${tpl.name} 吗？该操作不可恢复。`;

  if (!confirm(msg)) return;

  try {
    await axios.delete("/api/templates", {
      data: { name: tpl.name },
    });

    alert("模板已删除");
    await loadTemplates();
  } catch (error) {
    alert(error.response?.data?.error || "删除失败");
  }
}

function handleSaved() {
  currentPage.value = 1;
  loadTemplates();
}

function formatBytes(bytes) {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let idx = 0;
  let value = bytes;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx++;
  }
  return `${value.toFixed(value < 10 && idx > 0 ? 1 : 0)} ${units[idx]}`;
}

function formatTime(timeStr) {
  if (!timeStr) return "—";
  try {
    return new Date(timeStr).toLocaleString("zh-CN");
  } catch {
    return timeStr;
  }
}

async function loadProjectTypes() {
  projectTypesList.value = await getProjectTypes();
}

onMounted(() => {
  loadProjectTypes();
  loadTemplates();
});
</script>

<style scoped>
.template-panel {
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

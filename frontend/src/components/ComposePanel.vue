<template>
  <div class="compose-panel">
    <div class="mb-4 inline-flex w-full rounded-lg border border-slate-200 bg-slate-50 p-1">
      <button
        type="button"
        class="flex-1 rounded-md px-4 py-2 text-sm font-medium transition"
        :class="inputMode === 'file' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
        @click="inputMode = 'file'"
      >
        <i class="fas fa-file-upload mr-1"></i> 上传文件
      </button>
      <button
        type="button"
        class="flex-1 rounded-md px-4 py-2 text-sm font-medium transition"
        :class="inputMode === 'text' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
        @click="inputMode = 'text'"
      >
        <i class="fas fa-edit mr-1"></i> 文本输入
      </button>
    </div>

    <div class="mb-4">
      <input
        v-if="inputMode === 'file'"
        type="file"
        class="block w-full text-sm text-slate-600 file:mr-4 file:rounded-md file:border-0 file:bg-blue-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-blue-700"
        accept=".yml,.yaml,.YML,.YAML,.txt"
        @change="handleFileChange"
      />
      <codemirror
        v-else
        v-model="composeText"
        :style="{ height: '400px', fontSize: '13px' }"
        :autofocus="true"
        :indent-with-tab="true"
        :tab-size="2"
        :extensions="extensions"
        placeholder="粘贴 docker-compose.yml 内容..."
      />
      <p class="mt-1 text-xs text-slate-500">自动提取镜像列表</p>
    </div>

    <Button type="button" class="mb-4 w-full" :disabled="parsing" @click="parseCompose">
      <i class="fas fa-search"></i>
      {{ parsing ? "解析中..." : "解析镜像" }}
    </Button>

    <div v-if="images.length > 0" class="mt-3">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span class="text-sm text-slate-500">共 {{ images.length }} 个镜像</span>
        <div class="flex flex-wrap items-center gap-2">
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="selectAll" type="checkbox" class="h-4 w-4 rounded border-slate-300" @change="toggleSelectAll" />
            全选
          </label>
          <NativeSelect v-model="compress" class="h-9 w-auto">
            <option value="none">tar</option>
            <option value="gzip">tar.gz</option>
          </NativeSelect>
          <Button variant="outline" size="sm" :disabled="selectedImages.length === 0 || exporting" @click="downloadSelected">
            <i class="fas fa-download"></i>
            {{ exporting ? "导出中..." : "下载" }}
            <i v-if="exporting" class="fas fa-spinner fa-spin"></i>
          </Button>
        </div>
      </div>

      <div class="max-h-[300px] overflow-y-auto rounded-lg border border-slate-200">
        <Table>
          <TableHeader class="sticky top-0 bg-slate-50">
            <TableRow>
              <TableHead class="w-8"></TableHead>
              <TableHead>服务</TableHead>
              <TableHead>镜像:标签</TableHead>
              <TableHead class="text-end w-20">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="(img, index) in images" :key="index">
              <TableCell>
                <input v-model="img.selected" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
              </TableCell>
              <TableCell>{{ img.service }}</TableCell>
              <TableCell>{{ img.image }}{{ img.tag && img.tag !== "latest" ? ":" + img.tag : "" }}</TableCell>
              <TableCell class="text-end">
                <Button variant="outline" size="sm" :disabled="exporting" @click="downloadImage(img)">
                  <i class="fas fa-download"></i>
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>

    <div v-if="exporting" class="export-status-banner mt-3 rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
      <div class="flex items-start gap-2">
        <i class="fas fa-spinner fa-spin mt-0.5"></i>
        <div>
          <strong>正在创建导出任务...</strong>
          <div v-if="currentExporting" class="mt-1 text-xs">
            当前: <code>{{ currentExporting.image }}{{ currentExporting.tag && currentExporting.tag !== "latest" ? ":" + currentExporting.tag : "" }}</code>
            <span v-if="exportProgress.total > 1"> ({{ exportProgress.current }}/{{ exportProgress.total }})</span>
          </div>
          <p class="mt-1 text-xs text-slate-600">
            <i class="fas fa-info-circle"></i> 任务创建后，请到「导出任务」标签页查看进度和下载文件
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import axios from "axios";
import { Codemirror } from "vue-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import { yaml as yamlLang } from "@codemirror/lang-yaml";
import Button from "@/components/ui/button/Button.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import { registerTask } from "@/composables/useTaskCompletionWatcher";

const inputMode = ref("file");
const composeText = ref("");
const images = ref([]);
const compress = ref("none");
const selectAll = ref(false);
const parsing = ref(false);
const exporting = ref(false);
const currentExporting = ref(null);
const exportProgress = ref({ current: 0, total: 0 });

const extensions = [oneDark, yamlLang()];

const selectedImages = computed(() => images.value.filter((img) => img.selected));

function handleFileChange(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    composeText.value = ev.target.result;
  };
  reader.readAsText(file);
}

function toggleSelectAll() {
  images.value.forEach((img) => {
    img.selected = selectAll.value;
  });
}

async function parseCompose() {
  if (!composeText.value.trim()) {
    alert("请上传文件或输入 docker-compose.yml 内容");
    return;
  }
  parsing.value = true;
  try {
    const res = await axios.post("/api/parse-compose", { content: composeText.value });
    images.value = (res.data.images || []).map((img) => ({ ...img, selected: false }));
    alert(`解析成功，共 ${images.value.length} 个镜像`);
  } catch (error) {
    alert(error.response?.data?.error || "解析失败");
  } finally {
    parsing.value = false;
  }
}

async function downloadImage(img) {
  if (exporting.value) {
    alert("正在提交任务，请稍候...");
    return;
  }
  exporting.value = true;
  currentExporting.value = img;
  try {
    const res = await axios.post("/api/export-image", {
      image: img.image,
      tag: img.tag || "latest",
      compress: compress.value,
    });
    if (res.data?.task_id) {
      registerTask(res.data.task_id, {
        task_type: "export",
        image: img.image,
        tag: img.tag || "latest",
      });
    }
    alert(
      `导出任务已创建！\n镜像: ${img.image}${img.tag && img.tag !== "latest" ? ":" + img.tag : ""}\n任务ID: ${res.data.task_id}\n\n请到「导出任务」标签页查看进度和下载文件。`
    );
  } catch (error) {
    alert(
      error.response?.data?.detail ||
        error.response?.data?.error ||
        error.message ||
        "创建导出任务失败"
    );
  } finally {
    exporting.value = false;
    currentExporting.value = null;
  }
}

async function downloadSelected() {
  if (exporting.value) {
    alert("正在提交任务，请稍候...");
    return;
  }
  const selected = selectedImages.value;
  if (selected.length === 0) {
    alert("请至少选择一个镜像");
    return;
  }
  exporting.value = true;
  exportProgress.value = { current: 0, total: selected.length };
  setTimeout(() => {
    document.querySelector(".export-status-banner")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, 100);
  try {
    const taskIds = [];
    for (let i = 0; i < selected.length; i++) {
      const img = selected[i];
      currentExporting.value = img;
      exportProgress.value.current = i + 1;
      try {
        const res = await axios.post("/api/export-image", {
          image: img.image,
          tag: img.tag || "latest",
          compress: compress.value,
        });
        if (res.data?.task_id) {
          registerTask(res.data.task_id, {
            task_type: "export",
            image: img.image,
            tag: img.tag || "latest",
          });
          taskIds.push(res.data.task_id);
        }
      } catch (error) {
        console.error(`镜像 ${img.image} 创建任务失败:`, error.response?.data?.error || error.message);
      }
    }
    if (taskIds.length > 0) {
      alert(`已创建 ${taskIds.length} 个导出任务！\n\n请到「导出任务」标签页查看进度和下载文件。`);
    } else {
      alert("所有任务创建失败，请检查网络连接");
    }
  } finally {
    exporting.value = false;
    currentExporting.value = null;
    exportProgress.value = { current: 0, total: 0 };
  }
}
</script>

<style scoped>
.compose-panel {
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

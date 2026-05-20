<template>
  <div class="export-panel">
    <div class="mb-4 flex w-full flex-wrap gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1 sm:inline-flex sm:w-auto">
      <button
        type="button"
        class="flex-1 rounded-md px-4 py-2 text-sm font-medium transition sm:flex-none"
        :class="exportMode === 'single' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
        @click="exportMode = 'single'"
      >
        <i class="fas fa-cube mr-1"></i> 单个镜像
      </button>
      <button
        type="button"
        class="flex-1 rounded-md px-4 py-2 text-sm font-medium transition sm:flex-none"
        :class="exportMode === 'compose' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'"
        @click="exportMode = 'compose'"
      >
        <i class="fas fa-diagram-project mr-1"></i> Compose 批量导出
      </button>
    </div>

    <div v-if="exportMode === 'single'">
      <form class="space-y-4" @submit.prevent="handleExport">
        <div class="space-y-2">
          <Label><i class="fas fa-server mr-1"></i> 镜像仓库</Label>
          <NativeSelect v-model="form.registry" @change="updateImageName">
            <option v-for="reg in registries" :key="reg.name" :value="reg.name">
              {{ reg.name }} - {{ reg.registry }}{{ reg.active ? " (激活)" : "" }}
            </option>
          </NativeSelect>
          <p class="text-xs text-slate-500">选择仓库后会自动拼接镜像名，默认使用激活的仓库</p>
        </div>

        <div class="grid gap-4 md:grid-cols-12">
          <div class="space-y-2 md:col-span-6">
            <Label>镜像名称 <span class="text-red-600">*</span></Label>
            <Input
              v-model="form.image"
              type="text"
              :placeholder="imagePlaceholder"
              required
              @input="handleImageNameInput"
              @paste="handleImageNamePaste"
            />
            <p class="text-xs text-slate-500">选择仓库后会自动拼接完整镜像名，您也可以手动修改</p>
          </div>
          <div class="space-y-2 md:col-span-3">
            <Label>标签</Label>
            <Input v-model="form.tag" type="text" />
          </div>
          <div class="space-y-2 md:col-span-3">
            <Label>压缩</Label>
            <NativeSelect v-model="form.compress">
              <option value="none">不压缩</option>
              <option value="gzip">GZIP</option>
            </NativeSelect>
          </div>
        </div>

        <label class="flex items-start gap-2 text-sm text-slate-700">
          <input v-model="form.useLocal" type="checkbox" class="mt-1 h-4 w-4 rounded border-slate-300" />
          <span>
            <i class="fas fa-server mr-1"></i> 使用本地仓库（不执行 pull 操作）
            <span class="mt-1 block text-xs text-slate-500">勾选后，将直接从本地 Docker 导出镜像，不会从远程仓库拉取</span>
          </span>
        </label>

        <Button type="submit" class="w-full" :disabled="exporting">
          <i class="fas fa-download"></i>
          {{ exporting ? "导出中..." : "导出镜像" }}
          <i v-if="exporting" class="fas fa-spinner fa-spin"></i>
        </Button>
      </form>

      <div
        v-if="exporting"
        class="mt-3 rounded-md border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900"
      >
        <div class="flex items-start gap-2">
          <i class="fas fa-spinner fa-spin mt-0.5"></i>
          <div>
            <strong>正在创建导出任务...</strong>
            <p class="mt-1 text-xs">镜像: <code>{{ form.image }}:{{ form.tag }}</code></p>
            <p class="mt-1 text-xs text-slate-600">
              <i class="fas fa-info-circle"></i> 任务创建后，请到「任务管理」标签页查看进度和下载文件
            </p>
          </div>
        </div>
      </div>
    </div>

    <ComposePanel v-else />
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, onMounted, ref } from "vue";
import ComposePanel from "@/components/ComposePanel.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import { registerTask } from "@/composables/useTaskCompletionWatcher";

const exportMode = ref("single");

const form = ref({
  registry: "",
  image: "",
  tag: "latest",
  compress: "none",
  useLocal: false,
});

const registries = ref([]);
const exporting = ref(false);

const imagePlaceholder = computed(() => {
  const selectedRegistry = registries.value.find((r) => r.name === form.value.registry);
  if (selectedRegistry?.registry_prefix?.trim()) {
    return `${selectedRegistry.registry_prefix.trim()}/myapp/demo`;
  }
  return "myapp/demo";
});

async function loadRegistries() {
  try {
    const res = await axios.get("/api/registries");
    registries.value = res.data.registries || [];
    const activeRegistry = registries.value.find((r) => r.active);
    if (activeRegistry) {
      form.value.registry = activeRegistry.name;
      updateImageName();
    } else if (registries.value.length > 0) {
      form.value.registry = registries.value[0].name;
      updateImageName();
    }
  } catch (error) {
    console.error("加载仓库列表失败:", error);
  }
}

function updateImageName() {
  const selectedRegistry = registries.value.find((r) => r.name === form.value.registry);
  if (selectedRegistry?.registry_prefix) {
    const prefix = selectedRegistry.registry_prefix.trim();
    if (prefix) {
      if (!form.value.image || !form.value.image.startsWith(prefix)) {
        let imageName = form.value.image;
        registries.value.forEach((reg) => {
          const regPrefix = reg.registry_prefix?.trim();
          if (regPrefix && imageName.startsWith(`${regPrefix}/`)) {
            imageName = imageName.substring(regPrefix.length + 1);
          }
        });
        form.value.image = imageName ? `${prefix}/${imageName}`.replace(/\/+/g, "/") : `${prefix}/myapp/demo`;
      }
    } else if (form.value.image) {
      registries.value.forEach((reg) => {
        const regPrefix = reg.registry_prefix?.trim();
        if (regPrefix && form.value.image.startsWith(`${regPrefix}/`)) {
          form.value.image = form.value.image.substring(regPrefix.length + 1);
        }
      });
    }
  }
}

function handleImageNameInput(event) {
  parseImageNameAndTag(event.target.value);
}

function handleImageNamePaste() {
  setTimeout(() => parseImageNameAndTag(form.value.image), 0);
}

function parseImageNameAndTag(inputValue) {
  if (!inputValue || typeof inputValue !== "string") return;
  const lastColonIndex = inputValue.lastIndexOf(":");
  if (lastColonIndex > 0 && lastColonIndex < inputValue.length - 1) {
    const afterColon = inputValue.substring(lastColonIndex + 1);
    if (!afterColon.includes("/") && !/^\d+$/.test(afterColon)) {
      form.value.image = inputValue.substring(0, lastColonIndex);
      if (afterColon.trim()) form.value.tag = afterColon.trim();
    }
  }
}

async function handleExport() {
  if (!form.value.image) {
    alert("请输入镜像名称");
    return;
  }
  if (exporting.value) {
    alert("正在提交任务，请稍候...");
    return;
  }
  exporting.value = true;
  try {
    const payload = {
      image: form.value.image.trim(),
      tag: form.value.tag,
      compress: form.value.compress,
      use_local: form.value.useLocal,
    };
    if (form.value.registry) payload.registry = form.value.registry;
    const res = await axios.post("/api/export-image", payload);
    if (res.data?.task_id) {
      registerTask(res.data.task_id, {
        task_type: "export",
        image: payload.image,
        tag: payload.tag,
      });
    }
    alert(`导出任务已创建！\n任务ID: ${res.data.task_id}\n\n请到「任务管理」标签页查看进度和下载文件。`);
  } catch (error) {
    alert(
      error.response?.data?.detail ||
        error.response?.data?.error ||
        error.message ||
        "创建导出任务失败"
    );
  } finally {
    exporting.value = false;
  }
}

onMounted(() => loadRegistries());
</script>

<style scoped>
.export-panel {
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

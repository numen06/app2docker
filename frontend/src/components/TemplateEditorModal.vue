<template>
  <FormDialog
    :model-value="modelValue"
    :title="isNew ? '新增模板' : '编辑模板'"
    icon="fa-code"
    size="xl"
    @update:model-value="close"
  >
    <Badge v-if="isBuiltin" variant="warning" class="mb-3">
      <i class="fas fa-lock"></i> 内置
    </Badge>

    <div class="mb-4 grid gap-4 sm:grid-cols-2">
      <div class="space-y-2">
        <Label>模板名称 <span class="text-red-600">*</span></Label>
        <Input
          v-model="form.name"
          type="text"
          :disabled="isBuiltin"
          placeholder="例如: my-custom-template"
        />
        <p v-if="isBuiltin" class="text-xs text-amber-700">
          <i class="fas fa-info-circle"></i> 内置模板不可重命名，保存后将在用户目录创建覆盖
        </p>
      </div>
      <div class="space-y-2">
        <Label>项目类型 <span class="text-red-600">*</span></Label>
        <NativeSelect
          :value="form.projectType"
          :disabled="!canChangeProjectType"
          @change="onProjectTypeChange"
        >
          <option value="jar">Java 应用（JAR）</option>
          <option value="nodejs">Node.js 应用</option>
          <option value="python">Python 应用</option>
          <option value="go">Go 应用</option>
          <option value="web">静态网站</option>
        </NativeSelect>
        <p v-if="!canChangeProjectType" class="text-xs text-amber-700">
          <i class="fas fa-lock"></i> 内置模板的项目类型不可修改
        </p>
        <p v-else-if="!isNew && projectTypeChanged" class="text-xs text-sky-700">
          <i class="fas fa-info-circle"></i> 修改项目类型后，模板将移动到新目录
        </p>
        <p v-else class="text-xs text-slate-500">
          <i class="fas fa-lightbulb"></i> 请从下拉列表中选择项目类型
        </p>
      </div>
    </div>

    <div class="mb-2 flex items-center justify-between">
      <Label class="mb-0">模板内容 <span class="text-red-600">*</span></Label>
      <Button type="button" variant="outline" size="sm" @click="fileInput?.click()">
        <i class="fas fa-upload"></i> 从文件加载
      </Button>
    </div>
    <input
      ref="fileInput"
      type="file"
      class="hidden"
      accept=".dockerfile,.Dockerfile,.txt"
      @change="handleFileUpload"
    />
    <codemirror
      v-model="form.content"
      :style="{ height: 'min(500px, 60vh)', fontSize: '13px' }"
      :autofocus="true"
      :indent-with-tab="false"
      :tab-size="4"
      :extensions="extensions"
    />

    <template #footer>
      <Button type="button" variant="secondary" @click="close">取消</Button>
      <Button type="button" :disabled="saving" @click="save">
        <i v-if="saving" class="fas fa-spinner fa-spin"></i>
        <i v-else class="fas fa-save"></i>
        {{ saving ? "保存中..." : "保存" }}
      </Button>
    </template>
  </FormDialog>
</template>

<script setup>
import { StreamLanguage } from "@codemirror/language";
import { shell } from "@codemirror/legacy-modes/mode/shell";
import { oneDark } from "@codemirror/theme-one-dark";
import axios from "axios";
import { computed, ref, watch } from "vue";
import { Codemirror } from "vue-codemirror";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Badge from "@/components/ui/badge/Badge.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";

const props = defineProps({
  modelValue: Boolean,
  template: Object,
  isNew: Boolean,
});

const emit = defineEmits(["update:modelValue", "saved"]);

const form = ref({ name: "", projectType: "jar", content: "" });
const saving = ref(false);
const originalName = ref("");
const fileInput = ref(null);

const extensions = [oneDark, StreamLanguage.define(shell)];

const isBuiltin = computed(() => props.template?.type === "builtin");
const canChangeProjectType = computed(() => props.isNew || !isBuiltin.value);
const projectTypeChanged = computed(() => {
  if (props.isNew || !props.template) return false;
  return form.value.projectType !== props.template.project_type;
});

watch(
  () => props.modelValue,
  async (show) => {
    if (!show) return;
    if (props.isNew) {
      if (props.template?.content) {
        form.value = {
          name: props.template.name || "",
          projectType: props.template.project_type || "jar",
          content: props.template.content || "",
        };
        originalName.value = "";
      } else {
        form.value = {
          name: "",
          projectType: "jar",
          content:
            "# 新建 Dockerfile 模板\nFROM \n\nCOPY . /app\nWORKDIR /app\n\nEXPOSE 8080\n\nCMD []",
        };
        originalName.value = "";
      }
    } else if (props.template) {
      try {
        const res = await axios.get(`/api/templates?name=${encodeURIComponent(props.template.name)}`);
        form.value = {
          name: res.data.name,
          projectType: props.template.project_type || "jar",
          content: res.data.content || "",
        };
        originalName.value = res.data.name;
      } catch {
        alert("加载模板内容失败");
        close();
      }
    }
  }
);

function onProjectTypeChange(e) {
  form.value.projectType = e.target.value
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "");
}

function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    form.value.content = ev.target.result;
    if (props.isNew && !form.value.name) {
      form.value.name = file.name
        .replace(/\.Dockerfile$/i, "")
        .replace(/\.[^/.]+$/, "")
        .replace(/[^a-zA-Z0-9_-]/g, "-");
    }
  };
  reader.readAsText(file);
}

async function save() {
  if (!form.value.name.trim()) {
    alert("模板名称不能为空");
    return;
  }
  if (!form.value.content.trim()) {
    alert("模板内容不能为空");
    return;
  }
  if (!form.value.projectType.trim()) {
    alert("项目类型不能为空");
    return;
  }
  if (!/^[a-z0-9_-]+$/.test(form.value.projectType)) {
    alert("项目类型只能包含小写字母、数字、下划线和连字符");
    return;
  }
  if (projectTypeChanged.value) {
    const confirmMsg =
      `您正在将模板的项目类型从 "${props.template.project_type}" 修改为 "${form.value.projectType}"。\n\n` +
      `模板将从 data/templates/${props.template.project_type}/ 移动到 data/templates/${form.value.projectType}/\n\n` +
      `确认要继续吗？`;
    if (!confirm(confirmMsg)) return;
  }

  saving.value = true;
  try {
    const payload = {
      name: form.value.name.trim(),
      content: form.value.content,
      project_type: form.value.projectType,
    };
    if (!props.isNew) {
      payload.original_name = originalName.value;
      payload.old_project_type = props.template.project_type || form.value.projectType;
    }
    const method = props.isNew ? "post" : "put";
    const res = await axios[method]("/api/templates", payload);
    alert(
      projectTypeChanged.value ? "模板已保存并移动到新的项目类型目录" : res.data.message || "模板保存成功"
    );
    emit("saved");
    close();
  } catch (error) {
    alert(error.response?.data?.detail || error.response?.data?.error || error.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

function close() {
  emit("update:modelValue", false);
}
</script>

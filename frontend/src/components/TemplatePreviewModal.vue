<template>
  <FormDialog
    :model-value="modelValue"
    title="模板预览"
    icon="eye"
    size="xl"
    @update:model-value="close"
  >
    <div v-if="template?.name" class="-mt-2 mb-3 flex flex-wrap items-center gap-2 text-sm text-slate-600">
      <span>{{ template.name }}</span>
      <Badge v-if="template?.type === 'builtin'" variant="warning">
        <AppIcon  name="lock" /> 内置
      </Badge>
    </div>

    <div v-if="loading" class="py-8 text-center text-slate-500">
      <AppIcon  name="spinner" class="mr-2" spin /> 加载中...
    </div>

    <template v-else>
      <div class="mb-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p class="text-xs font-semibold text-slate-500">模板名称</p>
          <p class="text-sm text-slate-900">{{ templateData?.name ||"-" }}</p>
        </div>
        <div>
          <p class="text-xs font-semibold text-slate-500">项目类型</p>
          <Badge :variant="template?.project_type === 'jar' ? 'default' : 'success'">
            {{ template?.project_type ==="nodejs" ?"Node.js" :"JAR" }}
          </Badge>
        </div>
        <div>
          <p class="text-xs font-semibold text-slate-500">文件大小</p>
          <p class="text-sm text-slate-900">{{ formatSize(template?.size) }}</p>
        </div>
        <div>
          <p class="text-xs font-semibold text-slate-500">更新时间</p>
          <p class="text-sm text-slate-900">{{ formatDate(template?.updated_at) }}</p>
        </div>
      </div>

      <div
        v-if="templateInfo && (templateInfo.params?.length > 0 || templateInfo.services?.length > 0)"
        class="mb-4"
      >
        <div class="mb-3 flex gap-1 border-b border-slate-200">
          <button
            v-if="templateInfo.params?.length > 0"
            type="button"
            class="border-b-2 px-4 py-2 text-sm font-medium transition"
            :class="activeTab === 'params'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'"
            @click="activeTab = 'params'"
          >
            <AppIcon  name="sliders-h" /> 模板参数
            <Badge variant="default" class="ml-1">{{ templateInfo.params.length }}</Badge>
          </button>
          <button
            v-if="templateInfo.services?.length > 0"
            type="button"
            class="border-b-2 px-4 py-2 text-sm font-medium transition"
            :class="activeTab === 'services'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'"
            @click="activeTab = 'services'"
          >
            <AppIcon  name="server" /> 服务阶段
            <Badge variant="info" class="ml-1">{{ templateInfo.services.length }}</Badge>
          </button>
        </div>

        <div v-show="activeTab === 'params' && templateInfo.params?.length > 0">
          <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <Card v-for="param in templateInfo.params" :key="param.name" class="bg-slate-50">
              <CardContent class="p-3">
                <div class="flex items-start justify-between gap-2">
                  <div>
                    <code class="font-semibold text-blue-600">{{ param.name }}</code>
                    <p v-if="param.default" class="mt-1 text-xs text-slate-500">
                      默认值: <code>{{ param.default }}</code>
                    </p>
                  </div>
                  <Badge v-if="param.required" variant="danger">必填</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div v-show="activeTab === 'services' && templateInfo.services?.length > 0" class="overflow-x-auto rounded-lg border border-slate-200">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-[40%]">服务名称</TableHead>
                <TableHead class="w-[30%]">端口</TableHead>
                <TableHead class="w-[30%]">用户</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="service in templateInfo.services" :key="service.name">
                <TableCell><code class="text-blue-600">{{ service.name }}</code></TableCell>
                <TableCell>
                  <Badge v-if="service.port">{{ service.port }}</Badge>
                  <span v-else class="text-slate-400">-</span>
                </TableCell>
                <TableCell>
                  <Badge v-if="service.user" variant="info">{{ service.user }}</Badge>
                  <span v-else class="text-slate-400">-</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </div>

      <Label class="mb-2 block">
        <AppIcon  name="file-code" /> 模板内容
      </Label>
      <codemirror
        v-model="content"
        :style="{ height: 'min(500px, 60vh)', fontSize: '13px' }"
        :disabled="true"
        :extensions="extensions"
      />
    </template>

    <template #footer>
      <Button type="button" variant="secondary" @click="close">关闭</Button>
    </template>
  </FormDialog>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

import { ref, watch } from "vue";
import axios from "axios";
import { Codemirror } from "vue-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import { StreamLanguage } from "@codemirror/language";
import { shell } from "@codemirror/legacy-modes/mode/shell";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Badge from "@/components/ui/badge/Badge.vue";
import Button from "@/components/ui/button/Button.vue";
import Card from "@/components/ui/card/Card.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import Label from "@/components/ui/label/Label.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";

const props = defineProps({ modelValue: Boolean, template: Object });
const emit = defineEmits(["update:modelValue"]);

const loading = ref(false);
const content = ref("");
const templateData = ref(null);
const templateInfo = ref(null);
const activeTab = ref("params");

const extensions = [oneDark, StreamLanguage.define(shell)];

watch(
  () => props.modelValue,
  async (show) => {
    if (!show || !props.template) return;
    loading.value = true;
    templateInfo.value = null;
    activeTab.value ="params";
    try {
      const res = await axios.get(`/api/templates?name=${encodeURIComponent(props.template.name)}`);
      templateData.value = res.data;
      content.value = res.data.content ||"";
      try {
        const infoRes = await axios.get("/api/template-params", {
          params: { template: props.template.name, project_type: props.template.project_type },
        });
        templateInfo.value = {
          params: infoRes.data.params || [],
          services: infoRes.data.services || [],
        };
        if (
          (!templateInfo.value.params || templateInfo.value.params.length === 0) &&
          templateInfo.value.services?.length > 0
        ) {
          activeTab.value ="services";
        }
      } catch {
        templateInfo.value = { params: [], services: [] };
      }
    } catch {
      toastError("加载模板内容失败");
      close();
    } finally {
      loading.value = false;
    }
  }
);

function formatSize(bytes) {
  if (!bytes) return"-";
  if (bytes < 1024) return bytes +" B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) +" KB";
  return (bytes / (1024 * 1024)).toFixed(1) +" MB";
}

function formatDate(dateStr) {
  if (!dateStr) return"-";
  try {
    return new Date(dateStr).toLocaleString("zh-CN", {
      year:"numeric",
      month:"2-digit",
      day:"2-digit",
      hour:"2-digit",
      minute:"2-digit",
    });
  } catch {
    return dateStr;
  }
}

function close() {
  emit("update:modelValue", false);
}
</script>

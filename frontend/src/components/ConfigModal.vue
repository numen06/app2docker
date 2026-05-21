<template>
  <FormDialog
    :model-value="modelValue"
    title="Docker 配置"
    icon="fa-cog"
    size="lg"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <form class="space-y-6" @submit.prevent="save">
      <div>
        <h4 class="mb-3 flex items-center gap-2 text-sm font-semibold text-blue-600">
          <i class="fas fa-server"></i> Docker 构建配置
        </h4>
        <Label class="mb-2 block">
          <i class="fas fa-cogs mr-1"></i> 编译模式 <span class="text-red-600">*</span>
        </Label>
        <AlertBanner
          variant="info"
          message="全局设置：选择的编译模式将应用于所有构建任务"
          class="mb-3"
        />
        <div class="grid gap-3 sm:grid-cols-3">
          <Card
            v-for="mode in buildModes"
            :key="mode.value"
            :class="[
              'cursor-pointer transition',
              buildMode === mode.value ? 'border-2 border-blue-600 ring-1 ring-blue-600' : 'hover:border-slate-300',
            ]"
            @click="buildMode = mode.value"
          >
            <CardContent class="p-4">
              <label class="flex cursor-pointer items-start gap-2">
                <input
                  v-model="buildMode"
                  type="radio"
                  :value="mode.value"
                  class="mt-1 h-4 w-4 border-slate-300 text-blue-600"
                />
                <span>
                  <span class="font-semibold text-slate-900" v-html="mode.label"></span>
                  <span class="mt-2 block text-xs text-slate-500" v-html="mode.hint"></span>
                </span>
              </label>
            </CardContent>
          </Card>
        </div>
      </div>

      <template v-if="buildMode === 'tcp2375' || buildMode === 'tls'">
        <AlertBanner
          variant="info"
          message="远程 Docker 配置需要确保远程主机的 Docker 守护进程已开启 TCP 访问"
        />
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="space-y-2 sm:col-span-2">
            <Label>远程主机地址 *</Label>
            <Input v-model="config.remote.host" type="text" placeholder="192.168.1.100" required />
          </div>
          <div class="space-y-2">
            <Label>端口</Label>
            <Input v-model.number="config.remote.port" type="number" :placeholder="buildMode === 'tls' ? '2376' : '2375'" />
            <p class="text-xs text-slate-500">
              默认端口：{{ buildMode === "tls" ? "2376 (TLS)" : "2375 (TCP)" }}
            </p>
          </div>
        </div>
        <div v-if="buildMode === 'tls'" class="grid gap-4 sm:grid-cols-2">
          <AlertBanner variant="success" message="TLS 加密连接已启用" />
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="config.remote.verify_tls" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
            验证 TLS 证书
          </label>
          <div class="space-y-2 sm:col-span-2">
            <Label>证书路径</Label>
            <Input v-model="config.remote.cert_path" type="text" placeholder="/path/to/certs" />
            <p class="text-xs text-slate-500">证书目录应包含 ca.pem, cert.pem, key.pem</p>
          </div>
        </div>
      </template>

      <AlertBanner
        variant="info"
        message="镜像仓库配置已移至数据源配置页面的「镜像仓库」标签页，请前往该页面进行配置。"
      />

      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <Label>暴露端口</Label>
          <Input v-model.number="config.expose_port" type="number" />
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="config.default_push" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
            默认推送镜像
          </label>
        </div>
      </div>

      <div class="flex justify-end">
        <Button type="submit" :disabled="saving">
          <i class="fas fa-save"></i>
          {{ saving ? "保存中..." : "保存配置" }}
        </Button>
      </div>
    </form>
  </FormDialog>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

import axios from "axios";
import { ref, watch } from "vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Card from "@/components/ui/card/Card.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";

const props = defineProps({ modelValue: Boolean });
const emit = defineEmits(["update:modelValue"]);

const buildModes = [
  {
    value: "local",
    label: '<i class="fas fa-cube text-green-600"></i> 容器内编译',
    hint: '通过挂载的 docker.sock 连接本地 Docker<br/><span class="text-amber-600"><i class="fas fa-exclamation-triangle"></i> 支持复杂编译流程</span>',
  },
  {
    value: "tcp2375",
    label: '<i class="fas fa-network-wired text-amber-600"></i> 远程 Docker (TCP)',
    hint: '通过 TCP 端口连接远程 Docker<br/><span class="text-red-600"><i class="fas fa-shield-alt"></i> 明文传输，不安全</span>',
  },
  {
    value: "tls",
    label: '<i class="fas fa-lock text-green-600"></i> 远程 Docker (TLS)',
    hint: '通过 TLS 加密连接远程 Docker<br/><span class="text-green-600"><i class="fas fa-shield-alt"></i> 安全，推荐生产环境</span>',
  },
];

const config = ref({
  expose_port: 8080,
  default_push: false,
  use_remote: false,
  remote: { host: "", port: 2375, use_tls: false, cert_path: "", verify_tls: true },
});

const buildMode = ref("local");
const saving = ref(false);

async function loadConfig() {
  try {
    const res = await axios.get("/api/get-config");
    const docker = res.data.docker || {};
    const remote = docker.remote || {};
    config.value = {
      expose_port: docker.expose_port || 8080,
      default_push: docker.default_push === true,
      use_remote: docker.use_remote === true,
      remote: {
        host: remote.host || "",
        port: remote.port || 2375,
        use_tls: remote.use_tls === true,
        cert_path: remote.cert_path || "",
        verify_tls: remote.verify_tls !== false,
      },
    };
    if (!config.value.use_remote) buildMode.value = "local";
    else if (config.value.remote.use_tls) buildMode.value = "tls";
    else buildMode.value = "tcp2375";
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.response?.data?.error || error.message;
    toastError(`加载配置失败: ${errorMsg}`);
  }
}

async function save() {
  saving.value = true;
  try {
    if (buildMode.value === "local") {
      config.value.use_remote = false;
    } else {
      config.value.use_remote = true;
      if (buildMode.value === "tls") {
        config.value.remote.use_tls = true;
        if (!config.value.remote.port || config.value.remote.port === 2375) {
          config.value.remote.port = 2376;
        }
      } else if (buildMode.value === "tcp2375") {
        config.value.remote.use_tls = false;
        if (!config.value.remote.port || config.value.remote.port === 2376) {
          config.value.remote.port = 2375;
        }
      }
    }

    const formData = new FormData();
    formData.append("expose_port", String(config.value.expose_port));
    formData.append("default_push", config.value.default_push ? "on" : "off");
    formData.append("use_remote", config.value.use_remote ? "on" : "off");
    formData.append("remote_host", config.value.remote.host);
    formData.append("remote_port", String(config.value.remote.port));
    formData.append("remote_use_tls", config.value.remote.use_tls ? "on" : "off");
    formData.append("remote_cert_path", config.value.remote.cert_path);
    formData.append("remote_verify_tls", config.value.remote.verify_tls ? "on" : "off");

    await axios.post("/api/save-config", formData);
    await loadConfig();
    toastSuccess("配置保存成功");
    emit("update:modelValue", false);
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.response?.data?.error || "保存配置失败";
    toastInfo(errorMsg);
  } finally {
    saving.value = false;
  }
}

watch(buildMode, (newMode) => {
  if (newMode === "tls") {
    if (!config.value.remote.port || config.value.remote.port === 2375) {
      config.value.remote.port = 2376;
    }
  } else if (newMode === "tcp2375") {
    if (!config.value.remote.port || config.value.remote.port === 2376) {
      config.value.remote.port = 2375;
    }
  }
});

watch(
  () => props.modelValue,
  (val) => {
    if (val) loadConfig();
  },
  { immediate: true }
);
</script>

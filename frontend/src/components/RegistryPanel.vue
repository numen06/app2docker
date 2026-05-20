<template>
  <div>
    <PageToolbar title="镜像仓库配置" icon="fa-box">
      <template #actions>
        <Button variant="outline" size="sm" :disabled="loadingRegistries" @click="loadRegistries">
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loadingRegistries }"></i>
          刷新
        </Button>
        <Button size="sm" @click="showCreateRegistryModal">
          <i class="fas fa-plus"></i>
          新建仓库
        </Button>
      </template>
    </PageToolbar>

    <div v-if="loadingRegistries" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <i class="fas fa-spinner fa-spin"></i>
      加载中…
    </div>

    <EmptyState
      v-else-if="!registries.length"
      message='暂无镜像仓库，点击「新建仓库」添加'
      icon="fa-box"
    />

    <div v-else class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      <Card
        v-for="(registry, index) in registries"
        :key="registry.registry_id || index"
        :class="registry.active ? 'ring-2 ring-blue-500 ring-offset-1' : ''"
        class="flex h-full flex-col transition hover:-translate-y-0.5 hover:shadow-md"
      >
        <CardHeader class="space-y-3 border-b border-slate-100 pb-3">
          <div class="flex items-start justify-between gap-2">
            <CardTitle class="text-base">{{ registry.name }}</CardTitle>
            <Badge v-if="registry.active" variant="info">激活</Badge>
          </div>
          <div class="flex flex-wrap gap-1">
            <Button variant="outline" size="sm" class="flex-1" @click="editRegistry(index)">
              <i class="fas fa-edit"></i>
            </Button>
            <Button
              variant="outline"
              size="sm"
              class="flex-1"
              :disabled="testingRegistry === index"
              @click="testRegistryLogin(index)"
            >
              <i class="fas fa-vial" :class="{ 'fa-spin': testingRegistry === index }"></i>
            </Button>
            <Button
              variant="outline"
              size="sm"
              class="flex-1"
              title="成员授权"
              @click="openResourcePermission(registry)"
            >
              <i class="fas fa-user-shield"></i>
            </Button>
            <Button
              variant="destructive"
              size="sm"
              class="flex-1"
              @click="removeRegistry(registry)"
            >
              <i class="fas fa-trash"></i>
            </Button>
          </div>
        </CardHeader>
        <CardContent class="space-y-3 p-4 text-sm">
          <div class="flex gap-2 text-slate-600">
            <i class="fas fa-server mt-0.5 w-4 shrink-0 text-slate-400"></i>
            <code class="truncate font-mono text-xs text-slate-800" :title="registry.registry">{{
              registry.registry
            }}</code>
          </div>
          <div v-if="registry.registry_prefix" class="flex gap-2 text-slate-600">
            <i class="fas fa-tag mt-0.5 w-4 shrink-0 text-slate-400"></i>
            <span>前缀：{{ registry.registry_prefix }}</span>
          </div>
          <div class="flex gap-2 text-slate-600">
            <i class="fas fa-shield-alt mt-0.5 w-4 shrink-0 text-slate-400"></i>
            <span>{{
              !registry.username && !registry.has_password
                ? "无需认证（公开仓库）"
                : registry.username && registry.has_password
                  ? "已配置认证"
                  : "认证不完整"
            }}</span>
          </div>
          <div
            v-if="registry.username || registry.has_password"
            class="flex gap-2 text-slate-600"
          >
            <i class="fas fa-user mt-0.5 w-4 shrink-0 text-slate-400"></i>
            <span>账号：{{ registry.username || "未设置" }}</span>
          </div>
          <div
            v-if="registry.username || registry.has_password"
            class="flex gap-2 text-slate-600"
          >
            <i class="fas fa-key mt-0.5 w-4 shrink-0 text-slate-400"></i>
            <span>密码：{{ registry.has_password ? "已设置" : "未设置" }}</span>
          </div>
          <AlertBanner
            v-if="registryTestResult[index]"
            :message="registryTestResult[index].message"
            :variant="registryTestResult[index].success ? 'success' : 'danger'"
            :show-icon="true"
            class="!mt-0"
          />
        </CardContent>
      </Card>
    </div>

    <FormDialog
      v-model="showRegistryModal"
      :title="editingRegistryId ? '编辑镜像仓库' : '新建镜像仓库'"
      icon="fa-box"
      size="lg"
    >
      <form class="space-y-4" @submit.prevent="saveRegistry">
        <div class="space-y-2">
          <Label>仓库名称 <span class="text-red-500">*</span></Label>
          <Input v-model="registryForm.name" placeholder="如：Docker Hub" required />
        </div>
        <div class="space-y-2">
          <Label>Registry 地址 <span class="text-red-500">*</span></Label>
          <Input v-model="registryForm.registry" placeholder="docker.io" required />
        </div>
        <div class="space-y-2">
          <Label>镜像前缀（可选）</Label>
          <Input v-model="registryForm.registry_prefix" placeholder="your-namespace" />
          <p class="text-xs text-slate-500">用于自动生成镜像名称的前缀</p>
        </div>
        <div class="space-y-2">
          <Label>认证信息（可选）</Label>
          <p class="text-xs text-slate-500">公开仓库可留空；私有仓库需填写用户名和密码</p>
        </div>
        <div class="space-y-2">
          <Label>账号</Label>
          <Input v-model="registryForm.username" placeholder="用户名（可选）" />
        </div>
        <div class="space-y-2">
          <Label>密码</Label>
          <div class="flex gap-2">
            <Input v-model="registryForm.password" type="password" placeholder="密码（可选）" class="flex-1" />
            <Button
              type="button"
              variant="outline"
              :disabled="testingRegistry === 'current'"
              @click="testCurrentRegistryLogin"
            >
              <i class="fas fa-vial" :class="{ 'fa-spin': testingRegistry === 'current' }"></i>
              {{ testingRegistry === "current" ? "测试中…" : "测试" }}
            </Button>
          </div>
          <AlertBanner
            v-if="registryTestResult['current']"
            :message="registryTestResult['current'].message"
            :variant="registryTestResult['current'].success ? 'success' : 'danger'"
          />
          <ul
            v-if="registryTestResult['current']?.suggestions?.length"
            class="list-inside list-disc text-xs text-slate-600"
          >
            <li v-for="(s, idx) in registryTestResult['current'].suggestions" :key="idx">{{ s }}</li>
          </ul>
        </div>
        <label class="flex cursor-pointer items-start gap-2 text-sm">
          <input
            v-model="registryForm.active"
            type="checkbox"
            class="mt-1 h-4 w-4 rounded border-slate-300"
          />
          <span>
            <span class="font-medium text-slate-900">设为激活仓库</span>
            <span class="mt-0.5 block text-xs text-slate-500">激活的仓库将作为默认推送目标</span>
          </span>
        </label>
      </form>
      <template #footer>
        <Button variant="outline" type="button" @click="closeRegistryModal">取消</Button>
        <Button
          type="button"
          :disabled="!registryForm.name || !registryForm.registry || savingRegistries"
          @click="saveRegistry"
        >
          <i class="fas fa-save"></i>
          保存
        </Button>
      </template>
    </FormDialog>

    <ResourceMemberPermissionDialog
      v-model="permissionDialogOpen"
      resource-type="registry"
      :resource-id="permissionTarget?.registry_id || ''"
      :team-id="teamStore.activeTeamId"
      :resource-name="permissionTarget?.name || ''"
    />
  </div>
</template>

<script setup>
import axios from "axios";
import { onMounted, ref } from "vue";
import { useTeamStore } from "@/stores/team";
import ResourceMemberPermissionDialog from "@/components/team/ResourceMemberPermissionDialog.vue";

const teamStore = useTeamStore();
const permissionDialogOpen = ref(false);
const permissionTarget = ref(null);

function openResourcePermission(registry) {
  permissionTarget.value = registry;
  permissionDialogOpen.value = true;
}
import PageToolbar from "@/components/ui/PageToolbar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import { Badge } from "@/components/ui/badge";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";

const registries = ref([]);
const loadingRegistries = ref(false);
const savingRegistries = ref(false);
const testingRegistry = ref(null);
const registryTestResult = ref({});
const showRegistryModal = ref(false);
const editingRegistryId = ref(null);
const registryForm = ref({
  name: "",
  registry: "",
  registry_prefix: "",
  username: "",
  password: "",
  active: false,
});

async function loadRegistries() {
  loadingRegistries.value = true;
  try {
    const res = await axios.get("/api/registries");
    registries.value = res.data.registries || [];
  } catch (error) {
    console.error("加载镜像仓库配置失败:", error);
    alert("加载镜像仓库配置失败");
  } finally {
    loadingRegistries.value = false;
  }
}

function showCreateRegistryModal() {
  editingRegistryId.value = null;
  registryForm.value = {
    name: "",
    registry: "docker.io",
    registry_prefix: "",
    username: "",
    password: "",
    active: false,
  };
  registryTestResult.value = {};
  showRegistryModal.value = true;
}

function editRegistry(index) {
  const registry = registries.value[index];
  editingRegistryId.value = registry.registry_id || null;
  registryForm.value = {
    name: registry.name,
    registry: registry.registry,
    registry_prefix: registry.registry_prefix || "",
    username: registry.username || "",
    password: registry.has_password ? "******" : "",
    active: registry.active,
  };
  registryTestResult.value = {};
  showRegistryModal.value = true;
}

function closeRegistryModal() {
  showRegistryModal.value = false;
  editingRegistryId.value = null;
  registryForm.value = {
    name: "",
    registry: "",
    registry_prefix: "",
    username: "",
    password: "",
    active: false,
  };
  registryTestResult.value = {};
}

async function saveRegistry() {
  if (!registryForm.value.name || !registryForm.value.registry) {
    alert("请填写仓库名称和 Registry 地址");
    return;
  }

  savingRegistries.value = true;
  try {
    const passwordUnchanged = registryForm.value.password === "******";
    const payload = {
      name: registryForm.value.name,
      registry: registryForm.value.registry,
      registry_prefix: registryForm.value.registry_prefix || "",
      username: registryForm.value.username || "",
      active: registryForm.value.active,
    };
    if (!passwordUnchanged && registryForm.value.password) {
      payload.password = registryForm.value.password;
    } else if (!passwordUnchanged) {
      payload.password = "";
    }

    if (editingRegistryId.value) {
      await axios.put(`/api/registries/${editingRegistryId.value}`, payload);
    } else {
      await axios.post("/api/registries", {
        ...payload,
        team_id: teamStore.activeTeamId,
      });
    }
    await loadRegistries();
    closeRegistryModal();
  } catch (error) {
    console.error("保存镜像仓库失败:", error);
    alert(error.response?.data?.detail || "保存镜像仓库失败");
  } finally {
    savingRegistries.value = false;
  }
}

async function testCurrentRegistryLogin() {
  if (!registryForm.value.registry) {
    alert("请先填写 Registry 地址");
    return;
  }
  const username = (registryForm.value.username || "").trim();
  const password = registryForm.value.password;
  const hasPassword = Boolean(password && password !== "******");
  if ((username && !hasPassword) || (!username && hasPassword)) {
    alert("用户名和密码需同时填写，或均留空（公开仓库）");
    return;
  }
  const withAuth = Boolean(username && hasPassword);

  testingRegistry.value = "current";
  registryTestResult.value["current"] = null;

  try {
    const payload = {
      name: registryForm.value.name || "",
      registry_id: editingRegistryId.value || "",
      registry: registryForm.value.registry,
      username: registryForm.value.username || "",
    };
    if (withAuth) {
      payload.password = registryForm.value.password;
    }
    const res = await axios.post("/api/registries/test", payload);
    registryTestResult.value["current"] = {
      success: res.data.success,
      message: res.data.message,
      details: res.data.details,
      suggestions: res.data.suggestions,
    };
  } catch (error) {
    const errorData = error.response?.data || {};
    registryTestResult.value["current"] = {
      success: false,
      message: errorData.message || errorData.detail || "测试失败",
      suggestions: errorData.suggestions,
    };
  } finally {
    testingRegistry.value = null;
  }
}

async function removeRegistry(registry) {
  if (!registry?.registry_id) return;
  if (!confirm(`确定删除镜像仓库「${registry.name}」吗？`)) return;
  try {
    await axios.delete(`/api/registries/${registry.registry_id}`);
    await loadRegistries();
  } catch (error) {
    alert(error.response?.data?.detail || "删除失败");
  }
}

async function testRegistryLogin(index) {
  const registry = registries.value[index];
  if (!registry.registry) {
    alert("请先填写 Registry 地址");
    return;
  }
  if (registry.username && !registry.has_password) {
    alert("已填写用户名但未配置密码，请补全或清空用户名");
    return;
  }

  testingRegistry.value = index;
  registryTestResult.value[index] = null;

  try {
    const res = await axios.post("/api/registries/test", {
      name: registry.name || "",
      registry_id: registry.registry_id || "",
      registry: registry.registry,
      username: registry.username || "",
    });
    registryTestResult.value[index] = {
      success: res.data.success,
      message: res.data.message,
      suggestions: res.data.suggestions,
    };
  } catch (error) {
    const errorData = error.response?.data || {};
    registryTestResult.value[index] = {
      success: false,
      message: errorData.message || errorData.detail || "测试失败",
      suggestions: errorData.suggestions,
    };
  } finally {
    testingRegistry.value = null;
  }
}

onMounted(() => {
  loadRegistries();
});
</script>

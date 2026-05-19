<template>
  <div
    v-if="teamId"
    class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
  >
    <h3 class="mb-2 font-semibold text-slate-900">流水线资源权限</h3>
    <p class="mb-4 text-xs text-slate-500">
      选择流水线后为团队成员设置 admin / edit / run / view 权限。
    </p>
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div class="grow space-y-2">
        <Label for="pipeline-pick">流水线</Label>
        <NativeSelect
          id="pipeline-pick"
          v-model="selectedPipelineId"
          class="w-full"
          @change="loadMembers"
        >
          <option value="">请选择流水线</option>
          <option
            v-for="p in pipelines"
            :key="p.pipeline_id"
            :value="p.pipeline_id"
          >
            {{ p.name }}
          </option>
        </NativeSelect>
      </div>
      <Button
        type="button"
        size="sm"
        variant="outline"
        :disabled="loadingPipelines"
        @click="fetchPipelines"
      >
        刷新列表
      </Button>
    </div>

    <div v-if="selectedPipelineId && canManageResource" class="mt-6 space-y-4">
      <div class="flex flex-wrap items-end gap-2 border-t border-slate-100 pt-4">
        <div class="min-w-[140px] grow space-y-1">
          <Label>成员</Label>
          <NativeSelect v-model="targetUserId" class="w-full">
            <option value="">选择成员</option>
            <option
              v-for="m in teamMembers"
              :key="m.user_id"
              :value="m.user_id"
            >
              {{ m.username }}
            </option>
          </NativeSelect>
        </div>
        <div class="min-w-[120px] space-y-1">
          <Label>权限</Label>
          <NativeSelect v-model="newPermission" class="w-full">
            <option value="view">查看</option>
            <option value="run">运行</option>
            <option value="edit">编辑</option>
            <option value="admin">管理员</option>
          </NativeSelect>
        </div>
        <Button
          type="button"
          size="sm"
          :disabled="!targetUserId || saving"
          @click="setPermission"
        >
          {{ saving ? "保存中…" : "设置权限" }}
        </Button>
      </div>

      <div v-if="permLoading" class="text-sm text-slate-500">加载权限…</div>
      <ul
        v-else
        class="divide-y divide-slate-100 rounded-md border border-slate-200"
      >
        <li
          v-for="row in resourceMembers"
          :key="row.user_id"
          class="flex flex-wrap items-center justify-between gap-2 px-3 py-2 text-sm"
        >
          <span class="font-medium text-slate-800">{{ row.username }}</span>
          <span class="text-slate-600">{{ permLabel(row.permission) }}</span>
        </li>
        <li
          v-if="!resourceMembers.length"
          class="px-3 py-4 text-center text-slate-500"
        >
          暂无单独设置的成员权限
        </li>
      </ul>
      <p v-if="permError" class="text-sm text-amber-700">{{ permError }}</p>
    </div>
    <p
      v-else-if="selectedPipelineId && !canManageResource"
      class="mt-4 text-sm text-slate-500"
    >
      您对该流水线无管理员权限，无法管理成员。
    </p>
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, ref, watch } from "vue";
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";

const props = defineProps({
  teamId: { type: String, default: "" },
});

const teamStore = useTeamStore();

const pipelines = ref([]);
const selectedPipelineId = ref("");
const loadingPipelines = ref(false);
const resourceMembers = ref([]);
const permLoading = ref(false);
const permError = ref("");
const targetUserId = ref("");
const newPermission = ref("view");
const saving = ref(false);
const myPermission = ref(null);

const teamMembers = computed(() => teamStore.members || []);

const canManageResource = computed(
  () => myPermission.value === "admin" || teamStore.canManageTeam
);

function permLabel(p) {
  const map = { admin: "管理员", edit: "编辑", run: "运行", view: "查看" };
  return map[p] || p;
}

async function fetchPipelines() {
  if (!props.teamId) return;
  loadingPipelines.value = true;
  try {
    const res = await axios.get("/api/pipelines", {
      params: { team_id: props.teamId },
    });
    pipelines.value = res.data?.pipelines || [];
  } catch {
    pipelines.value = [];
  } finally {
    loadingPipelines.value = false;
  }
}

async function loadMyPermission() {
  if (!selectedPipelineId.value) {
    myPermission.value = null;
    return;
  }
  try {
    const res = await axios.get(
      `/api/pipelines/${selectedPipelineId.value}/my-permission`
    );
    myPermission.value = res.data?.permission || null;
  } catch {
    myPermission.value = null;
  }
}

async function loadMembers() {
  permError.value = "";
  resourceMembers.value = [];
  if (!selectedPipelineId.value) return;
  await loadMyPermission();
  if (!canManageResource.value) return;
  permLoading.value = true;
  try {
    const res = await axios.get(
      `/api/pipelines/${selectedPipelineId.value}/members`
    );
    resourceMembers.value = Array.isArray(res.data) ? res.data : [];
  } catch (e) {
    permError.value =
      e?.response?.data?.detail || "无法加载成员权限（需要流水线 admin）";
    resourceMembers.value = [];
  } finally {
    permLoading.value = false;
  }
}

async function setPermission() {
  if (!selectedPipelineId.value || !targetUserId.value) return;
  saving.value = true;
  permError.value = "";
  try {
    await axios.put(
      `/api/pipelines/${selectedPipelineId.value}/members/${targetUserId.value}`,
      { permission: newPermission.value }
    );
    await loadMembers();
    targetUserId.value = "";
  } catch (e) {
    permError.value = e?.response?.data?.detail || "设置失败";
  } finally {
    saving.value = false;
  }
}

watch(
  () => props.teamId,
  (id) => {
    selectedPipelineId.value = "";
    if (id) {
      teamStore.fetchMembers(id);
      fetchPipelines();
    }
  },
  { immediate: true }
);
</script>

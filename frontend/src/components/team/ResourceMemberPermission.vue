<template>
  <div v-if="resourceId" class="space-y-4">
    <div>
      <h4 class="text-sm font-semibold text-slate-900">成员权限</h4>
      <p class="mt-1 text-xs text-slate-500">
        为当前资源指定团队成员的访问级别（查看 / 运行 / 编辑 / 管理员）。
      </p>
    </div>

    <div v-if="canManageResource" class="space-y-4">
      <div class="flex flex-wrap items-end gap-2">
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
          {{ saving ?"保存中…" :"设置权限" }}
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
          <div class="flex items-center gap-2">
            <span class="text-slate-600">{{ permLabel(row.permission) }}</span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              :disabled="removingId === row.user_id"
              @click="removePermission(row)"
            >
              {{ removingId === row.user_id ?"…" :"移除" }}
            </Button>
          </div>
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
    <p v-else class="text-sm text-slate-500">
      您对该资源无管理员权限，无法管理成员。
    </p>
  </div>
</template>

<script setup>
import { showConfirm } from "@/composables/useConfirm";

import axios from "axios";
import { computed, ref, watch } from "vue";
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";

const API_PREFIX = {
  pipeline:"/api/pipelines",
  git_source:"/api/git-sources",
  agent_host:"/api/hosts",
  deploy_config:"/api/deploy-configs",
  resource_package:"/api/resource-packages",
  registry:"/api/registries",
  template:"/api/templates",
};

const props = defineProps({
  resourceType: {
    type: String,
    required: true,
    validator: (v) =>
      ["pipeline","git_source","agent_host","deploy_config","resource_package","registry","template",
      ].includes(v),
  },
  resourceId: { type: String, default:"" },
  teamId: { type: String, default:"" },
});

const teamStore = useTeamStore();

const resourceMembers = ref([]);
const permLoading = ref(false);
const permError = ref("");
const targetUserId = ref("");
const newPermission = ref("view");
const saving = ref(false);
const removingId = ref("");
const myPermission = ref(null);

const apiBase = computed(() => API_PREFIX[props.resourceType] ||"");

const teamMembers = computed(() => teamStore.members || []);

const canManageResource = computed(
  () => myPermission.value ==="admin" || teamStore.canManageTeam
);

function permLabel(p) {
  const map = { admin:"管理员", edit:"编辑", run:"运行", view:"查看" };
  return map[p] || p;
}

async function loadMyPermission() {
  if (!props.resourceId || !apiBase.value) {
    myPermission.value = null;
    return;
  }
  try {
    const res = await axios.get(
      `${apiBase.value}/${props.resourceId}/my-permission`
    );
    myPermission.value = res.data?.permission || null;
  } catch {
    myPermission.value = null;
  }
}

async function loadMembers() {
  permError.value ="";
  resourceMembers.value = [];
  if (!props.resourceId || !apiBase.value) return;
  await loadMyPermission();
  if (!canManageResource.value) return;
  permLoading.value = true;
  try {
    const res = await axios.get(
      `${apiBase.value}/${props.resourceId}/members`
    );
    resourceMembers.value = Array.isArray(res.data) ? res.data : [];
  } catch (e) {
    permError.value =
      e?.response?.data?.detail ||"无法加载成员权限（需要资源管理员权限）";
    resourceMembers.value = [];
  } finally {
    permLoading.value = false;
  }
}

async function setPermission() {
  if (!props.resourceId || !targetUserId.value || !apiBase.value) return;
  saving.value = true;
  permError.value ="";
  try {
    await axios.put(
      `${apiBase.value}/${props.resourceId}/members/${targetUserId.value}`,
      { permission: newPermission.value }
    );
    await loadMembers();
    targetUserId.value ="";
  } catch (e) {
    permError.value = e?.response?.data?.detail ||"设置失败";
  } finally {
    saving.value = false;
  }
}

async function removePermission(row) {
  if (!props.resourceId || !apiBase.value) return;
  if (!(await showConfirm({ message: `确定移除「${row.username}」对该资源的单独权限吗？` }))) return;
  removingId.value = row.user_id;
  permError.value ="";
  try {
    await axios.delete(
      `${apiBase.value}/${props.resourceId}/members/${row.user_id}`
    );
    await loadMembers();
  } catch (e) {
    permError.value = e?.response?.data?.detail ||"移除失败";
  } finally {
    removingId.value ="";
  }
}

watch(
  () => [props.resourceId, props.teamId, props.resourceType],
  ([rid, tid]) => {
    targetUserId.value ="";
    if (tid) teamStore.fetchMembers(tid);
    if (rid) loadMembers();
    else {
      resourceMembers.value = [];
      myPermission.value = null;
    }
  },
  { immediate: true }
);
</script>

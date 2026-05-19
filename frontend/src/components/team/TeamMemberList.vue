<template>
  <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
      <h3 class="font-semibold text-slate-900">成员列表</h3>
      <Button v-if="teamStore.canManageTeam" size="sm" type="button" @click="$emit('invite')">
        <i class="fas fa-user-plus mr-1"></i>
        邀请成员
      </Button>
    </div>
    <div class="p-4">
      <div v-if="loading" class="py-8 text-center text-sm text-slate-500">加载中…</div>
      <div v-else-if="error" class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
        {{ error }}
      </div>
      <template v-else>
      <!-- 移动端：卡片列表 -->
      <div class="md:hidden space-y-3">
        <div
          v-for="m in members"
          :key="m.user_id"
          class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0 flex-1">
              <div class="font-medium text-slate-900">{{ m.username }}</div>
              <div class="mt-0.5 truncate text-xs text-slate-500">{{ m.email || "—" }}</div>
            </div>
            <span
              v-if="!teamStore.canManageTeam || m.role === 'owner'"
              class="shrink-0 text-sm text-slate-600"
            >{{ roleLabel(m.role) }}</span>
          </div>
          <div
            v-if="teamStore.canManageTeam && m.role !== 'owner'"
            class="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-200 pt-3"
          >
            <NativeSelect
              :value="m.role"
              class="min-h-11 min-w-[120px] flex-1"
              @change="onRoleChange(m, $event)"
            >
              <option value="member">成员</option>
              <option value="admin">管理员</option>
            </NativeSelect>
            <Button
              variant="destructive"
              size="sm"
              type="button"
              class="min-h-11 shrink-0"
              @click="removeMember(m)"
            >
              移除
            </Button>
          </div>
        </div>
      </div>

      <!-- 桌面端：表格 -->
      <div class="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>用户名</TableHead>
              <TableHead>邮箱</TableHead>
              <TableHead>角色</TableHead>
              <TableHead class="text-end">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="m in members" :key="m.user_id">
              <TableCell class="font-medium">{{ m.username }}</TableCell>
              <TableCell>{{ m.email || "—" }}</TableCell>
              <TableCell>
                <NativeSelect
                  v-if="teamStore.canManageTeam && m.role !== 'owner'"
                  :value="m.role"
                  class="max-w-[140px]"
                  @change="onRoleChange(m, $event)"
                >
                  <option value="member">成员</option>
                  <option value="admin">管理员</option>
                </NativeSelect>
                <span v-else class="text-sm">{{ roleLabel(m.role) }}</span>
              </TableCell>
              <TableCell class="text-end">
                <Button
                  v-if="teamStore.canManageTeam && m.role !== 'owner'"
                  variant="destructive"
                  size="sm"
                  type="button"
                  @click="removeMember(m)"
                >
                  移除
                </Button>
                <span v-else class="text-xs text-slate-400">—</span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import axios from "axios";
import { ref, watch } from "vue";
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import Table from "@/components/ui/table/Table.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableRow from "@/components/ui/table/TableRow.vue";

const props = defineProps({
  teamId: { type: String, default: "" },
});

defineEmits(["invite"]);

const teamStore = useTeamStore();
const members = ref([]);
const loading = ref(false);
const error = ref("");

function roleLabel(r) {
  const map = { owner: "所有者", admin: "管理员", member: "成员" };
  return map[r] || r;
}

async function load() {
  if (!props.teamId) return;
  loading.value = true;
  error.value = "";
  try {
    const res = await axios.get(`/api/teams/${props.teamId}/members`);
    members.value = Array.isArray(res.data)
      ? res.data.map((x) => ({ ...x }))
      : [];
  } catch (e) {
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail === "string"
        ? detail
        : "无法加载成员列表";
    members.value = [];
  } finally {
    loading.value = false;
  }
}

async function onRoleChange(m, ev) {
  const newRole = ev.target.value;
  const prev = m.role;
  try {
    await axios.patch(`/api/teams/${props.teamId}/members/${m.user_id}`, {
      role: newRole,
    });
    m.role = newRole;
  } catch (e) {
    m.role = prev;
    const detail = e?.response?.data?.detail;
    alert(typeof detail === "string" ? detail : "更新角色失败");
  }
}

async function removeMember(m) {
  if (!confirm(`确定要将「${m.username}」移出团队吗？`)) return;
  try {
    await axios.delete(`/api/teams/${props.teamId}/members/${m.user_id}`);
    await load();
  } catch (e) {
    const detail = e?.response?.data?.detail;
    alert(typeof detail === "string" ? detail : "移除失败");
  }
}

watch(
  () => props.teamId,
  () => load(),
  { immediate: true }
);
</script>

<template>
  <div class="space-y-6">
    <div v-if="teamStore.loading" class="text-sm text-slate-500">正在加载团队信息…</div>
    <div
      v-else-if="teamStore.error && !teamStore.memberships.length"
      class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      {{ teamStore.error }}
    </div>
    <div
      v-else-if="!teamStore.memberships.length"
      class="rounded-lg border border-slate-200 bg-white p-6 text-center text-slate-600"
    >
      您尚未加入任何团队，请前往
      <RouterLink to="/onboarding" class="font-medium text-blue-600 hover:text-blue-700">
        创建或加入团队
      </RouterLink>
      。
    </div>
    <template v-else>
      <div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h3 class="mb-4 font-semibold text-slate-900">基本信息</h3>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div class="grow space-y-2">
            <Label for="team-name">名称</Label>
            <Input id="team-name" v-model="teamName" :disabled="!teamStore.canManageTeam" />
          </div>
          <Button type="button" :disabled="!teamStore.canManageTeam || savingName" @click="saveTeamName">
            {{ savingName ? "保存中…" : "保存" }}
          </Button>
        </div>
        <p v-if="!teamStore.canManageTeam" class="mt-2 text-xs text-slate-500">
          仅团队所有者或管理员可修改团队名称。
        </p>
      </div>

      <div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h3 class="mb-4 font-semibold text-slate-900">任务设置</h3>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div class="grow space-y-2">
            <Label for="task-cleanup-days">任务保留天数</Label>
            <Input
              id="task-cleanup-days"
              v-model.number="taskCleanupDays"
              type="number"
              min="1"
              max="365"
              :disabled="!teamStore.canManageTeam"
            />
            <p class="text-xs text-slate-500">
              超过该天数的已完成任务将被自动清理，默认 7 天。
            </p>
          </div>
          <Button
            type="button"
            :disabled="!teamStore.canManageTeam || savingCleanupDays"
            @click="saveTaskCleanupDays"
          >
            {{ savingCleanupDays ? "保存中…" : "保存" }}
          </Button>
        </div>
        <p v-if="!teamStore.canManageTeam" class="mt-2 text-xs text-slate-500">
          仅团队所有者或管理员可修改此设置。
        </p>
      </div>

      <div
        v-if="isOwner"
        class="rounded-lg border border-amber-200 bg-amber-50/40 p-6 shadow-sm"
      >
        <h3 class="mb-2 font-semibold text-slate-900">转移所有权</h3>
        <p class="mb-4 text-sm text-slate-600">
          将团队所有权转移给其他成员后，对方将成为所有者，您将变为管理员。删除团队等仅所有者可执行的操作将不再对您开放。
        </p>
        <p
          v-if="!transferCandidates.length && !membersLoading"
          class="text-sm text-slate-600"
        >
          请先邀请至少一名其他成员后再转移所有权。
        </p>
        <div
          v-else
          class="flex flex-col gap-3 sm:flex-row sm:items-end"
        >
          <div class="grow space-y-2">
            <Label for="transfer-target">新所有者</Label>
            <NativeSelect
              id="transfer-target"
              v-model="transferTargetId"
              :disabled="membersLoading || transferring"
              class="min-h-11"
            >
              <option value="">请选择成员</option>
              <option
                v-for="m in transferCandidates"
                :key="m.user_id"
                :value="m.user_id"
              >
                {{ m.username }}{{ m.email ? ` (${m.email})` : "" }}
              </option>
            </NativeSelect>
          </div>
          <Button
            type="button"
            variant="destructive"
            :disabled="!transferTargetId || membersLoading || transferring"
            @click="transferOwnership"
          >
            {{ transferring ? "转移中…" : "转移所有权" }}
          </Button>
        </div>
      </div>

      <TeamMemberList
        ref="memberListRef"
        :team-id="teamStore.activeTeamId"
        @invite="inviteOpen = true"
      />

      <InviteMemberDialog
        v-if="teamStore.activeTeamId"
        v-model="inviteOpen"
        :team-id="teamStore.activeTeamId"
        :allow-owner-invite="isOwner"
        @invited="onInvited"
      />
    </template>
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, ref, watch } from "vue";
import { RouterLink } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import InviteMemberDialog from "@/components/team/InviteMemberDialog.vue";
import TeamMemberList from "@/components/team/TeamMemberList.vue";

const teamStore = useTeamStore();
const authStore = useAuthStore();

const teamName = ref("");
const taskCleanupDays = ref(7);
const savingName = ref(false);
const savingCleanupDays = ref(false);
const inviteOpen = ref(false);
const memberListRef = ref(null);
const teamMembers = ref([]);
const membersLoading = ref(false);
const transferTargetId = ref("");
const transferring = ref(false);

const isOwner = computed(() => {
  const m = teamStore.activeMembership;
  return m?.role === "owner";
});

const transferCandidates = computed(() => {
  const me = (authStore.username || "").trim();
  return teamMembers.value.filter(
    (m) => m.role !== "owner" && m.username !== me
  );
});

async function loadMembersForTransfer(teamId) {
  if (!teamId || !isOwner.value) {
    teamMembers.value = [];
    transferTargetId.value = "";
    return;
  }
  membersLoading.value = true;
  try {
    const res = await axios.get(`/api/teams/${teamId}/members`);
    teamMembers.value = Array.isArray(res.data)
      ? res.data.map((x) => ({ ...x }))
      : [];
    if (
      transferTargetId.value &&
      !transferCandidates.value.some((m) => m.user_id === transferTargetId.value)
    ) {
      transferTargetId.value = "";
    }
  } catch {
    teamMembers.value = [];
    transferTargetId.value = "";
  } finally {
    membersLoading.value = false;
  }
}

async function transferOwnership() {
  const teamId = teamStore.activeTeamId;
  const targetId = transferTargetId.value;
  if (!teamId || !targetId) return;
  const target = transferCandidates.value.find((m) => m.user_id === targetId);
  if (!target) return;
  const label = target.username || target.email || "该成员";
  if (
    !confirm(
      `确定将团队所有权转移给「${label}」吗？\n\n转移后对方将成为所有者，您将变为管理员，且无法再删除团队。`
    )
  ) {
    return;
  }
  transferring.value = true;
  try {
    await axios.patch(`/api/teams/${teamId}/members/${targetId}`, {
      role: "owner",
    });
    transferTargetId.value = "";
    await teamStore.fetchMyTeams();
    await loadMembersForTransfer(teamId);
    await memberListRef.value?.load?.();
  } catch (e) {
    const detail = e?.response?.data?.detail;
    alert(typeof detail === "string" ? detail : "转移所有权失败");
  } finally {
    transferring.value = false;
  }
}

watch(
  () => teamStore.activeTeam,
  (t) => {
    teamName.value = t?.name || "";
  },
  { immediate: true }
);

async function loadTeamSettings(teamId) {
  if (!teamId) return;
  try {
    const res = await axios.get(`/api/teams/${teamId}/settings`);
    taskCleanupDays.value = res.data?.task_cleanup_days ?? 7;
  } catch {
    taskCleanupDays.value = 7;
  }
}

watch(
  () => teamStore.activeTeamId,
  (id) => {
    loadTeamSettings(id);
    loadMembersForTransfer(id);
  },
  { immediate: true }
);

watch(isOwner, (owner) => {
  if (owner && teamStore.activeTeamId) {
    loadMembersForTransfer(teamStore.activeTeamId);
  } else {
    teamMembers.value = [];
    transferTargetId.value = "";
  }
});

async function saveTeamName() {
  const id = teamStore.activeTeamId;
  if (!id || !teamStore.canManageTeam) return;
  savingName.value = true;
  try {
    await axios.patch(`/api/teams/${id}`, { name: teamName.value.trim() });
    await teamStore.fetchMyTeams();
  } catch (e) {
    const detail = e?.response?.data?.detail;
    alert(typeof detail === "string" ? detail : "保存失败");
  } finally {
    savingName.value = false;
  }
}

async function saveTaskCleanupDays() {
  const id = teamStore.activeTeamId;
  if (!id || !teamStore.canManageTeam) return;
  const days = parseInt(taskCleanupDays.value, 10);
  if (isNaN(days) || days < 1 || days > 365) {
    alert("请输入 1–365 之间的有效天数");
    return;
  }
  savingCleanupDays.value = true;
  try {
    await axios.put(`/api/teams/${id}/settings`, { task_cleanup_days: days });
    taskCleanupDays.value = days;
  } catch (e) {
    const detail = e?.response?.data?.detail;
    alert(typeof detail === "string" ? detail : "保存失败");
  } finally {
    savingCleanupDays.value = false;
  }
}

async function onInvited() {
  const id = teamStore.activeTeamId;
  if (isOwner.value && id) {
    await loadMembersForTransfer(id);
  }
  await memberListRef.value?.load?.();
}
</script>

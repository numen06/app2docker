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

      <TeamMemberList :team-id="teamStore.activeTeamId" @invite="inviteOpen = true" />

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
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import InviteMemberDialog from "@/components/team/InviteMemberDialog.vue";
import TeamMemberList from "@/components/team/TeamMemberList.vue";

const teamStore = useTeamStore();

const teamName = ref("");
const taskCleanupDays = ref(7);
const savingName = ref(false);
const savingCleanupDays = ref(false);
const inviteOpen = ref(false);

const isOwner = computed(() => {
  const m = teamStore.activeMembership;
  return m?.role === "owner";
});

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
  },
  { immediate: true }
);

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

function onInvited() {
  /* optional refresh member list via TeamMemberList watch teamId */
}
</script>

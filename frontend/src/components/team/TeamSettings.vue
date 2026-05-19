<template>
  <div class="space-y-6">
    <div v-if="teamStore.loading" class="text-sm text-slate-500">加载团队信息…</div>
    <div v-else-if="teamStore.error && !teamStore.memberships.length" class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      {{ teamStore.error }}
    </div>
    <div v-else-if="!teamStore.memberships.length" class="rounded-lg border border-slate-200 bg-white p-6 text-center text-slate-600">
      暂无团队，请先
      <RouterLink to="/onboarding" class="font-medium text-blue-600 hover:text-blue-700">
        创建或加入团队
      </RouterLink>
      。
    </div>
    <template v-else>
      <div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <Label class="mb-2 block" for="team-picker">当前团队</Label>
        <NativeSelect id="team-picker" class="w-full sm:max-w-md" :value="teamStore.activeTeamId" @change="onPickTeam">
          <option v-for="m in teamStore.memberships" :key="m.team.team_id" :value="m.team.team_id">
            {{ m.team.name }}（{{ roleLabel(m.role) }}）
          </option>
        </NativeSelect>
      </div>

      <div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h3 class="mb-4 font-semibold text-slate-900">团队名称</h3>
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
          仅管理员或所有者可以修改团队名称。
        </p>
      </div>

      <TeamMemberList :team-id="teamStore.activeTeamId" @invite="inviteOpen = true" />

      <InviteMemberDialog
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
import { RouterLink, useRouter } from "vue-router";
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import InviteMemberDialog from "@/components/team/InviteMemberDialog.vue";
import TeamMemberList from "@/components/team/TeamMemberList.vue";

const router = useRouter();
const teamStore = useTeamStore();

const teamName = ref("");
const savingName = ref(false);
const inviteOpen = ref(false);

const isOwner = computed(() => {
  const m = teamStore.activeMembership;
  return m?.role === "owner";
});

function roleLabel(r) {
  const map = { owner: "所有者", admin: "管理员", member: "成员" };
  return map[r] || r;
}

async function onPickTeam(ev) {
  const nextId = ev.target.value;
  if (!nextId || nextId === teamStore.activeTeamId) return;
  await teamStore.setCurrentTeam(nextId);
  await router.replace(`/teams/${nextId}/settings`);
  window.dispatchEvent(
    new CustomEvent("team-context-changed", { detail: { teamId: nextId } })
  );
}

watch(
  () => teamStore.activeTeam,
  (t) => {
    teamName.value = t?.name || "";
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

function onInvited() {
  /* optional refresh member list via TeamMemberList watch teamId */
}
</script>

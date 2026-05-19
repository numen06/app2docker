<template>
  <div class="space-y-4">
    <div v-if="teamStore.loading" class="text-sm text-slate-500">加载团队信息…</div>
    <AlertBanner
      v-else-if="teamStore.error && !teamStore.memberships.length"
      :message="teamStore.error"
      variant="warning"
    />
    <div
      v-else-if="!teamStore.memberships.length"
      class="rounded-lg border border-slate-200 bg-slate-50 p-4 text-center text-sm text-slate-600"
    >
      您尚未加入任何团队。
      <div class="mt-3 flex flex-wrap justify-center gap-2">
        <Button size="sm" type="button" @click="goOnboarding">创建或加入团队</Button>
      </div>
    </div>
    <template v-else>
      <Card>
        <CardContent class="space-y-3 p-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h4 class="text-sm font-semibold text-slate-900">当前团队</h4>
            <Badge variant="default">{{ roleLabel(teamStore.activeTeamRole) }}</Badge>
          </div>
          <NativeSelect
            class="w-full"
            :value="teamStore.activeTeamId"
            @change="onPickTeam"
          >
            <option
              v-for="m in teamStore.memberships"
              :key="m.team.team_id"
              :value="m.team.team_id"
            >
              {{ m.team.name }}（{{ roleLabel(m.role) }}）
            </option>
          </NativeSelect>
          <p v-if="teamStore.activeTeam?.description" class="text-xs text-slate-500">
            {{ teamStore.activeTeam.description }}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent class="space-y-3 p-4">
          <h4 class="text-sm font-semibold text-slate-900">团队名称</h4>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-end">
            <Input
              v-model="teamName"
              class="flex-1"
              :disabled="!teamStore.canManageTeam"
              placeholder="团队名称"
            />
            <Button
              type="button"
              size="sm"
              :disabled="!teamStore.canManageTeam || savingName"
              @click="saveTeamName"
            >
              {{ savingName ? "保存中…" : "保存" }}
            </Button>
          </div>
          <p v-if="!teamStore.canManageTeam" class="text-xs text-slate-500">
            仅管理员或所有者可修改团队名称。
          </p>
        </CardContent>
      </Card>

      <TeamMemberList
        :team-id="teamStore.activeTeamId"
        @invite="inviteOpen = true"
      />

      <PipelinePermissionPanel
        v-if="teamStore.activeTeamId"
        :team-id="teamStore.activeTeamId"
      />

      <div class="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
        <Button variant="outline" size="sm" type="button" @click="goOnboarding">
          <i class="fas fa-plus mr-1"></i>创建/加入团队
        </Button>
      </div>

      <InviteMemberDialog
        v-model="inviteOpen"
        :team-id="teamStore.activeTeamId"
        :allow-owner-invite="isOwner"
      />
    </template>
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useTeamStore } from "@/stores/team";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import { Badge } from "@/components/ui/badge";
import Button from "@/components/ui/button/Button.vue";
import Card from "@/components/ui/card/Card.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import Input from "@/components/ui/input/Input.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import InviteMemberDialog from "@/components/team/InviteMemberDialog.vue";
import TeamMemberList from "@/components/team/TeamMemberList.vue";
import PipelinePermissionPanel from "@/components/team/PipelinePermissionPanel.vue";

const emit = defineEmits(["team-changed"]);

const router = useRouter();
const teamStore = useTeamStore();

const teamName = ref("");
const savingName = ref(false);
const inviteOpen = ref(false);

const isOwner = computed(() => teamStore.activeMembership?.role === "owner");

function roleLabel(r) {
  const map = { owner: "所有者", admin: "管理员", member: "成员" };
  return map[r] || r || "—";
}

async function onPickTeam(ev) {
  const nextId = ev.target?.value;
  if (!nextId || nextId === teamStore.activeTeamId) return;
  await teamStore.setCurrentTeam(nextId);
  emit("team-changed", nextId);
}

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

function goOnboarding() {
  router.push("/onboarding");
}

watch(
  () => teamStore.activeTeam,
  (t) => {
    teamName.value = t?.name || "";
  },
  { immediate: true }
);

watch(
  () => teamStore.activeTeamId,
  (id) => {
    if (id) teamStore.fetchMembers(id);
  },
  { immediate: true }
);
</script>

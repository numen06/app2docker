<template>
  <div class="min-h-screen bg-slate-50">
    <header class="sticky top-0 z-10 border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div class="flex min-w-0 flex-1 items-center gap-3">
          <span class="truncate text-sm font-semibold text-slate-800">
            <i class="fas fa-people-group mr-2 text-blue-600"></i>
            {{ teamStore.activeTeam?.name || "团队设置" }}
          </span>
          <NativeSelect
            v-if="teamStore.memberships.length > 1"
            class="max-w-[220px] shrink-0 text-sm"
            :value="teamId"
            @change="onSwitchTeam"
          >
            <option
              v-for="m in teamStore.memberships"
              :key="m.team.team_id"
              :value="m.team.team_id"
            >
              {{ m.team.name }}（{{ roleLabel(m.role) }}）
            </option>
          </NativeSelect>
        </div>
        <RouterLink
          to="/app/dashboard"
          class="text-sm text-slate-500 hover:text-slate-700"
        >
          返回控制台
        </RouterLink>
      </div>
    </header>
    <div class="mx-auto max-w-5xl px-4 py-6">
      <router-view :key="teamId" />
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useTeamStore } from "@/stores/team";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";

const route = useRoute();
const router = useRouter();
const teamStore = useTeamStore();

const teamId = computed(() => String(route.params.teamId || ""));

function roleLabel(r) {
  const map = { owner: "所有者", admin: "管理员", member: "成员" };
  return map[r] || r;
}

async function onSwitchTeam(ev) {
  const nextId = ev.target.value;
  if (!nextId || nextId === teamId.value) return;
  await teamStore.setCurrentTeam(nextId);
  await router.replace(`/teams/${nextId}/settings`);
}

watch(
  teamId,
  async (id) => {
    if (!id) return;
    await teamStore.setCurrentTeam(id);
  },
  { immediate: true }
);
</script>

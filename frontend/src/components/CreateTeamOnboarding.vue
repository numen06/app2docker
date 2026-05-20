<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
    <Card class="w-full max-w-lg shadow-lg shadow-slate-200/70">
      <CardHeader class="pb-4 text-center">
        <div class="mb-2 flex justify-center">
          <i class="fas fa-people-group text-4xl text-blue-600"></i>
        </div>
        <CardTitle class="text-center">加入或创建团队</CardTitle>
        <CardDescription>
          每位用户需至少属于一个团队。创建新团队或通过邀请链接加入已有团队。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div class="mb-4 flex rounded-lg border border-slate-200 p-1">
          <button
            type="button"
            class="flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors"
            :class="
              mode === 'create'
                ? 'bg-blue-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            "
            @click="mode = 'create'"
          >
            创建团队
          </button>
          <button
            type="button"
            class="flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors"
            :class="
              mode === 'join'
                ? 'bg-blue-600 text-white'
                : 'text-slate-600 hover:bg-slate-100'
            "
            @click="mode = 'join'"
          >
            加入团队
          </button>
        </div>

        <form v-if="mode === 'create'" class="space-y-4" @submit.prevent="createTeam">
          <div class="space-y-2">
            <Label for="team-name">团队名称</Label>
            <Input
              id="team-name"
              v-model="teamName"
              placeholder="例如：研发一组"
              required
              minlength="1"
            />
          </div>
          <div class="space-y-2">
            <Label for="team-desc">描述（可选）</Label>
            <Input id="team-desc" v-model="teamDesc" placeholder="团队简介" />
          </div>
          <Button type="submit" class="w-full" :disabled="loading">
            {{ loading ? "创建中…" : "创建并进入" }}
          </Button>
        </form>

        <form v-else class="space-y-4" @submit.prevent="joinTeam">
          <div class="space-y-2">
            <Label for="invite-token">邀请链接</Label>
            <Input
              id="invite-token"
              v-model="inviteToken"
              placeholder="粘贴邀请链接，或直接打开管理员发来的链接"
              required
            />
            <p class="text-xs text-slate-500">
              支持完整邀请链接；登录账号邮箱须与邀请绑定的邮箱一致。
            </p>
          </div>
          <Button type="submit" class="w-full" :disabled="loading">
            {{ loading ? "加入中…" : "接受邀请并进入" }}
          </Button>
        </form>

        <div
          v-if="error"
          class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {{ error }}
        </div>

        <p
          v-if="authStore.isGlobalAdmin"
          class="mt-4 text-center text-sm text-slate-500"
        >
          您是系统管理员，可
          <RouterLink
            to="/app/dashboard"
            class="font-medium text-blue-600 hover:text-blue-700"
          >
            跳过并进入系统后台
          </RouterLink>
        </p>
      </CardContent>
    </Card>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { extractInviteToken } from "@/utils/teamInvite";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardDescription from "@/components/ui/card/CardDescription.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const teamStore = useTeamStore();

const mode = ref("create");
const teamName = ref("");
const teamDesc = ref("");
const inviteToken = ref("");
const loading = ref(false);
const error = ref("");

async function goToAppDashboard(teamId) {
  await teamStore.setCurrentTeam(teamId);
  await teamStore.fetchMyTeams();
  await router.replace("/app/dashboard");
}

async function createTeam() {
  if (loading.value) return;
  error.value = "";
  loading.value = true;
  try {
    const res = await axios.post("/api/teams", {
      name: teamName.value.trim(),
      description: teamDesc.value.trim(),
    });
    const teamId = res.data?.team_id;
    if (!teamId) {
      error.value = "创建失败：未返回团队 ID";
      return;
    }
    await goToAppDashboard(teamId);
  } catch (e) {
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail === "string" ? detail : e?.message || "创建团队失败";
  } finally {
    loading.value = false;
  }
}

async function joinTeam() {
  if (loading.value) return;
  error.value = "";
  const token = extractInviteToken(inviteToken.value);
  if (!token) {
    error.value = "请输入有效的邀请码";
    return;
  }
  loading.value = true;
  try {
    const res = await axios.post(
      `/api/teams/invitations/${encodeURIComponent(token)}/accept`
    );
    const teamId = res.data?.team?.team_id;
    if (!teamId) {
      error.value = "加入失败：未返回团队信息";
      return;
    }
    await goToAppDashboard(teamId);
  } catch (e) {
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail === "string" ? detail : e?.message || "接受邀请失败";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  const fromQuery = route.query.invite;
  if (typeof fromQuery === "string" && fromQuery.trim()) {
    mode.value = "join";
    inviteToken.value = fromQuery.trim();
  }

  authStore.applyAxiosAuthHeader();
  try {
    await authStore.fetchMe();
  } catch {
    /* ignore */
  }
  await teamStore.fetchMyTeams();
  if (teamStore.memberships.length) {
    const id =
      teamStore.activeTeamId || teamStore.memberships[0]?.team?.team_id;
    if (id) {
      await router.replace("/app/dashboard");
    }
  }
});
</script>

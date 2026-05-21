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
        <div
          v-if="!activeInviteFromQuery"
          class="mb-4 flex rounded-lg border border-slate-200 p-1"
        >
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

        <template v-else>
          <div v-if="previewLoading" class="py-8 text-center text-sm text-slate-500">
            <i class="fas fa-spinner fa-spin mr-2"></i>正在加载邀请信息…
          </div>

          <div
            v-else-if="invitePreview?.already_member"
            class="space-y-4"
          >
            <div
              class="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-800"
            >
              您已是 <strong>{{ invitePreview.team_name }}</strong> 的成员（当前角色：{{
                roleLabel(invitePreview.current_role)
              }}）。
            </div>
            <Button type="button" class="w-full" :disabled="loading" @click="enterTeam">
              {{ loading ? "进入中…" : "进入团队" }}
            </Button>
          </div>

          <div
            v-else-if="invitePreview?.status === 'valid'"
            class="space-y-4"
          >
            <div class="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
              <p>
                邀请加入团队：<strong>{{ invitePreview.team_name }}</strong>
              </p>
              <p class="mt-1 text-slate-600">
                加入后角色：{{ roleLabel(invitePreview.invite_role) }}
              </p>
            </div>
            <Button type="button" class="w-full" :disabled="loading" @click="acceptInvite">
              {{ loading ? "加入中…" : "接受邀请并进入" }}
            </Button>
            <details v-if="!activeInviteFromQuery" class="text-sm text-slate-500">
              <summary class="cursor-pointer hover:text-slate-700">手动粘贴邀请链接</summary>
              <form class="mt-3 space-y-2" @submit.prevent="joinTeamManual">
                <Input
                  v-model="inviteToken"
                  placeholder="粘贴邀请链接"
                  required
                />
                <Button type="submit" variant="secondary" class="w-full" :disabled="loading">
                  使用粘贴的链接加入
                </Button>
              </form>
            </details>
          </div>

          <div
            v-else-if="invitePreview?.status === 'expired'"
            class="space-y-4"
          >
            <div
              class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
            >
              邀请链接已过期。请联系团队管理员重新发送邀请。
            </div>
            <form
              v-if="!activeInviteFromQuery"
              class="space-y-4"
              @submit.prevent="joinTeamManual"
            >
              <div class="space-y-2">
                <Label for="invite-token">邀请链接</Label>
                <Input
                  id="invite-token"
                  v-model="inviteToken"
                  placeholder="粘贴新的邀请链接"
                  required
                />
              </div>
              <Button type="submit" class="w-full" :disabled="loading">
                {{ loading ? "加入中…" : "接受邀请并进入" }}
              </Button>
            </form>
          </div>

          <div
            v-else-if="invitePreview?.status === 'used'"
            class="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
          >
            该邀请已被使用。请联系团队管理员获取新的邀请链接。
          </div>

          <form
            v-else-if="!activeInviteFromQuery"
            class="space-y-4"
            @submit.prevent="joinTeamManual"
          >
            <div class="space-y-2">
              <Label for="invite-token">邀请链接</Label>
              <Input
                id="invite-token"
                v-model="inviteToken"
                placeholder="粘贴邀请链接，或直接打开管理员发来的链接"
                required
              />
              <p class="text-xs text-slate-500">
                支持完整邀请链接；登录后即可接受邀请加入团队。
              </p>
            </div>
            <Button type="submit" class="w-full" :disabled="loading">
              {{ loading ? "加入中…" : "接受邀请并进入" }}
            </Button>
          </form>
        </template>

        <div
          v-if="infoMessage"
          class="mt-4 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800"
        >
          {{ infoMessage }}
        </div>

        <div
          v-if="error"
          class="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {{ error }}
        </div>

        <p v-if="showBackLink" class="mt-4 text-center text-sm text-slate-500">
          <RouterLink
            :to="backLinkTo"
            class="font-medium text-blue-600 hover:text-blue-700"
          >
            {{ backLinkLabel }}
          </RouterLink>
        </p>

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
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { extractInviteToken } from "@/utils/teamInvite";
import { isUserNotFoundResponse } from "@/utils/auth";
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
const previewLoading = ref(false);
const error = ref("");
const infoMessage = ref("");
const invitePreview = ref(null);

const activeInviteFromQuery = computed(() => {
  const q = route.query.invite;
  return typeof q === "string" && q.trim().length > 0;
});

const showBackLink = computed(
  () =>
    invitePreview.value?.already_member ||
    teamStore.hasTeams ||
    activeInviteFromQuery.value
);

const backLinkTo = computed(() =>
  invitePreview.value?.already_member || teamStore.hasTeams
    ? "/app/dashboard"
    : "/"
);

const backLinkLabel = computed(() =>
  invitePreview.value?.already_member || teamStore.hasTeams
    ? "返回工作台"
    : "返回首页"
);

function roleLabel(role) {
  const r = (role || "").toLowerCase();
  if (r === "owner") return "所有者";
  if (r === "admin") return "管理员";
  if (r === "member") return "成员";
  return role || "—";
}

async function handleStaleSession(e) {
  if (!isUserNotFoundResponse(e)) return false;
  await authStore.logout();
  await router.replace(`/login?redirect=${encodeURIComponent(route.fullPath)}`);
  return true;
}

async function goToAppDashboard(teamId) {
  await teamStore.setCurrentTeam(teamId);
  await teamStore.fetchMyTeams();
  await router.replace("/app/dashboard");
}

function resolveInviteToken() {
  if (activeInviteFromQuery.value) {
    return extractInviteToken(String(route.query.invite));
  }
  return extractInviteToken(inviteToken.value);
}

async function renewInviteForAdmin(preview) {
  const res = await axios.get(`/api/teams/${preview.team_id}/invite/current`, {
    params: { role: preview.invite_role },
  });
  const newToken = res.data?.token;
  if (!newToken) {
    error.value = "续期失败：未返回新邀请令牌";
    return false;
  }
  infoMessage.value = "邀请链接已过期，已自动为您生成新链接。";
  await router.replace({
    path: "/onboarding",
    query: { invite: newToken },
  });
  return true;
}

async function loadInvitePreview(token, { allowRenew = true } = {}) {
  if (!token) {
    invitePreview.value = null;
    return;
  }
  previewLoading.value = true;
  error.value = "";
  try {
    const res = await axios.get(
      `/api/teams/invitations/${encodeURIComponent(token)}`
    );
    const data = res.data;
    if (
      allowRenew &&
      data?.status === "expired" &&
      data?.can_renew_as_admin
    ) {
      const renewed = await renewInviteForAdmin(data);
      if (renewed) {
        const next = extractInviteToken(String(route.query.invite));
        await loadInvitePreview(next, { allowRenew: false });
        return;
      }
    }
    invitePreview.value = data;
  } catch (e) {
    if (await handleStaleSession(e)) return;
    invitePreview.value = null;
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail === "string" ? detail : e?.message || "加载邀请信息失败";
  } finally {
    previewLoading.value = false;
  }
}

async function acceptInvite() {
  const token = resolveInviteToken();
  if (!token) {
    error.value = "请输入有效的邀请码";
    return;
  }
  if (loading.value) return;
  error.value = "";
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
    if (await handleStaleSession(e)) return;
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail === "string" ? detail : e?.message || "接受邀请失败";
  } finally {
    loading.value = false;
  }
}

async function joinTeamManual() {
  const token = extractInviteToken(inviteToken.value);
  if (!token) {
    error.value = "请输入有效的邀请码";
    return;
  }
  await loadInvitePreview(token);
  if (invitePreview.value?.status === "valid" && !invitePreview.value?.already_member) {
    await acceptInvite();
  }
}

async function enterTeam() {
  const teamId = invitePreview.value?.team_id;
  if (!teamId || loading.value) return;
  error.value = "";
  loading.value = true;
  try {
    await goToAppDashboard(teamId);
  } catch (e) {
    if (await handleStaleSession(e)) return;
    error.value = e?.message || "进入团队失败";
  } finally {
    loading.value = false;
  }
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
    if (await handleStaleSession(e)) return;
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail === "string" ? detail : e?.message || "创建团队失败";
  } finally {
    loading.value = false;
  }
}

watch(
  () => route.query.invite,
  async (invite) => {
    if (typeof invite === "string" && invite.trim()) {
      mode.value = "join";
      inviteToken.value = invite.trim();
      await loadInvitePreview(extractInviteToken(invite));
    } else {
      invitePreview.value = null;
      infoMessage.value = "";
    }
  }
);

onMounted(async () => {
  const fromQuery = route.query.invite;
  if (typeof fromQuery === "string" && fromQuery.trim()) {
    mode.value = "join";
    inviteToken.value = fromQuery.trim();
  }

  authStore.applyAxiosAuthHeader();
  try {
    await authStore.fetchMe();
  } catch (e) {
    if (await handleStaleSession(e)) return;
  }
  await teamStore.fetchMyTeams();

  const hasInvite =
    typeof fromQuery === "string" && fromQuery.trim().length > 0;
  if (hasInvite) {
    await loadInvitePreview(extractInviteToken(fromQuery));
  } else if (teamStore.memberships.length) {
    const id =
      teamStore.activeTeamId || teamStore.memberships[0]?.team?.team_id;
    if (id) {
      await router.replace("/app/dashboard");
    }
  }
});
</script>

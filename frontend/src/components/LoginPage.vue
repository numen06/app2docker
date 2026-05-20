<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
    <Card class="w-full max-w-md shadow-lg shadow-slate-200/70">
      <CardHeader class="pb-4 text-center">
        <div class="mb-2 flex justify-center">
          <i class="fas fa-box-open text-4xl text-blue-600"></i>
        </div>
        <CardTitle class="text-center">App2Docker</CardTitle>
        <CardDescription>Docker 镜像构建平台 · 安全登录</CardDescription>
      </CardHeader>
      <CardContent>
        <form class="space-y-4" @submit.prevent="handleLogin">
          <div class="space-y-2">
            <Label for="login-user"><i class="fas fa-user mr-1 text-slate-400"></i>用户名</Label>
            <Input
              id="login-user"
              v-model="username"
              type="text"
              autocomplete="username"
              placeholder="请输入用户名"
              required
            />
          </div>
          <div class="space-y-2">
            <Label for="login-pass"><i class="fas fa-lock mr-1 text-slate-400"></i>密码</Label>
            <Input
              id="login-pass"
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              required
            />
          </div>
          <label class="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
            <input v-model="rememberMe" type="checkbox" class="h-4 w-4 rounded border-slate-300" />
            记住我
          </label>
          <Button type="submit" class="w-full" :disabled="loading">
            <span v-if="loading">登录中…</span>
            <span v-else>登录</span>
          </Button>
          <div v-if="error" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {{ error }}
          </div>
        </form>
      </CardContent>
      <CardFooter class="flex-col gap-3 text-center text-sm text-slate-600">
        <div>
          还没有账号？
          <RouterLink :to="registerLink" class="font-medium text-blue-600 hover:text-blue-700">立即注册</RouterLink>
        </div>
        <div>
          <RouterLink to="/" class="text-slate-500 hover:text-slate-700">← 返回首页</RouterLink>
        </div>
        <div v-if="appVersion" class="border-t border-slate-100 pt-3 text-xs text-slate-500">
          <i class="fas fa-code-branch mr-1"></i>
          当前版本 <strong class="text-slate-700">v{{ appVersion }}</strong>
        </div>
        <div class="text-xs">
          <a
            :href="GITEE_REPO_URL"
            target="_blank"
            rel="noopener noreferrer"
            class="break-all text-slate-500 hover:text-blue-600"
          >
            {{ GITEE_REPO_URL }}
          </a>
        </div>
      </CardFooter>
    </Card>

    <UserCenterModal
      v-if="showChangePassword"
      v-model:show="showChangePassword"
      :username="loginUsername || ''"
      :require-password-change="true"
      @password-changed="handlePasswordChangeSuccess"
    />
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { parseLoginRedirect } from "@/utils/auth";
import { useAuthStore } from "@/stores/auth";
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardDescription from "@/components/ui/card/CardDescription.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import CardFooter from "@/components/ui/card/CardFooter.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import UserCenterModal from "@/components/UserCenterModal.vue";

const GITEE_REPO_URL = "https://gitee.com/numen06/app2docker";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const teamStore = useTeamStore();

const registerLink = computed(() => {
  const redirect = parseLoginRedirect(route.query.redirect);
  if (!redirect) return "/register";
  return `/register?redirect=${encodeURIComponent(redirect)}`;
});

const appVersion = ref("");
const username = ref("");
const password = ref("");
const rememberMe = ref(true);
const loading = ref(false);
const error = ref("");
const showChangePassword = ref(false);
const loginToken = ref(null);
const loginUsername = ref(null);

onMounted(async () => {
  try {
    const res = await axios.get("/api/public/version");
    if (res.data?.success && res.data.version) {
      appVersion.value = res.data.version;
    }
  } catch {
    /* optional */
  }
});

async function finishLogin(token, name) {
  authStore.setSession({
    token,
    username: name,
    remember: rememberMe.value,
  });
  const redirect = parseLoginRedirect(route.query.redirect);
  if (redirect) {
    await router.replace(redirect);
    return;
  }
  try {
    await authStore.fetchMe();
  } catch {
    /* ignore */
  }
  await teamStore.fetchTeams();
  const id = teamStore.currentTeamId;
  if (id) {
    await teamStore.setCurrentTeam(id);
    await router.replace("/app/dashboard");
  } else if (authStore.isGlobalAdmin) {
    await router.replace("/app/dashboard");
  } else {
    await router.replace("/onboarding");
  }
}

async function handleLogin() {
  if (loading.value) return;
  error.value = "";
  loading.value = true;
  try {
    const res = await axios.post("/api/login", {
      username: username.value.trim(),
      password: password.value,
    });
    if (res.data.success) {
      if (res.data.require_password_change) {
        loginToken.value = res.data.token;
        loginUsername.value = res.data.username;
        axios.defaults.headers.common.Authorization = `Bearer ${res.data.token}`;
        showChangePassword.value = true;
        loading.value = false;
        return;
      }
      await finishLogin(res.data.token, res.data.username);
      loading.value = false;
    } else {
      error.value = res.data.error || "登录失败";
      loading.value = false;
    }
  } catch (err) {
    console.error("登录错误:", err);
    if (err.response) {
      const status = err.response.status;
      if (status === 401) {
        error.value = "用户名或密码错误";
      } else {
        error.value =
          err.response.data?.error ||
          err.response.data?.detail ||
          "登录失败，请检查用户名和密码";
      }
    } else if (err.request) {
      error.value = "网络连接失败，请检查网络设置";
    } else {
      error.value = "登录失败，请稍后重试";
    }
    loading.value = false;
  }
}

async function handlePasswordChangeSuccess() {
  await finishLogin(loginToken.value, loginUsername.value);
  showChangePassword.value = false;
}
</script>

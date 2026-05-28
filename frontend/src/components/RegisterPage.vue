<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
    <Card class="w-full max-w-md shadow-lg shadow-slate-200/70">
      <CardHeader class="pb-4 text-center">
        <div class="mb-2 flex justify-center">
          <AppIcon  name="box-open" class="text-4xl text-blue-600" />
        </div>
        <CardTitle class="text-center">创建账号</CardTitle>
        <CardDescription>注册后即可登录控制台（用户名 ≥ 1，密码 ≥ 6 位）</CardDescription>
      </CardHeader>
      <CardContent>
        <form class="space-y-4" @submit.prevent="submit">
          <div class="space-y-2">
            <Label for="reg-user">用户名</Label>
            <Input id="reg-user" v-model="username" autocomplete="username" placeholder="请输入用户名" required />
          </div>
          <div class="space-y-2">
            <Label for="reg-email">邮箱</Label>
            <Input id="reg-email" v-model="email" type="email" autocomplete="email" placeholder="name@example.com" />
          </div>
          <div class="space-y-2">
            <Label for="reg-pass">密码</Label>
            <Input
              id="reg-pass"
              v-model="password"
              type="password"
              autocomplete="new-password"
              placeholder="至少 6 位"
              required
              minlength="6"
            />
          </div>
          <div v-if="error" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {{ error }}
          </div>
          <Button type="submit" class="w-full" :disabled="loading">
            <span v-if="loading">提交中…</span>
            <span v-else>注册并登录</span>
          </Button>
        </form>
      </CardContent>
      <CardFooter class="flex-col gap-2 text-center text-sm text-slate-600">
        <span>已有账号？</span>
        <RouterLink :to="loginLink" class="font-medium text-blue-600 hover:text-blue-700">去登录</RouterLink>
      </CardFooter>
    </Card>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { parseLoginRedirect } from "@/utils/auth";
import axios from "axios";
import { RouterLink } from "vue-router";
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

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const teamStore = useTeamStore();

const loginLink = computed(() => {
  const redirect = parseLoginRedirect(route.query.redirect);
  if (!redirect) return"/login";
  return `/login?redirect=${encodeURIComponent(redirect)}`;
});

const username = ref("");
const password = ref("");
const email = ref("");
const loading = ref(false);
const error = ref("");

async function submit() {
  if (loading.value) return;
  error.value ="";
  loading.value = true;
  try {
    const res = await axios.post("/api/register", {
      username: username.value.trim(),
      password: password.value,
      email: email.value.trim() || undefined,
    });
    const d = res.data || {};
    if (!d.success || !d.token) {
      error.value = d.detail || d.error ||"注册失败";
      loading.value = false;
      return;
    }
    authStore.setSession({
      token: d.token,
      username: d.username,
      remember: true,
    });
    try {
      await authStore.fetchMe();
    } catch {
      /* ignore */
    }
    const redirect = parseLoginRedirect(route.query.redirect);
    if (redirect) {
      await router.replace(redirect);
      loading.value = false;
      return;
    }
    await teamStore.fetchTeams();
    const id = teamStore.currentTeamId;
    if (id) {
      await router.replace("/app/dashboard");
    } else if (authStore.isGlobalAdmin) {
      await router.replace("/app/dashboard");
    } else {
      await router.replace("/onboarding");
    }
    loading.value = false;
  } catch (e) {
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail ==="string"
        ? detail
        : e?.response?.data?.error || e?.message ||"注册失败，请稍后重试";
    loading.value = false;
  }
}
</script>

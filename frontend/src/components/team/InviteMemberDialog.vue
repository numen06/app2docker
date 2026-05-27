<template>
  <FormDialog v-model="openProxy" title="邀请成员" icon="link" size="md">
    <div v-if="loading" class="py-6 text-center text-sm text-slate-500">
      <AppIcon  name="spinner" class="mr-2" spin />正在生成邀请链接…
    </div>
    <div v-else-if="error" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ error }}
    </div>
    <div v-else class="space-y-4">
      <p class="text-sm text-slate-600">
        将下方邀请链接发给对方，对方登录后打开链接即可加入团队（链接 7 天内有效，过期后将自动续期）。
      </p>
      <div class="space-y-2">
        <Label for="invite-role">加入后角色</Label>
        <NativeSelect id="invite-role" v-model="role" :disabled="loading">
          <option value="member">成员</option>
          <option v-if="allowAdminInvite" value="admin">管理员</option>
        </NativeSelect>
      </div>
      <div class="space-y-2">
        <Label for="invite-link">邀请链接</Label>
        <div class="flex flex-col gap-2 sm:flex-row">
          <Input
            id="invite-link"
            :model-value="inviteLink"
            readonly
            class="font-mono text-xs sm:flex-1"
            @focus="($event.target)?.select?.()"
          />
          <Button
            type="button"
            class="shrink-0 sm:w-auto"
            :disabled="!inviteLink"
            @click="copyInviteLink"
          >
            <AppIcon  name="copy" class="mr-1" />
            {{ copyDone ?"已复制" :"复制链接" }}
          </Button>
        </div>
      </div>
      <p v-if="inviteExpiresAt" class="text-xs text-slate-500">
        有效期至 {{ inviteExpiresAt }}
      </p>
      <p v-if="copyHint" class="text-xs" :class="copyDone ? 'text-emerald-700' : 'text-amber-700'">
        {{ copyHint }}
      </p>
    </div>

    <template #footer>
      <Button variant="secondary" type="button" :disabled="loading" @click="forceNewLink">
        重新生成
      </Button>
      <Button type="button" @click="openProxy = false">完成</Button>
    </template>
  </FormDialog>
</template>

<script setup>
import axios from "axios";
import { computed, ref, watch } from "vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import { copyToClipboard } from "@/utils/clipboard";
import { buildTeamInviteLink, formatInviteExpiresAt } from "@/utils/teamInvite";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  teamId: { type: String, default:"" },
  allowAdminInvite: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue","invited"]);

const openProxy = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const role = ref("member");
const loading = ref(false);
const error = ref("");
const inviteLink = ref("");
const inviteExpiresAt = ref("");
const inviteExpiresAtIso = ref("");
const copyDone = ref(false);
const copyHint = ref("");

let roleChangeTimer = null;
let skipRoleRegenerate = false;

function isExpiredIso(iso) {
  if (!iso) return true;
  return new Date(iso).getTime() < Date.now();
}

function applyInviteResponse(data, { copy = true } = {}) {
  const token = data?.token;
  if (!token) {
    error.value ="未返回邀请令牌，请稍后重试";
    return false;
  }
  inviteExpiresAtIso.value = data?.expires_at ||"";
  inviteExpiresAt.value = formatInviteExpiresAt(data?.expires_at);
  inviteLink.value = buildTeamInviteLink(token);
  if (copy) {
    copyToClipboard(inviteLink.value).then((copied) => {
      copyDone.value = copied;
      copyHint.value = copied
        ?"链接已复制到剪贴板，可直接发送给被邀请人。"
        :"请手动选中上方链接后复制。";
    });
  }
  emit("invited");
  return true;
}

watch(openProxy, (v) => {
  if (v && props.teamId) {
    skipRoleRegenerate = true;
    role.value ="member";
    error.value ="";
    copyDone.value = false;
    copyHint.value ="";
    fetchCurrentLink().finally(() => {
      skipRoleRegenerate = false;
    });
  }
});

watch(role, () => {
  if (skipRoleRegenerate || !openProxy.value || !props.teamId || loading.value) return;
  if (role.value ==="admin" && !props.allowAdminInvite) {
    skipRoleRegenerate = true;
    role.value ="member";
    skipRoleRegenerate = false;
    return;
  }
  clearTimeout(roleChangeTimer);
  roleChangeTimer = setTimeout(() => {
    fetchCurrentLink();
  }, 300);
});

async function fetchCurrentLink({ copy = true, retryIfExpired = true } = {}) {
  if (!props.teamId || loading.value) return;
  error.value ="";
  loading.value = true;
  inviteLink.value ="";
  try {
    const res = await axios.get(`/api/teams/${props.teamId}/invite/current`, {
      params: { role: role.value },
    });
    if (retryIfExpired && isExpiredIso(res.data?.expires_at)) {
      const retry = await axios.get(`/api/teams/${props.teamId}/invite/current`, {
        params: { role: role.value },
      });
      applyInviteResponse(retry.data, { copy });
      return;
    }
    applyInviteResponse(res.data, { copy });
  } catch (e) {
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail ==="string"
        ? detail
        : e?.response?.data?.message || e?.message ||"生成邀请链接失败";
  } finally {
    loading.value = false;
  }
}

async function forceNewLink() {
  if (!props.teamId || loading.value) return;
  copyDone.value = false;
  copyHint.value ="";
  error.value ="";
  loading.value = true;
  inviteLink.value ="";
  try {
    const res = await axios.post(`/api/teams/${props.teamId}/invite`, {
      role: role.value,
    });
    applyInviteResponse(res.data, { copy: true });
  } catch (e) {
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail ==="string"
        ? detail
        : e?.response?.data?.message || e?.message ||"生成邀请链接失败";
  } finally {
    loading.value = false;
  }
}

async function copyInviteLink() {
  if (!inviteLink.value) return;
  const ok = await copyToClipboard(inviteLink.value);
  copyDone.value = ok;
  copyHint.value = ok ?"链接已复制到剪贴板。" :"自动复制失败，请手动选中链接后复制。";
}
</script>

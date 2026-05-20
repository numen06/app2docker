<template>
  <FormDialog v-model="openProxy" title="邀请成员" icon="fa-user-plus" size="md">
    <div v-if="!inviteLink" class="space-y-4">
      <p class="text-sm text-slate-600">
        填写被邀请人邮箱并选择角色，生成邀请链接后复制发给对方；对方需使用该邮箱登录后打开链接加入团队。
      </p>
      <div class="space-y-2">
        <Label for="invite-email">被邀请人邮箱</Label>
        <Input
          id="invite-email"
          v-model="email"
          type="email"
          placeholder="member@example.com"
          autocomplete="off"
        />
      </div>
      <div class="space-y-2">
        <Label for="invite-role">角色</Label>
        <NativeSelect id="invite-role" v-model="role">
          <option value="member">成员</option>
          <option value="admin">管理员</option>
          <option v-if="allowOwnerInvite" value="owner">所有者</option>
        </NativeSelect>
      </div>
      <div
        v-if="error"
        class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
      >
        {{ error }}
      </div>
    </div>

    <div v-else class="space-y-4">
      <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-900">
        <p class="font-medium">邀请链接已生成</p>
        <p v-if="inviteExpiresAt" class="mt-1 text-xs text-emerald-800">
          有效期至 {{ inviteExpiresAt }}（7 天内有效）
        </p>
        <p v-if="inviteEmail" class="mt-1 text-xs text-emerald-800">
          绑定邮箱：{{ inviteEmail }}（接受邀请的账号须与此邮箱一致）
        </p>
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
            variant="outline"
            @click="copyInviteLink"
          >
            <i class="fas fa-copy mr-1"></i>
            {{ copyDone ? "已复制" : "复制链接" }}
          </Button>
        </div>
      </div>
      <p v-if="copyHint" class="text-xs" :class="copyDone ? 'text-emerald-700' : 'text-amber-700'">
        {{ copyHint }}
      </p>
    </div>

    <template #footer>
      <template v-if="inviteLink">
        <Button variant="secondary" type="button" @click="resetForAnother">再邀请一位</Button>
        <Button type="button" @click="openProxy = false">完成</Button>
      </template>
      <template v-else>
        <Button variant="secondary" type="button" @click="openProxy = false">取消</Button>
        <Button
          type="button"
          :disabled="submitting || !teamId || !email.trim()"
          @click="submit"
        >
          {{ submitting ? "生成中…" : "生成邀请链接" }}
        </Button>
      </template>
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
  teamId: { type: String, default: "" },
  allowOwnerInvite: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "invited"]);

const openProxy = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const email = ref("");
const role = ref("member");
const submitting = ref(false);
const error = ref("");
const inviteLink = ref("");
const inviteEmail = ref("");
const inviteExpiresAt = ref("");
const copyDone = ref(false);
const copyHint = ref("");

watch(openProxy, (v) => {
  if (v) {
    resetForm();
  }
});

function resetForm() {
  email.value = "";
  role.value = "member";
  error.value = "";
  inviteLink.value = "";
  inviteEmail.value = "";
  inviteExpiresAt.value = "";
  copyDone.value = false;
  copyHint.value = "";
}

function resetForAnother() {
  inviteLink.value = "";
  inviteEmail.value = "";
  inviteExpiresAt.value = "";
  copyDone.value = false;
  copyHint.value = "";
  error.value = "";
}

async function submit() {
  if (!props.teamId || submitting.value || !email.value.trim()) return;
  error.value = "";
  submitting.value = true;
  try {
    const res = await axios.post(`/api/teams/${props.teamId}/invite`, {
      email: email.value.trim(),
      role: role.value,
    });
    const token = res.data?.token;
    if (!token) {
      error.value = "未返回邀请令牌，请稍后重试";
      return;
    }
    inviteEmail.value = res.data?.email || email.value.trim();
    inviteExpiresAt.value = formatInviteExpiresAt(res.data?.expires_at);
    inviteLink.value = buildTeamInviteLink(token);
    emit("invited");
  } catch (e) {
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail === "string"
        ? detail
        : e?.response?.data?.message || e?.message || "生成邀请失败";
  } finally {
    submitting.value = false;
  }
}

async function copyInviteLink() {
  if (!inviteLink.value) return;
  const ok = await copyToClipboard(inviteLink.value);
  copyDone.value = ok;
  copyHint.value = ok
    ? "链接已复制，请发送给被邀请人。"
    : "自动复制失败，请手动选中链接后复制。";
}
</script>

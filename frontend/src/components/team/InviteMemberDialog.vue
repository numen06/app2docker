<template>
  <BaseDialog v-model="openProxy">
    <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
      <h2 class="text-lg font-semibold text-slate-900">邀请成员</h2>
      <button
        type="button"
        class="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800"
        aria-label="关闭"
        @click="openProxy = false"
      >
        <i class="fas fa-times"></i>
      </button>
    </div>
    <div class="space-y-4 overflow-y-auto px-4 py-4">
      <div class="space-y-2">
        <Label for="invite-email">邮箱</Label>
        <Input id="invite-email" v-model="email" type="email" placeholder="member@example.com" autocomplete="off" />
      </div>
      <div class="space-y-2">
        <Label for="invite-role">角色</Label>
        <NativeSelect id="invite-role" :value="role" @change="role = $event.target.value">
          <option value="member">成员</option>
          <option value="admin">管理员</option>
          <option v-if="allowOwnerInvite" value="owner">所有者</option>
        </NativeSelect>
      </div>
      <p v-if="inviteHint" class="text-xs text-slate-600">{{ inviteHint }}</p>
      <div v-if="error" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ error }}
      </div>
    </div>
    <div class="flex justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3">
      <Button variant="secondary" type="button" @click="openProxy = false">取消</Button>
      <Button type="button" :disabled="submitting" @click="submit">
        {{ submitting ? "发送中…" : "发送邀请" }}
      </Button>
    </div>
  </BaseDialog>
</template>

<script setup>
import axios from "axios";
import { computed, ref, watch } from "vue";
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  teamId: { type: String, required: true },
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
const inviteHint = ref("");

watch(openProxy, (v) => {
  if (v) {
    email.value = "";
    role.value = "member";
    error.value = "";
    inviteHint.value = "";
  }
});

async function submit() {
  if (!props.teamId || submitting.value) return;
  error.value = "";
  submitting.value = true;
  try {
    const res = await axios.post(`/api/teams/${props.teamId}/invite`, {
      email: email.value.trim(),
      role: role.value,
    });
    inviteHint.value =
      "邀请已创建。请将邀请链接或令牌发给对方；对方需在个人资料填写相同邮箱后接受邀请。";
    if (res.data?.token) {
      inviteHint.value += `（令牌：${res.data.token}）`;
    }
    emit("invited");
  } catch (e) {
    const detail = e?.response?.data?.detail;
    error.value =
      typeof detail === "string"
        ? detail
        : e?.response?.data?.message || e?.message || "邀请失败";
  } finally {
    submitting.value = false;
  }
}
</script>

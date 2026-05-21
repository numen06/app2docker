<template>
  <FormDialog
    :model-value="show"
    title="需要修改密码"
    icon="fa-exclamation-triangle"
    icon-class="text-amber-600"
    size="md"
    @update:model-value="$emit('update:show', $event)"
  >
    <AlertBanner
      variant="warning"
      message="检测到您使用的是默认密码，为了安全起见，请先修改密码。"
    />
    <form class="mt-4 space-y-4" @submit.prevent="handleChangePassword">
      <div class="space-y-2">
        <Label>
          <i class="fas fa-lock mr-1"></i> 当前密码 <span class="text-red-600">*</span>
        </Label>
        <Input
          v-model="form.oldPassword"
          type="password"
          placeholder="请输入当前密码"
          required
          autocomplete="current-password"
        />
      </div>
      <div class="space-y-2">
        <Label>
          <i class="fas fa-key mr-1"></i> 新密码 <span class="text-red-600">*</span>
        </Label>
        <Input
          v-model="form.newPassword"
          type="password"
          placeholder="请输入新密码（至少6位）"
          required
          minlength="6"
          autocomplete="new-password"
        />
        <p class="text-xs text-slate-500">密码长度至少6位</p>
      </div>
      <div class="space-y-2">
        <Label>
          <i class="fas fa-key mr-1"></i> 确认新密码 <span class="text-red-600">*</span>
        </Label>
        <Input
          v-model="form.confirmPassword"
          type="password"
          placeholder="请再次输入新密码"
          required
          minlength="6"
          autocomplete="new-password"
        />
      </div>
      <AlertBanner v-if="error" variant="danger" :message="error" />
    </form>
    <template #footer>
      <Button type="button" :disabled="loading || !canSubmit" @click="handleChangePassword">
        <i v-if="loading" class="fas fa-spinner fa-spin"></i>
        {{ loading ? "修改中..." : "修改密码" }}
      </Button>
    </template>
  </FormDialog>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

import { ref, computed } from "vue";
import axios from "axios";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";

defineProps({
  show: { type: Boolean, default: false },
});

const emit = defineEmits(["update:show", "success"]);

const form = ref({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const loading = ref(false);
const error = ref("");

const canSubmit = computed(
  () =>
    form.value.oldPassword &&
    form.value.newPassword &&
    form.value.confirmPassword &&
    form.value.newPassword.length >= 6 &&
    form.value.newPassword === form.value.confirmPassword
);

async function handleChangePassword() {
  if (!canSubmit.value) {
    error.value = "请填写完整信息，且新密码长度至少6位，两次输入需一致";
    return;
  }
  if (form.value.newPassword !== form.value.confirmPassword) {
    error.value = "两次输入的密码不一致";
    return;
  }
  if (form.value.newPassword.length < 6) {
    error.value = "新密码长度至少6位";
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const res = await axios.post("/api/change-password", {
      old_password: form.value.oldPassword,
      new_password: form.value.newPassword,
    });

    if (res.data.success) {
      emit("success");
      emit("update:show", false);
      toastSuccess("密码修改成功！");
      form.value = { oldPassword: "", newPassword: "", confirmPassword: "" };
    } else {
      error.value = res.data.error || "修改密码失败";
    }
  } catch (err) {
    error.value = err.response?.data?.error || err.message || "修改密码失败";
  } finally {
    loading.value = false;
  }
}
</script>

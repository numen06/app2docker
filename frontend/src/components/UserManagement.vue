<template>
  <div>
    <PageToolbar title="用户管理" icon="fa-users">
      <template #actions>
        <Button variant="outline" size="sm" @click="loadUsers" title="刷新">
          <i class="fas fa-sync-alt"></i>
          刷新
        </Button>
        <Button size="sm" @click="showCreateModal = true">
          <i class="fas fa-plus"></i>
          创建用户
        </Button>
      </template>
    </PageToolbar>

    <div class="space-y-3 md:hidden">
      <div
        v-for="user in users"
        :key="user.user_id"
        class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
      >
        <div class="min-w-0">
          <div class="font-medium text-slate-900">{{ user.username }}</div>
          <div class="mt-0.5 truncate text-xs text-slate-500">{{ user.email || "—" }}</div>
          <div class="mt-2 flex flex-wrap gap-1">
            <Badge v-for="role in user.roles" :key="role" variant="default">{{ role }}</Badge>
            <Badge :variant="user.enabled ? 'success' : 'danger'">
              {{ user.enabled ? "启用" : "禁用" }}
            </Badge>
          </div>
          <p class="mt-1 text-xs text-slate-500">{{ formatDate(user.created_at) }}</p>
        </div>
        <div class="mt-3 flex flex-wrap gap-2 border-t border-slate-200 pt-3">
          <Button variant="outline" size="sm" title="编辑" @click="editUser(user)">
            <i class="fas fa-edit"></i>
          </Button>
          <Button
            variant="outline"
            size="sm"
            title="修改密码"
            :disabled="user.username === 'admin'"
            @click="changePassword(user)"
          >
            <i class="fas fa-key"></i>
          </Button>
          <Button variant="outline" size="sm" title="API 密钥" @click="openAppKeysModal(user)">
            <i class="fas fa-fingerprint"></i>
          </Button>
          <Button
            variant="outline"
            size="sm"
            :title="user.enabled ? '禁用' : '启用'"
            :disabled="user.username === 'admin'"
            @click="toggleEnable(user)"
          >
            <i class="fas" :class="user.enabled ? 'fa-ban' : 'fa-check'"></i>
          </Button>
          <Button
            variant="destructive"
            size="sm"
            title="删除"
            :disabled="user.username === currentUsername"
            @click="deleteUser(user)"
          >
            <i class="fas fa-trash"></i>
          </Button>
        </div>
      </div>
    </div>

    <div class="hidden md:block">
      <Table min-width-class="min-w-[52rem]">
        <TableHeader>
          <TableRow>
            <TableHead>用户名</TableHead>
            <TableHead>邮箱</TableHead>
            <TableHead>角色</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>创建时间</TableHead>
            <TableHead class="text-end">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="user in users" :key="user.user_id">
            <TableCell class="font-medium text-slate-900">{{ user.username }}</TableCell>
            <TableCell class="max-w-[12rem] truncate text-slate-600" :title="user.email || ''">
              {{ user.email || "—" }}
            </TableCell>
            <TableCell>
              <Badge
                v-for="role in user.roles"
                :key="role"
                variant="default"
                class="mr-1"
              >
                {{ role }}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge :variant="user.enabled ? 'success' : 'danger'">
                {{ user.enabled ? "启用" : "禁用" }}
              </Badge>
            </TableCell>
            <TableCell class="whitespace-nowrap text-slate-600">{{ formatDate(user.created_at) }}</TableCell>
            <TableCell class="text-end">
              <div class="flex justify-end gap-1">
                <Button variant="outline" size="sm" title="编辑" @click="editUser(user)">
                  <i class="fas fa-edit"></i>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  title="修改密码"
                  :disabled="user.username === 'admin'"
                  @click="changePassword(user)"
                >
                  <i class="fas fa-key"></i>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  title="管理该用户的 API 密钥"
                  @click="openAppKeysModal(user)"
                >
                  <i class="fas fa-fingerprint"></i>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  :title="user.enabled ? '禁用' : '启用'"
                  :disabled="user.username === 'admin'"
                  @click="toggleEnable(user)"
                >
                  <i class="fas" :class="user.enabled ? 'fa-ban' : 'fa-check'"></i>
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  title="删除"
                  :disabled="user.username === currentUsername"
                  @click="deleteUser(user)"
                >
                  <i class="fas fa-trash"></i>
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <PaginationBar
      :page="currentPage"
      :page-size="pageSize"
      :total="totalUsers"
      :total-pages="totalPages"
      @update:page="changePage"
    />

    <FormDialog
      :model-value="showCreateModal || showEditModal"
      :title="showCreateModal ? '创建用户' : '编辑用户'"
      icon="fa-user"
      size="md"
      @update:model-value="(v) => !v && closeModal()"
    >
      <form class="space-y-4" @submit.prevent="saveUser">
        <div class="space-y-2">
          <Label>用户名 <span class="text-red-500">*</span></Label>
          <Input v-model="form.username" required :disabled="showEditModal" />
        </div>

        <div v-if="showCreateModal" class="space-y-2">
          <Label>密码 <span class="text-red-500">*</span></Label>
          <Input v-model="form.password" type="password" required minlength="6" />
          <p class="text-xs text-slate-500">密码长度至少 6 位</p>
        </div>

        <div class="space-y-2">
          <Label>邮箱</Label>
          <Input v-model="form.email" type="email" />
        </div>

        <div class="space-y-2">
          <Label>角色 <span class="text-red-500">*</span></Label>
          <div class="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50/50 p-3">
            <label
              v-for="role in availableRoles"
              :key="role.role_id"
              class="flex cursor-pointer items-start gap-2 text-sm"
            >
              <input
                v-model="form.roles"
                type="checkbox"
                class="mt-1 h-4 w-4 rounded border-slate-300"
                :value="role.name"
              />
              <span>
                <span class="font-medium text-slate-900">{{ role.name }}</span>
                <span class="text-slate-500">（{{ role.description }}）</span>
              </span>
            </label>
          </div>
        </div>

        <label v-if="showEditModal" class="flex cursor-pointer items-center gap-2 text-sm">
          <input
            v-model="form.enabled"
            type="checkbox"
            class="h-4 w-4 rounded border-slate-300"
          />
          <span class="font-medium text-slate-900">启用用户</span>
        </label>

        <AlertBanner :message="error" />
      </form>
      <template #footer>
        <Button variant="outline" type="button" @click="closeModal">取消</Button>
        <Button type="button" @click="saveUser">保存</Button>
      </template>
    </FormDialog>

    <FormDialog
      v-model="showPasswordModal"
      :title="`修改密码 — ${passwordForm.username}`"
      icon="fa-key"
      size="md"
    >
      <form class="space-y-4" @submit.prevent="savePassword">
        <div class="space-y-2">
          <Label>新密码 <span class="text-red-500">*</span></Label>
          <Input
            v-model="passwordForm.newPassword"
            type="password"
            required
            minlength="6"
          />
          <p class="text-xs text-slate-500">密码长度至少 6 位</p>
        </div>
        <AlertBanner :message="passwordError" />
      </form>
      <template #footer>
        <Button variant="outline" type="button" @click="showPasswordModal = false">取消</Button>
        <Button type="button" @click="savePassword">保存</Button>
      </template>
    </FormDialog>

    <FormDialog
      v-model="showAppKeysModal"
      :title="appKeysDialogTitle"
      icon="fa-fingerprint"
      size="xl"
      @update:model-value="(v) => !v && closeAppKeysModal()"
    >
      <p class="mb-4 text-sm text-slate-600">
        以下密钥归属该用户，请求头可使用
        <code class="rounded bg-slate-100 px-1 text-xs">X-API-Key</code>
        携带完整密钥。新建密钥仅显示一次明文，请通知用户妥善保存。
      </p>

      <div class="mb-3 flex items-center justify-between">
        <span class="text-sm font-semibold text-slate-900">密钥列表</span>
        <Button
          size="sm"
          type="button"
          :disabled="adminAppKeysLoading"
          @click="adminShowCreateForm = !adminShowCreateForm"
        >
          <i class="fas fa-plus"></i>
          创建密钥
        </Button>
      </div>

      <Card v-if="adminShowCreateForm" class="mb-4">
        <CardContent class="space-y-3 p-4">
          <div class="space-y-2">
            <Label>名称</Label>
            <Input
              v-model="adminNewAppKey.name"
              placeholder="例如：CI 调用密钥"
              maxlength="255"
            />
          </div>
          <div class="space-y-2">
            <Label>过期时间（可选）</Label>
            <Input v-model="adminNewAppKey.expiresAt" type="datetime-local" />
          </div>
          <Button
            size="sm"
            type="button"
            :disabled="adminCreatingAppKey || !adminNewAppKey.name.trim()"
            @click="createAdminAppKey"
          >
            <i v-if="adminCreatingAppKey" class="fas fa-spinner fa-spin"></i>
            生成密钥
          </Button>
        </CardContent>
      </Card>

      <AlertBanner
        v-if="adminCreatedAppKey"
        :message="`请立即复制并交给该用户，该密钥仅展示一次：${adminCreatedAppKey}`"
        variant="warning"
      />
      <AlertBanner :message="adminAppKeysError" />

      <div
        v-if="adminAppKeysLoading"
        class="flex items-center gap-2 py-6 text-sm text-slate-500"
      >
        <i class="fas fa-spinner fa-spin"></i>
        加载中…
      </div>
      <EmptyState
        v-else-if="adminAppKeys.length === 0"
        message="该用户暂无 API 密钥"
        icon="fa-fingerprint"
      />
      <Table v-else min-width-class="min-w-[48rem]">
          <TableHeader>
            <TableRow>
              <TableHead>名称</TableHead>
              <TableHead>前缀</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>最后使用</TableHead>
              <TableHead>过期时间</TableHead>
              <TableHead class="text-end">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="item in adminAppKeys" :key="item.key_id">
              <TableCell>{{ item.name }}</TableCell>
              <TableCell>
                <code class="rounded bg-slate-100 px-1 text-xs">{{ item.key_prefix }}</code>
              </TableCell>
              <TableCell>
                <Badge :variant="item.enabled ? 'success' : 'default'">
                  {{ item.enabled ? "启用" : "禁用" }}
                </Badge>
              </TableCell>
              <TableCell class="text-slate-600">{{ formatAppKeyTime(item.last_used_at) }}</TableCell>
              <TableCell class="text-slate-600">{{ formatAppKeyTime(item.expires_at) }}</TableCell>
              <TableCell class="text-end">
                <div class="flex justify-end gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    type="button"
                    @click="toggleAdminAppKey(item.key_id)"
                  >
                    {{ item.enabled ? "禁用" : "启用" }}
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    type="button"
                    @click="removeAdminAppKey(item.key_id)"
                  >
                    删除
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
      </Table>
      <template #footer>
        <Button variant="outline" type="button" @click="closeAppKeysModal">关闭</Button>
      </template>
    </FormDialog>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import axios from "axios";
import { computed, onMounted, ref } from "vue";
import { getUsername } from "../utils/auth";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import { Badge } from "@/components/ui/badge";
import Card from "@/components/ui/card/Card.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";

const users = ref([]);
const currentPage = ref(1);
const pageSize = ref(10);
const totalUsers = ref(0);
const totalPages = ref(0);
const availableRoles = ref([]);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showPasswordModal = ref(false);
const currentUsername = ref("");
const error = ref("");
const passwordError = ref("");

const form = ref({
  user_id: "",
  username: "",
  password: "",
  email: "",
  roles: [],
  enabled: true,
});

const passwordForm = ref({
  user_id: "",
  username: "",
  newPassword: "",
});

const showAppKeysModal = ref(false);
const appKeysTargetUser = ref(null);
const adminAppKeys = ref([]);
const adminAppKeysLoading = ref(false);
const adminAppKeysError = ref("");
const adminShowCreateForm = ref(false);
const adminCreatingAppKey = ref(false);
const adminCreatedAppKey = ref("");
const adminNewAppKey = ref({ name: "", expiresAt: "" });

const appKeysDialogTitle = computed(() =>
  appKeysTargetUser.value
    ? `API 密钥 — ${appKeysTargetUser.value.username}`
    : "API 密钥"
);

onMounted(async () => {
  currentUsername.value = getUsername() || "";
  await loadUsers();
  await loadRoles();
});

function changePage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  currentPage.value = page;
  loadUsers();
}

async function loadUsers() {
  try {
    const res = await axios.get("/api/users", {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
      },
    });
    users.value = res.data.users || [];
    totalUsers.value = res.data.total ?? users.value.length;
    totalPages.value = res.data.total_pages ?? 0;
    if (users.value.length === 0 && currentPage.value > 1 && totalPages.value > 0) {
      currentPage.value = totalPages.value;
      return loadUsers();
    }
  } catch (err) {
    console.error("加载用户列表失败:", err);
    toastError("加载用户列表失败: " + (err.response?.data?.detail || err.message));
    users.value = [];
    totalUsers.value = 0;
    totalPages.value = 0;
  }
}

async function loadRoles() {
  try {
    const res = await axios.get("/api/roles");
    availableRoles.value = res.data.roles || [];
  } catch (err) {
    console.error("加载角色列表失败:", err);
  }
}

function editUser(user) {
  form.value = {
    user_id: user.user_id,
    username: user.username,
    password: "",
    email: user.email || "",
    roles: [...user.roles],
    enabled: user.enabled,
  };
  showEditModal.value = true;
}

function changePassword(user) {
  if (user.username === "admin") {
    toastError("不能修改超级管理员的密码");
    return;
  }

  passwordForm.value = {
    user_id: user.user_id,
    username: user.username,
    newPassword: "",
  };
  showPasswordModal.value = true;
  passwordError.value = "";
}

async function saveUser() {
  error.value = "";

  try {
    if (showCreateModal.value) {
      await axios.post("/api/users", {
        username: form.value.username,
        password: form.value.password,
        email: form.value.email || null,
        roles: form.value.roles,
      });
      toastSuccess("用户创建成功");
      currentPage.value = 1;
    } else {
      await axios.put(`/api/users/${form.value.user_id}`, {
        email: form.value.email || null,
        enabled: form.value.enabled,
        roles: form.value.roles,
      });
      toastSuccess("用户更新成功");
    }

    closeModal();
    await loadUsers();
  } catch (err) {
    console.error("保存用户失败:", err);
    error.value = err.response?.data?.detail || err.message || "操作失败";
  }
}

async function savePassword() {
  passwordError.value = "";

  try {
    await axios.put(`/api/users/${passwordForm.value.user_id}/password`, {
      new_password: passwordForm.value.newPassword,
    });
    toastSuccess("密码修改成功");
    showPasswordModal.value = false;
  } catch (err) {
    console.error("修改密码失败:", err);
    passwordError.value = err.response?.data?.detail || err.message || "操作失败";
  }
}

async function toggleEnable(user) {
  if (user.username === "admin") {
    toastError("不能修改超级管理员的状态");
    return;
  }

  if (!(await showConfirm({ message: `确定要${user.enabled ? "禁用" : "启用"}用户 ${user.username} 吗？`, danger: true }))) {
    return;
  }

  try {
    const newEnabled = !user.enabled;
    await axios.put(`/api/users/${user.user_id}/enable`, {
      enabled: newEnabled,
    });
    toastInfo(`用户已${newEnabled ? "启用" : "禁用"}`);
    await loadUsers();
  } catch (err) {
    console.error("操作失败:", err);
    toastError("操作失败: " + (err.response?.data?.detail || err.message));
  }
}

async function deleteUser(user) {
  if (!(await showConfirm({ message: `确定要删除用户 ${user.username} 吗？此操作不可恢复！`, danger: true }))) {
    return;
  }

  try {
    await axios.delete(`/api/users/${user.user_id}`);
    toastSuccess("用户删除成功");
    await loadUsers();
  } catch (err) {
    console.error("删除用户失败:", err);
    toastError("删除失败: " + (err.response?.data?.detail || err.message));
  }
}

function closeModal() {
  showCreateModal.value = false;
  showEditModal.value = false;
  form.value = {
    user_id: "",
    username: "",
    password: "",
    email: "",
    roles: [],
    enabled: true,
  };
  error.value = "";
}

function formatDate(dateString) {
  if (!dateString) return "—";
  const date = new Date(dateString);
  return date.toLocaleString("zh-CN");
}

function formatAppKeyTime(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("zh-CN");
  } catch {
    return value;
  }
}

function openAppKeysModal(user) {
  appKeysTargetUser.value = {
    user_id: user.user_id,
    username: user.username,
  };
  adminAppKeysError.value = "";
  adminCreatedAppKey.value = "";
  adminShowCreateForm.value = false;
  adminNewAppKey.value = { name: "", expiresAt: "" };
  showAppKeysModal.value = true;
  loadAdminAppKeys();
}

function closeAppKeysModal() {
  showAppKeysModal.value = false;
  appKeysTargetUser.value = null;
  adminAppKeys.value = [];
  adminAppKeysError.value = "";
  adminCreatedAppKey.value = "";
  adminShowCreateForm.value = false;
  adminNewAppKey.value = { name: "", expiresAt: "" };
}

async function loadAdminAppKeys() {
  const uid = appKeysTargetUser.value?.user_id;
  if (!uid) return;
  adminAppKeysLoading.value = true;
  adminAppKeysError.value = "";
  try {
    const res = await axios.get(`/api/users/${uid}/app-keys`);
    adminAppKeys.value = res.data?.app_keys || [];
  } catch (err) {
    console.error("加载用户 API 密钥失败:", err);
    adminAppKeysError.value =
      err.response?.data?.detail || err.message || "加载失败";
    adminAppKeys.value = [];
  } finally {
    adminAppKeysLoading.value = false;
  }
}

async function createAdminAppKey() {
  const uid = appKeysTargetUser.value?.user_id;
  if (!uid || !adminNewAppKey.value.name.trim()) return;
  adminCreatingAppKey.value = true;
  adminAppKeysError.value = "";
  try {
    const payload = { name: adminNewAppKey.value.name.trim() };
    if (adminNewAppKey.value.expiresAt) {
      payload.expires_at = new Date(adminNewAppKey.value.expiresAt).toISOString();
    }
    const res = await axios.post(`/api/users/${uid}/app-keys`, payload);
    adminCreatedAppKey.value = res.data?.app_key || "";
    adminNewAppKey.value = { name: "", expiresAt: "" };
    adminShowCreateForm.value = false;
    await loadAdminAppKeys();
  } catch (err) {
    adminAppKeysError.value =
      err.response?.data?.detail || err.message || "创建失败";
  } finally {
    adminCreatingAppKey.value = false;
  }
}

async function toggleAdminAppKey(keyId) {
  const uid = appKeysTargetUser.value?.user_id;
  if (!uid) return;
  adminAppKeysError.value = "";
  try {
    await axios.put(`/api/users/${uid}/app-keys/${keyId}/toggle`);
    await loadAdminAppKeys();
  } catch (err) {
    adminAppKeysError.value =
      err.response?.data?.detail || err.message || "操作失败";
  }
}

async function removeAdminAppKey(keyId) {
  if (!(await showConfirm({ message: "确定删除该 API 密钥吗？此操作不可恢复。", danger: true }))) return;
  const uid = appKeysTargetUser.value?.user_id;
  if (!uid) return;
  adminAppKeysError.value = "";
  try {
    await axios.delete(`/api/users/${uid}/app-keys/${keyId}`);
    await loadAdminAppKeys();
  } catch (err) {
    adminAppKeysError.value =
      err.response?.data?.detail || err.message || "删除失败";
  }
}
</script>

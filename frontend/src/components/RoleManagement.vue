<template>
  <div>
    <PageToolbar title="角色管理" icon="fa-user-shield">
      <template #actions>
        <Button variant="outline" size="sm" @click="loadRoles">
          <i class="fas fa-sync-alt"></i>
          刷新
        </Button>
        <Button size="sm" @click="openCreate">
          <i class="fas fa-plus"></i>
          创建角色
        </Button>
      </template>
    </PageToolbar>

    <div class="space-y-3 md:hidden">
      <EmptyState v-if="roles.length === 0" message="暂无角色" />

      <div
        v-for="role in roles"
        :key="role.role_id"
        class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
      >
        <div class="min-w-0">
          <div class="font-medium text-slate-900">
            {{ role.name }}
            <Badge v-if="isSystemRole(role.name)" variant="info" class="ml-2">系统角色</Badge>
          </div>
          <p class="mt-1 text-sm text-slate-600">{{ role.description || "—" }}</p>
          <p class="mt-1 text-xs text-slate-500">权限 {{ role.permissions?.length || 0 }} 项</p>
        </div>
        <div class="mt-3 flex flex-wrap gap-2 border-t border-slate-200 pt-3">
          <Button variant="outline" size="sm" title="编辑" @click="editRole(role)">
            <i class="fas fa-edit"></i>
          </Button>
          <Button variant="outline" size="sm" title="查看权限" @click="viewPermissions(role)">
            <i class="fas fa-eye"></i>
          </Button>
          <Button
            v-if="!isSystemRole(role.name)"
            variant="destructive"
            size="sm"
            title="删除"
            @click="deleteRole(role)"
          >
            <i class="fas fa-trash"></i>
          </Button>
        </div>
      </div>
    </div>

    <div class="hidden md:block">
      <Table min-width-class="min-w-[40rem]">
        <TableHeader>
          <TableRow>
            <TableHead>角色名称</TableHead>
            <TableHead>描述</TableHead>
            <TableHead>权限数量</TableHead>
            <TableHead class="text-end">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="role in roles" :key="role.role_id">
            <TableCell class="font-medium text-slate-900">
              {{ role.name }}
              <Badge v-if="isSystemRole(role.name)" variant="info" class="ml-2">系统角色</Badge>
            </TableCell>
            <TableCell class="text-slate-600">{{ role.description || "—" }}</TableCell>
            <TableCell>
              <Badge>{{ role.permissions?.length || 0 }}</Badge>
            </TableCell>
            <TableCell class="text-end">
              <div class="flex justify-end gap-1">
                <Button variant="outline" size="sm" title="编辑" @click="editRole(role)">
                  <i class="fas fa-edit"></i>
                </Button>
                <Button variant="outline" size="sm" title="查看权限" @click="viewPermissions(role)">
                  <i class="fas fa-eye"></i>
                </Button>
                <Button
                  v-if="!isSystemRole(role.name)"
                  variant="destructive"
                  size="sm"
                  title="删除"
                  @click="deleteRole(role)"
                >
                  <i class="fas fa-trash"></i>
                </Button>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>

    <!-- 创建/编辑 -->
    <BaseDialog v-model="formDialogOpen">
      <div
        class="relative z-10 mx-auto flex max-h-[90vh] w-full max-w-[calc(100vw-1.5rem)] shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl sm:max-w-2xl"
        @click.stop
      >
        <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h3 class="text-lg font-semibold text-slate-900">
            {{ showCreateModal ? "创建角色" : "编辑角色" }}
          </h3>
          <button
            type="button"
            class="rounded-md p-2 text-slate-500 hover:bg-slate-100"
            @click="closeModal"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="overflow-y-auto px-4 py-4">
          <form class="space-y-4" @submit.prevent="saveRole">
            <div class="space-y-2">
              <Label>角色名称 <span class="text-red-500">*</span></Label>
              <Input
                v-model="form.name"
                required
                :disabled="showEditModal && isSystemRole(form.name)"
                placeholder="例如: developer, tester"
              />
              <p
                v-if="showEditModal && isSystemRole(form.name)"
                class="text-xs text-amber-700"
              >
                系统默认角色不能修改名称
              </p>
            </div>
            <div class="space-y-2">
              <Label>描述</Label>
              <textarea
                v-model="form.description"
                rows="2"
                class="flex min-h-[80px] w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                placeholder="角色描述"
              />
            </div>
            <div class="space-y-2">
              <Label>权限配置 <span class="text-red-500">*</span></Label>
              <div
                class="max-h-80 overflow-y-auto rounded-lg border border-slate-200 bg-slate-50/50 p-3"
              >
                <label
                  v-for="permission in availablePermissions"
                  :key="permission.permission_id"
                  class="mb-2 flex cursor-pointer items-start gap-2 text-sm"
                >
                  <input
                    v-model="form.permissions"
                    type="checkbox"
                    class="mt-1 h-4 w-4 rounded border-slate-300"
                    :value="permission.code"
                  />
                  <span>
                    <span class="font-medium text-slate-900">{{ permission.name }}</span>
                    <span class="ml-2 text-slate-500">({{ permission.code }})</span>
                  </span>
                </label>
                <p
                  v-if="availablePermissions.length === 0"
                  class="py-4 text-center text-sm text-slate-500"
                >
                  暂无权限数据
                </p>
              </div>
              <p class="text-xs text-slate-500">
                已选择 <strong class="text-slate-800">{{ form.permissions.length }}</strong> 个权限
              </p>
            </div>
            <AlertBanner :message="error" />
          </form>
        </div>
        <div class="modal-footer flex flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3 sm:flex-row sm:justify-end">
          <Button variant="outline" type="button" class="w-full sm:w-auto" @click="closeModal">取消</Button>
          <Button type="button" class="w-full sm:w-auto" @click="saveRole">保存</Button>
        </div>
      </div>
    </BaseDialog>

    <!-- 查看权限 -->
    <BaseDialog v-model="showViewModal">
      <div
        class="relative z-10 mx-auto flex w-full max-w-[calc(100vw-1.5rem)] shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl sm:max-w-lg"
        @click.stop
      >
        <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h3 class="text-lg font-semibold text-slate-900">
            角色权限 — {{ viewRole.name }}
          </h3>
          <button
            type="button"
            class="rounded-md p-2 text-slate-500 hover:bg-slate-100"
            @click="showViewModal = false"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="max-h-[60vh] overflow-y-auto px-4 py-4">
          <ul
            v-if="viewRole.permissions?.length"
            class="divide-y divide-slate-100 rounded-lg border border-slate-200"
          >
            <li
              v-for="permCode in viewRole.permissions"
              :key="permCode"
              class="px-3 py-2 text-sm"
            >
              <span class="font-medium text-slate-900">{{ getPermissionName(permCode) }}</span>
              <span class="ml-2 text-slate-500">({{ permCode }})</span>
            </li>
          </ul>
          <EmptyState v-else message="该角色暂无权限" icon="fa-shield-halved" />
        </div>
        <div class="flex justify-end border-t border-slate-200 bg-slate-50 px-4 py-3">
          <Button variant="outline" @click="showViewModal = false">关闭</Button>
        </div>
      </div>
    </BaseDialog>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import axios from "axios";
import { computed, onMounted, ref } from "vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import { Badge } from "@/components/ui/badge";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";

const roles = ref([]);
const availablePermissions = ref([]);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showViewModal = ref(false);
const viewRole = ref({});
const error = ref("");

const form = ref({
  role_id: "",
  name: "",
  description: "",
  permissions: [],
});

const formDialogOpen = computed({
  get: () => showCreateModal.value || showEditModal.value,
  set: (v) => {
    if (!v) closeModal();
  },
});

onMounted(async () => {
  await loadRoles();
  await loadPermissions();
});

function openCreate() {
  showCreateModal.value = true;
  error.value = "";
}

async function loadRoles() {
  try {
    const res = await axios.get("/api/roles");
    roles.value = res.data.roles || [];
  } catch (err) {
    toastError("加载角色列表失败: " + (err.response?.data?.detail || err.message));
  }
}

async function loadPermissions() {
  try {
    const res = await axios.get("/api/permissions");
    availablePermissions.value = res.data.permissions || [];
  } catch (err) {
    console.error("加载权限列表失败:", err);
  }
}

function isSystemRole(roleName) {
  return ["admin", "user", "readonly"].includes(roleName);
}

function editRole(role) {
  form.value = {
    role_id: role.role_id,
    name: role.name,
    description: role.description || "",
    permissions: [...(role.permissions || [])],
  };
  showEditModal.value = true;
  error.value = "";
}

function viewPermissions(role) {
  viewRole.value = role;
  showViewModal.value = true;
}

function getPermissionName(permCode) {
  const perm = availablePermissions.value.find((p) => p.code === permCode);
  return perm ? perm.name : permCode;
}

async function saveRole() {
  error.value = "";
  try {
    if (showCreateModal.value) {
      await axios.post("/api/roles", {
        name: form.value.name,
        description: form.value.description || null,
        permissions: form.value.permissions,
      });
      toastSuccess("角色创建成功");
    } else {
      await axios.put(`/api/roles/${form.value.role_id}`, {
        description: form.value.description || null,
        permissions: form.value.permissions,
      });
      toastSuccess("角色更新成功");
    }
    closeModal();
    await loadRoles();
  } catch (err) {
    error.value = err.response?.data?.detail || err.message || "操作失败";
  }
}

async function deleteRole(role) {
  if (!(await showConfirm({ message: `确定要删除角色 "${role.name}" 吗？此操作不可恢复！`, danger: true }))) return;
  try {
    await axios.delete(`/api/roles/${role.role_id}`);
    toastSuccess("角色删除成功");
    await loadRoles();
  } catch (err) {
    toastError("删除失败: " + (err.response?.data?.detail || err.message));
  }
}

function closeModal() {
  showCreateModal.value = false;
  showEditModal.value = false;
  form.value = { role_id: "", name: "", description: "", permissions: [] };
  error.value = "";
}
</script>

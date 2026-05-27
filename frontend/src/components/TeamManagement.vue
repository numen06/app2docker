<template>
  <div>
    <PageToolbar title="团队管理" icon="people-group">
      <template #actions>
        <Button variant="outline" size="sm" title="刷新" @click="loadTeams">
          <AppIcon  name="sync-alt" />
          刷新
        </Button>
        <Button size="sm" @click="openCreate">
          <AppIcon  name="plus" />
          创建团队
        </Button>
      </template>
    </PageToolbar>

    <div class="space-y-3 md:hidden">
      <EmptyState v-if="teams.length === 0" message="暂无团队" />
      <div
        v-for="team in teams"
        :key="team.team_id"
        class="rounded-lg border border-slate-200 bg-slate-50/50 p-3"
      >
        <div class="font-medium text-slate-900">{{ team.name }}</div>
        <div class="mt-0.5 text-xs text-slate-500">{{ team.slug }}</div>
        <div class="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
          <span>成员 {{ team.member_count }}</span>
          <span>所有者 {{ team.owner_username ||"—" }}</span>
          <span>保留 {{ team.task_cleanup_days }} 天</span>
        </div>
        <p class="mt-1 text-xs text-slate-500">{{ formatDate(team.created_at) }}</p>
        <div class="mt-3 flex flex-wrap gap-2 border-t border-slate-200 pt-3">
          <Button variant="outline" size="sm" title="编辑" @click="editTeam(team)">
            <AppIcon  name="edit" />
          </Button>
          <Button
            variant="destructive"
            size="sm"
            title="解散团队"
            @click="openDissolve(team)"
          >
            <AppIcon  name="user-slash" />
            解散
          </Button>
        </div>
      </div>
    </div>

    <div class="hidden md:block">
      <Table min-width-class="min-w-[56rem]">
        <TableHeader>
          <TableRow>
            <TableHead>名称</TableHead>
            <TableHead>Slug</TableHead>
            <TableHead>成员数</TableHead>
            <TableHead>所有者</TableHead>
            <TableHead>创建人</TableHead>
            <TableHead>任务保留</TableHead>
            <TableHead>创建时间</TableHead>
            <TableHead class="text-end">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="teams.length === 0">
            <TableCell colspan="8" class="text-center text-slate-500">暂无团队</TableCell>
          </TableRow>
          <TableRow v-for="team in teams" :key="team.team_id">
            <TableCell class="font-medium text-slate-900">{{ team.name }}</TableCell>
            <TableCell class="text-slate-600">{{ team.slug }}</TableCell>
            <TableCell>{{ team.member_count }}</TableCell>
            <TableCell>{{ team.owner_username ||"—" }}</TableCell>
            <TableCell>{{ team.created_by_username ||"—" }}</TableCell>
            <TableCell>{{ team.task_cleanup_days }} 天</TableCell>
            <TableCell class="text-slate-600">{{ formatDate(team.created_at) }}</TableCell>
            <TableCell class="text-end">
              <div class="flex justify-end gap-1">
                <Button variant="outline" size="sm" title="编辑" @click="editTeam(team)">
                  <AppIcon  name="edit" />
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  title="解散团队"
                  @click="openDissolve(team)"
                >
                  <AppIcon  name="user-slash" />
                  解散
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
      :total="totalTeams"
      :total-pages="totalPages"
      @update:page="changePage"
    />

    <FormDialog
      v-model="showDissolveModal"
      title="解散团队"
      icon="user-slash"
      icon-class="text-red-600"
      size="md"
      @update:model-value="(v) => !v && closeDissolveModal()"
    >
      <div class="space-y-4">
        <p class="text-sm text-slate-600">
          解散后该团队及其全部业务数据将被永久删除，且无法恢复。
        </p>
        <p class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          请输入团队名称
          <strong class="font-semibold">「{{ dissolveTarget?.name }}」</strong>
          以确认解散：
        </p>
        <div class="space-y-2">
          <Label for="dissolve-confirm-name">团队名称</Label>
          <Input
            id="dissolve-confirm-name"
            v-model="dissolveConfirmName"
            autocomplete="off"
            placeholder="输入上方引号内的团队名称"
            @keyup.enter="confirmDissolve"
          />
        </div>
        <AlertBanner :message="dissolveError" />
      </div>
      <template #footer>
        <Button variant="outline" type="button" :disabled="dissolving" @click="closeDissolveModal">
          取消
        </Button>
        <Button
          variant="destructive"
          type="button"
          :disabled="dissolving || (dissolveTarget && isProtectedTeam(dissolveTarget))"
          @click="confirmDissolve"
        >
          {{ dissolving ?"解散中…" :"确认解散" }}
        </Button>
      </template>
    </FormDialog>

    <FormDialog
      :model-value="showCreateModal || showEditModal"
      :title="showCreateModal ? '创建团队' : '编辑团队'"
      icon="people-group"
      size="md"
      @update:model-value="(v) => !v && closeModal()"
    >
      <form class="space-y-4" @submit.prevent="saveTeam">
        <div class="space-y-2">
          <Label>名称 <span class="text-red-500">*</span></Label>
          <Input v-model="form.name" required maxlength="255" />
        </div>

        <div class="space-y-2">
          <Label>描述</Label>
          <Input v-model="form.description" />
        </div>

        <div class="space-y-2">
          <Label>任务保留天数 <span class="text-red-500">*</span></Label>
          <Input
            v-model.number="form.task_cleanup_days"
            type="number"
            min="1"
            max="365"
            required
          />
          <p class="text-xs text-slate-500">1–365 天</p>
        </div>

        <div v-if="showCreateModal" class="space-y-2">
          <Label>所有者 <span class="text-red-500">*</span></Label>
          <NativeSelect v-model="form.owner_user_id" required class="w-full">
            <option value="" disabled>请选择用户</option>
            <option v-for="u in userOptions" :key="u.user_id" :value="u.user_id">
              {{ u.username }}{{ u.email ? ` (${u.email})` :"" }}
            </option>
          </NativeSelect>
        </div>

        <AlertBanner :message="error" />
      </form>
      <template #footer>
        <Button variant="outline" type="button" @click="closeModal">取消</Button>
        <Button type="button" @click="saveTeam">保存</Button>
      </template>
    </FormDialog>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

import axios from "axios";
import { onMounted, ref } from "vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import NativeSelect from "@/components/ui/select/NativeSelect.vue";
import Table from "@/components/ui/table/Table.vue";
import TableHeader from "@/components/ui/table/TableHeader.vue";
import TableBody from "@/components/ui/table/TableBody.vue";
import TableRow from "@/components/ui/table/TableRow.vue";
import TableHead from "@/components/ui/table/TableHead.vue";
import TableCell from "@/components/ui/table/TableCell.vue";
import PaginationBar from "@/components/ui/PaginationBar.vue";

const DEFAULT_TEAM_NAME ="默认团队";
const DEFAULT_TEAM_SLUG ="default";

const teams = ref([]);
const userOptions = ref([]);
const currentPage = ref(1);
const pageSize = ref(10);
const totalTeams = ref(0);
const totalPages = ref(0);
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showDissolveModal = ref(false);
const dissolveTarget = ref(null);
const dissolveConfirmName = ref("");
const dissolveError = ref("");
const dissolving = ref(false);
const error = ref("");

const form = ref({
  team_id:"",
  name:"",
  description:"",
  task_cleanup_days: 7,
  owner_user_id:"",
});

onMounted(async () => {
  await loadTeams();
  await loadUserOptions();
});

function isProtectedTeam(team) {
  return team.name === DEFAULT_TEAM_NAME || team.slug === DEFAULT_TEAM_SLUG;
}

function changePage(page) {
  if (page < 1 || page > totalPages.value || page === currentPage.value) return;
  currentPage.value = page;
  loadTeams();
}

async function loadTeams() {
  try {
    const res = await axios.get("/api/admin/teams", {
      params: { page: currentPage.value, page_size: pageSize.value },
    });
    teams.value = res.data.teams || [];
    totalTeams.value = res.data.total ?? teams.value.length;
    totalPages.value = res.data.total_pages ?? 0;
    if (teams.value.length === 0 && currentPage.value > 1 && totalPages.value > 0) {
      currentPage.value = totalPages.value;
      return loadTeams();
    }
  } catch (err) {
    console.error("加载团队管理数据失败:", err);
    toastError("加载团队管理数据失败:" + (err.response?.data?.detail || err.message));
    teams.value = [];
    totalTeams.value = 0;
    totalPages.value = 0;
  }
}

async function loadUserOptions() {
  try {
    const res = await axios.get("/api/users", {
      params: { page: 1, page_size: 200 },
    });
    userOptions.value = res.data.users || [];
  } catch (err) {
    console.error("加载用户列表失败:", err);
  }
}

function openCreate() {
  form.value = {
    team_id:"",
    name:"",
    description:"",
    task_cleanup_days: 7,
    owner_user_id: userOptions.value[0]?.user_id ||"",
  };
  error.value ="";
  showCreateModal.value = true;
  showEditModal.value = false;
}

function editTeam(team) {
  form.value = {
    team_id: team.team_id,
    name: team.name,
    description: team.description ||"",
    task_cleanup_days: team.task_cleanup_days ?? 7,
    owner_user_id:"",
  };
  error.value ="";
  showEditModal.value = true;
  showCreateModal.value = false;
}

function closeModal() {
  showCreateModal.value = false;
  showEditModal.value = false;
  error.value ="";
}

async function saveTeam() {
  error.value ="";
  const days = parseInt(form.value.task_cleanup_days, 10);
  if (isNaN(days) || days < 1 || days > 365) {
    error.value ="任务保留天数须在 1–365 之间";
    return;
  }
  try {
    if (showCreateModal.value) {
      if (!form.value.owner_user_id) {
        error.value ="请选择团队所有者";
        return;
      }
      await axios.post("/api/admin/teams", {
        name: form.value.name.trim(),
        description: form.value.description ||"",
        owner_user_id: form.value.owner_user_id,
        task_cleanup_days: days,
      });
      toastSuccess("团队创建成功");
      currentPage.value = 1;
    } else {
      await axios.put(`/api/admin/teams/${form.value.team_id}`, {
        name: form.value.name.trim(),
        description: form.value.description ||"",
        task_cleanup_days: days,
      });
      toastSuccess("团队更新成功");
    }
    closeModal();
    await loadTeams();
  } catch (err) {
    console.error("保存团队失败:", err);
    error.value = err.response?.data?.detail || err.message ||"操作失败";
  }
}

function openDissolve(team) {
  if (isProtectedTeam(team)) {
    dissolveError.value ="不能解散系统保留的默认团队";
    dissolveTarget.value = team;
    dissolveConfirmName.value ="";
    showDissolveModal.value = true;
    return;
  }
  dissolveTarget.value = team;
  dissolveConfirmName.value ="";
  dissolveError.value ="";
  showDissolveModal.value = true;
}

function closeDissolveModal() {
  showDissolveModal.value = false;
  dissolveTarget.value = null;
  dissolveConfirmName.value ="";
  dissolveError.value ="";
  dissolving.value = false;
}

async function confirmDissolve() {
  const team = dissolveTarget.value;
  if (!team) return;
  if (isProtectedTeam(team)) {
    dissolveError.value ="不能解散系统保留的默认团队";
    return;
  }
  const typed = dissolveConfirmName.value.trim();
  if (!typed) {
    dissolveError.value ="请输入团队名称";
    return;
  }
  if (typed !== team.name.trim()) {
    dissolveError.value ="团队名称不匹配，请重新输入";
    return;
  }
  dissolving.value = true;
  dissolveError.value ="";
  try {
    await axios.delete(`/api/admin/teams/${team.team_id}`);
    closeDissolveModal();
    await loadTeams();
  } catch (err) {
    console.error("解散团队失败:", err);
    dissolveError.value =
      err.response?.data?.detail || err.message ||"解散团队失败";
  } finally {
    dissolving.value = false;
  }
}

function formatDate(dateString) {
  if (!dateString) return"—";
  return new Date(dateString).toLocaleString("zh-CN");
}
</script>

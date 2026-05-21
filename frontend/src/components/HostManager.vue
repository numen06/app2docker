<template>
  <div class="host-manager-root">
  <div v-show="shouldShow && showList" class="host-manager-panel">
    <div v-if="loading" class="py-12 text-center text-slate-500">
      <i class="fas fa-spinner fa-spin"></i> 加载中...
    </div>
    <EmptyState v-else-if="filteredHosts.length === 0" message="暂无 SSH 主机" icon="fa-server" />
    <div v-else class="host-cards-grid">
      <Card
        v-for="host in filteredHosts"
        :key="host.host_id"
        class="flex h-full min-h-[15rem] flex-col transition hover:shadow-md"
      >
        <CardHeader class="space-y-2 border-b border-slate-100 pb-3">
          <div class="flex items-start justify-between gap-2">
            <CardTitle class="min-w-0 flex-1 truncate text-base">{{ host.name }}</CardTitle>
            <div class="host-card__tools flex shrink-0 flex-wrap justify-end gap-0">
              <Button
                variant="ghost"
                size="sm"
                :disabled="testingConnection === host.host_id"
                title="测试连接"
                @click="testConnection(host)"
              >
                <i v-if="testingConnection === host.host_id" class="fas fa-spinner fa-spin"></i>
                <i v-else class="fas fa-plug"></i>
              </Button>
              <Button variant="ghost" size="sm" title="编辑" @click="editHost(host)">
                <i class="fas fa-edit"></i>
              </Button>
              <Button variant="ghost" size="sm" title="成员授权" @click="openResourcePermission(host)">
                <i class="fas fa-user-shield"></i>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                class="text-red-600 hover:text-red-700"
                title="删除"
                @click="deleteHost(host)"
              >
                <i class="fas fa-trash"></i>
              </Button>
            </div>
          </div>
          <div class="flex flex-wrap gap-1">
            <Badge><i class="fas fa-server mr-1"></i>SSH</Badge>
            <Badge v-if="host.has_private_key" variant="info"><i class="fas fa-key mr-1"></i>密钥</Badge>
            <Badge v-else-if="host.has_password">密码</Badge>
            <Badge v-else variant="warning">未配置</Badge>
          </div>
          <p
            class="min-h-0 text-sm text-slate-500 line-clamp-2"
            :class="{ invisible: !host.description }"
          >{{ host.description }}</p>
        </CardHeader>
        <CardContent class="flex flex-1 flex-col space-y-3 p-4 text-sm">
          <div class="flex items-start gap-2 text-slate-600">
            <i class="fas fa-network-wired mt-0.5 w-4 text-slate-400"></i>
            <div>
              <div><strong>{{ host.host }}</strong><span class="text-slate-500">:{{ host.port }}</span></div>
              <div class="mt-1 text-slate-500"><i class="fas fa-user mr-1"></i>{{ host.username }}</div>
            </div>
          </div>
          <div>
            <div v-if="host.checking_docker" class="text-slate-500"><i class="fas fa-spinner fa-spin"></i> 检测中...</div>
            <template v-else>
              <Badge v-if="host.docker_available" variant="success" class="mb-1">
                <i class="fab fa-docker mr-1"></i>Docker 可用
              </Badge>
              <Badge v-else class="mb-1"><i class="fab fa-docker mr-1"></i>Docker 不可用</Badge>
              <p v-if="host.docker_version" class="text-xs text-slate-500">
                <i class="fas fa-info-circle mr-1"></i>{{ host.docker_version }}
              </p>
            </template>
          </div>
          <p class="mt-auto min-h-11 border-t border-slate-100 pt-2 text-xs text-slate-500">
            <i class="fas fa-clock mr-1"></i>{{ formatTime(host.created_at) }}
          </p>
        </CardContent>
      </Card>
    </div>
  </div>

    <FormDialog
      :model-value="showAddModal || showEditModal"
      :title="editingHost ? '编辑主机' : '添加主机'"
      icon="fa-server"
      size="lg"
      @update:model-value="(v) => !v && closeModal()"
    >
      <form class="space-y-6" @submit.prevent="saveHost">
        <div>
          <h4 class="mb-3 border-b border-slate-200 pb-2 text-sm font-semibold text-slate-600">
            <i class="fas fa-server mr-2"></i>主机信息
          </h4>
          <div class="grid gap-3 md:grid-cols-2">
            <div class="space-y-2">
              <Label>主机名称 <span class="text-red-600">*</span></Label>
              <Input v-model="hostForm.name" placeholder="例如：生产服务器" required />
            </div>
            <div class="space-y-2">
              <Label>主机地址 <span class="text-red-600">*</span></Label>
              <Input v-model="hostForm.host" placeholder="例如：192.168.1.100" required />
            </div>
            <div class="space-y-2">
              <Label>SSH 端口 <span class="text-red-600">*</span></Label>
              <Input v-model.number="hostForm.port" type="number" min="1" max="65535" required />
            </div>
            <div class="space-y-2 md:col-span-2">
              <Label>描述（可选）</Label>
              <Input v-model="hostForm.description" placeholder="请输入主机描述信息..." />
            </div>
          </div>
        </div>

        <div>
          <h4 class="mb-3 border-b border-slate-200 pb-2 text-sm font-semibold text-slate-600">
            <i class="fas fa-key mr-2"></i>SSH 认证配置
          </h4>
          <div class="mb-4 inline-flex w-full rounded-lg border border-slate-200 bg-slate-50 p-1">
            <button
              type="button"
              class="flex-1 rounded-md px-3 py-2 text-sm font-medium"
              :class="authType === 'password' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600'"
              @click="authType = 'password'"
            >
              <i class="fas fa-lock mr-1"></i>密码认证
            </button>
            <button
              type="button"
              class="flex-1 rounded-md px-3 py-2 text-sm font-medium"
              :class="authType === 'key' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-600'"
              @click="authType = 'key'"
            >
              <i class="fas fa-key mr-1"></i>密钥认证
            </button>
          </div>

          <div v-if="authType === 'password'" class="grid gap-3 md:grid-cols-2">
            <div class="space-y-2">
              <Label>SSH 用户名 <span class="text-red-600">*</span></Label>
              <Input v-model="hostForm.username" required />
            </div>
            <div class="space-y-2">
              <Label>SSH 密码 <span class="text-red-600">*</span></Label>
              <Input v-model="hostForm.password" type="password" :required="!editingHost" />
              <p v-if="editingHost?.has_password" class="text-xs text-slate-500">留空表示不修改密码</p>
            </div>
          </div>

          <div v-if="authType === 'key'" class="space-y-3">
            <div class="space-y-2">
              <Label>SSH 用户名 <span class="text-red-600">*</span></Label>
              <Input v-model="hostForm.username" required />
            </div>
            <div class="space-y-2">
              <Label>SSH 私钥 <span class="text-red-600">*</span></Label>
              <textarea
                v-model="hostForm.private_key"
                class="min-h-[100px] w-full rounded-md border border-slate-200 px-3 py-2 font-mono text-xs"
                :required="!editingHost"
                placeholder="-----BEGIN RSA PRIVATE KEY-----"
              />
            </div>
            <div class="space-y-2">
              <Label>私钥密码（可选）</Label>
              <Input v-model="hostForm.key_password" type="password" />
            </div>
          </div>

          <div class="mt-4 border-t border-slate-200 pt-4">
            <Button type="button" variant="outline" size="sm" :disabled="testingConnectionForm" @click="testConnectionFromForm">
              <i v-if="testingConnectionForm" class="fas fa-spinner fa-spin"></i>
              <i v-else class="fas fa-plug"></i>
              {{ testingConnectionForm ? "测试中..." : "测试连接" }}
            </Button>
            <AlertBanner
              v-if="testResult"
              class="mt-2"
              :variant="testResult.success ? 'success' : 'danger'"
              :message="testResult.message + (testResult.success && testResult.docker_available ? ` (${testResult.docker_version})` : '')"
            />
          </div>
        </div>

      </form>
      <template #footer>
        <Button variant="secondary" size="sm" @click="closeModal">取消</Button>
        <Button size="sm" :disabled="saving || testingConnectionForm" @click="saveHost">
          <i v-if="saving" class="fas fa-spinner fa-spin"></i>
          <i v-else class="fas fa-save"></i>
          {{ saving ? "保存中..." : "保存" }}
        </Button>
      </template>
    </FormDialog>

    <ResourceMemberPermissionDialog
      v-model="permissionDialogOpen"
      resource-type="agent_host"
      :resource-id="permissionTarget?.host_id || ''"
      :team-id="activeTeamId"
      :resource-name="permissionTarget?.name || ''"
    />
  </div>
</template>

<script>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";
import { showConfirm } from "@/composables/useConfirm";

import axios from "axios";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import Input from "@/components/ui/input/Input.vue";
import Label from "@/components/ui/label/Label.vue";
import Badge from "@/components/ui/badge/Badge.vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import AlertBanner from "@/components/ui/AlertBanner.vue";
import ResourceMemberPermissionDialog from "@/components/team/ResourceMemberPermissionDialog.vue";
import { useTeamStore } from "@/stores/team";

export default {
  name: "HostManager",
  components: {
    FormDialog,
    Button,
    Input,
    Label,
    Badge,
    Card,
    CardHeader,
    CardTitle,
    CardContent,
    EmptyState,
    AlertBanner,
    ResourceMemberPermissionDialog,
  },
  props: {
    filterType: { type: String, default: "all" },
    /** 为 false 时仅保留弹窗能力（供「全部」视图委托 SSH 编辑，不切换筛选） */
    showList: { type: Boolean, default: true },
  },
  data() {
    return {
      hosts: [],
      loading: false,
      showAddModal: false,
      showEditModal: false,
      permissionDialogOpen: false,
      permissionTarget: null,
      editingHost: null,
      saving: false,
      testingConnection: null,
      testingConnectionForm: false,
      testResult: null,
      authType: "password",
      hostForm: {
        name: "",
        host: "",
        port: 22,
        username: "",
        password: "",
        private_key: "",
        key_password: "",
        docker_version: null,
        description: "",
      },
    };
  },
  computed: {
    shouldShow() {
      return this.filterType === "all" || this.filterType === "ssh";
    },
    filteredHosts() {
      return this.shouldShow ? this.hosts : [];
    },
    activeTeamId() {
      return useTeamStore().activeTeamId || "";
    },
  },
  mounted() {
    this.loadHosts();
  },
  methods: {
    async loadHosts() {
      this.loading = true;
      try {
        const res = await axios.get("/api/hosts");
        if (res.data.hosts) {
          this.hosts = res.data.hosts || [];
          this.checkDockerForAllHosts();
        }
      } catch (error) {
        toastError("加载主机列表失败: " + (error.response?.data?.detail || error.message));
      } finally {
        this.loading = false;
      }
    },
    async checkDockerForAllHosts() {
      for (const host of this.hosts) {
        if (host.docker_version || (!host.has_password && !host.has_private_key)) continue;
        this.$set(host, "checking_docker", true);
        try {
          const res = await axios.post(`/api/hosts/${host.host_id}/test-ssh`);
          if (res.data.success && res.data.docker_available) {
            this.$set(host, "docker_available", true);
            if (res.data.docker_version) {
              this.$set(host, "docker_version", res.data.docker_version);
              await axios.put(`/api/hosts/${host.host_id}`, { docker_version: res.data.docker_version });
            }
          } else {
            this.$set(host, "docker_available", false);
          }
        } catch {
          this.$set(host, "docker_available", false);
        } finally {
          this.$set(host, "checking_docker", false);
        }
      }
    },
    closeModal() {
      this.showAddModal = false;
      this.showEditModal = false;
      this.editingHost = null;
      this.testResult = null;
      this.authType = "password";
      this.hostForm = {
        name: "",
        host: "",
        port: 22,
        username: "",
        password: "",
        private_key: "",
        key_password: "",
        docker_version: null,
        description: "",
      };
    },
    openResourcePermission(host) {
      this.permissionTarget = host;
      this.permissionDialogOpen = true;
    },
    editHost(host) {
      this.editingHost = host;
      this.showEditModal = true;
      this.hostForm = {
        name: host.name,
        host: host.host,
        port: host.port,
        username: host.username,
        password: "",
        private_key: "",
        key_password: "",
        docker_version: host.docker_version || null,
        description: host.description || "",
      };
      this.authType = host.has_private_key ? "key" : "password";
      this.testResult = null;
    },
    async testConnectionFromForm() {
      if (!this.hostForm.host || !this.hostForm.username) {
        toastError("请先填写主机地址和用户名");
        return;
      }
      if (this.authType === "password" && !this.hostForm.password) {
        toastError("请填写 SSH 密码");
        return;
      }
      if (this.authType === "key" && !this.hostForm.private_key) {
        toastError("请填写 SSH 私钥");
        return;
      }
      this.testingConnectionForm = true;
      this.testResult = null;
      try {
        const res = await axios.post("/api/hosts/test-ssh", {
          host: this.hostForm.host,
          port: this.hostForm.port,
          username: this.hostForm.username,
          password: this.authType === "password" ? this.hostForm.password : null,
          private_key: this.authType === "key" ? this.hostForm.private_key : null,
          key_password: this.authType === "key" ? this.hostForm.key_password : null,
        });
        this.testResult = res.data;
        if (this.testResult.success && this.testResult.docker_available && this.testResult.docker_version) {
          this.hostForm.docker_version = this.testResult.docker_version;
        }
      } catch (error) {
        this.testResult = {
          success: false,
          message: error.response?.data?.detail || error.message || "测试连接失败",
        };
      } finally {
        this.testingConnectionForm = false;
      }
    },
    async testConnection(host) {
      this.testingConnection = host.host_id;
      try {
        const res = await axios.post(`/api/hosts/${host.host_id}/test-ssh`);
        if (res.data.success) {
          toastSuccess(`连接成功！\n${res.data.message}${res.data.docker_available ? "\nDocker: " + res.data.docker_version : "\nDocker 不可用"}`);
          if (res.data.docker_available && res.data.docker_version) {
            await axios.put(`/api/hosts/${host.host_id}`, { docker_version: res.data.docker_version });
          }
          this.loadHosts();
        } else {
          toastError(`连接失败：${res.data.message}`);
        }
      } catch (error) {
        toastError("测试连接失败: " + (error.response?.data?.detail || error.message));
      } finally {
        this.testingConnection = null;
      }
    },
    async saveHost() {
      if (!this.hostForm.name || !this.hostForm.host || !this.hostForm.username) {
        toastError("请填写必填字段");
        return;
      }
      if (this.authType === "password" && !this.hostForm.password && !this.editingHost) {
        toastError("请填写 SSH 密码");
        return;
      }
      if (this.authType === "key" && !this.hostForm.private_key && !this.editingHost) {
        toastError("请填写 SSH 私钥");
        return;
      }
      this.saving = true;
      try {
        const hostData = {
          name: this.hostForm.name,
          host: this.hostForm.host,
          port: this.hostForm.port,
          username: this.hostForm.username,
        };
        if (this.hostForm.docker_version) hostData.docker_version = this.hostForm.docker_version;
        if (this.hostForm.description) hostData.description = this.hostForm.description;
        if (this.authType === "password") {
          if (!this.editingHost) {
            hostData.password = this.hostForm.password;
            hostData.private_key = null;
            hostData.key_password = null;
          } else {
            if (this.hostForm.password) hostData.password = this.hostForm.password;
            if (this.editingHost.has_private_key) {
              hostData.private_key = "";
              hostData.key_password = "";
            }
          }
        } else if (!this.editingHost) {
          hostData.private_key = this.hostForm.private_key;
          hostData.key_password = this.hostForm.key_password || null;
          hostData.password = null;
        } else {
          if (this.hostForm.private_key) {
            hostData.private_key = this.hostForm.private_key;
            hostData.key_password = this.hostForm.key_password || null;
          }
          if (this.editingHost.has_password) hostData.password = "";
        }
        const res = this.editingHost
          ? await axios.put(`/api/hosts/${this.editingHost.host_id}`, hostData)
          : await axios.post("/api/hosts", hostData);
        if (res.data.success) {
          toastSuccess(this.editingHost ? "主机更新成功" : "主机添加成功");
          this.closeModal();
          this.loadHosts();
        }
      } catch (error) {
        toastError("保存主机失败: " + (error.response?.data?.detail || error.message));
      } finally {
        this.saving = false;
      }
    },
    async deleteHost(host) {
      if (!(await showConfirm({ message: `确定要删除主机 "${host.name}" 吗？`, danger: true }))) return;
      try {
        const res = await axios.delete(`/api/hosts/${host.host_id}`);
        if (res.data.success) {
          toastSuccess("主机已删除");
          this.loadHosts();
        }
      } catch (error) {
        toastError("删除主机失败: " + (error.response?.data?.detail || error.message));
      }
    },
    formatTime(timeStr) {
      if (!timeStr) return "-";
      return new Date(timeStr).toLocaleString("zh-CN");
    },
  },
};
</script>

<template>
  <div class="min-h-[400px]">
    <div class="mb-4 flex items-center justify-between gap-3">
      <h2 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
        <AppIcon  name="chart-line" class="text-blue-600" />
        {{ dashboardTitle }}
      </h2>
      <Button variant="outline" size="sm" :disabled="loading" @click="loadDashboard">
        <AppIcon name="sync-alt" />
        刷新
      </Button>
    </div>

    <div v-if="loading && !stats" class="flex items-center justify-center gap-2 py-12 text-sm text-slate-500">
      <AppIcon  name="spinner" spin />
      加载中…
    </div>

    <template v-else>
      <div class="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard title="总任务数" :value="stats?.totalTasks" icon="tasks" accent="blue">
          <template #footer>
            <div class="grid grid-cols-2 gap-2 text-center text-sm">
              <div>
                <p class="text-slate-500">运行中</p>
                <p class="font-semibold text-amber-600">{{ stats?.runningTasks || 0 }}</p>
              </div>
              <div>
                <p class="text-slate-500">已完成</p>
                <p class="font-semibold text-green-600">{{ stats?.completedTasks || 0 }}</p>
              </div>
            </div>
          </template>
        </StatCard>

        <StatCard title="流水线" :value="stats?.pipelines" icon="project-diagram" accent="sky">
          <template #footer>
            <div class="grid grid-cols-2 gap-2 text-center text-sm">
              <div>
                <p class="text-slate-500">已启用</p>
                <p class="font-semibold text-green-600">{{ stats?.enabledPipelines || 0 }}</p>
              </div>
              <div>
                <p class="text-slate-500">已禁用</p>
                <p class="font-semibold text-slate-600">{{ stats?.disabledPipelines || 0 }}</p>
              </div>
            </div>
          </template>
        </StatCard>

        <StatCard title="数据源" :value="stats?.datasources" icon="database" accent="green">
          <template #footer>
            <div class="text-center text-sm">
              <p class="text-slate-500">Git 仓库</p>
              <p class="font-semibold text-slate-900">{{ stats?.datasources || 0 }}</p>
            </div>
          </template>
        </StatCard>

        <StatCard title="镜像仓库" :value="stats?.registries" icon="box" accent="amber">
          <template #footer>
            <div class="text-center text-sm">
              <p class="text-slate-500">已配置</p>
              <p class="font-semibold text-slate-900">{{ stats?.registries || 0 }}</p>
            </div>
          </template>
        </StatCard>

        <StatCard title="模板" :value="stats?.templates" icon="layer-group" accent="slate" />
        <StatCard title="资源包" :value="stats?.resourcePackages" icon="archive" accent="dark" />
        <StatCard title="主机" :value="stats?.hosts" icon="server" accent="red" />
        <StatCard
          title="存储使用"
          :value="formatStorage(stats?.totalStorage || 0)"
          icon="hdd"
          accent="blue"
        >
          <template #footer>
            <div class="space-y-1 text-sm">
              <div class="flex justify-between gap-2">
                <span class="text-slate-500">构建目录</span>
                <span class="font-medium text-slate-900">{{ formatStorage(stats?.buildStorage || 0) }}</span>
              </div>
              <div class="flex justify-between gap-2">
                <span class="text-slate-500">导出目录</span>
                <span class="font-medium text-slate-900">{{ formatStorage(stats?.exportStorage || 0) }}</span>
              </div>
            </div>
          </template>
        </StatCard>
      </div>

      <Card>
        <CardHeader class="border-b border-slate-100 pb-3">
          <CardTitle class="flex items-center gap-2 text-base">
            <AppIcon  name="info-circle" class="text-sky-600" />
            系统信息
          </CardTitle>
        </CardHeader>
        <CardContent class="p-4">
          <div v-if="systemInfo" class="space-y-4 text-sm">
            <div class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
              <InfoBlock title="Docker 状态" icon="docker" icon-class="text-sky-600">
                <Badge :variant="systemInfo.connected ? 'success' : 'danger'">
                  {{ systemInfo.connected ?"已连接" :"未连接" }}
                </Badge>
                <div v-if="systemInfo.builder_type" class="mt-2 space-y-1 text-slate-600">
                  <p>
                    类型:
                    <span class="font-medium text-slate-900">{{
                      systemInfo.builder_type ==="local"
                        ?"本地"
                        : systemInfo.builder_type ==="remote"
                          ?"远程"
                          :"模拟"
                    }}</span>
                  </p>
                  <p v-if="systemInfo.remote_host">
                    地址: <span class="font-medium">{{ systemInfo.remote_host }}</span>
                  </p>
                </div>
                <p
                  v-if="systemInfo.connection_error"
                  class="mt-2 rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700"
                >
                  <AppIcon  name="exclamation-triangle" /> {{ systemInfo.connection_error }}
                </p>
              </InfoBlock>

              <InfoBlock title="版本信息" icon="code-branch" icon-class="text-blue-600">
                <div class="space-y-1 text-slate-600">
                  <p v-if="systemInfo.version">
                    Docker: <span class="font-medium text-slate-900">{{ systemInfo.version }}</span>
                  </p>
                  <p v-if="systemInfo.api_version">
                    API: <span class="font-medium text-slate-900">{{ systemInfo.api_version }}</span>
                  </p>
                  <p v-if="systemInfo.runtime">
                    运行时: <span class="font-medium text-slate-900">{{ systemInfo.runtime }}</span>
                  </p>
                  <p v-if="systemInfo.buildx_available" class="flex flex-wrap items-center gap-1">
                    <Badge variant="success">Buildx 可用</Badge>
                    <span v-if="systemInfo.buildx_version" class="text-xs text-slate-500">
                      v{{ systemInfo.buildx_version }}
                    </span>
                  </p>
                </div>
              </InfoBlock>

              <InfoBlock title="系统资源" icon="server" icon-class="text-green-600">
                <div class="space-y-1 text-slate-600">
                  <p v-if="systemInfo.ncpu">
                    CPU: <span class="font-medium text-slate-900">{{ systemInfo.ncpu }} 核</span>
                  </p>
                  <p v-if="systemInfo.mem_total">
                    内存:
                    <span class="font-medium text-slate-900">{{ formatStorage(systemInfo.mem_total) }}</span>
                  </p>
                  <p v-if="systemInfo.os_type">
                    系统: <span class="font-medium text-slate-900">{{ systemInfo.os_type }}</span>
                  </p>
                  <p v-if="systemInfo.arch">
                    架构: <span class="font-medium text-slate-900">{{ systemInfo.arch }}</span>
                  </p>
                </div>
              </InfoBlock>

              <InfoBlock title="资源统计" icon="cubes" icon-class="text-amber-600">
                <div class="space-y-1 text-slate-600">
                  <p v-if="systemInfo.images_count !== undefined">
                    镜像:
                    <span class="font-medium text-slate-900">{{ systemInfo.images_count }}</span>
                    <span v-if="systemInfo.images_size > 0" class="text-xs text-slate-500">
                      ({{ formatStorage(systemInfo.images_size) }})
                    </span>
                  </p>
                  <p v-if="systemInfo.containers_total !== undefined">
                    容器:
                    <span class="font-medium text-slate-900">{{ systemInfo.containers_total }}</span>
                    <span v-if="systemInfo.containers_running !== undefined" class="text-green-600">
                      (运行: {{ systemInfo.containers_running }})
                    </span>
                  </p>
                  <p v-if="systemInfo.volumes_count !== undefined">
                    数据卷:
                    <span class="font-medium text-slate-900">{{ systemInfo.volumes_count }}</span>
                  </p>
                  <p v-if="systemInfo.networks_count !== undefined">
                    网络:
                    <span class="font-medium text-slate-900">{{ systemInfo.networks_count }}</span>
                  </p>
                </div>
              </InfoBlock>
            </div>

            <div
              v-if="systemInfo.storage_driver || systemInfo.docker_root || systemInfo.kernel_version"
              class="rounded-lg border border-slate-200 bg-slate-50/80 p-4"
            >
              <h4 class="mb-2 flex items-center gap-2 font-medium text-slate-900">
                <AppIcon  name="cog" class="text-slate-500" />
                系统配置
              </h4>
              <div class="grid grid-cols-1 gap-2 text-slate-600 md:grid-cols-3">
                <p v-if="systemInfo.storage_driver">
                  存储驱动:
                  <span class="font-medium text-slate-900">{{ systemInfo.storage_driver }}</span>
                </p>
                <p v-if="systemInfo.docker_root" class="break-all">
                  Docker 根目录:
                  <span class="font-mono text-xs font-medium text-slate-900">{{ systemInfo.docker_root }}</span>
                </p>
                <p v-if="systemInfo.kernel_version">
                  内核版本:
                  <span class="font-medium text-slate-900">{{ systemInfo.kernel_version }}</span>
                </p>
              </div>
            </div>
          </div>
          <div v-else class="flex items-center justify-center gap-2 py-8 text-sm text-slate-500">
            <AppIcon  name="spinner" spin />
            加载系统信息中…
          </div>
        </CardContent>
      </Card>
    </template>
  </div>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

import axios from "axios";
import { computed, onMounted, ref } from "vue";
import { useTeamStore } from "@/stores/team";
import Button from "@/components/ui/button/Button.vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import StatCard from "@/components/ui/StatCard.vue";
import { Badge } from "@/components/ui/badge";
import InfoBlock from "@/components/ui/InfoBlock.vue";

defineEmits(["navigate"]);

const teamStore = useTeamStore();
const dashboardTitle = computed(() => {
  const name = teamStore.activeTeam?.name;
  return name ? `${name} · 团队仪表盘` :"系统仪表盘";
});

const loading = ref(false);
const stats = ref(null);
const systemInfo = ref(null);

const defaultStats = () => ({
  totalTasks: 0,
  runningTasks: 0,
  completedTasks: 0,
  pipelines: 0,
  enabledPipelines: 0,
  disabledPipelines: 0,
  datasources: 0,
  registries: 0,
  templates: 0,
  resourcePackages: 0,
  hosts: 0,
  buildStorage: 0,
  exportStorage: 0,
  totalStorage: 0,
});

async function loadDashboard() {
  loading.value = true;
  try {
    const [dashboardRes, dockerInfoRes] = await Promise.all([
      axios.get("/api/dashboard/stats"),
      axios.get("/api/docker/info").catch(() => ({ data: null })),
    ]);

    if (dashboardRes.data?.success) {
      stats.value = dashboardRes.data.stats;
    } else {
      stats.value = defaultStats();
    }

    systemInfo.value = dockerInfoRes?.data || null;
  } catch (error) {
    console.error("加载仪表盘数据失败:", error);
    toastError("加载仪表盘数据失败:" + (error.response?.data?.detail || error.message));
    stats.value = defaultStats();
  } finally {
    loading.value = false;
  }
}

function formatStorage(bytes) {
  if (!bytes || bytes === 0) return"0 B";
  const units = ["B","KB","MB","GB","TB"];
  let size = bytes;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

onMounted(() => {
  loadDashboard();
});
</script>

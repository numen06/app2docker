<template>
  <div class="space-y-4">
    <div class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 class="text-lg font-semibold text-slate-900">团队仪表盘</h2>
      <p class="mt-1 text-sm text-slate-600">
        以下为控制台首页摘要；可从卡片跳转到对应后台 Tab。
      </p>
    </div>
    <DashboardPanel @navigate="onNavigate" />
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import DashboardPanel from "@/components/DashboardPanel.vue";

const router = useRouter();

function onNavigate(tab, params) {
  if (params?.status) {
    sessionStorage.setItem("taskStatusFilter", params.status);
  }
  router.push(`/app/${tab}`);
}
</script>

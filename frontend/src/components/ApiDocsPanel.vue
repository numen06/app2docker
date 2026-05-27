<template>
  <div class="space-y-4">
    <div class="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
      <AppIcon  name="circle-info" class="mr-1" />
      接口认证支持 <code class="rounded bg-white/80 px-1">Authorization: Bearer &lt;token&gt;</code> 或
      <code class="rounded bg-white/80 px-1">X-API-Key: &lt;appkey&gt;</code>
    </div>

    <div class="flex gap-1 border-b border-slate-200">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        class="border-b-2 px-4 py-2 text-sm font-medium transition"
        :class="activeTab === tab.id
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-slate-500 hover:text-slate-800'"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <Card v-if="activeTab === 'tasks'">
      <CardHeader class="border-b border-slate-100 pb-3">
        <CardTitle class="text-base">任务接口（示例）</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4 p-4 text-sm">
        <ApiEndpoint label="获取任务列表" method="GET" path="/api/tasks" />
        <ApiEndpoint label="获取单个任务详情" method="GET" path="/api/tasks/{task_id}" />
        <ApiEndpoint label="停止任务" method="POST" path="/api/tasks/{task_id}/stop" />
        <ApiEndpoint label="删除任务" method="DELETE" path="/api/tasks/{task_id}" />
      </CardContent>
    </Card>

    <Card v-else>
      <CardHeader class="border-b border-slate-100 pb-3">
        <CardTitle class="text-base">流水线接口（示例）</CardTitle>
      </CardHeader>
      <CardContent class="space-y-4 p-4 text-sm">
        <ApiEndpoint label="获取流水线列表" method="GET" path="/api/pipelines" />
        <ApiEndpoint label="创建流水线" method="POST" path="/api/pipelines" />
        <ApiEndpoint label="更新流水线" method="PUT" path="/api/pipelines/{pipeline_id}" />
        <ApiEndpoint label="执行流水线" method="POST" path="/api/pipelines/{pipeline_id}/run" />
      </CardContent>
    </Card>
  </div>
</template>

<script setup>
import { ref } from "vue";
import Card from "@/components/ui/card/Card.vue";
import CardHeader from "@/components/ui/card/CardHeader.vue";
import CardTitle from "@/components/ui/card/CardTitle.vue";
import CardContent from "@/components/ui/card/CardContent.vue";
import ApiEndpoint from "@/components/ui/ApiEndpoint.vue";

const activeTab = ref("tasks");
const tabs = [
  { id:"tasks", label:"任务相关" },
  { id:"pipeline", label:"流水线相关" },
];
</script>

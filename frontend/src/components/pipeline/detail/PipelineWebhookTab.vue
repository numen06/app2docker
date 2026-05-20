<template>
  <div class="pipeline-webhook-tab max-w-lg">
    <label class="mb-2 block text-sm font-medium text-slate-700">Webhook URL</label>
    <div class="mb-3 flex gap-2">
      <input
        :value="webhookUrl"
        type="text"
        class="flex h-9 min-w-0 flex-1 rounded-md border border-slate-200 px-3 py-1 font-mono text-sm"
        readonly
      />
      <Button variant="outline" size="sm" @click="copyWebhookUrl">
        <i class="fas fa-copy"></i> 复制
      </Button>
    </div>
    <div class="alert alert-info small mb-0">
      <strong>使用说明：</strong><br />
      1. 在 Git 平台仓库设置中添加 Webhook<br />
      2. 将上述 URL 粘贴到 Payload URL<br />
      3. Content Type 选择 <code>application/json</code><br />
      4. Secret 填写流水线配置的 Webhook 密钥（如有）<br />
      5. 选择 Push events 等触发事件
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from "vue";
import Button from "@/components/ui/button/Button.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { copyToClipboard } from "@/utils/clipboard.js";

const detail = inject(PIPELINE_DETAIL_KEY);

const webhookUrl = computed(() => {
  const p = detail.pipeline.value;
  if (!p) return "";
  const token = p.webhook_token;
  if (!token) return "请先设置 Webhook Token（在「编辑配置」→ Webhook 设置中配置）";
  return `${window.location.origin}/api/webhook/${token}`;
});

async function copyWebhookUrl() {
  const url = webhookUrl.value;
  if (!url || url.startsWith("请先")) {
    alert(url || "无可复制的 URL");
    return;
  }
  const ok = await copyToClipboard(url);
  alert(ok ? "Webhook URL 已复制" : "复制失败");
}
</script>

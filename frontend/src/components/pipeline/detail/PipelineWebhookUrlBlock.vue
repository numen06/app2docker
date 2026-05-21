<template>
  <section class="pipeline-webhook-block pipeline-webhook-block--url">
    <h3 class="pipeline-webhook-block__title">
      <i class="fas fa-link"></i> Webhook URL
    </h3>
    <p class="pipeline-webhook-block__desc">
      将下方地址配置到 Git 仓库的 Webhook，推送代码时可触发本流水线构建。
    </p>
    <div class="pipeline-webhook-url-row">
      <input
        :value="webhookUrl"
        type="text"
        class="flex h-9 min-w-0 flex-1 rounded-md border border-slate-200 bg-white px-3 py-1 font-mono text-sm"
        readonly
      />
      <Button variant="outline" size="sm" type="button" @click="copyWebhookUrl">
        <i class="fas fa-copy mr-1"></i> 复制
      </Button>
    </div>
    <p class="pipeline-webhook-field__hint mt-2 mb-0">
      Payload URL 填上述地址；Content-Type 选 <code>application/json</code>；Secret 与下方「Webhook 密钥」一致（如有）。
    </p>
  </section>
</template>

<script setup>
import { toastSuccess, toastError, toastInfo, toastApiError } from "@/utils/notify";

import { computed, inject } from "vue";
import Button from "@/components/ui/button/Button.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { copyToClipboard } from "@/utils/clipboard.js";

const props = defineProps({
  webhookToken: { type: String, default: "" },
});

const detail = inject(PIPELINE_DETAIL_KEY, null);

const webhookUrl = computed(() => {
  const token =
    props.webhookToken ||
    detail?.pipeline?.value?.webhook_token ||
    "";
  if (!token) {
    return "请先配置 Webhook Token（下方可生成）";
  }
  return `${window.location.origin}/api/webhook/${token}`;
});

async function copyWebhookUrl() {
  const url = webhookUrl.value;
  if (!url || url.startsWith("请先")) {
    toastInfo(url || "无可复制的 URL");
    return;
  }
  const ok = await copyToClipboard(url);
  ok ? toastSuccess("Webhook URL 已复制") : toastError("复制失败");
}
</script>

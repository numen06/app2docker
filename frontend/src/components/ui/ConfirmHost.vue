<template>
  <BaseDialog :model-value="!!pending" @update:model-value="onBackdropClose">
    <div
      class="relative z-10 mx-auto w-full max-w-md shrink-0 rounded-lg border border-slate-200 bg-white text-slate-900 shadow-xl"
      @click.stop
    >
      <div class="border-b border-slate-200 px-4 py-3">
        <h3 class="text-lg font-semibold text-slate-900">
          {{ pending?.title || "确认" }}
        </h3>
      </div>
      <div class="px-4 py-4">
        <p class="whitespace-pre-wrap text-sm text-slate-700">
          {{ pending?.message }}
        </p>
      </div>
      <div
        class="flex flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3 sm:flex-row sm:justify-end"
      >
        <Button variant="secondary" @click="resolveConfirm(false)">
          {{ pending?.cancelText || "取消" }}
        </Button>
        <Button
          :variant="pending?.danger ? 'destructive' : 'default'"
          @click="resolveConfirm(true)"
        >
          {{ pending?.confirmText || "确定" }}
        </Button>
      </div>
    </div>
  </BaseDialog>
</template>

<script setup>
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import { resolveConfirm, useConfirm } from "@/composables/useConfirm";

const { pending } = useConfirm();

function onBackdropClose(open) {
  if (!open) resolveConfirm(false);
}
</script>

<template>
  <div
    class="pointer-events-none fixed top-16 right-4 z-[2100] flex max-w-sm flex-col items-end gap-2"
    aria-live="polite"
    aria-relevant="additions"
  >
    <transition-group name="toast-slide">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto w-full rounded-lg border bg-white p-3 shadow-xl"
        :class="variantBorder[toast.variant] || variantBorder.info"
        role="status"
      >
        <div class="flex items-start gap-2">
          <AppIcon
            :name="variantIcon[toast.variant] || variantIcon.info"
            class="mt-0.5 h-4 w-4 shrink-0"
            :class="variantIconClass[toast.variant] || variantIconClass.info"
          />
          <div
            class="min-w-0 flex-1 whitespace-pre-wrap text-sm text-slate-800"
          >
            {{ toast.message }}
          </div>
          <button
            type="button"
            class="shrink-0 rounded p-1 text-slate-500 hover:bg-slate-100"
            aria-label="关闭"
            @click="dismissToast(toast.id)"
          >
            <AppIcon name="times" class="h-4 w-4" />
          </button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { useToast } from "@/composables/useToast";

const { toasts, dismissToast } = useToast();

const variantBorder = {
  success:"border-green-200",
  error:"border-red-200",
  info:"border-sky-200",
};

const variantIcon = {
  success:"check-circle",
  error:"times-circle",
  info:"circle-info",
};

const variantIconClass = {
  success:"text-green-600",
  error:"text-red-600",
  info:"text-sky-600",
};
</script>

<style scoped>
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.25s ease;
}
.toast-slide-enter-from {
  opacity: 0;
  transform: translateX(1rem);
}
.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(1rem);
}
.toast-slide-move {
  transition: transform 0.25s ease;
}
</style>

<template>
  <BaseDialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)">
    <div
      class="relative z-10 mx-auto flex max-h-[90vh] w-full shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white text-slate-900 shadow-xl"
      :class="widthClass"
      @click.stop
    >
      <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
        <h3 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
          <i v-if="icon" :class="['fas', icon, iconClass]"></i>
          {{ title }}
        </h3>
        <button
          type="button"
          class="rounded-md p-2 text-slate-500 hover:bg-slate-100"
          aria-label="关闭"
          @click="$emit('update:modelValue', false)"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <slot />
      </div>
      <div
        v-if="$slots.footer"
        class="flex shrink-0 flex-col gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3 sm:flex-row sm:justify-end"
      >
        <slot name="footer" />
      </div>
    </div>
  </BaseDialog>
</template>

<script setup>
import { computed } from "vue";
import BaseDialog from "@/components/ui/dialog/BaseDialog.vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, required: true },
  icon: { type: String, default: "" },
  iconClass: { type: String, default: "text-blue-600" },
  size: { type: String, default: "md" },
});

defineEmits(["update:modelValue"]);

const widths = {
  sm: "max-w-md",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
  "2xl": "max-w-[min(96vw,1400px)]",
};
const widthClass = computed(() => widths[props.size] || widths.md);
</script>

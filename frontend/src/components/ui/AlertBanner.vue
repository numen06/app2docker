<template>
  <div
    v-if="message"
    :class="
      cn(
        'mt-3 rounded-md border px-3 py-2 text-sm',
        variants[variant] ?? variants.danger
      )
    "
    role="alert"
  >
    <i v-if="showIcon" :class="['fas', icons[variant], 'mr-1']"></i>
    {{ message }}
  </div>
</template>

<script setup>
import { cn } from "@/lib/utils";

defineProps({
  message: { type: String, default: "" },
  variant: { type: String, default: "danger" },
  showIcon: { type: Boolean, default: true },
});

const variants = {
  danger: "border-red-200 bg-red-50 text-red-800",
  info: "border-sky-200 bg-sky-50 text-sky-900",
  success: "border-green-200 bg-green-50 text-green-800",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
};

const icons = {
  danger: "fa-exclamation-circle",
  info: "fa-circle-info",
  success: "fa-check-circle",
  warning: "fa-exclamation-triangle",
};
</script>

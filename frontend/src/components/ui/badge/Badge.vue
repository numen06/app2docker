<template>
  <span
    :class="
      cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium',
        variants[variant] ?? variants.default,
        $attrs.class ?? ''
      )
    "
  >
    <slot />
  </span>
</template>

<script setup>
import { cn } from "@/lib/utils";

defineOptions({ inheritAttrs: false });

defineProps({
  variant: { type: String, default: "default" },
});

const variants = {
  default: "bg-slate-100 text-slate-700",
  success: "bg-green-100 text-green-800",
  danger: "bg-red-100 text-red-800",
  warning: "bg-amber-100 text-amber-900",
  info: "bg-sky-100 text-sky-800",
};
</script>

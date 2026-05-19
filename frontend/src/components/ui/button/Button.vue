<template>
  <component
    :is="as"
    :type="as === 'button' ? type : undefined"
    :class="cn(base, variants[variant] ?? variants.default, sizes[size] ?? sizes.default, $attrs.class ?? '')"
    :disabled="disabled || undefined"
    v-bind="filteredAttrs"
  >
    <slot />
  </component>
</template>

<script setup>
import { computed, useAttrs } from "vue";
import { cn } from "@/lib/utils";

const props = defineProps({
  as: { type: String, default: "button" },
  type: { type: String, default: "button" },
  variant: { type: String, default: "default" },
  size: { type: String, default: "default" },
  disabled: { type: Boolean, default: false },
});

const attrs = useAttrs();

const filteredAttrs = computed(() => {
  const { class: _c, ...rest } = attrs;
  return rest;
});

const base =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50";

const variants = {
  default: "bg-blue-600 text-white hover:bg-blue-700",
  secondary: "border border-slate-200 bg-white text-slate-900 hover:bg-slate-50",
  outline: "border border-slate-300 bg-transparent hover:bg-slate-50 text-slate-900",
  ghost: "hover:bg-slate-100 text-slate-700",
  destructive: "bg-red-600 text-white hover:bg-red-700",
  link: "text-blue-600 underline-offset-4 hover:underline",
};

const sizes = {
  default: "h-10 px-4 py-2",
  sm: "h-9 rounded-md px-3 text-xs",
  lg: "h-11 rounded-md px-8",
};
</script>

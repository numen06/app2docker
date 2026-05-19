<template>
  <label
    :class="cn('text-sm font-medium leading-none text-slate-700 peer-disabled:cursor-not-allowed peer-disabled:opacity-70', $attrs.class ?? '')"
    v-bind="$attrs"
  >
    <slot />
  </label>
</template>

<script setup>
import { cn } from "@/lib/utils";

defineOptions({ inheritAttrs: false });
</script>

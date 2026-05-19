<template>
  <div :class="cn('flex flex-col gap-2 border-t border-slate-100 bg-slate-50/80 p-4', $attrs.class ?? '')">
    <slot />
  </div>
</template>

<script setup>
import { cn } from "@/lib/utils";
</script>

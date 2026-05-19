<template>
  <div :class="cn('rounded-xl border border-slate-200 bg-white text-slate-950 shadow-sm', $attrs.class ?? '')">
    <slot />
  </div>
</template>

<script setup>
import { cn } from "@/lib/utils";
</script>

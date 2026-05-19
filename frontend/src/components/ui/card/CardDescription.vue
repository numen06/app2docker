<template>
  <p :class="cn('text-sm text-slate-500', $attrs.class ?? '')">
    <slot />
  </p>
</template>

<script setup>
import { cn } from "@/lib/utils";
</script>

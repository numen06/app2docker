<template>
  <h3 :class="cn('text-xl font-semibold leading-none tracking-tight', $attrs.class ?? '')">
    <slot />
  </h3>
</template>

<script setup>
import { cn } from "@/lib/utils";
</script>

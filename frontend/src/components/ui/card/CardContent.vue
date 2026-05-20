<template>
  <div :class="cn('p-6 pt-4', $attrs.class ?? '')">
    <slot />
  </div>
</template>

<script setup>
import { cn } from "@/lib/utils";
</script>

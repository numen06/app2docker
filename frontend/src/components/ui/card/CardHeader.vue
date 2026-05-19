<template>
  <div :class="cn('flex flex-col gap-1.5 p-6 pb-0', $attrs.class ?? '')">
    <slot />
  </div>
</template>

<script setup>
import { cn } from "@/lib/utils";
</script>

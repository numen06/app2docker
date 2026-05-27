<template>
  <div class="flex flex-col items-center justify-center py-12 text-center text-slate-500">
    <AppIcon v-if="icon" :name="icon" class="mb-3 h-8 w-8 text-slate-300" />
    <p class="text-sm">{{ message }}</p>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default:"暂无数据" },
  icon: { type: String, default:"inbox" },
});
</script>

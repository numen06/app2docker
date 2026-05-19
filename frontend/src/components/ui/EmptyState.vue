<template>
  <div class="flex flex-col items-center justify-center py-12 text-center text-slate-500">
    <i v-if="icon" :class="['fas', icon, 'mb-3 text-3xl text-slate-300']"></i>
    <p class="text-sm">{{ message }}</p>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: "暂无数据" },
  icon: { type: String, default: "fa-inbox" },
});
</script>

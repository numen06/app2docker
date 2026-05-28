<template>
  <div class="h-full rounded-lg border border-slate-200 bg-slate-50/60 p-4">
    <div class="mb-2 flex items-center gap-2">
      <AppIcon :name="icon" :class="[iconClass, 'text-lg']" />
      <h4 class="font-medium text-slate-900">{{ title }}</h4>
    </div>
    <slot />
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  icon: { type: String, required: true },
  iconClass: { type: String, default:"text-slate-500" },
});
</script>

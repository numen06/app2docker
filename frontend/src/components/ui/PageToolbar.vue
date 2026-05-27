<template>
  <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <h2 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
      <AppIcon v-if="icon" :name="icon" :class="iconClass" />
      {{ title }}
    </h2>
    <div v-if="$slots.actions" class="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:justify-end">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  icon: { type: String, default:"" },
  iconClass: { type: String, default:"text-blue-600" },
});
</script>

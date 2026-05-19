<template>
  <div class="space-y-1">
    <p class="text-slate-500">{{ label }}</p>
    <code class="block rounded-md bg-slate-100 px-2 py-1.5 font-mono text-xs text-slate-800">
      <span class="mr-2 font-semibold text-blue-600">{{ method }}</span
      >{{ path }}
    </code>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  method: { type: String, required: true },
  path: { type: String, required: true },
});
</script>

<template>
  <div
    class="w-full max-w-full overflow-x-auto rounded-lg border border-slate-200 [-webkit-overflow-scrolling:touch]"
  >
    <table :class="['w-full caption-bottom text-sm', minWidthClass]">
      <slot />
    </table>
  </div>
</template>

<script setup>
defineProps({
  /** Tailwind min-width class, e.g. min-w-[52rem] for wide tables */
  minWidthClass: { type: String, default: "min-w-[42rem]" },
});
</script>

<template>
  <select
    :class="cn(
        'flex h-10 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50',
        $attrs.class ?? ''
      )"
    :value="modelValue"
    @change="onChange"
    v-bind="selectAttrs"
  >
    <slot />
  </select>
</template>

<script setup>
import { computed, useAttrs } from "vue";
import { cn } from "@/lib/utils";

defineOptions({ inheritAttrs: false });

const modelValue = defineModel({ type: [String, Number], default:"" });

const attrs = useAttrs();
const selectAttrs = computed(() => {
  const { class: _c, ...rest } = attrs;
  return rest;
});

function onChange(e) {
  modelValue.value = e.target.value;
}
</script>

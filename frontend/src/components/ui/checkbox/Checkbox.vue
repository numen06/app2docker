<template>
  <input
    v-model="modelValue"
    type="checkbox"
    :disabled="disabled || undefined"
    :class="cn(
        'h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50',
        $attrs.class ?? ''
      )"
    v-bind="checkboxAttrs"
  />
</template>

<script setup>
import { computed, useAttrs } from "vue";
import { cn } from "@/lib/utils";

defineOptions({ inheritAttrs: false });

const modelValue = defineModel({ type: Boolean, default: false });

defineProps({
  disabled: { type: Boolean, default: false },
});

const attrs = useAttrs();
const checkboxAttrs = computed(() => {
  const { class: _class, ...rest } = attrs;
  return rest;
});
</script>

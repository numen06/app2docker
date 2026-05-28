<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue ? 'true' : 'false'"
    :disabled="disabled || undefined"
    :class="cn(
        'inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        modelValue ? 'bg-blue-600' : 'bg-slate-200',
        $attrs.class ?? ''
      )"
    @click="toggle"
  >
    <span
      :class="cn(
          'pointer-events-none block h-5 w-5 rounded-full bg-white shadow transition-transform',
          modelValue ? 'translate-x-5' : 'translate-x-0'
        )"
    />
  </button>
</template>

<script setup>
import { cn } from "@/lib/utils";

defineOptions({ inheritAttrs: false });

const modelValue = defineModel({ type: Boolean, default: false });

const props = defineProps({
  disabled: { type: Boolean, default: false },
});

function toggle() {
  if (!props.disabled) modelValue.value = !modelValue.value;
}
</script>

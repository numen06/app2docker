<template>
  <textarea
    :class="cn(
        'min-h-24 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-50',
        $attrs.class ?? ''
      )"
    :value="modelValue"
    v-bind="textareaAttrs"
    @input="onInput"
  />
</template>

<script setup>
import { computed, useAttrs } from "vue";
import { cn } from "@/lib/utils";

defineOptions({ inheritAttrs: false });

const modelValue = defineModel({ type: [String, Number], default:"" });
const attrs = useAttrs();

const textareaAttrs = computed(() => {
  const { class: _class, ...rest } = attrs;
  return rest;
});

function onInput(event) {
  modelValue.value = event.target.value;
}
</script>

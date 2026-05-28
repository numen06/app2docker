<template>
  <div :class="cn('w-full', $attrs.class ?? '')">
    <div class="flex flex-wrap gap-1 border-b border-slate-200" role="tablist">
      <button
        v-for="item in items"
        :key="item.value"
        type="button"
        role="tab"
        :aria-selected="modelValue === item.value ? 'true' : 'false'"
        :class="cn(
            'inline-flex items-center gap-2 rounded-t-md px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 hover:text-slate-900',
            modelValue === item.value
              ? 'border border-slate-200 border-b-white bg-white text-blue-700'
              : 'border border-transparent'
          )"
        @click="modelValue = item.value"
      >
        <AppIcon v-if="item.icon" :name="item.icon" class="h-4 w-4" />
        {{ item.label }}
      </button>
    </div>
    <div class="pt-3">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { cn } from "@/lib/utils";

defineOptions({ inheritAttrs: false });

const modelValue = defineModel({ type: [String, Number], default:"" });

defineProps({
  items: { type: Array, default: () => [] },
});
</script>

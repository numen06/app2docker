<template>
  <form :class="cn('grid gap-4', props.class)" v-bind="delegatedAttrs" @submit="onSubmit">
    <slot />
  </form>
</template>

<script setup>
import { computed, useAttrs } from "vue";
import { cn } from "@/lib/utils";

const props = defineProps({
  class: { type: [String, Array, Object], default: "" },
});

const emit = defineEmits(["submit"]);

const attrs = useAttrs();

const delegatedAttrs = computed(() => {
  const { class: _c, onSubmit: _o, ...rest } = attrs;
  return rest;
});

function onSubmit(ev) {
  emit("submit", ev);
}
</script>

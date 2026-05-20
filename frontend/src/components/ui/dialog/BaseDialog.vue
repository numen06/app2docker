<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto p-3 sm:p-4"
      role="dialog"
      aria-modal="true"
    >
      <div
        class="absolute inset-0 bg-black/50"
        aria-hidden="true"
        @click="$emit('update:modelValue', false)"
      />
      <slot />
    </div>
  </Teleport>
</template>

<script setup>
import { onUnmounted, watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

function onKeydown(e) {
  if (e.key === "Escape" && props.modelValue) {
    emit("update:modelValue", false);
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) window.addEventListener("keydown", onKeydown);
    else window.removeEventListener("keydown", onKeydown);
  },
  { immediate: true }
);

onUnmounted(() => window.removeEventListener("keydown", onKeydown));
</script>

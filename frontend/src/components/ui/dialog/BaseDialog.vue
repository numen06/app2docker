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

let bodyScrollLockCount = 0;
let savedBodyOverflow = "";
let savedBodyPaddingRight = "";

function lockBodyScroll() {
  if (typeof document === "undefined") return;
  if (bodyScrollLockCount === 0) {
    savedBodyOverflow = document.body.style.overflow;
    savedBodyPaddingRight = document.body.style.paddingRight;
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }
  }
  bodyScrollLockCount += 1;
}

function unlockBodyScroll() {
  if (typeof document === "undefined") return;
  bodyScrollLockCount = Math.max(0, bodyScrollLockCount - 1);
  if (bodyScrollLockCount === 0) {
    document.body.style.overflow = savedBodyOverflow;
    document.body.style.paddingRight = savedBodyPaddingRight;
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      lockBodyScroll();
      window.addEventListener("keydown", onKeydown);
    } else {
      unlockBodyScroll();
      window.removeEventListener("keydown", onKeydown);
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (props.modelValue) unlockBodyScroll();
  window.removeEventListener("keydown", onKeydown);
});
</script>

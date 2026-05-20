<template>
  <div class="steps-indicator" :class="className">
    <p
      v-if="showMobileHint"
      class="steps-mobile-hint mb-2 text-center text-sm text-slate-500 md:hidden"
    >
      步骤 {{ currentStep }} / {{ steps.length }}
    </p>
    <div class="steps-indicator__scroll">
      <div class="steps-indicator__grid" :style="gridStyle">
        <template v-for="(step, index) in steps" :key="step.num">
          <div
            class="step-item"
            :style="{ gridColumn: index * 2 + 1, gridRow: 1 }"
            :class="{
              active: currentStep === step.num,
              completed: currentStep > step.num,
              disabled: !allowJumpAhead && currentStep < step.num,
            }"
            @click="onStepClick(step.num)"
          >
            <div class="step-number">{{ step.num }}</div>
          </div>
          <div
            v-if="index < steps.length - 1"
            class="step-connector"
            :style="{ gridColumn: index * 2 + 2, gridRow: 1 }"
            :class="{ completed: currentStep > step.num }"
          ></div>
          <div
            class="step-label-col"
            :style="{ gridColumn: index * 2 + 1, gridRow: 2 }"
            :class="{
              active: currentStep === step.num,
              completed: currentStep > step.num,
              disabled: !allowJumpAhead && currentStep < step.num,
            }"
          >
            <span class="step-label">{{ step.label }}</span>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import "@/styles/steps-indicator.css";

const props = defineProps({
  steps: {
    type: Array,
    required: true,
    // [{ num: 1, label: '...' }, ...]
  },
  currentStep: {
    type: Number,
    required: true,
  },
  /** 允许点击未到达的步骤 */
  allowJumpAhead: {
    type: Boolean,
    default: false,
  },
  showMobileHint: {
    type: Boolean,
    default: true,
  },
  className: {
    type: String,
    default: "mb-4",
  },
  /** 桌面端步骤列之间的连接线宽度 */
  connectorWidth: {
    type: String,
    default: "3.75rem",
  },
  mobileConnectorWidth: {
    type: String,
    default: "1.25rem",
  },
});

const emit = defineEmits(["update:currentStep", "step-click"]);

const gridStyle = computed(() => {
  const parts = [];
  for (let i = 0; i < props.steps.length; i++) {
    parts.push("minmax(5rem, 1fr)");
    if (i < props.steps.length - 1) {
      parts.push(props.connectorWidth);
    }
  }
  return {
    gridTemplateColumns: parts.join(" "),
  };
});

function onStepClick(num) {
  if (!props.allowJumpAhead && num > props.currentStep) return;
  emit("update:currentStep", num);
  emit("step-click", num);
}
</script>

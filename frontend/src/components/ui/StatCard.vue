<template>
  <Card
    :class="cn(
        'h-full border-l-4 transition hover:-translate-y-0.5 hover:shadow-md',
        accentBorder[accent] || accentBorder.blue
      )"
  >
    <CardContent class="p-4">
      <div class="flex items-center gap-3">
        <div
          :class="cn(
              'flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-white',
              accentBg[accent] || accentBg.blue
            )"
        >
          <AppIcon :name="icon" class="text-lg" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-sm text-slate-500">{{ title }}</p>
          <p class="text-2xl font-semibold tracking-tight text-slate-900">{{ displayValue }}</p>
        </div>
      </div>
      <div v-if="$slots.footer" class="mt-3 border-t border-slate-100 pt-3">
        <slot name="footer" />
      </div>
    </CardContent>
  </Card>
</template>

<script setup>
import { computed } from "vue";
import { cn } from "@/lib/utils";
import Card from "@/components/ui/card/Card.vue";
import CardContent from "@/components/ui/card/CardContent.vue";

const props = defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], default: 0 },
  icon: { type: String, required: true },
  accent: {
    type: String,
    default:"blue",
    validator: (v) =>
      ["blue","sky","green","amber","red","slate","dark"].includes(v),
  },
});

const displayValue = computed(() =>
  props.value === null || props.value === undefined ? 0 : props.value
);

const accentBorder = {
  blue:"border-l-blue-600",
  sky:"border-l-sky-500",
  green:"border-l-green-600",
  amber:"border-l-amber-500",
  red:"border-l-red-600",
  slate:"border-l-slate-500",
  dark:"border-l-slate-800",
};

const accentBg = {
  blue:"bg-blue-600",
  sky:"bg-sky-500",
  green:"bg-green-600",
  amber:"bg-amber-500",
  red:"bg-red-600",
  slate:"bg-slate-500",
  dark:"bg-slate-800",
};
</script>

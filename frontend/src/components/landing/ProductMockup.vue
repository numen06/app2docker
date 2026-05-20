<template>
  <div
    :class="[
      'overflow-hidden rounded-lg border border-slate-200 bg-white shadow-md shadow-slate-200/50',
      compact ? 'text-[10px]' : 'text-xs',
    ]"
    role="img"
    :aria-label="label || '产品界面预览'"
  >
    <div
      class="flex items-center gap-2 border-b border-slate-200 bg-slate-100 px-2 py-1.5 sm:px-3 sm:py-2"
    >
      <div class="flex gap-1">
        <span class="h-2 w-2 rounded-full bg-red-400/90 sm:h-2.5 sm:w-2.5"></span>
        <span class="h-2 w-2 rounded-full bg-amber-400/90 sm:h-2.5 sm:w-2.5"></span>
        <span class="h-2 w-2 rounded-full bg-emerald-400/90 sm:h-2.5 sm:w-2.5"></span>
      </div>
      <div
        class="min-w-0 flex-1 truncate rounded-md bg-white px-2 py-0.5 text-[9px] text-slate-500 sm:text-[10px]"
      >
        app2docker.local{{ urlPath }}
      </div>
    </div>

    <img
      :src="imageSrc"
      :alt="label || 'App2Docker 界面截图'"
      :width="imageWidth"
      :height="imageHeight"
      class="block w-full bg-slate-50 object-cover object-top-left"
      :class="compact ? 'aspect-video max-h-[140px]' : 'aspect-video'"
      loading="lazy"
      decoding="async"
    />

    <p
      v-if="label && !compact"
      class="border-t border-slate-100 bg-slate-50 px-2 py-1 text-center text-[10px] text-slate-500 sm:px-3"
    >
      {{ label }}
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  variant: {
    type: String,
    default: "dashboard",
    validator: (v) => ["dashboard", "pipeline", "team", "deploy"].includes(v),
  },
  label: {
    type: String,
    default: "",
  },
  compact: {
    type: Boolean,
    default: false,
  },
});

const urlPaths = {
  dashboard: "/app/dashboard",
  pipeline: "/app/pipeline",
  team: "/app/team",
  deploy: "/app/deploy",
};

const imageMeta = {
  dashboard: { src: "/landing/dashboard.webp", width: 840, height: 472 },
  pipeline: { src: "/landing/pipeline.webp", width: 480, height: 270 },
  team: { src: "/landing/team.webp", width: 480, height: 270 },
  deploy: { src: "/landing/deploy.webp", width: 480, height: 270 },
};

const urlPath = computed(() => urlPaths[props.variant] ?? "/app");

const imageSrc = computed(() => imageMeta[props.variant]?.src ?? imageMeta.dashboard.src);
const imageWidth = computed(() => imageMeta[props.variant]?.width ?? 840);
const imageHeight = computed(() => imageMeta[props.variant]?.height ?? 472);
</script>

<template>
  <div
    :class="[
      'overflow-hidden rounded-lg border border-slate-200 bg-white shadow-md shadow-slate-200/50',
      compact ? 'text-[10px]' : 'text-xs',
    ]"
    role="img"
    :aria-label="label || '产品界面预览'"
  >
    <div class="flex items-center gap-2 border-b border-slate-200 bg-slate-100 px-2 py-1.5 sm:px-3 sm:py-2">
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

    <div :class="['flex bg-slate-50', compact ? 'min-h-[120px]' : 'min-h-[200px] sm:min-h-[240px]']">
      <aside
        :class="[
          'shrink-0 border-r border-slate-200 bg-slate-800',
          compact ? 'w-10 p-1.5' : 'w-12 p-2 sm:w-14 sm:p-2.5',
        ]"
      >
        <div class="mb-2 h-1.5 w-6 rounded bg-slate-600"></div>
        <div
          v-for="n in 5"
          :key="n"
          :class="[
            'mb-1 rounded',
            n === 1 ? 'bg-blue-500/80' : 'bg-slate-600/60',
            compact ? 'h-1 w-full' : 'h-1.5 w-full sm:h-2',
          ]"
        ></div>
      </aside>

      <div class="min-w-0 flex-1 p-2 sm:p-3">
        <div class="mb-2 flex items-center justify-between gap-2">
          <div class="h-2 w-16 rounded bg-slate-300 sm:h-2.5 sm:w-24"></div>
          <div v-if="variant === 'deploy'" class="h-2 w-8 rounded bg-emerald-400/70 sm:w-10"></div>
        </div>

        <template v-if="variant === 'dashboard'">
          <div class="mb-2 grid grid-cols-3 gap-1 sm:gap-1.5">
            <div v-for="c in 3" :key="c" class="rounded border border-slate-200 bg-white p-1.5 sm:p-2">
              <div class="h-1 w-6 rounded bg-slate-300"></div>
              <div class="mt-1 h-3 w-full rounded bg-blue-100"></div>
            </div>
          </div>
          <div class="rounded border border-slate-200 bg-white p-2">
            <div class="mb-1.5 h-1.5 w-20 rounded bg-slate-300"></div>
            <div class="space-y-1">
              <div v-for="r in 4" :key="r" class="flex gap-1">
                <div class="h-1.5 flex-1 rounded bg-slate-100"></div>
                <div class="h-1.5 w-6 rounded bg-slate-200"></div>
              </div>
            </div>
          </div>
        </template>

        <template v-else-if="variant === 'pipeline'">
          <div class="mb-2 flex gap-1">
            <div
              v-for="s in 4"
              :key="s"
              :class="['h-1.5 flex-1 rounded', s <= 3 ? 'bg-blue-400/70' : 'bg-slate-200']"
            ></div>
          </div>
          <div class="space-y-1 rounded border border-slate-200 bg-white p-1.5">
            <div v-for="row in 3" :key="row" class="flex items-center gap-1.5">
              <div
                :class="[
                  'h-2 w-2 shrink-0 rounded-full',
                  row === 1 ? 'bg-emerald-400' : row === 2 ? 'bg-amber-400' : 'bg-slate-300',
                ]"
              ></div>
              <div class="h-1.5 flex-1 rounded bg-slate-100"></div>
              <div class="h-1.5 w-8 rounded bg-slate-200"></div>
            </div>
          </div>
          <div class="mt-1.5 rounded bg-slate-800/90 p-1 font-mono">
            <div class="h-0.5 w-full rounded bg-emerald-500/50"></div>
            <div class="mt-0.5 h-0.5 w-3/4 rounded bg-slate-600"></div>
          </div>
        </template>

        <template v-else-if="variant === 'team'">
          <div class="space-y-1">
            <div
              v-for="m in 3"
              :key="m"
              class="flex items-center gap-1.5 rounded border border-slate-200 bg-white p-1"
            >
              <div class="h-3 w-3 shrink-0 rounded-full bg-slate-300"></div>
              <div class="h-1 flex-1 rounded bg-slate-200"></div>
              <div :class="['h-1.5 w-6 rounded', m === 1 ? 'bg-blue-200' : 'bg-slate-100']"></div>
            </div>
          </div>
        </template>

        <template v-else-if="variant === 'deploy'">
          <div class="space-y-1">
            <div
              v-for="t in 3"
              :key="t"
              class="flex items-center gap-1 rounded border border-slate-200 bg-white p-1"
            >
              <div
                :class="[
                  'h-1.5 w-1.5 shrink-0 rounded-full',
                  t === 1 ? 'bg-emerald-400' : t === 2 ? 'bg-blue-400' : 'bg-slate-300',
                ]"
              ></div>
              <div class="h-1 flex-1 rounded bg-slate-100"></div>
              <div class="h-1 w-5 rounded bg-slate-200"></div>
            </div>
          </div>
          <div class="mt-1.5 grid grid-cols-2 gap-1">
            <div class="rounded border border-dashed border-slate-300 bg-slate-100/80 p-1.5">
              <div class="h-1 w-8 rounded bg-slate-300"></div>
            </div>
            <div class="rounded border border-slate-200 bg-white p-1.5">
              <div class="h-1 w-6 rounded bg-blue-200"></div>
            </div>
          </div>
        </template>
      </div>
    </div>

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
  pipeline: "/app/pipelines",
  team: "/app/team",
  deploy: "/app/deploy",
};

const urlPath = computed(() => urlPaths[props.variant] ?? "/app");
</script>

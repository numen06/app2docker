<template>
  <div
    v-if="open"
    class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"
    @click.self="close"
  >
    <div
      class="relative z-10 mx-auto flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl"
      @click.stop
    >
      <div class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3">
        <h5 class="mb-0 text-base font-semibold">
          <i class="fas fa-history mr-1"></i>
          历史构建
          <span v-if="pipeline" class="ml-1 text-sm font-normal text-slate-500">
            {{ pipeline.name }}
          </span>
        </h5>
        <button
          type="button"
          class="rounded-md p-2 text-slate-500 hover:bg-slate-100"
          @click="close"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto p-4">
        <PipelineHistoryTab v-if="pipeline" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, provide } from "vue";
import PipelineHistoryTab from "@/components/pipeline/detail/PipelineHistoryTab.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";

const props = defineProps({
  open: { type: Boolean, default: false },
  pipeline: { type: Object, default: null },
  viewTaskLogs: { type: Function, required: true },
});

const emit = defineEmits(["update:open"]);

const pipelineRef = computed(() => props.pipeline);

provide(PIPELINE_DETAIL_KEY, {
  pipeline: pipelineRef,
  loading: computed(() => false),
  error: computed(() => ""),
  refresh: () => {},
  setTab: () => {},
  viewTaskLogs: props.viewTaskLogs,
  viewingLogs: computed(() => false),
});

function close() {
  emit("update:open", false);
}
</script>

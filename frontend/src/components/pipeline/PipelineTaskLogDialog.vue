<template>
  <div
    v-if="logs.showLogModal.value"
    class="fixed inset-0 z-[2000] flex items-center justify-center overflow-y-auto bg-black/50 p-4"
    @click.self="logs.closeLogModal()"
  >
    <div
      class="relative z-10 mx-auto w-full max-w-5xl"
      style="max-width: 90%"
      @click.stop
    >
      <div
        class="relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl"
      >
        <div
          class="flex shrink-0 items-center justify-between border-b border-slate-200 px-4 py-3"
          :class="logs.getLogStatusHeaderClass(logs.selectedTask.value?.status)"
        >
          <h5 class="modal-title mb-0">
            <i :class="logs.getLogStatusIcon(logs.selectedTask.value?.status)"></i>
            任务日志 - {{ logs.selectedTask.value?.image || '未知' }}:{{ logs.selectedTask.value?.tag || 'latest' }}
            <span v-if="logs.isLogTaskRunning.value" class="badge bg-primary ml-2">
              <span class="fas fa-spinner fa-spin mr-1" style="width: 0.7rem; height: 0.7rem"></span>
              运行中
            </span>
          </h5>
          <button type="button" class="rounded-md p-2 text-slate-500 hover:bg-slate-100" @click="logs.closeLogModal()">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="min-h-0 flex-1 overflow-y-auto" style="display: flex; flex-direction: column; max-height: 80vh">
          <div v-if="logs.selectedTask.value" class="border-b border-slate-200 p-3">
            <small class="text-slate-500">
              任务ID: <code>{{ logs.selectedTask.value.task_id?.substring(0, 8) || '未知' }}</code>
            </small>
          </div>
          <div style="flex: 1; overflow: hidden; display: flex; flex-direction: column">
            <div class="flex flex-wrap gap-1 border-b border-slate-200 p-2">
              <Button type="button" variant="outline" size="sm" :disabled="logs.refreshingLogs.value" @click="logs.refreshLogs()">
                <i class="fas fa-sync-alt" :class="{ 'fa-spin': logs.refreshingLogs.value }"></i> 刷新
              </Button>
              <Button type="button" variant="outline" size="sm" @click="logs.toggleAutoScroll()">
                {{ logs.autoScroll.value ? '暂停自动滚动' : '启用自动滚动' }}
              </Button>
              <Button type="button" variant="outline" size="sm" @click="logs.copyLogs()">复制日志</Button>
            </div>
            <pre
              ref="logContainerEl"
              class="mb-0 flex-1 overflow-y-auto bg-dark p-3 font-mono text-light"
              style="font-size: 0.85rem; white-space: pre-wrap; min-height: 200px"
            >{{ logs.taskLogs.value || '暂无日志' }}</pre>
          </div>
        </div>
        <div class="flex shrink-0 justify-end gap-2 border-t border-slate-200 bg-slate-50 px-4 py-3">
          <Button type="button" variant="outline" size="sm" @click="logs.closeLogModal()">关闭</Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue';
import Button from '@/components/ui/button/Button.vue';

const props = defineProps({ logs: { type: Object, required: true } });
const logContainerEl = ref(null);

onMounted(() => {
  if (props.logs.logContainer) props.logs.logContainer.value = logContainerEl.value;
});
watch(logContainerEl, (el) => {
  if (props.logs.logContainer) props.logs.logContainer.value = el;
});
</script>

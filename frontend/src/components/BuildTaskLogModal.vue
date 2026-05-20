<template>
  <TaskLogModal
    v-model="open"
    :task="task"
    @task-status-updated="onTaskStatusUpdated"
  />
</template>

<script setup>
import { computed } from "vue";
import TaskLogModal from "@/components/TaskLogModal.vue";

const props = defineProps({
  controller: { type: Object, required: true },
});

const emit = defineEmits(["task-status-updated"]);

const open = computed({
  get: () => props.controller.showLogModal.value,
  set: (v) => {
    if (!v) props.controller.closeLogModal();
  },
});

const task = computed(() => props.controller.selectedTask.value);

function onTaskStatusUpdated(status) {
  props.controller.handleTaskStatusUpdated(status);
  emit("task-status-updated", status);
}
</script>

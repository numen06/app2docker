<template>
  <FormDialog
    :model-value="modelValue"
    :title="dialogTitle"
    icon="fa-user-shield"
    size="md"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <ResourceMemberPermission
      :resource-type="resourceType"
      :resource-id="resourceId"
      :team-id="teamId"
    />
    <template #footer>
      <Button variant="outline" size="sm" type="button" @click="$emit('update:modelValue', false)">
        关闭
      </Button>
    </template>
  </FormDialog>
</template>

<script setup>
import { computed } from "vue";
import FormDialog from "@/components/ui/dialog/FormDialog.vue";
import Button from "@/components/ui/button/Button.vue";
import ResourceMemberPermission from "@/components/team/ResourceMemberPermission.vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  resourceType: {
    type: String,
    required: true,
    validator: (v) =>
      ["pipeline", "git_source", "agent_host", "deploy_config"].includes(v),
  },
  resourceId: { type: String, default: "" },
  teamId: { type: String, default: "" },
  resourceName: { type: String, default: "" },
});

defineEmits(["update:modelValue"]);

const typeLabels = {
  pipeline: "流水线",
  git_source: "数据源",
  agent_host: "主机",
  deploy_config: "部署配置",
};

const dialogTitle = computed(() => {
  const label = typeLabels[props.resourceType] || "资源";
  const name = props.resourceName?.trim();
  return name ? `成员授权 · ${label}：${name}` : `成员授权 · ${label}`;
});
</script>

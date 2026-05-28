<template>
  <div class="pipeline-permission-tab">
    <p class="mb-3 text-sm text-slate-600">
      管理团队成员对此流水线的访问权限。
    </p>
    <Button size="sm" @click="permissionDialogOpen = true">
      <AppIcon  name="user-shield" class="mr-1" /> 配置成员授权
    </Button>
    <ResourceMemberPermissionDialog
      v-model="permissionDialogOpen"
      resource-type="pipeline"
      :resource-id="pipeline?.pipeline_id"
      :team-id="teamStore.activeTeamId"
      :resource-name="pipeline?.name || ''"
    />
  </div>
</template>

<script setup>
import { computed, inject, ref } from "vue";
import Button from "@/components/ui/button/Button.vue";
import ResourceMemberPermissionDialog from "@/components/team/ResourceMemberPermissionDialog.vue";
import { PIPELINE_DETAIL_KEY } from "@/composables/pipelineDetailContext";
import { useTeamStore } from "@/stores/team";

const detail = inject(PIPELINE_DETAIL_KEY);
const teamStore = useTeamStore();
const permissionDialogOpen = ref(false);

const pipeline = computed(() => detail.pipeline.value);
</script>

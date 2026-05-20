<template>
  <div class="pipeline-editor-page max-w-5xl">
    <div class="mb-4 flex flex-wrap items-center gap-3">
      <Button type="button" variant="outline" size="sm" @click="goBack">
        <i class="fas fa-arrow-left mr-1"></i> 返回列表
      </Button>
      <p v-if="pageLoading" class="mb-0 text-sm text-slate-500">
        <i class="fas fa-spinner fa-spin mr-1"></i> 加载中…
      </p>
    </div>

    <PipelineFormEditor v-if="!pageLoading" />

    <div
      v-if="!pageLoading"
      class="sticky bottom-0 z-10 mt-6 flex justify-end gap-2 border-t border-slate-200 bg-white py-4"
    >
      <Button type="button" variant="outline" size="sm" :disabled="saving" @click="goBack">
        取消
      </Button>
      <Button type="button" size="sm" :disabled="saving" @click="onSave">
        <span v-if="saving" class="fas fa-spinner fa-spin mr-1"></span>
        <i v-else class="fas fa-save mr-1"></i>
        {{ saving ? "保存中…" : "保存" }}
      </Button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, provide, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import Button from "@/components/ui/button/Button.vue";
import PipelineFormEditor from "@/components/pipeline/PipelineFormEditor.vue";
import { usePipelineEditor } from "@/composables/usePipelineEditor";

const route = useRoute();
const router = useRouter();
const pageLoading = ref(true);

const isEdit = computed(() => route.name === "pipeline-edit");

const editor = usePipelineEditor({
  onSaved: () => {
    router.push("/app/pipeline");
  },
});

provide("pipelineEditor", editor);

const { saving, initCreateForm, loadPipelineForEdit } = editor;

function goBack() {
  router.push("/app/pipeline");
}

async function onSave() {
  await editor.savePipeline();
}

onMounted(async () => {
  pageLoading.value = true;
  if (isEdit.value) {
    const id = String(route.params.pipelineId || "");
    if (!id) {
      router.replace("/app/pipeline");
      return;
    }
    const ok = await loadPipelineForEdit(id);
    if (!ok) {
      router.replace("/app/pipeline");
      return;
    }
  } else {
    initCreateForm();
  }
  pageLoading.value = false;
});
</script>
